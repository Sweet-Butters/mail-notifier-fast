"""Cloud Run FastAPI — multi-account version."""

from __future__ import annotations

import base64
import html
import json
import os

from fastapi import FastAPI, HTTPException, Request
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

import bot_handler
import state
from classify import RateLimitError, classify
from i18n import t

import requests

app = FastAPI()

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])
WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _send_telegram(text: str) -> None:
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=10,
    )


def _gmail_service_for(account: str):
    """계정별 OAuth token으로 Gmail service 생성."""
    token_dict = state.load_token(account)
    if not token_dict:
        raise RuntimeError(f"No token for {account}")
    creds = Credentials.from_authorized_user_info(token_dict, GMAIL_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleAuthRequest())
        # refreshed token 저장
        state.save_token(account, json.loads(creds.to_json()))
    return build("gmail", "v1", credentials=creds)


def _format_alert(account: str, meta: dict, reasoning: str) -> str:
    label = bot_handler._account_label(account)  # "[email] " or ""
    subject = html.escape(meta["subject"])
    sender = html.escape(meta["from"])
    snippet = html.escape(meta["snippet"][:300])
    reason = html.escape(reasoning)
    email = bot_handler.extract_email(meta["from"])
    judgment = t("alert_judgment", reason=reason)
    block_hint = (
        f"\n\n<i>{t('alert_block_hint')}</i> <code>/block @{account} {email}</code>"
        if email else ""
    )
    return (
        f"🔔 <b>{label}{subject}</b>\n"
        f"From: {sender}\n"
        f"<i>{judgment}</i>\n\n"
        f"{snippet}"
        f"{block_hint}"
    )


@app.get("/")
def health():
    return {"status": "ok", "version": "fast-2.0-multi", "accounts": len(state.list_accounts())}


@app.post("/renew-watch/{secret}")
def renew_watch(secret: str):
    """모든 등록 계정의 Gmail watch를 갱신."""
    if WEBHOOK_SECRET and secret != WEBHOOK_SECRET:
        raise HTTPException(403, "invalid secret")

    project_id = os.environ.get("GCP_PROJECT_ID", "")
    topic = os.environ.get("PUBSUB_TOPIC", "gmail-notifications-fast")
    if not project_id:
        _send_telegram("❌ <b>Watch renewal failed</b>\nGCP_PROJECT_ID env missing")
        raise HTTPException(500, "GCP_PROJECT_ID env missing")

    results = {}
    for account in state.list_accounts():
        try:
            svc = _gmail_service_for(account)
            r = svc.users().watch(userId="me", body={
                "topicName": f"projects/{project_id}/topics/{topic}",
                "labelIds": ["INBOX"],
            }).execute()
            results[account] = {"ok": True, "historyId": r["historyId"]}
        except Exception as e:
            err = str(e)[:200]
            results[account] = {"ok": False, "error": err}
            _send_telegram(
                f"❌ <b>Gmail watch 갱신 실패: {account}</b>\n\n<code>{err}</code>"
            )

    return {"accounts": results}


@app.post("/telegram/{secret}")
async def telegram_webhook(secret: str, request: Request):
    if WEBHOOK_SECRET and secret != WEBHOOK_SECRET:
        raise HTTPException(403, "invalid secret")
    update = await request.json()
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return {"ok": True}
    chat_id = msg.get("chat", {}).get("id")
    if chat_id != TELEGRAM_CHAT_ID:
        return {"ok": True}
    text = msg.get("text", "").strip()
    try:
        reply = bot_handler.handle(text)
    except Exception as e:
        reply = f"⚠️ Error: <code>{html.escape(str(e)[:300])}</code>"
    if reply:
        _send_telegram(reply)
    return {"ok": True}


@app.post("/pubsub")
async def pubsub_push(request: Request):
    """Pub/Sub message → emailAddress로 계정 식별 → 해당 계정 처리."""
    body = await request.json()
    msg = body.get("message", {})
    data_b64 = msg.get("data", "")
    if not data_b64:
        return {"ok": True}

    payload = json.loads(base64.b64decode(data_b64).decode("utf-8"))
    email_address = payload.get("emailAddress", "")
    new_history_id = str(payload.get("historyId", ""))

    if not email_address or not new_history_id:
        return {"ok": True, "error": "missing fields"}

    if email_address not in state.list_accounts():
        # Pub/Sub이 등록 안 된 계정 메시지를 보내는 경우 (예: 등록 해제 후 잔여)
        return {"ok": True, "ignored": True, "account": email_address}

    last = state.load_history_id(email_address)
    if not last:
        state.save_history_id(email_address, new_history_id)
        return {"ok": True, "baseline": new_history_id, "account": email_address}

    if new_history_id == last:
        return {"ok": True, "no_change": True, "account": email_address}

    try:
        service = _gmail_service_for(email_address)
        history_resp = service.users().history().list(
            userId="me",
            startHistoryId=last,
            historyTypes=["messageAdded"],
        ).execute()
    except Exception as e:
        state.save_history_id(email_address, new_history_id)
        return {"ok": False, "error": "history_fetch_failed", "detail": str(e)[:200]}

    new_msg_ids = []
    for h in history_resp.get("history", []):
        for m in h.get("messagesAdded", []):
            mid = m.get("message", {}).get("id")
            labels = m.get("message", {}).get("labelIds", [])
            if mid and "INBOX" in labels:
                new_msg_ids.append(mid)

    blocked = set(state.load_blocked(email_address))
    notified = 0
    for mid in new_msg_ids:
        full = service.users().messages().get(
            userId="me", id=mid, format="metadata",
            metadataHeaders=["Subject", "From"],
        ).execute()
        headers = {h["name"]: h["value"] for h in full["payload"]["headers"]}
        meta = {
            "id": mid,
            "subject": headers.get("Subject", "(제목 없음)"),
            "from": headers.get("From", ""),
            "snippet": full.get("snippet", ""),
        }

        sender_email = bot_handler.extract_email(meta["from"])
        if sender_email and sender_email in blocked:
            continue

        try:
            result = classify(email_address, meta["from"], meta["subject"], meta["snippet"])
        except RateLimitError:
            q = state.load_quota()
            if not q.get("alerted"):
                _send_telegram(t("quota_alert", status=_quota_text()))
                state.mark_quota_alerted()
            break

        if result["notify"]:
            _send_telegram(_format_alert(email_address, meta, result["reasoning"]))
            notified += 1

    state.save_history_id(email_address, new_history_id)
    return {"ok": True, "account": email_address, "processed": len(new_msg_ids), "notified": notified}


def _quota_text() -> str:
    d = state.load_quota()
    used = d.get("calls", 0)
    remaining = state.quota_remaining()
    pct = min(100, (used / state.DAILY_LIMIT) * 100) if state.DAILY_LIMIT else 0
    bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
    return t("quota_message", bar=bar, pct=pct, used=used, limit=state.DAILY_LIMIT, remaining=remaining)

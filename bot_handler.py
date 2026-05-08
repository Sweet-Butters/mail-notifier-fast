"""Telegram bot 명령 — multi-account + alias + smart parse."""

from __future__ import annotations

import os
import re

import state
from i18n import t, get_lang, set_lang


# 'account'와 'acc' 둘 다 허용
KNOWN_COMMANDS = {
    "add", "remove", "watch", "unwatch", "block", "unblock",
    "list", "status", "help", "start", "quota", "lang",
    "account", "acc",
}


def normalize(text: str) -> str | None:
    text = text.strip()
    if not text:
        return None
    parts = text.split(maxsplit=1)
    cmd = parts[0].lstrip("/").lower()
    arg = parts[1] if len(parts) > 1 else ""
    if cmd not in KNOWN_COMMANDS:
        return None
    # acc → account 정규화
    if cmd == "acc":
        cmd = "account"
    return f"/{cmd}" + (f" {arg}" if arg else "")


def _extract_email(text: str) -> str | None:
    """텍스트 안에서 @ 포함된 첫 토큰을 이메일로 추출 (smart 파싱)."""
    for token in text.split():
        if "@" in token and " " not in token:
            t = token.strip().lower()
            if "." in t.split("@")[1]:  # 도메인 부분에 . 있어야 진짜 이메일
                return t
    return None


def _parse_account_arg(rest: str) -> tuple[str | None, str]:
    """'@email_or_alias rest' → (resolved_full_email, rest). '@' 없으면 (None, rest)."""
    rest = rest.strip()
    if not rest.startswith("@"):
        return None, rest
    parts = rest[1:].split(maxsplit=1)
    short = parts[0]
    remainder = parts[1] if len(parts) > 1 else ""
    return state.resolve_alias(short), remainder


def _resolve_account(specified: str | None) -> tuple[str | None, str | None]:
    if specified:
        if specified not in state.list_accounts():
            return None, t("account_unknown", account=specified)
        return specified, None
    default = state.default_account()
    if not default:
        return None, t("no_accounts_registered")
    return default, None


def _account_label(account: str) -> str:
    if state.is_multi_account():
        # 별칭이 있으면 별칭 우선 표시
        aliases_inv = {v: k for k, v in state.load_aliases().items()}
        short = aliases_inv.get(account, account)
        return f"[{short}] "
    return ""


def handle(text: str) -> str | None:
    normalized = normalize(text)
    if not normalized:
        return None

    text = normalized.strip()

    if text in ("/help", "/start"):
        return t("help")

    if text == "/quota":
        return _quota_status_text()

    if text == "/lang":
        return t("lang_current", lang=get_lang())

    if text.startswith("/lang "):
        new_lang = text[6:].strip().lower()
        if set_lang(new_lang):
            return t("lang_changed", lang=new_lang)
        return t("lang_invalid", lang=new_lang)

    # ───────── account 관리 ─────────
    if text == "/account" or text == "/account list":
        accounts = state.list_accounts()
        aliases = state.load_aliases()
        aliases_inv = {v: k for k, v in aliases.items()}
        if not accounts:
            return t("account_list_empty")
        out = [t("account_list_header", count=len(accounts))]
        default = state.default_account()
        for a in accounts:
            marker = " ⭐" if a == default else ""
            alias = aliases_inv.get(a, "")
            alias_str = f" (@{alias})" if alias else ""
            out.append(f"  • <code>{a}</code>{alias_str}{marker}")
        return "\n".join(out)

    if text.startswith("/account add"):
        # smart 파싱: 인자 안에서 @ 토큰 자동 추출
        arg = text[len("/account add"):].strip()
        email = _extract_email(arg)
        if not email:
            return t("add_invalid_with_example", input=arg or "(empty)")
        if email in state.list_accounts():
            return t("account_already_added", account=email)
        return _start_oauth_for(email)

    if text.startswith("/account confirm"):
        redirect_url = text[len("/account confirm"):].strip()
        return _complete_oauth(redirect_url)

    if text.startswith("/account remove"):
        arg = text[len("/account remove"):].strip()
        email = _extract_email(arg) or arg
        if email not in state.list_accounts():
            return t("account_unknown", account=email)
        # 알리어스도 같이 삭제
        aliases = state.load_aliases()
        aliases = {k: v for k, v in aliases.items() if v != email}
        state.save_aliases(aliases)
        state.remove_account(email)
        return t("account_removed", account=email)

    # account copy @src @dst [parts...]
    if text.startswith("/account copy"):
        arg = text[len("/account copy"):].strip()
        # 파싱: @src @dst [senders|watching|blocked ...]
        tokens = arg.split()
        if len(tokens) < 2 or not tokens[0].startswith("@") or not tokens[1].startswith("@"):
            return t("copy_usage")
        src = state.resolve_alias(tokens[0][1:])
        dst = state.resolve_alias(tokens[1][1:])
        parts = tokens[2:] if len(tokens) > 2 else None
        # 검증
        if src not in state.list_accounts():
            return t("account_unknown", account=src)
        if dst not in state.list_accounts():
            return t("account_unknown", account=dst)
        if src == dst:
            return t("copy_same_account")
        # 잘못된 파트
        if parts:
            invalid = [p for p in parts if p not in state.VALID_PARTS]
            if invalid:
                return t("copy_invalid_parts", parts=", ".join(invalid))
        # 복사 실행
        result = state.copy_config(src, dst, parts)
        summary = "\n".join(f"  • {p}: {n}개" for p, n in result.items())
        return t("copy_success", src=src, dst=dst, summary=summary)

    # account alias <short> = <email>
    if text.startswith("/account alias"):
        arg = text[len("/account alias"):].strip()
        # `remove SHORT` 처리
        if arg.startswith("remove "):
            short = arg[len("remove "):].strip()
            aliases = state.load_aliases()
            if short in aliases:
                del aliases[short]
                state.save_aliases(aliases)
                return t("alias_removed", short=short)
            return t("alias_not_found", short=short)
        # `SHORT = EMAIL` 또는 `SHORT EMAIL`
        if "=" in arg:
            short, _, email_raw = arg.partition("=")
        else:
            parts = arg.split(maxsplit=1)
            if len(parts) < 2:
                return t("alias_usage")
            short, email_raw = parts
        short = short.strip().lower()
        email = _extract_email(email_raw) or email_raw.strip().lower()
        if not short or "@" in short:
            return t("alias_short_invalid", short=short)
        if email not in state.list_accounts():
            return t("account_unknown", account=email)
        aliases = state.load_aliases()
        aliases[short] = email
        state.save_aliases(aliases)
        return t("alias_set", short=short, email=email)

    # ───────── /list ─────────
    if text == "/list" or text.startswith("/list "):
        rest = text[len("/list"):].strip()
        if rest.startswith("@"):
            email, _ = _parse_account_arg(rest)
            account, err = _resolve_account(email)
            if err:
                return err
            return _list_one_account(account)
        accounts = state.list_accounts()
        if not accounts:
            return t("no_accounts_registered")
        return "\n\n".join(_list_one_account(a) for a in accounts)

    # ───────── /status ─────────
    if text == "/status":
        accounts = state.list_accounts()
        return t(
            "status_message",
            accounts=len(accounts),
            quota=state.load_quota().get("calls", 0),
            limit=state.DAILY_LIMIT,
            lang=get_lang(),
        )

    return _account_scoped_command(text)


def _list_one_account(account: str) -> str:
    emails = state.load_senders(account)
    watch = state.load_watching(account)
    blocked = state.load_blocked(account)
    out = [t("list_header_account", account=account)]
    out.append(t("list_senders", count=len(emails)))
    out.extend(f"  • <code>{e}</code>" for e in emails) if emails else out.append(t("list_empty"))
    out.append("")
    out.append(t("list_watching", count=len(watch)))
    out.extend(f"  #{i+1}. {w}" for i, w in enumerate(watch)) if watch else out.append(t("list_empty"))
    out.append("")
    out.append(t("list_blocked", count=len(blocked)))
    out.extend(f"  • <code>{e}</code>" for e in blocked) if blocked else out.append(t("list_empty"))
    return "\n".join(out)


def _account_scoped_command(text: str) -> str:
    parts = text.split(maxsplit=1)
    cmd = parts[0]
    rest = parts[1] if len(parts) > 1 else ""

    account_specified, payload = _parse_account_arg(rest)
    account, err = _resolve_account(account_specified)
    if err:
        return err

    label = _account_label(account)

    if cmd == "/add":
        email = _extract_email(payload) or payload.strip().lower()
        if "@" not in email or " " in email:
            return t("add_invalid", email=email)
        emails = state.load_senders(account)
        if email in emails:
            return label + t("add_exists", email=email)
        emails.append(email)
        state.save_senders(account, emails)
        return label + t("add_success", email=email, count=len(emails))

    if cmd == "/remove":
        email = _extract_email(payload) or payload.strip().lower()
        emails = state.load_senders(account)
        if email not in emails:
            return label + t("remove_not_found", email=email)
        emails.remove(email)
        state.save_senders(account, emails)
        return label + t("remove_success", email=email, count=len(emails))

    if cmd == "/watch":
        desc = payload.strip()
        if not desc:
            return t("watch_usage")
        if len(desc) > 300:
            return t("watch_too_long", length=len(desc), max_length=300)
        watch = state.load_watching(account)
        if desc in watch:
            return label + t("watch_exists", desc=desc)
        watch.append(desc)
        state.save_watching(account, watch)
        return label + t("watch_added", n=len(watch), desc=desc, count=len(watch))

    if cmd == "/unwatch":
        arg = payload.strip()
        watch = state.load_watching(account)
        if not watch:
            return label + t("unwatch_empty")
        if arg.isdigit():
            idx = int(arg) - 1
            if 0 <= idx < len(watch):
                removed = watch.pop(idx)
                state.save_watching(account, watch)
                return label + t("unwatch_by_index", n=idx + 1, desc=removed, count=len(watch))
            return label + t("unwatch_index_invalid", n=arg, max=len(watch))
        if arg in watch:
            watch.remove(arg)
            state.save_watching(account, watch)
            return label + t("unwatch_by_text", desc=arg, count=len(watch))
        return label + t("unwatch_not_found")

    if cmd == "/block":
        email = _extract_email(payload) or payload.strip().lower()
        if "@" not in email or " " in email:
            return t("block_invalid", email=email)
        blocked = state.load_blocked(account)
        if email in blocked:
            return label + t("block_exists", email=email)
        blocked.append(email)
        state.save_blocked(account, blocked)
        return label + t("block_added", email=email, count=len(blocked))

    if cmd == "/unblock":
        email = _extract_email(payload) or payload.strip().lower()
        blocked = state.load_blocked(account)
        if email not in blocked:
            return label + t("unblock_not_found", email=email)
        blocked.remove(email)
        state.save_blocked(account, blocked)
        return label + t("unblock_success", email=email, count=len(blocked))

    return t("unknown_command", text=text)


def _start_oauth_for(email: str) -> str:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    from google_auth_oauthlib.flow import InstalledAppFlow

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    cred_path = "/tmp/credentials_fast.json"

    cred_json = os.environ.get("GOOGLE_OAUTH_CLIENT_JSON")
    if not cred_json:
        return t("oauth_misconfigured")
    with open(cred_path, "w") as f:
        f.write(cred_json)

    flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
    flow.redirect_uri = "http://localhost:8080/"
    auth_url, oauth_state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        login_hint=email,
        include_granted_scopes="true",
    )
    state.save_onboarding(email, oauth_state, flow.code_verifier)

    project_id = os.environ.get("GCP_PROJECT_ID", "your-project-id")
    return t("oauth_start", email=email, url=auth_url, project_id=project_id)


def _complete_oauth(redirect_url: str) -> str:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    from urllib.parse import parse_qs, urlparse
    from google_auth_oauthlib.flow import InstalledAppFlow

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    cred_path = "/tmp/credentials_fast.json"

    parsed = urlparse(redirect_url)
    qs = parse_qs(parsed.query)
    received_state = qs.get("state", [""])[0]

    # 모든 onboarding state를 검사해서 매칭되는 계정 찾기
    target_account = None
    target_meta = None
    from google.cloud import storage
    bucket = storage.Client().bucket(os.environ.get("GCS_BUCKET", ""))
    for blob in bucket.list_blobs(prefix="onboarding/"):
        import json as _json
        data = _json.loads(blob.download_as_text())
        if data.get("state") == received_state:
            target_account = blob.name.replace("onboarding/", "").replace(".json", "")
            target_meta = data
            break

    if not target_account or not target_meta:
        return t("oauth_state_not_found")

    cred_json = os.environ.get("GOOGLE_OAUTH_CLIENT_JSON")
    with open(cred_path, "w") as f:
        f.write(cred_json)

    flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES, state=received_state)
    flow.redirect_uri = "http://localhost:8080/"
    flow.code_verifier = target_meta["code_verifier"]
    flow.fetch_token(authorization_response=redirect_url)

    creds = flow.credentials
    import json as _json
    state.save_token(target_account, _json.loads(creds.to_json()))
    state.add_account(target_account)
    state.clear_onboarding(target_account)

    project_id = os.environ.get("GCP_PROJECT_ID", "")
    topic = os.environ.get("PUBSUB_TOPIC", "gmail-notifications-fast")
    from googleapiclient.discovery import build
    service = build("gmail", "v1", credentials=creds)
    result = service.users().watch(userId="me", body={
        "topicName": f"projects/{project_id}/topics/{topic}",
        "labelIds": ["INBOX"],
    }).execute()
    state.save_history_id(target_account, result["historyId"])

    return t("oauth_completed", account=target_account)


def _quota_status_text() -> str:
    d = state.load_quota()
    used = d.get("calls", 0)
    remaining = state.quota_remaining()
    pct = min(100, (used / state.DAILY_LIMIT) * 100) if state.DAILY_LIMIT else 0
    bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
    return t("quota_message", bar=bar, pct=pct, used=used, limit=state.DAILY_LIMIT, remaining=remaining)


def extract_email(sender_full: str) -> str:
    m = re.search(r"<([^>]+@[^>]+)>", sender_full)
    if m:
        return m.group(1).strip().lower()
    if "@" in sender_full:
        return sender_full.strip().lower()
    return ""

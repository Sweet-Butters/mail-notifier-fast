"""Per-account GCS state — multi-account support.

GCS path scheme:
  accounts.txt                                # registered email list (newline-separated)
  accounts/<email>/senders.txt                # important senders (per account)
  accounts/<email>/watching.txt               # watch list (per account)
  accounts/<email>/blocked.txt                # blocked senders (per account)
  accounts/<email>/token.json                 # OAuth token (per account)
  accounts/<email>/last_history_id.txt        # Gmail watch state (per account)
  language.txt                                # GLOBAL — UI language
  quota.json                                  # GLOBAL — Gemini quota (shared)
  onboarding/<email>.json                     # transient OAuth state (state + code_verifier)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from functools import lru_cache

from google.cloud import storage

BUCKET_NAME = os.environ.get("GCS_BUCKET", "mail-fast-state")
DAILY_LIMIT = 250


@lru_cache(maxsize=1)
def _bucket():
    return storage.Client().bucket(BUCKET_NAME)


def _read(path: str, default: str = "") -> str:
    blob = _bucket().blob(path)
    if not blob.exists():
        return default
    return blob.download_as_text()


def _write(path: str, content: str) -> None:
    _bucket().blob(path).upload_from_string(content)


def _delete(path: str) -> None:
    blob = _bucket().blob(path)
    if blob.exists():
        blob.delete()


def _delete_prefix(prefix: str) -> None:
    """Delete all blobs under a prefix."""
    for blob in _bucket().list_blobs(prefix=prefix):
        blob.delete()


# ───────────────────────── account registry ─────────────────────────


def list_accounts() -> list[str]:
    raw = _read("accounts.txt")
    return [line.strip() for line in raw.splitlines() if line.strip() and not line.startswith("#")]


def add_account(email: str) -> None:
    accounts = list_accounts()
    if email in accounts:
        return
    accounts.append(email)
    _write("accounts.txt", "\n".join(accounts) + "\n")


def remove_account(email: str) -> None:
    accounts = [a for a in list_accounts() if a != email]
    _write("accounts.txt", "\n".join(accounts) + "\n" if accounts else "")
    _delete_prefix(f"accounts/{email}/")


def default_account() -> str | None:
    accounts = list_accounts()
    return accounts[0] if accounts else None


def is_multi_account() -> bool:
    return len(list_accounts()) >= 2


# ───────────────────────── senders ─────────────────────────


def load_senders(account: str) -> list[str]:
    raw = _read(f"accounts/{account}/senders.txt")
    return [
        line.split("#")[0].strip()
        for line in raw.splitlines()
        if line.strip() and not line.strip().startswith("#") and "@" in line.split("#")[0]
    ]


def save_senders(account: str, emails: list[str]) -> None:
    header = f"# Important senders for {account}\n"
    _write(f"accounts/{account}/senders.txt", header + "\n".join(emails) + "\n")


# ───────────────────────── watching ─────────────────────────


def load_watching(account: str) -> list[str]:
    raw = _read(f"accounts/{account}/watching.txt")
    return [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def save_watching(account: str, items: list[str]) -> None:
    header = f"# Watch list for {account}\n"
    _write(f"accounts/{account}/watching.txt", header + "\n".join(items) + "\n")


# ───────────────────────── blocked ─────────────────────────


def load_blocked(account: str) -> list[str]:
    raw = _read(f"accounts/{account}/blocked.txt")
    return [
        line.split("#")[0].strip().lower()
        for line in raw.splitlines()
        if line.strip() and not line.strip().startswith("#") and "@" in line.split("#")[0]
    ]


def save_blocked(account: str, emails: list[str]) -> None:
    header = f"# Blocked senders for {account}\n"
    _write(f"accounts/{account}/blocked.txt", header + "\n".join(emails) + "\n")


# ───────────────────────── per-account token ─────────────────────────


def load_token(account: str) -> dict | None:
    raw = _read(f"accounts/{account}/token.json")
    if not raw:
        return None
    return json.loads(raw)


def save_token(account: str, token_dict: dict) -> None:
    _write(f"accounts/{account}/token.json", json.dumps(token_dict, ensure_ascii=False, indent=2))


# ───────────────────────── per-account history id ─────────────────────────


def load_history_id(account: str) -> str:
    return _read(f"accounts/{account}/last_history_id.txt").strip()


def save_history_id(account: str, history_id: str) -> None:
    _write(f"accounts/{account}/last_history_id.txt", str(history_id))


# ───────────────────────── global language ─────────────────────────


def load_language() -> str:
    return _read("language.txt", os.environ.get("DEFAULT_LANG", "ko")).strip() or "ko"


def save_language(lang: str) -> None:
    _write("language.txt", lang + "\n")


# ───────────────────────── global quota ─────────────────────────


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def load_quota() -> dict:
    raw = _read("quota.json")
    if not raw:
        return {"date": _today(), "calls": 0, "alerted": False}
    try:
        d = json.loads(raw)
    except Exception:
        return {"date": _today(), "calls": 0, "alerted": False}
    if d.get("date") != _today():
        return {"date": _today(), "calls": 0, "alerted": False}
    d.setdefault("alerted", False)
    return d


def save_quota(d: dict) -> None:
    _write("quota.json", json.dumps(d, ensure_ascii=False, indent=2))


def increment_quota() -> dict:
    d = load_quota()
    d["calls"] = d.get("calls", 0) + 1
    save_quota(d)
    return d


def mark_quota_alerted() -> None:
    d = load_quota()
    d["alerted"] = True
    save_quota(d)


def quota_remaining() -> int:
    return max(0, DAILY_LIMIT - load_quota().get("calls", 0))


# ───────────────────────── account aliases ─────────────────────────


def load_aliases() -> dict[str, str]:
    """{short: full_email} 매핑."""
    raw = _read("aliases.json")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def save_aliases(aliases: dict[str, str]) -> None:
    _write("aliases.json", json.dumps(aliases, ensure_ascii=False, indent=2))


def resolve_alias(short_or_full: str) -> str:
    """별칭이면 풀 이메일로, 풀 이메일이면 그대로 반환."""
    aliases = load_aliases()
    return aliases.get(short_or_full, short_or_full)


# ───────────────────────── account config copy ─────────────────────────

VALID_PARTS = {"senders", "watching", "blocked"}


def copy_config(src: str, dst: str, parts: list[str] | None = None) -> dict:
    """src 계정의 senders/watching/blocked를 dst로 복사.

    parts=None이면 모두 복사. ['watch'] / ['senders'] 등으로 일부만 가능.
    Returns: {part: count_copied}.
    """
    targets = parts if parts else list(VALID_PARTS)
    result = {}
    for part in targets:
        if part not in VALID_PARTS:
            continue
        src_blob = f"accounts/{src}/{part}.txt"
        dst_blob = f"accounts/{dst}/{part}.txt"
        content = _read(src_blob)
        if content:
            _write(dst_blob, content)
            # 복사된 항목 수 (주석 제외)
            count = sum(
                1 for line in content.splitlines()
                if line.strip() and not line.strip().startswith("#")
            )
            result[part] = count
        else:
            result[part] = 0
    return result


# ───────────────────────── OAuth onboarding ─────────────────────────


def save_onboarding(email: str, state: str, code_verifier: str) -> None:
    """OAuth state/code_verifier 임시 저장 (account add → account confirm 사이)."""
    _write(
        f"onboarding/{email}.json",
        json.dumps({"state": state, "code_verifier": code_verifier, "ts": _today()}),
    )


def load_onboarding(email: str) -> dict | None:
    raw = _read(f"onboarding/{email}.json")
    if not raw:
        return None
    return json.loads(raw)


def clear_onboarding(email: str) -> None:
    _delete(f"onboarding/{email}.json")

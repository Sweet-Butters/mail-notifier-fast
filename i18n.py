"""i18n strings — multi-account version."""

from __future__ import annotations

import os

DEFAULT_LANG = os.environ.get("DEFAULT_LANG", "ko")
SUPPORTED_LANGS = {"ko", "en"}


def get_lang() -> str:
    from state import load_language
    lang = load_language().strip().lower()
    return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


def set_lang(lang: str) -> bool:
    if lang not in SUPPORTED_LANGS:
        return False
    from state import save_language
    save_language(lang)
    return True


def t(key: str, **kwargs) -> str:
    lang = get_lang()
    template = STRINGS.get(lang, {}).get(key)
    if template is None:
        template = STRINGS[DEFAULT_LANG].get(key, f"[missing:{key}]")
    return template.format(**kwargs) if kwargs else template


STRINGS: dict[str, dict[str, str]] = {
    "ko": {
        "help": """🤖 <b>명령어 (Multi-account)</b>

<b>📬 계정 관리 (account 또는 acc)</b>
<code>acc</code> — 등록 메일 목록
<code>acc add foo@gmail.com</code> — 새 메일 등록 (OAuth 시작)
<code>acc confirm URL</code> — OAuth 완료
<code>acc remove EMAIL</code> — 등록 해제
<code>acc alias y = me@example.com</code> — 짧은 별칭 (이후 <code>@y</code> 사용)
<code>acc alias remove y</code>
<code>acc copy @src @dst</code> — 설정 복사 (senders/watching/blocked 모두)
<code>acc copy @src @dst watching</code> — 일부만 복사

<b>👤 발신자</b>
<code>add foo@bar.com</code>  /  <code>add @y foo@bar.com</code>
<code>remove foo@bar.com</code>

<b>👀 기다리는 메일</b>
<code>watch 회사X 인턴 합격 안내</code>  /  <code>watch @y 키워드</code>
<code>unwatch 1</code>

<b>🚫 차단</b>
<code>block spam@x.com</code>  /  <code>unblock spam@x.com</code>

<b>📊 조회</b>
<code>list</code> — 전체 / <code>list @y</code> — 특정 계정
<code>status</code> / <code>quota</code> / <code>lang ko|en</code> / <code>help</code>

<i>💡 계정 1개면 @account 생략 OK</i>
<i>💡 별칭 등록 후엔 <code>@y</code>처럼 짧게</i>
<i>💡 명령어 안에 @ 포함된 텍스트 = 자동으로 이메일 추출 (오타 허용)</i>
⚡ 실시간 (1~5초)""",

        "list_header_account": "📋 <b>{account}</b>",
        "list_senders": "<b>👤 중요 발신자 ({count})</b>",
        "list_watching": "<b>👀 기다리는 메일 ({count})</b>",
        "list_blocked": "<b>🚫 차단 발신자 ({count})</b>",
        "list_empty": "  <i>(없음)</i>",

        "status_message": (
            "📊 <b>시스템 상태</b> (⚡ Fast / Multi-account)\n"
            "  등록된 메일: <b>{accounts}개</b>\n"
            "  Gemini 사용: <b>{quota}/{limit}</b>회\n"
            "  분류 모델: Gemini 2.5 Flash\n"
            "  언어: <b>{lang}</b>\n"
            "  cron: 실시간 webhook + Pub/Sub"
        ),

        "lang_current": "🌐 현재 언어: <b>{lang}</b>",
        "lang_invalid": "⚠️ 지원 안 함: <code>{lang}</code> (ko/en)",
        "lang_changed": "✅ 언어 변경: <b>{lang}</b>",

        "add_invalid": "⚠️ 이메일 형식 아님: <code>{email}</code>",
        "add_exists": "ℹ️ 이미 등록된 발신자: <code>{email}</code>",
        "add_success": "✅ 발신자 추가: <code>{email}</code> (총 {count}개)",
        "remove_not_found": "ℹ️ 등록 안 됨: <code>{email}</code>",
        "remove_success": "🗑 발신자 제거: <code>{email}</code> (총 {count}개)",

        "watch_usage": "⚠️ 사용법: <code>watch DESC</code> 또는 <code>watch @account DESC</code>",
        "watch_too_long": "⚠️ 너무 깁니다 ({length}자, 최대 {max_length}자)",
        "watch_exists": "ℹ️ 이미 등록됨: <i>{desc}</i>",
        "watch_added": "✅ #{n} 추가: <i>{desc}</i> (총 {count}개)",
        "unwatch_empty": "ℹ️ 등록된 항목 없음.",
        "unwatch_index_invalid": "⚠️ #{n} 없음 (현재 1~{max})",
        "unwatch_by_index": "🗑 #{n} 제거: <i>{desc}</i> (총 {count}개)",
        "unwatch_by_text": "🗑 제거: <i>{desc}</i> (총 {count}개)",
        "unwatch_not_found": "ℹ️ 매칭 항목 없음. <code>list</code>로 #번호 확인하세요.",

        "block_invalid": "⚠️ 이메일 형식 아님: <code>{email}</code>",
        "block_exists": "ℹ️ 이미 차단됨: <code>{email}</code>",
        "block_added": "🚫 차단: <code>{email}</code> (총 {count}개)",
        "unblock_not_found": "ℹ️ 차단 목록에 없음: <code>{email}</code>",
        "unblock_success": "♻️ 차단 해제: <code>{email}</code> (총 {count}개)",

        "quota_message": (
            "📈 <b>Gemini 사용량 (UTC 오늘)</b>\n"
            "  <code>{bar}</code>  {pct:.0f}%\n"
            "  사용: <b>{used}</b>회 / 한도: ~<b>{limit}</b>회\n"
            "  남은 추정: <b>{remaining}</b>회"
        ),
        "quota_alert": "⚠️ <b>Gemini 한도 도달</b>\n\n{status}",

        "alert_judgment": "판단: {reason}",
        "alert_block_hint": "잘못 잡혔으면 발신자 차단:",

        "unknown_command": "❓ 모르는 명령: <code>{text}</code>\n<code>help</code> 보세요",

        # 계정 관리 신규
        "add_invalid_with_example": (
            "⚠️ 이메일을 못 찾았어요. 입력: <code>{input}</code>\n\n"
            "올바른 사용법:\n<code>acc add foo@gmail.com</code>"
        ),
        "alias_usage": "⚠️ 사용법: <code>acc alias SHORT = EMAIL</code>\n예: <code>acc alias y = me@example.com</code>",
        "alias_short_invalid": "⚠️ 별칭은 영문/숫자 (이메일 X). 받음: <code>{short}</code>",
        "alias_set": "✅ 별칭 등록: <code>@{short}</code> → <code>{email}</code>",
        "copy_usage": "⚠️ 사용법: <code>acc copy @src @dst [parts]</code>\n예: <code>acc copy @y @g</code>\n부분: <code>senders</code> / <code>watching</code> / <code>blocked</code>",
        "copy_same_account": "⚠️ 같은 계정끼리 복사 불가",
        "copy_invalid_parts": "⚠️ 잘못된 파트: <code>{parts}</code>\n사용 가능: senders / watching / blocked",
        "copy_success": "✅ 설정 복사 완료\n  <b>{src}</b> → <b>{dst}</b>\n{summary}\n\n<i>대상의 기존 설정은 덮어쓰기 됩니다.</i>",
        "alias_removed": "🗑 별칭 제거: <code>@{short}</code>",
        "alias_not_found": "ℹ️ 별칭 없음: <code>@{short}</code>",
        "no_accounts_registered": (
            "ℹ️ 등록된 메일 계정이 없습니다.\n\n"
            "추가하려면: <code>acc add foo@gmail.com</code>"
        ),
        "account_unknown": "⚠️ 등록 안 된 메일: <code>{account}</code>\n<code>account list</code>로 확인하세요.",
        "account_already_added": "ℹ️ 이미 등록됨: <code>{account}</code>",
        "account_list_header": "📬 <b>등록된 메일 ({count}개)</b>",
        "account_list_empty": (
            "📬 <b>등록된 메일</b>\n  <i>(없음)</i>\n\n"
            "추가: <code>account add your@gmail.com</code>"
        ),
        "account_removed": "🗑 메일 등록 해제됨: <code>{account}</code>\n(state·token·watch 모두 삭제)",

        "oauth_misconfigured": "⚠️ OAuth credential 환경변수 미설정 (GOOGLE_OAUTH_CLIENT_JSON)",
        "oauth_start": (
            "🔐 <b>{email} OAuth 등록</b>\n\n"
            "<b>0단계 (선행 필수)</b>: 이 이메일이 GCP Test users에 등록돼있어야 합니다. 안 돼있으면 OAuth 시 '403 access_denied' 발생.\n\n"
            "👉 Test users 추가 페이지 (한 번만):\n"
            "https://console.cloud.google.com/auth/audience?project={project_id}\n"
            "→ 'Test users' 섹션 → '+ 사용자 추가' → <code>{email}</code> 입력 → 저장\n\n"
            "<b>1단계</b>: 시크릿 모드 브라우저로 아래 OAuth URL 열기\n"
            "<b>2단계</b>: <b>{email}</b>로 로그인 → 동의\n"
            "<b>3단계</b>: '연결 안 됨' 페이지의 주소창 URL 통째 복사\n"
            "<b>4단계</b>: <code>acc confirm &lt;복사한URL&gt;</code> 보내기\n\n"
            "🔗 OAuth URL:\n<code>{url}</code>"
        ),
        "oauth_state_not_found": (
            "⚠️ OAuth state가 만료/없음. <code>account add EMAIL</code> 다시 시작하세요."
        ),
        "oauth_completed": (
            "✅ <b>{account} 등록 완료</b>\n\n"
            "Gmail watch 활성화됨. 이 계정으로 오는 메일은 즉시 알림됩니다.\n\n"
            "사용 예: <code>add @{account} hr@somecorp.com</code>"
        ),

        "classifier_lang_directive": "reasoning은 한국어 한 문장으로 작성하세요.",
    },

    "en": {
        "help": """🤖 <b>Commands (Multi-account)</b>

<b>📬 Mail Account Management (account or acc)</b>
<code>acc</code> — registered mail accounts
<code>acc add EMAIL</code> — register new mail (OAuth)
<code>acc confirm URL</code> — complete OAuth
<code>acc remove EMAIL</code> — unregister
<code>acc alias y = me@example.com</code> — short alias (use as <code>@y</code>)
<code>acc copy @src @dst</code> — copy config (senders/watching/blocked)
<code>acc copy @src @dst watching</code> — copy specific part

<b>👤 Important Senders (per-account)</b>
<code>add EMAIL</code> or <code>add @account EMAIL</code>
<code>remove EMAIL</code>

<b>👀 Watch List (per-account)</b>
<code>watch DESC</code> or <code>watch @account DESC</code>
<code>unwatch N</code>

<b>🚫 Blocked (per-account)</b>
<code>block EMAIL</code>
<code>unblock EMAIL</code>

<b>📊 Info</b>
<code>list</code> — all accounts / <code>list @account</code> — single
<code>status</code>, <code>quota</code>
<code>lang ko|en</code>
<code>help</code>

<i>💡 With 1 account, @account is optional (default used)</i>
<i>💡 With 2+ accounts, alerts get [email] prefix</i>
⚡ <b>Real-time</b> (1-5s)""",

        "list_header_account": "📋 <b>{account}</b>",
        "list_senders": "<b>👤 Senders ({count})</b>",
        "list_watching": "<b>👀 Watch ({count})</b>",
        "list_blocked": "<b>🚫 Blocked ({count})</b>",
        "list_empty": "  <i>(none)</i>",

        "status_message": (
            "📊 <b>System Status</b> (⚡ Fast / Multi-account)\n"
            "  Registered accounts: <b>{accounts}</b>\n"
            "  Gemini today: <b>{quota}/{limit}</b>\n"
            "  Classifier: Gemini 2.5 Flash\n"
            "  Language: <b>{lang}</b>"
        ),

        "lang_current": "🌐 Current: <b>{lang}</b>",
        "lang_invalid": "⚠️ Unsupported: <code>{lang}</code>",
        "lang_changed": "✅ Language: <b>{lang}</b>",

        "add_invalid": "⚠️ Not a valid email: <code>{email}</code>",
        "add_exists": "ℹ️ Already registered: <code>{email}</code>",
        "add_success": "✅ Added: <code>{email}</code> (total {count})",
        "remove_not_found": "ℹ️ Not found: <code>{email}</code>",
        "remove_success": "🗑 Removed: <code>{email}</code> (total {count})",

        "watch_usage": "⚠️ Usage: <code>watch DESC</code> or <code>watch @account DESC</code>",
        "watch_too_long": "⚠️ Too long ({length}, max {max_length})",
        "watch_exists": "ℹ️ Exists: <i>{desc}</i>",
        "watch_added": "✅ #{n}: <i>{desc}</i> (total {count})",
        "unwatch_empty": "ℹ️ No items.",
        "unwatch_index_invalid": "⚠️ #{n} not found (1~{max})",
        "unwatch_by_index": "🗑 #{n}: <i>{desc}</i> (total {count})",
        "unwatch_by_text": "🗑 <i>{desc}</i> (total {count})",
        "unwatch_not_found": "ℹ️ No match. Use <code>list</code> for #index.",

        "block_invalid": "⚠️ Not a valid email: <code>{email}</code>",
        "block_exists": "ℹ️ Already blocked: <code>{email}</code>",
        "block_added": "🚫 Blocked: <code>{email}</code> (total {count})",
        "unblock_not_found": "ℹ️ Not in block list: <code>{email}</code>",
        "unblock_success": "♻️ Unblocked: <code>{email}</code> (total {count})",

        "quota_message": (
            "📈 <b>Gemini Usage (today UTC)</b>\n"
            "  <code>{bar}</code>  {pct:.0f}%\n"
            "  Used: <b>{used}</b> / Limit: ~<b>{limit}</b>\n"
            "  Remaining: <b>{remaining}</b>"
        ),
        "quota_alert": "⚠️ <b>Gemini quota reached</b>\n\n{status}",

        "alert_judgment": "Why: {reason}",
        "alert_block_hint": "If wrong, block sender:",

        "unknown_command": "❓ Unknown: <code>{text}</code>\n<code>help</code>",

        "add_invalid_with_example": (
            "⚠️ Couldn't find an email in: <code>{input}</code>\n\n"
            "Usage:\n<code>acc add foo@gmail.com</code>"
        ),
        "alias_usage": "⚠️ Usage: <code>acc alias SHORT = EMAIL</code>\nex: <code>acc alias y = me@example.com</code>",
        "alias_short_invalid": "⚠️ Alias must be alphanumeric (no @). Got: <code>{short}</code>",
        "alias_set": "✅ Alias set: <code>@{short}</code> → <code>{email}</code>",
        "copy_usage": "⚠️ Usage: <code>acc copy @src @dst [parts]</code>\nex: <code>acc copy @y @g</code>\nparts: <code>senders</code> / <code>watching</code> / <code>blocked</code>",
        "copy_same_account": "⚠️ Cannot copy to the same account",
        "copy_invalid_parts": "⚠️ Invalid parts: <code>{parts}</code>\nValid: senders / watching / blocked",
        "copy_success": "✅ Config copied\n  <b>{src}</b> → <b>{dst}</b>\n{summary}\n\n<i>Target's existing config was overwritten.</i>",
        "alias_removed": "🗑 Alias removed: <code>@{short}</code>",
        "alias_not_found": "ℹ️ Alias not found: <code>@{short}</code>",
        "no_accounts_registered": (
            "ℹ️ No mail accounts registered.\n\n"
            "Add one: <code>acc add your@gmail.com</code>"
        ),
        "account_unknown": "⚠️ Not registered: <code>{account}</code>",
        "account_already_added": "ℹ️ Already added: <code>{account}</code>",
        "account_list_header": "📬 <b>Registered ({count})</b>",
        "account_list_empty": (
            "📬 <b>Registered accounts</b>\n  <i>(none)</i>\n\n"
            "Add: <code>account add your@gmail.com</code>"
        ),
        "account_removed": "🗑 Removed: <code>{account}</code> (state/token/watch all deleted)",

        "oauth_misconfigured": "⚠️ OAuth credentials not configured",
        "oauth_start": (
            "🔐 <b>OAuth setup for {email}</b>\n\n"
            "<b>Step 0 (required first)</b>: This email must be added to GCP Test users, else OAuth returns '403 access_denied'.\n\n"
            "👉 Add Test user (one-time):\n"
            "https://console.cloud.google.com/auth/audience?project={project_id}\n"
            "→ 'Test users' → '+ Add users' → enter <code>{email}</code> → save\n\n"
            "<b>Step 1</b>: Open the OAuth URL below in INCOGNITO browser\n"
            "<b>Step 2</b>: Sign in as <b>{email}</b> → grant access\n"
            "<b>Step 3</b>: Copy URL from 'site can't be reached' page\n"
            "<b>Step 4</b>: Send <code>acc confirm &lt;pasted_URL&gt;</code>\n\n"
            "🔗 OAuth URL:\n<code>{url}</code>"
        ),
        "oauth_state_not_found": (
            "⚠️ OAuth state expired/missing. Restart with <code>account add EMAIL</code>."
        ),
        "oauth_completed": (
            "✅ <b>{account} registered</b>\n\n"
            "Gmail watch active. Mail to this account will trigger real-time alerts.\n\n"
            "e.g.: <code>add @{account} hr@somecorp.com</code>"
        ),

        "classifier_lang_directive": "Write reasoning as one short English sentence.",
    },
}

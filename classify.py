"""Gemini 분류기 — multi-account version.

senders/watching는 account 별로 따로 로드.
"""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

import state
from i18n import t

load_dotenv()

MODEL = "gemini-2.5-flash"

_client: genai.Client | None = None


class RateLimitError(Exception):
    pass


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def _system_prompt(account: str, senders: list[str], watching: list[str]) -> str:
    senders_block = "\n".join(f"- {s}" for s in senders) if senders else "(없음)"
    watching_block = "\n".join(f"- {w}" for w in watching) if watching else "(없음)"
    lang_directive = t("classifier_lang_directive")
    return f"""당신은 사용자가 놓치면 안 되는 중요한 이메일을 골라내는 분류기입니다.
이 메일은 사용자의 '{account}' 계정으로 도착한 메일입니다.

각 메일에 대해 **알림 보낼지(true) 말지(false)** 결정하고, 이유를 한 문장으로 설명하세요.

📌 <b>알림(notify=true) 기준</b>:
1. 면접 일정·결과 안내 메일
2. 합격/불합격/선정/탈락 통보, 전형 결과, 프로그램 선정(튜터/인턴/장학/공모전 등) 결과, OT/오리엔테이션 안내
3. 아래 <b>중요 발신자 목록</b>에서 온 메일 (이메일 주소 정확 매치):
{senders_block}
4. 아래 <b>기다리는 메일 항목</b>의 키워드가 제목/본문에 등장 (LOOSE 매칭):
{watching_block}

🚫 <b>무시(notify=false) 기준</b>:
- 광고/마케팅/이벤트/모집 광고/리뷰 모집
- 학교/기관 단체 공지 (위 watching 키워드와 매칭되면 알림)
- 뉴스레터·시스템 알림·자동발송·영수증
- 위 알림 기준 4개 중 어느 것에도 해당 안 됨

🎯 <b>reasoning에 무엇이 trigger인지 명시</b>:
- 발신자 매치: "중요 발신자 <email@domain> 매칭"
- 키워드 매치: "기다리는 메일 항목 '<키워드>' 매칭"
- 면접/합격 패턴: "면접 일정 안내 메일 패턴"
- 무시 사유: "광고성 메일", "단체 공지" 등

{lang_directive}

응답은 반드시 다음 JSON 형식으로만 답변하세요 (다른 설명 없이):
{{"notify": <true|false>, "reasoning": "<한 문장 trigger/사유 설명>"}}"""


def classify(account: str, sender: str, subject: str, body: str) -> dict:
    """이메일 한 통을 분류 (계정 컨텍스트 포함)."""
    senders = state.load_senders(account)
    watching = state.load_watching(account)
    user_msg = (
        f"[발신자] {sender}\n"
        f"[제목] {subject}\n"
        f"[본문 일부]\n{body[:1500]}"
    )

    try:
        response = _get_client().models.generate_content(
            model=MODEL,
            contents=user_msg,
            config=types.GenerateContentConfig(
                system_instruction=_system_prompt(account, senders, watching),
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        state.increment_quota()
    except genai_errors.ClientError as e:
        if e.code == 429 or "RESOURCE_EXHAUSTED" in str(e):
            raise RateLimitError(str(e)) from e
        raise

    result = json.loads(response.text)
    if not isinstance(result.get("notify"), bool):
        result = {
            "notify": False,
            "reasoning": f"분류 실패 (받은 응답: {response.text[:100]})",
        }
    result.setdefault("reasoning", "")
    return result

# ⚡ Mail Notifier Fast

> **Gmail 새 메일 도착 즉시 (1~5초) Gemini 분류 → Telegram 알림. 멀티 계정 지원.**
>
> AI-powered Gmail filter that classifies incoming mail and sends only the important ones to Telegram in real-time. Multi-account support: register multiple Gmail addresses under one bot, with per-account watch lists.

![Version](https://img.shields.io/badge/version-2.0--multi-blue)
![Latency](https://img.shields.io/badge/Latency-1~5%20sec-brightgreen)
![Multi-Account](https://img.shields.io/badge/Multi--account-yes-purple)
![i18n](https://img.shields.io/badge/i18n-ko%20%7C%20en-yellow)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-4285F4?logo=google&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

> 🇺🇸 English version: [Sweet-Butters/mail-notifier-fast_eng](https://github.com/Sweet-Butters/mail-notifier-fast_eng)

---

## 🎯 왜 이 프로젝트?

면접 결과·합격 통보·중요 인물 메일을 광고/공지 사이에서 **놓치지 않으려고** 만들었습니다. 단순 필터(키워드 매칭)는 광고에서 "면접" 단어만 쓰면 잡히는 거짓 양성이 너무 많아서, **LLM이 메일 맥락을 이해해서 분류**하도록 설계.

이전에 만들었던 [`mail-notifier`](https://github.com/Sweet-Butters/mail-notifier)(slow version)는 GitHub Actions cron으로 10분마다 폴링했는데, 진짜 합격 메일을 10분 늦게 받는 게 좀 답답했습니다. **이 fast 버전은 1~5초 안에 알림**.

## ⚖️ 이전 버전 (slow) vs 이번 (fast)

| 항목 | [Slow version](https://github.com/Sweet-Butters/mail-notifier) | **Fast version (이 repo)** |
|---|---|---|
| 메일 알림 지연 | 평균 10분 (cron 주기) | **1~5초** (Gmail Pub/Sub push) |
| 봇 명령 응답 | 평균 10분 | **1~3초** (Telegram webhook) |
| 동작 방식 | 폴링 (주기적으로 Gmail 확인) | **이벤트 드리븐** (메일 도착 즉시 push) |
| 멀티 계정 | ❌ (1개 메일만) | ✅ **여러 Gmail 동시 모니터링** |
| 인프라 | GitHub Actions cron | Cloud Run + Pub/Sub + Cloud Storage |
| 진입장벽 | 카드 필요 없음 | **GCP billing 활성화 필수** (무료 한도 안이지만 카드 등록 필요) |
| 운영 비용 | $0 / 월 | **$0 / 월** (Cloud Run · Pub/Sub free tier) |
| 24/7 동작 | ✅ (PC 꺼져있어도 OK) | ✅ |
| 설정 시간 (처음) | ~30분 | ~1시간 |

**한 줄 요약**: slow는 "충분히 동작하는 무료 버전", fast는 "진짜 실시간 + 여러 메일 관리".

## ✨ Features

- ⚡ **실시간 알림** — Gmail Pub/Sub `users.watch`로 메일 도착 즉시 트리거
- 🧠 **AI 분류** — Gemini 2.5 Flash가 발신자/내용/사용자 watch list 기반 알림 여부 판단
- 📬 **멀티 계정** — 한 봇으로 여러 Gmail 동시 관리, 계정별 독립 watch list / blocked list
- 🏷 **계정 별칭** — `@y` 같은 짧은 별칭 등록해서 입력 부담 줄이기
- 🔇 **노이즈 차단** — 학교 공지, 광고, 영수증, 뉴스레터 자동 무시
- 🚫 **1탭 차단** — 알림 메시지의 `/block` 링크 한 번 탭으로 발신자 영구 차단
- 🌐 **i18n** — 한국어 / 영어 봇 UI (`lang ko|en`)
- 🔄 **자동 갱신** — Gmail watch는 7일 만료라 Cloud Scheduler가 매일 자동 재등록
- 📈 **사용량 추적** — Gemini 일일 한도 모니터링, 한도 도달 시 Telegram 알림
- 🛡 **장애 알림** — watch 갱신 실패 시 Telegram에 즉시 알림 (수동 대응 가능)

## 🏗 Architecture

```
[Gmail 새 메일]                         [사용자 봇 명령]
        │                                       │
        ▼                                       ▼
[Gmail.users.watch]              [Telegram webhook]
        │                                       │
        ▼                                       ▼
[Pub/Sub 토픽]                                   │
        │                                       │
        └─────────────┐         ┌────────────────┘
                      ▼         ▼
                ┌───────────────────────┐
                │   Cloud Run (FastAPI) │
                │ /pubsub  /telegram/.. │
                └───────┬───────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
  [Gemini 2.5     [Cloud Storage   [Telegram
   분류기]        per-account state] sendMessage]
                        ▲
                        │
            [Cloud Scheduler 매일 09:00 UTC]
            → /renew-watch (Gmail watch 갱신)
```

## 🛠 Tech Stack

| 영역 | 기술 |
|---|---|
| 언어 | Python 3.12 |
| 웹 프레임워크 | FastAPI + uvicorn |
| LLM | Google Gemini 2.5 Flash (free tier) |
| 메일 인입 | Gmail API `users.watch` (Pub/Sub push) |
| 알림 | Telegram Bot API (webhook) |
| 컴퓨팅 | GCP Cloud Run (서버리스, scale-to-zero) |
| 메시지 큐 | GCP Pub/Sub |
| 상태 저장 | GCP Cloud Storage (per-account) |
| 인증 | OAuth2 Installed App flow (per-account) |
| 자동화 | Cloud Scheduler (watch 갱신) |

## 📁 Project Structure

```
mail_fast/
├── app.py              # FastAPI: /pubsub, /telegram/{secret}, /renew-watch/{secret}, /
├── bot_handler.py      # 봇 명령 디스패처 + 멀티 계정 + 별칭 + smart parse
├── classify.py         # Gemini 분류 (account 컨텍스트 포함)
├── state.py            # Cloud Storage 백엔드 (per-account paths)
├── i18n.py             # 한/영 메시지 (단일 source-of-truth dict)
├── send_telegram.py    # Telegram sendMessage 래퍼
├── Dockerfile          # Cloud Run 컨테이너
├── requirements.txt
├── deploy.sh           # 8단계 자동 배포 스크립트
├── .env.example
├── .gitignore
└── .dockerignore
```

## 🚧 Entry Barriers (진입장벽)

이 프로젝트를 본인 계정으로 돌리려면 다음이 필요합니다.

### 1. GCP billing 활성화 ⚠️ 가장 큰 허들

- Google Cloud 프로젝트 + **billing 계정 연결** (실제로는 free tier 안에서 동작하지만 카드 등록은 필수)
- 일부 학교 계정(`.edu`, `.ac.kr`)은 Google Pay에서 카드 등록이 막혀있을 수 있음 (`OR-KCCSEH-11` 에러)
- 막히면 개인 Google 계정(`@gmail.com`)으로 새 GCP 프로젝트 만들어서 우회 가능 (cross-project pattern)

### 2. OAuth Test users 사전 등록

- 각 Gmail 계정마다 **OAuth consent screen의 Test users**에 추가 필요 (`account add` 전에)
- GCP 콘솔에서 수동 (API로 자동화 불가)
- 봇이 `acc add` 응답에 이 단계 안내 URL 포함

### 3. Telegram bot

- BotFather로 봇 1개 생성 → 토큰
- 본인 chat_id (봇과 메시지 한 번 교환 → `getUpdates`로 추출)

### 4. Gemini API key

- [Google AI Studio](https://aistudio.google.com/apikey)에서 무료 발급
- Gemini 2.5 Flash 무료 한도 안에서 동작 (~250 RPD)

### 5. 시간 투자

- 처음 셋업: **~1시간** (GCP 콘솔 작업 + 코드 배포 + 첫 OAuth)
- 새 메일 추가: ~5분/계정 (Test user 등록 + OAuth flow)

## 🚀 Setup

### 1. Prerequisites

- Python 3.12+ (로컬 테스트용)
- gcloud CLI 인증됨 (billing 활성화된 GCP 계정으로)
- Telegram 봇 + chat_id
- Gemini API key

### 2. GCP — Gmail API + OAuth Client

```
1. https://console.cloud.google.com 새 프로젝트 (예: my-mail-fast)
2. APIs & Services → Library → Gmail API Enable
3. OAuth consent screen → External
   - 앱 이름, 지원 이메일 등 입력
   - Test users에 추적할 Gmail 주소 추가
4. Credentials → + OAuth client ID → Desktop app → JSON 다운로드
5. credentials_fast.json 으로 저장
```

### 3. .env 작성

```bash
cp .env.example .env
# 채우기:
# TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
# TELEGRAM_WEBHOOK_SECRET (random hex, openssl rand -hex 16)
# GEMINI_API_KEY
# GCP_PROJECT_ID, GCS_BUCKET (고유 이름), DEFAULT_LANG=ko
```

### 4. 배포

```bash
bash deploy.sh
```

자동 8단계:
1. APIs 활성화 (Pub/Sub, Cloud Run, Storage 등)
2. GCS 버킷 생성 (per-account state 저장)
3. Pub/Sub 토픽 생성
4. Gmail SA에 publisher 권한 부여
5. Cloud Run 빌드/배포
6. Pub/Sub push subscription 등록
7. Telegram webhook 설정
8. Cloud Scheduler watch 자동 갱신 (매일 09:00 UTC)

### 5. 첫 메일 등록 (폰 봇)

배포 후 폰 Telegram에서:

```
help                              ← 명령어 메뉴 확인
acc add YOUR_GMAIL@gmail.com       ← OAuth flow 시작
                                   봇이 OAuth URL + Test users 추가 안내 전송

# 안내대로 OAuth 동의 → "이 사이트에 연결할 수 없음" 페이지
# 주소창 URL 복사 → 봇으로 보내기:

acc confirm http://localhost:8080/?state=...&code=...
                                   봇이 token 저장 + Gmail watch 등록 + 완료 알림

# 이후 자유롭게:
add hr@somecorp.com            ← 중요 발신자 추가 (계정 1개라 @ 생략 가능)
watch 회사X 인턴 합격 안내              ← 기다리는 메일 키워드
list                              ← 현재 설정 보기
```

## 🤖 Bot Commands

폰 Telegram에서 봇에게 메시지 전송. 슬래시(`/`) 생략 가능.

### 계정 관리
| 명령 | 동작 |
|---|---|
| `acc` | 등록된 메일 목록 |
| `acc add EMAIL` | 새 메일 등록 (OAuth 시작) |
| `acc confirm URL` | OAuth 완료 (redirect URL 붙여넣기) |
| `acc remove EMAIL` | 메일 등록 해제 |
| `acc alias y = me@example.com` | 짧은 별칭 등록 (이후 `@y` 사용) |
| `acc alias remove y` | 별칭 제거 |
| `acc copy @src @dst` | 설정 복사 (senders + watching + blocked) |

### 발신자 / 키워드 / 차단 (계정별)
| 명령 | 동작 |
|---|---|
| `add EMAIL` 또는 `add @account EMAIL` | 중요 발신자 추가 |
| `remove EMAIL` | 발신자 제거 |
| `watch DESC` 또는 `watch @account DESC` | 기다리는 메일 키워드 추가 |
| `unwatch N` | watch 항목 제거 (#번호) |
| `block EMAIL` | 발신자 차단 (분류기 호출 X, 즉시 무시) |
| `unblock EMAIL` | 차단 해제 |

### 조회 / 설정
| 명령 | 동작 |
|---|---|
| `list` 또는 `list @account` | 모든 계정 / 특정 계정 설정 |
| `status` | 시스템 상태 |
| `quota` | Gemini 사용량 (progress bar) |
| `lang ko\|en` | UI 언어 전환 |
| `help` | 명령어 메뉴 |

### Smart 파싱
명령어 안에서 `@`가 포함된 토큰을 자동으로 이메일로 추출:
- `acc add email me@gmail.com` → `me@gmail.com`만 사용 ("email"은 무시)
- 오타에 관대함

## 📊 Cost

| 항목 | 사용량 (일반 사용자) | Free tier | 비용 |
|---|---|---|---|
| Cloud Run | ~수십 요청/일 | 2M 요청/월 | $0 |
| Pub/Sub | ~30 메시지/일 | 10GB/월 | $0 |
| Cloud Storage | <1MB | 5GB | $0 |
| Cloud Scheduler | 1 job, 30 calls/월 | 3 jobs/billing account | $0 |
| Gemini 2.5 Flash | ~30 호출/일 | ~250 RPD 추정 | $0 |
| Gmail API | ~30 호출/일 | 1B quota units/일 | $0 |
| **합계** | | | **$0 / 월** |

⚠️ free tier는 사용량 급증 시 유료 전환됨. budget alert 설정 권장.

## 🔒 Security

- 모든 비밀 정보(`.env`, `credentials_fast.json`, OAuth tokens)는 `.gitignore` 처리, 절대 commit 안 됨
- Cloud Run 환경변수는 GCP 인프라에서 암호화 저장
- Gmail scope는 `gmail.readonly`만 — 메일 수정/삭제/발송 불가
- Cloud Run endpoints는 secret URL path로 보호 (`/telegram/{secret}`, `/renew-watch/{secret}`)
- Telegram bot은 등록된 본인 chat_id에서 온 명령만 처리 (다른 사용자 무시)
- Per-account OAuth tokens는 Cloud Storage에 저장 (계정별 분리, 권한 격리)

## 🚧 Limitations

| 한계 | 영향 / 해결 |
|---|---|
| GCP billing 필수 | 일부 .edu 계정 카드 등록 막힘 — 개인 gmail.com 계정으로 우회 |
| OAuth Test users 수동 등록 | 새 메일 추가 시 GCP 콘솔 한 번 들어가야 함 (API로 자동화 불가) |
| OAuth 앱 검증 안 됨 | "Google에서 확인 안 됨" 경고 → 「고급」 → 「안전하지 않음」 클릭 필요 |
| Gemini free tier 5~10 RPM | 짧은 시간 다수 메일 동시 도착 시 일부 처리 지연 가능 |
| Gmail watch 7일 만료 | Cloud Scheduler가 매일 자동 갱신 (구현됨) |
| 한국 SMS 알림 | GCP Monitoring SMS는 한국 번호 미지원 — Telegram으로 대체 |

## 📝 Implementation Notes

- **분류 schema**: 카테고리 라벨(면접/합격여부/...) 대신 단순 `notify: bool` + `reasoning` 한 문장. 사용자 입장에선 알림 받을지 말지가 핵심, 카테고리 라벨은 노이즈.
- **Watching 매칭**: 키워드 일부 일치만으로도 알림 (loose). 단, 명시적 광고/이벤트 맥락은 `notify=false`.
- **첫 실행 baseline**: 메일 1통만 봐도 history_id 등록 → 이후 신규 메일만 처리. 과거 메일 폭탄 방지.
- **Quota 도달 시**: 부분 진행만 history_id에 기록 → 미처리 메일은 한도 리셋 후 다음 이벤트에서 처리.
- **Per-account routing**: Pub/Sub 메시지의 `emailAddress` 필드로 어느 계정의 메일인지 식별 → 해당 계정의 state/token 사용.

## 📋 License

MIT — 자유롭게 fork/수정 가능. [LICENSE](LICENSE) 참조.

---

<sub>Built by [@Sweet-Butters](https://github.com/Sweet-Butters)</sub>

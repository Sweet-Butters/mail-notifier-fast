#!/usr/bin/env bash
# Cloud Run + Pub/Sub + Gmail watch 자동 배포 스크립트.
#
# 전제: gcloud CLI 인증됨, billing 활성화, .env 채워짐.
# 실행: bash deploy.sh
set -euo pipefail

# .env 로드
if [ ! -f .env ]; then
    echo "❌ .env 없음. .env.example 복사 후 값 채우세요."
    exit 1
fi
set -a
source .env
set +a

# 필수 값 검증
: "${TELEGRAM_TOKEN:?TELEGRAM_TOKEN 누락}"
: "${TELEGRAM_CHAT_ID:?TELEGRAM_CHAT_ID 누락}"
: "${TELEGRAM_WEBHOOK_SECRET:?TELEGRAM_WEBHOOK_SECRET 누락}"
: "${GEMINI_API_KEY:?GEMINI_API_KEY 누락}"
: "${GCP_PROJECT_ID:?GCP_PROJECT_ID 누락}"
: "${GCS_BUCKET:?GCS_BUCKET 누락}"
GCP_REGION="${GCP_REGION:-us-central1}"
PUBSUB_TOPIC="${PUBSUB_TOPIC:-gmail-notifications-fast}"
SERVICE_NAME="mail-notifier-fast"

echo "════════════════════════════════════════"
echo "  Mail Notifier Fast — Cloud Run Deploy"
echo "  Project: $GCP_PROJECT_ID"
echo "  Region:  $GCP_REGION"
echo "  Service: $SERVICE_NAME"
echo "════════════════════════════════════════"
echo ""

gcloud config set project "$GCP_PROJECT_ID" >/dev/null

# 1. API 활성화
echo "[1/8] Enable required APIs..."
gcloud services enable \
    pubsub.googleapis.com \
    cloudfunctions.googleapis.com \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    storage.googleapis.com \
    artifactregistry.googleapis.com \
    gmail.googleapis.com 2>&1 | tail -3

# 2. GCS 버킷
echo "[2/8] Create GCS bucket (state)..."
if ! gcloud storage buckets describe "gs://$GCS_BUCKET" 2>/dev/null; then
    gcloud storage buckets create "gs://$GCS_BUCKET" \
        --location="$GCP_REGION" --uniform-bucket-level-access
fi

# 3. Pub/Sub 토픽
echo "[3/8] Create Pub/Sub topic..."
if ! gcloud pubsub topics describe "$PUBSUB_TOPIC" 2>/dev/null; then
    gcloud pubsub topics create "$PUBSUB_TOPIC"
fi

# 4. Gmail의 service account에 publisher role 부여
echo "[4/8] Grant Gmail service account publisher role..."
gcloud pubsub topics add-iam-policy-binding "$PUBSUB_TOPIC" \
    --member="serviceAccount:gmail-api-push@system.gserviceaccount.com" \
    --role="roles/pubsub.publisher" 2>&1 | tail -3 || true

# 5. Cloud Run 빌드 + 배포
echo "[5/8] Build & deploy Cloud Run..."
cat > /tmp/cloudrun-env.yaml <<EOF
TELEGRAM_TOKEN: "${TELEGRAM_TOKEN}"
TELEGRAM_CHAT_ID: "${TELEGRAM_CHAT_ID}"
TELEGRAM_WEBHOOK_SECRET: "${TELEGRAM_WEBHOOK_SECRET}"
GEMINI_API_KEY: "${GEMINI_API_KEY}"
GCS_BUCKET: "${GCS_BUCKET}"
DEFAULT_LANG: "${DEFAULT_LANG:-en}"
GCP_PROJECT_ID: "${GCP_PROJECT_ID}"
PUBSUB_TOPIC: "${PUBSUB_TOPIC}"
GOOGLE_OAUTH_CLIENT_JSON: |
$(cat credentials_fast.json | sed 's/^/  /')
EOF

gcloud run deploy "$SERVICE_NAME" \
    --source=. \
    --region="$GCP_REGION" \
    --platform=managed \
    --allow-unauthenticated \
    --memory=512Mi \
    --cpu=1 \
    --max-instances=3 \
    --quiet \
    --env-vars-file=/tmp/cloudrun-env.yaml

CLOUD_RUN_URL=$(gcloud run services describe "$SERVICE_NAME" --region="$GCP_REGION" --format='value(status.url)')
echo "  Service URL: $CLOUD_RUN_URL"

# 6. Pub/Sub push subscription
echo "[6/8] Create Pub/Sub push subscription..."
SUBSCRIPTION_NAME="${SERVICE_NAME}-pubsub-sub"
if ! gcloud pubsub subscriptions describe "$SUBSCRIPTION_NAME" 2>/dev/null; then
    gcloud pubsub subscriptions create "$SUBSCRIPTION_NAME" \
        --topic="$PUBSUB_TOPIC" \
        --push-endpoint="${CLOUD_RUN_URL}/pubsub" \
        --ack-deadline=60
fi

# 7. Telegram webhook 등록
echo "[7/8] Register Telegram webhook..."
WEBHOOK_URL="${CLOUD_RUN_URL}/telegram/${TELEGRAM_WEBHOOK_SECRET}"
curl -s "https://api.telegram.org/bot${TELEGRAM_TOKEN}/setWebhook?url=${WEBHOOK_URL}" | python3 -m json.tool | head -5

# 8. Gmail watch 등록 (mail이 도착하면 Pub/Sub로 publish)
echo "[8/8] (Optional) Cloud Scheduler 자동 갱신 등록..."
gcloud scheduler jobs create http mail-notifier-fast-renew \
    --location="$GCP_REGION" \
    --schedule="0 9 * * *" \
    --http-method=POST \
    --uri="${CLOUD_RUN_URL}/renew-watch/${TELEGRAM_WEBHOOK_SECRET}" \
    --description="Daily Gmail watch renewal" 2>&1 | tail -3 || true

echo ""
echo "════════════════════════════════════════"
echo "  ✅ Deploy 완료!"
echo "  Service: $CLOUD_RUN_URL"
echo "  Webhook: $WEBHOOK_URL"
echo ""
echo "  📱 다음 단계 (폰 봇):"
echo "  1. 봇한테 'help' 보내서 동작 확인"
echo "  2. 'acc add YOUR_GMAIL@gmail.com' 으로 첫 메일 등록 (OAuth flow)"
echo "  3. 'acc confirm <redirect URL>' 로 완료"
echo "════════════════════════════════════════"

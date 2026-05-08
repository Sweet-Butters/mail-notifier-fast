FROM python:3.12-slim

WORKDIR /app

# 의존성 캐싱: requirements 먼저 복사
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드
COPY *.py ./

# Cloud Run은 PORT 환경변수를 주입함 (보통 8080)
ENV PORT=8080
EXPOSE 8080

# uvicorn으로 FastAPI 앱 실행
CMD exec uvicorn app:app --host 0.0.0.0 --port ${PORT} --workers 1

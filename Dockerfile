# LangGraph Platform — container image for Cloud Run (or any container host)
#
# Build:  docker build -t langgraph-platform .
# Run:    docker run -p 8080:8080 langgraph-platform
# Deploy: gcloud run deploy langgraph-platform --source . --region australia-southeast1
#
# Runs in MOCK_MODE when OPENAI_API_KEY is unset (safe public demo);
# set OPENAI_API_KEY to enable real GPT-4o-mini responses.

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run injects PORT (default 8080)
ENV PORT=8080
EXPOSE 8080

CMD exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT}

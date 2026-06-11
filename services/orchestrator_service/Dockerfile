# ==============================================================================
# AskHR Orchestrator Service Dockerfile - Deployment Ready
# ==============================================================================
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY core/ /app/core/
COPY config.yaml /app/
COPY services/orchestrator_service/ /app/services/orchestrator_service/

EXPOSE 8081

ENV PYTHONUNBUFFERED=1

CMD ["python", "services/orchestrator_service/main.py"]

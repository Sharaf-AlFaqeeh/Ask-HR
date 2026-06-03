# ==============================================================================
# AskHR Vector DB & Ingestion Service Dockerfile - Deployment Ready
# ==============================================================================
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY core/ /app/core/
COPY config.yaml /app/
COPY services/vector_db_service/ /app/services/vector_db_service/

# By default, run ingestion on startup to ensure db is prepared
CMD ["python", "services/vector_db_service/data_ingestion.py"]

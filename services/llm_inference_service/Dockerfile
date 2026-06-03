# ==============================================================================
# AskHR LLM Inference Service Dockerfile - Deployment Ready
# ==============================================================================
FROM python:3.10-slim as builder

# Install build dependencies for compiling llama-cpp-python
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install dependencies (use virtualenv or direct pip install)
COPY requirements.txt .

# Optional environment variables for CUDA execution (e.g. GPU acceleration)
# ENV FORCE_CMAKE=1
# ENV CMAKE_ARGS="-DLLAMA_CUDA=on"

RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.10-slim

WORKDIR /app

# Copy compiled libraries from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY core/ /app/core/
COPY config.yaml /app/
COPY services/llm_inference_service/ /app/services/llm_inference_service/

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["python", "services/llm_inference_service/server.py"]

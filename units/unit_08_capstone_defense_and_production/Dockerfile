# ==============================================================================
# COSC 2060: Unit 8 Capstone Defense — Multi-Stage Production Dockerfile
# ==============================================================================
# Build & Verify inside GitHub Codespaces:
#   docker build -t apex-logistics-capstone:v1 .
#   docker run --rm apex-logistics-capstone:v1
# ==============================================================================

# Stage 1: Builder & Dependency Compilation
FROM python:3.11-slim AS builder
WORKDIR /app
COPY lab8_starter.py .

# Stage 2: Hardened Production Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app/lab8_starter.py /app/lab8_starter.py
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "lab8_starter.py"]

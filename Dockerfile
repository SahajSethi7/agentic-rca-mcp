FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# OUTPUT_DIR is the only writable artifact path (Phase 5 guardrail);
# docker-compose mounts ./outputs here so PDFs land on the host.
ENV OUTPUT_DIR=/app/outputs
RUN mkdir -p /app/outputs

EXPOSE 8000

# Default service: the FastAPI surface. The CLI and tests run as one-off
# commands, e.g.:
#   docker compose run --rm app python -m agentic_rca "checkout times out"
#   docker compose run --rm app python -m pytest
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]

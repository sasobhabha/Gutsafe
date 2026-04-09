FROM python:3.11-slim

WORKDIR /app

# System deps (kept minimal; sklearn/scipy wheels are prebuilt)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY data/ ./data/
COPY models/ ./models/
COPY web/ ./web/

# Render provides $PORT (default 10000). Bind 0.0.0.0 so it's reachable.
CMD sh -c "uvicorn api_server:app --host 0.0.0.0 --port ${PORT:-8000}"


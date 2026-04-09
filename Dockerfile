FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY data/ ./data/
COPY models/ ./models/
COPY web/ ./web/

ENV PYTHONPATH=/app/src

EXPOSE 8000

# Render, Fly, Railway, etc. set PORT
CMD sh -c "uvicorn api_server:app --host 0.0.0.0 --port ${PORT:-8000}"

FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Build context: V9-Docker (parent of mqtt/)
COPY mqtt/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mqtt/mqtt_client.py /app/mqtt_client.py
COPY shared /app/shared

ENV PYTHONPATH=/app

CMD ["python", "/app/mqtt_client.py"]

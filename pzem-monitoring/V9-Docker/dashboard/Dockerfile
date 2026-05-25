FROM python:3.11-slim

# Install OS dependencies for psycopg2 and matplotlib
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    pkg-config \
    libfreetype6-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Build context: V9-Docker (parent of dashboard/)
COPY dashboard/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY dashboard/ .
COPY shared /app/shared

ENV PYTHONPATH=/app

RUN mkdir -p /app/reports && chmod 755 /app/reports

ENV MPLBACKEND=Agg

EXPOSE 5000

CMD ["gunicorn", "-k", "eventlet", "-w", "1", "-b", "0.0.0.0:5000", "--timeout", "300", "--graceful-timeout", "30", "--keep-alive", "5", "--worker-connections", "1000", "app_with_reporting:app"]

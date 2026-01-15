FROM python:3.11-slim

# Install OS dependencies for psycopg2
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy MQTT client application
COPY mqtt_client.py .

# Run the MQTT client
CMD ["python", "mqtt_client.py"]

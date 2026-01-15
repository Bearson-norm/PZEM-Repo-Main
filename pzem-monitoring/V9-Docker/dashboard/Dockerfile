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

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create reports directory with proper permissions
RUN mkdir -p /app/reports && chmod 755 /app/reports

# Set matplotlib backend for headless operation
ENV MPLBACKEND=Agg

# Expose port
EXPOSE 5000

# Use gunicorn with eventlet for WebSocket support
CMD ["gunicorn", "-k", "eventlet", "-w", "1", "-b", "0.0.0.0:5000", "--timeout", "120", "app_with_reporting:app"]

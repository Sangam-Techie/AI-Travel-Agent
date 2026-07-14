# Dockerfile
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1


RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Default: run the API. docker-compose.yml overrides this per-service
# (api vs. streamlit frontend), but this makes a standalone
# `docker build -t travel-agent . && docker run -p 8000:8000 travel-agent` work too.
CMD ["uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
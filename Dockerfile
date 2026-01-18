# Dockerfile
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy apllication
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
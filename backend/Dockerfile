FROM python:3.10-slim

# Install git (required for git dependencies)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

EXPOSE 8081
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

ENTRYPOINT ["gunicorn", "app.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--threads", "4", "--timeout", "0", "--keep-alive", "650", "--bind", "0.0.0.0:8081"]

# Python RAG HTTP API Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY rag/ ./rag/
COPY rag_http_server.py .

# Create directories for data
RUN mkdir -p data rag_data

# Expose port
EXPOSE 8008

# Health check - увеличены таймауты для ML библиотек
HEALTHCHECK --interval=30s --timeout=15s --start-period=90s --retries=5 \
    CMD curl -f http://localhost:8008/health || exit 1

# Run the application
CMD ["python", "rag_http_server.py", "--host", "0.0.0.0", "--port", "8008"]
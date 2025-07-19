FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Create models directory
RUN mkdir -p /app/models

# Create non-root user
RUN useradd --create-home --shell /bin/bash cloudarb && \
    chown -R cloudarb:cloudarb /app
USER cloudarb

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run ML service
CMD ["python", "-m", "cloudarb.services.ml_forecasting"]
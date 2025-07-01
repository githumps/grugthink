# GrugThink Multi-Bot Container
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and web assets
COPY src/ src/
COPY grugthink.py .
COPY pyproject.toml ./
COPY docker/web/ web/
COPY docker/init-config.sh /usr/local/bin/init-config.sh

# Create directories for data
RUN mkdir -p /data

# Set environment variables
ENV PYTHONPATH=/app/src
ENV GRUGBOT_DATA_DIR=/data
ENV LOG_LEVEL=INFO

# Expose web dashboard port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Create non-root user for security and make init script executable
RUN useradd -m -u 1000 grugthink && \
    chown -R grugthink:grugthink /app /data && \
    chmod +x /usr/local/bin/init-config.sh
USER grugthink

# Run multi-bot container with config initialization
CMD ["/bin/bash", "-c", "/usr/local/bin/init-config.sh && python grugthink.py multi-bot --api-port 8080"]
# GrugThink Multi-Bot Container - Performance Optimized
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies with optimizations
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy requirements first for better caching
COPY requirements.txt ./

# Install Python dependencies with optimizations (fallback to regular requirements if prod fails)
RUN pip install --no-cache-dir --no-compile --disable-pip-version-check \
    --prefer-binary -r requirements.txt \
    && find /usr/local/lib/python3.11/site-packages -name '*.pyc' -delete \
    && find /usr/local/lib/python3.11/site-packages -name '__pycache__' -delete -type d \
    && pip cache purge \
    && apt-get remove -y gcc g++ \
    && apt-get autoremove -y \
    && rm -rf /tmp/* /var/tmp/*

# Copy source code and web assets
COPY src/ src/
COPY grugthink.py .
COPY pyproject.toml ./
COPY docker/web/ web/
COPY docker/personalities/ personalities/
COPY docker/init-config.sh /usr/local/bin/init-config.sh

# Create directories for data
RUN mkdir -p /data

# Set environment variables for performance
ENV PYTHONPATH=/app/src
ENV GRUGBOT_DATA_DIR=/data
ENV LOG_LEVEL=INFO
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONHASHSEED=random
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Expose web dashboard port
EXPOSE 8080

# Optimized health check
HEALTHCHECK --interval=60s --timeout=5s --start-period=30s --retries=2 \
    CMD curl -f http://localhost:8080/health || exit 1

# Create non-root user for security and make init script executable
RUN useradd -m -u 1000 grugthink && \
    chown -R grugthink:grugthink /app /data && \
    chmod +x /usr/local/bin/init-config.sh
USER grugthink

# Run multi-bot container with config initialization
CMD ["/bin/bash", "-c", "/usr/local/bin/init-config.sh && python grugthink.py multi-bot --api-port 8080"]
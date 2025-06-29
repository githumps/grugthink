# GrugThink Single Bot Container
FROM python:3.11.9-slim-bookworm

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ src/
COPY grugthink.py .
COPY pyproject.toml ./

# Set Python path
ENV PYTHONPATH=/app/src

# Create data directory
RUN mkdir -p /data
ENV GRUGBOT_DATA_DIR=/data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0, '/app/src'); from grugthink.config import Config; print('healthy')" || exit 1

# Run single bot
CMD ["python", "grugthink.py"]
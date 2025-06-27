# Stage 1: Builder
FROM python:3.11.9-slim-bookworm as builder

WORKDIR /app
COPY requirements.txt .

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    pip install --upgrade pip setuptools && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y gcc && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /root/.cache /usr/share/doc /usr/share/locale

# Stage 2: Runtime
FROM python:3.11.9-slim-bookworm

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

HEALTHCHECK CMD curl --fail http://localhost:8000/health || exit 1

CMD ["python3", "bot.py"]
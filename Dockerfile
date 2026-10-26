# QuantBIST Telegram bot (server). Steps: docs/SERVER.md
#   docker compose up -d --build
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/Istanbul

WORKDIR /app

COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock

COPY . .

# not root: a bug in the bot cannot change the server. data/, logs/ and backups/ are
# mounted from the host and must belong to uid 1000 (docs/SERVER.md, step 4)
RUN useradd --uid 1000 --create-home quantbist && chown -R quantbist /app
USER quantbist

# healthy = the bot wrote logs/heartbeat.txt in the last 20 minutes (core/reports/health.py)
HEALTHCHECK --interval=5m --timeout=30s --start-period=2m --retries=2 \
    CMD ["python", "-m", "core.reports.health", "--heartbeat"]

CMD ["python", "main.py"]

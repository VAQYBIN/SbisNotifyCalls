FROM python:3.11-slim

LABEL maintainer="VAQYBIN"
LABEL description="Email to Telegram Bot"

WORKDIR /app

RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN groupadd -r botuser && useradd -r -g botuser botuser

RUN mkdir -p /app/logs && \
    chown -R botuser:botuser /app

USER botuser

EXPOSE 8080

ENV PYTHONUNBUFFERED=1
ENV LOG_FILE=/app/logs/bot.log

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import request; request.get('http://localhost:8080/health')" || exit 1

CMD ["python", "main.py"]
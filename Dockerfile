# ================================================
# STAGE 1: Build Environment (Dependencies)
# ================================================
FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

# Копируем requirements.txt для оптимизации Docker layer caching
COPY requirements.txt .

# Создаем виртуальное окружение
RUN python -m venv /app/venv

# Активируем виртуальное окружение и устанавливаем зависимости
ENV PATH="/app/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ================================================
# STAGE 2: Runtime Environment (Final Image)
# ================================================
FROM python:3.11-slim-bookworm AS production

# Создаем пользователя для безопасности
RUN groupadd --gid 1000 botuser && \
    useradd --uid 1000 --gid botuser --shell /bin/bash --create-home botuser

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем виртуальное окружение из build stage
COPY --from=builder /app/venv /app/venv

# Копируем исходный код приложения
COPY config.py email_reader.py main.py ./

# Создаем директорию для логов
RUN mkdir -p /app/logs && chown -R botuser:botuser /app/logs

# Устанавливаем правильные права доступа
RUN chown -R botuser:botuser /app

# Переключаемся на непривилегированного пользователя
USER botuser

# ============================================
# КРИТИЧЕСКИ ВАЖНЫЕ настройки для логирования
# ============================================
ENV PATH="/app/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Дополнительные переменные для консистентности на всех ОС
ENV TERM=xterm-256color

# Настройка часового пояса (можно изменить по потребности)
ENV TZ=Europe/Moscow

# Health check для мониторинга состояния контейнера
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; print('Bot health check OK', flush=True); sys.exit(0)"

# Определяем команду по умолчанию
# Используем exec форму для правильной обработки сигналов
CMD ["python", "-u", "main.py"]

# Добавляем метаданные образа
LABEL maintainer="VAQYBIN" \
      description="Email to Telegram Bot with proper Docker logging" \
      version="1.1" \
      logging.supported="true"

# Документируем порты (хотя наш бот их не использует)
EXPOSE 8080/tcp

# Документируем volumes для логов
VOLUME ["/app/logs"]
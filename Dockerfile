# ================================================
# STAGE 1: Build Environment (Dependencies)
# ================================================
# Используем official Python образ как базовый для сборки
# Alpine версия меньше по размеру, но иногда могут быть проблемы с некоторыми пакетами
# Поэтому используем slim-bookworm для лучшей совместимости
FROM python:3.11-slim-bookworm AS builder

# Устанавливаем рабочую директорию для этапа сборки
WORKDIR /app

# Копируем только requirements.txt сначала
# Это важно для оптимизации Docker layer caching
# Если зависимости не изменились, Docker переиспользует слой
COPY requirements.txt .

# Создаем виртуальное окружение
# Это изолирует наши зависимости и упрощает копирование в финальный образ
RUN python -m venv /app/venv

# Активируем виртуальное окружение и устанавливаем зависимости
# --no-cache-dir экономит место, не сохраняя кэш pip
ENV PATH="/app/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# ================================================
# STAGE 2: Runtime Environment (Final Image)
# ================================================
# Финальный образ будет намного меньше, так как не содержит build tools
FROM python:3.11-slim-bookworm AS production

# Создаем пользователя для безопасности
# Никогда не запускайте приложения от root в продакшене
RUN groupadd --gid 1000 botuser && \
    useradd --uid 1000 --gid botuser --shell /bin/bash --create-home botuser

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем виртуальное окружение из build stage
COPY --from=builder /app/venv /app/venv

# Копируем исходный код приложения
# Порядок важен: сначала менее изменяемые файлы
COPY config.py email_reader.py main.py ./

# Устанавливаем правильные права доступа
RUN chown -R botuser:botuser /app

# Переключаемся на непривилегированного пользователя
USER botuser

# Настраиваем переменные окружения
ENV PATH="/app/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Определяем команду по умолчанию
# Используем exec форму для правильной обработки сигналов
CMD ["python", "main.py"]

# Добавляем метаданные образа
LABEL maintainer="VAQYBIN" \
      description="Email to Telegram Bot" \
      version="1.0"
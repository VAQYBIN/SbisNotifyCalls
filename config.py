import os
import logging
from dotenv import load_dotenv
from typing import List, Optional

# Загружаем переменные окружения
load_dotenv()


class Config:
    # Telegram Bot настройки
    BOT_TOKEN: str = os.getenv('BOT_TOKEN')

    # Группы для уведомлений
    NOTIFIED_GROUPS: List[str] = os.getenv('NOTIFIED_GROUPS', '').split(',')

    # Email настройки
    EMAIL_ACC: str = os.getenv('EMAIL_ACC')
    EMAIL_PASS: str = os.getenv('EMAIL_PASS')

    # Yandex IMAP настройки
    IMAP_SERVER: str = 'imap.yandex.ru'
    IMAP_PORT: int = 993

    # Настройки логирования
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO').upper()
    LOG_FILE: str = os.getenv('LOG_FILE', 'bot.log')
    LOG_MAX_FILE_SIZE: int = int(
        os.getenv('LOG_MAX_FILE_SIZE', '10485760'))  # 10MB
    LOG_BACKUP_COUNT: int = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    LOG_CONSOLE_OUTPUT: bool = os.getenv(
        'LOG_CONSOLE_OUTPUT', 'true').lower() in ('true', '1', 'yes', 'on')

    # Настройки мониторинга
    CHECK_INTERVAL: int = int(os.getenv('CHECK_INTERVAL', '30'))
    FILTER_SENDER: Optional[str] = os.getenv('FILTER_SENDER', None)

    # Проверка обязательных переменных
    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен в .env файле")
        if not cls.EMAIL_ACC:
            raise ValueError("EMAIL_ACC не установлен в .env файле")
        if not cls.EMAIL_PASS:
            raise ValueError("EMAIL_PASS не установлен в .env файле")
        if not cls.NOTIFIED_GROUPS or cls.NOTIFIED_GROUPS == ['']:
            raise ValueError("NOTIFIED_GROUPS не установлен в .env файле")

        # Убираем пустые элементы из списка групп
        cls.NOTIFIED_GROUPS = [group.strip()
                               for group in cls.NOTIFIED_GROUPS if group.strip()]

        # Проверка уровня логирования
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if cls.LOG_LEVEL not in valid_log_levels:
            logging.warning(
                f"⚠️  Неверный LOG_LEVEL: {cls.LOG_LEVEL}, используется INFO")
            cls.LOG_LEVEL = 'INFO'

        # Проверка интервала мониторинга
        if cls.CHECK_INTERVAL < 10:
            logging.warning(
                f"⚠️  Слишком маленький CHECK_INTERVAL: {cls.CHECK_INTERVAL}, используется 10 секунд")
            cls.CHECK_INTERVAL = 10

        logging.info("✅ Конфигурация загружена:")
        logging.info(f"📧 Email: {cls.EMAIL_ACC}")
        logging.info(f"📱 Групп для уведомлений: {len(cls.NOTIFIED_GROUPS)}")
        logging.info(f"📝 Уровень логирования: {cls.LOG_LEVEL}")
        logging.info(f"📁 Файл логов: {cls.LOG_FILE}")
        logging.info(f"⏱️  Интервал проверки: {cls.CHECK_INTERVAL} сек")
        if cls.FILTER_SENDER:
            logging.info(f"🔍 Фильтр отправителя: {cls.FILTER_SENDER}")


# Проверяем конфигурацию при импорте модуля
Config.validate()

import os
from dotenv import load_dotenv
from typing import List

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

        print("✅ Конфигурация загружена:")
        print(f"📧 Email: {cls.EMAIL_ACC}")
        print(f"📱 Групп для уведомлений: {len(cls.NOTIFIED_GROUPS)}")


# Проверяем конфигурацию при импорте модуля
Config.validate()

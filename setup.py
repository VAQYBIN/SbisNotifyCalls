#!/usr/bin/env python3
"""
Скрипт для настройки и проверки Email to Telegram Bot
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Настройка простого логирования для setup скрипта
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def check_python_version():
    """Проверка версии Python"""
    if sys.version_info < (3, 8):
        logger.error("❌ Требуется Python 3.8 или выше")
        logger.error(f"Текущая версия: {sys.version}")
        return False
    logger.info(
        f"✅ Python версия: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True


def install_dependencies():
    """Установка зависимостей"""
    logger.info("\n📦 Установка зависимостей...")

    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        logger.info("✅ Зависимости успешно установлены")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Ошибка установки зависимостей: {e}")
        return False


def check_env_file():
    """Проверка .env файла"""
    logger.info("\n🔧 Проверка .env файла...")

    env_file = Path(".env")
    env_example = Path(".env.example")

    if not env_file.exists():
        if env_example.exists():
            logger.info("📋 .env файл не найден, создаем из .env.example")
            env_example.rename(env_file)
            logger.info("✅ .env файл создан")
            logger.warning("⚠️  Не забудьте заполнить его своими данными!")
        else:
            logger.error("❌ .env файл не найден")
            logger.info("Создайте .env файл с переменными:")
            logger.info("BOT_TOKEN=ваш-токен")
            logger.info("NOTIFIED_GROUPS=id-группы")
            logger.info("EMAIL_ACC=почта@yandex.ru")
            logger.info("EMAIL_PASS=пароль")
            return False
    else:
        logger.info("✅ .env файл найден")

    # Проверяем обязательные переменные
    try:
        from dotenv import load_dotenv
        load_dotenv()

        required_vars = ['BOT_TOKEN', 'NOTIFIED_GROUPS',
                         'EMAIL_ACC', 'EMAIL_PASS']
        missing_vars = []

        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            logger.error(
                f"❌ Отсутствуют переменные: {', '.join(missing_vars)}")
            return False

        logger.info("✅ Все обязательные переменные установлены")
        return True

    except ImportError:
        logger.warning(
            "⚠️  python-dotenv не установлен, пропускаем проверку переменных")
        return True


def create_systemd_service():
    """Создание systemd сервиса (для Linux)"""
    if os.name != 'posix':
        return

    logger.info("\n🔧 Хотите создать systemd сервис для автозапуска? (y/N): ")
    response = input().lower().strip()

    if response not in ['y', 'yes', 'да']:
        return

    current_dir = Path.cwd()
    python_path = sys.executable

    service_content = f"""[Unit]
Description=Email to Telegram Bot
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'root')}
WorkingDirectory={current_dir}
Environment=PATH={os.getenv('PATH')}
ExecStart={python_path} main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

    service_path = Path("/etc/systemd/system/email-telegram-bot.service")

    try:
        logger.info(f"Создаем сервис: {service_path}")
        logger.info("Требуются права администратора...")

        with open("email-telegram-bot.service", "w") as f:
            f.write(service_content)

        subprocess.run(
            ["sudo", "cp", "email-telegram-bot.service", str(service_path)], check=True)
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        subprocess.run(["sudo", "systemctl", "enable",
                       "email-telegram-bot"], check=True)

        logger.info("✅ Systemd сервис создан и включен")
        logger.info("Команды управления:")
        logger.info("  sudo systemctl start email-telegram-bot    # Запустить")
        logger.info("  sudo systemctl stop email-telegram-bot     # Остановить")
        logger.info("  sudo systemctl status email-telegram-bot   # Статус")
        logger.info("  sudo systemctl logs email-telegram-bot     # Логи")

        os.remove("email-telegram-bot.service")

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Ошибка создания сервиса: {e}")
    except PermissionError:
        logger.error("❌ Недостаточно прав для создания сервиса")


def main():
    """Главная функция установки"""
    logger.info("🚀 Настройка Email to Telegram Bot\n")

    # Проверка Python
    if not check_python_version():
        return False

    # Установка зависимостей
    if not install_dependencies():
        return False

    # Проверка .env
    if not check_env_file():
        return False

    # Создание systemd сервиса (опционально)
    create_systemd_service()

    logger.info("\n🎉 Настройка завершена!")
    logger.info("\n📋 Следующие шаги:")
    logger.info("1. Отредактируйте .env файл с вашими данными")
    logger.info("2. Убедитесь, что IMAP включен в настройках Yandex.Почты")
    logger.info("3. Добавьте бота в Telegram группы как администратора")
    logger.info("4. Запустите бота: python main.py")

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⏹️ Установка прервана")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Неожиданная ошибка: {e}")
        sys.exit(1)

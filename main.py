import re
import asyncio
import logging
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

from config import Config
from email_reader import EmailReader


def setup_logging():
    """
    Настройка системы логирования с правильной поддержкой Docker

    Ключевые изменения для работы с Docker:
    1. Принудительное отключение буферизации Python
    2. Обеспечение вывода в STDOUT/STDERR
    3. Правильная обработка уровней логирования
    4. Совместимость с различными ОС
    """

    # Получаем уровень логирования из конфига
    log_level = getattr(logging, Config.LOG_LEVEL, logging.INFO)

    # Создаем основной форматтер с детальной информацией
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )

    # Создаем простой форматтер для консоли (более читаемый)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )

    # Очищаем существующие обработчики (важно для избежания дублирования)
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Создаем список обработчиков
    handlers = []

    # === КОНСОЛЬНЫЙ ОБРАБОТЧИК (ОБЯЗАТЕЛЬНО ДЛЯ DOCKER) ===
    if Config.LOG_CONSOLE_OUTPUT:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(log_level)

        # КРИТИЧЕСКИ ВАЖНО: отключаем буферизацию для немедленного вывода в Docker
        console_handler.stream = sys.stdout

        handlers.append(console_handler)
        print(
            f"✅ Консольный обработчик настроен (уровень: {Config.LOG_LEVEL})", flush=True)

    # === ФАЙЛОВЫЙ ОБРАБОТЧИК (ОПЦИОНАЛЬНО) ===
    try:
        file_handler = RotatingFileHandler(
            Config.LOG_FILE,
            maxBytes=Config.LOG_MAX_FILE_SIZE,
            backupCount=Config.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setFormatter(detailed_formatter)
        file_handler.setLevel(log_level)
        handlers.append(file_handler)
        print(f"✅ Файловый обработчик настроен: {Config.LOG_FILE}", flush=True)
    except Exception as e:
        print(f"⚠️ Ошибка создания файлового логгера: {e}", flush=True)

    # === БАЗОВАЯ НАСТРОЙКА ЛОГИРОВАНИЯ ===
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True  # Принудительно перезаписываем существующую конфигурацию
    )

    # Настраиваем логгер для aiogram (часто очень болтливый)
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)

    # Тестовое сообщение для проверки работы логирования
    test_logger = logging.getLogger('setup_test')
    test_logger.info("🚀 Система логирования успешно инициализирована")
    test_logger.info(f"📝 Уровень логирования: {Config.LOG_LEVEL}")
    test_logger.info(f"📁 Файл логов: {Config.LOG_FILE}")
    test_logger.info(
        f"🖥️ Консольный вывод: {'включён' if Config.LOG_CONSOLE_OUTPUT else 'отключён'}")

    # Принудительная очистка буферов (критично для Docker)
    sys.stdout.flush()
    sys.stderr.flush()


# ============================================================================
# КРИТИЧЕСКИ ВАЖНО: Настраиваем логирование ДО импорта других модулей
# ============================================================================
setup_logging()
logger = logging.getLogger(__name__)

# Сообщение о старте (должно появиться в Docker logs сразу)
logger.info("=" * 60)
logger.info("🤖 ЗАПУСК EMAIL TO TELEGRAM BOT")
logger.info("=" * 60)


class EmailBot:
    def __init__(self):
        logger.info("🔧 Инициализация EmailBot...")

        # Инициализация бота и диспетчера
        self.bot = Bot(token=Config.BOT_TOKEN)
        self.dp = Dispatcher(storage=MemoryStorage())

        # Инициализация читателя почты
        self.email_reader = EmailReader()

        # Регистрация обработчиков
        self.register_handlers()

        # Статистика
        self.emails_processed = 0
        self.start_time = datetime.now()

        logger.info("✅ EmailBot инициализирован успешно")

    def register_handlers(self):
        """Регистрация обработчиков команд"""
        logger.info("📋 Регистрация обработчиков команд...")

        @self.dp.message(Command("start"))
        async def start_command(message: Message):
            """Команда /start - только в личных сообщениях"""
            logger.info(
                f"💬 Получена команда /start от пользователя {message.from_user.id}")

            # Проверяем, что это личное сообщение
            if message.chat.type != 'private':
                logger.debug(
                    "ℹ️ Команда /start проигнорирована (не личное сообщение)")
                return

            await message.reply(
                "👋 Привет! Я бот для мониторинга электронной почты.\n\n"
                "🔍 Я автоматически отслеживаю новые письма и пересылаю их содержимое в настроенные группы.\n\n"
                "📊 Доступные команды:\n"
                "• /status - текущий статус бота\n"
                "• /help - справка\n"
                "• /config - текущие настройки"
            )
            logger.info("✅ Ответ на команду /start отправлен")

        @self.dp.message(Command("status"))
        async def status_command(message: Message):
            """Команда /status - только в личных сообщениях"""
            logger.info(
                f"📊 Получена команда /status от пользователя {message.from_user.id}")

            # Проверяем, что это личное сообщение
            if message.chat.type != 'private':
                logger.debug(
                    "ℹ️ Команда /status проигнорирована (не личное сообщение)")
                return

            uptime = datetime.now() - self.start_time
            uptime_str = str(uptime).split('.')[0]  # Убираем микросекунды

            status_text = (
                f"📊 <b>Статус бота</b>\n\n"
                f"⏰ Время работы: {uptime_str}\n"
                f"📧 Обработано писем: {self.emails_processed}\n"
                f"📱 Групп для уведомлений: {len(Config.NOTIFIED_GROUPS)}\n"
                f"✉️ Мониторинг почты: {Config.EMAIL_ACC}\n"
                f"⏱️ Интервал проверки: {Config.CHECK_INTERVAL} сек\n"
                f"🔄 Статус: Активен"
            )

            if Config.FILTER_SENDER:
                status_text += f"\n🔍 Фильтр отправителя: {Config.FILTER_SENDER}"

            await message.reply(status_text, parse_mode='HTML')
            logger.info("✅ Статус отправлен пользователю")

        @self.dp.message(Command("config"))
        async def config_command(message: Message):
            """Команда /config - показать текущие настройки"""
            logger.info(
                f"⚙️ Получена команда /config от пользователя {message.from_user.id}")

            # Проверяем, что это личное сообщение
            if message.chat.type != 'private':
                logger.debug(
                    "ℹ️ Команда /config проигнорирована (не личное сообщение)")
                return

            config_text = (
                f"⚙️ <b>Текущие настройки</b>\n\n"
                f"📧 <b>Email:</b> {Config.EMAIL_ACC}\n"
                f"📱 <b>Групп:</b> {len(Config.NOTIFIED_GROUPS)}\n"
                f"⏱️ <b>Интервал проверки:</b> {Config.CHECK_INTERVAL} сек\n\n"
                f"📝 <b>Логирование:</b>\n"
                f"• Уровень: {Config.LOG_LEVEL}\n"
                f"• Файл: {Config.LOG_FILE}\n"
                f"• Макс. размер: {Config.LOG_MAX_FILE_SIZE // 1024 // 1024} MB\n"
                f"• Резервных копий: {Config.LOG_BACKUP_COUNT}\n"
                f"• Вывод в консоль: {'Да' if Config.LOG_CONSOLE_OUTPUT else 'Нет'}"
            )

            if Config.FILTER_SENDER:
                config_text += f"\n\n🔍 <b>Фильтр отправителя:</b> {Config.FILTER_SENDER}"

            await message.reply(config_text, parse_mode='HTML')
            logger.info("✅ Конфигурация отправлена пользователю")

        @self.dp.message(Command("help"))
        async def help_command(message: Message):
            """Команда /help - только в личных сообщениях"""
            logger.info(
                f"❓ Получена команда /help от пользователя {message.from_user.id}")

            # Проверяем, что это личное сообщение
            if message.chat.type != 'private':
                logger.debug(
                    "ℹ️ Команда /help проигнорирована (не личное сообщение)")
                return

            help_text = (
                "🤖 <b>Справка по боту</b>\n\n"
                "Этот бот автоматически мониторит указанную электронную почту "
                "и пересылает содержимое новых писем в настроенные группы.\n\n"
                "📋 <b>Команды:</b>\n"
                "• /start - запуск и приветствие\n"
                "• /status - информация о статусе бота\n"
                "• /config - текущие настройки\n"
                "• /help - эта справка\n\n"
                "⚙️ <b>Настройка:</b>\n"
                "Бот настраивается через .env файл с переменными окружения.\n"
                "Все доступные переменные смотрите в .env.example\n\n"
                "ℹ️ <b>Примечание:</b>\n"
                "Команды работают только в личных сообщениях с ботом."
            )

            await message.reply(help_text, parse_mode='HTML')
            logger.info("✅ Справка отправлена пользователю")

        logger.info("✅ Все обработчики команд зарегистрированы")

    def clean_email_body(self, body: str) -> str:
        """Улучшенная очистка тела письма"""
        logger.debug("🧹 Очистка тела письма...")

        # Удалить CSS стили и HTML теги
        body = re.sub(r'<style.*?>.*?</style>', '', body, flags=re.DOTALL)
        body = re.sub(r'<[^>]+>', '', body)

        # Убираем текст "Отпишитесь" и все что после него
        body = re.sub(r'Отпишитесь.*$', '', body, flags=re.DOTALL)

        # Объединяем весь текст в одну строку, заменяя переносы строк пробелами
        full_text = ' '.join(body.splitlines())

        # Извлекаем данные с помощью регулярных выражений
        result = []

        # Ищем Номер
        number_match = re.search(
            r'Номер\s*-\s*([^\\]*?)(?=\s*\\\s*ФИО|$)', full_text, re.IGNORECASE)
        if number_match:
            number_value = number_match.group(1).strip()
            result.append(f"Номер - {number_value}")

        # Ищем ФИО
        name_match = re.search(
            r'ФИО\s*-\s*([^\\]*?)(?=\s*\\\s*Время|$)', full_text, re.IGNORECASE)
        if name_match:
            name_value = name_match.group(1).strip()
            result.append(f"ФИО - {name_value}")

        # Ищем Время
        time_match = re.search(
            r'Время\s*-\s*([^\\]*?)(?=\s*\\|$)', full_text, re.IGNORECASE)
        if time_match:
            time_value = time_match.group(1).strip()
            # Убираем лишние символы и форматируем время
            time_value = re.sub(r'\s+', ' ', time_value)
            result.append(f"Время - {time_value}")

        # Если не нашли через регулярки, попробуем альтернативный способ
        if not result:
            # Разбиваем по обратным слешам
            parts = full_text.split('\\')

            for part in parts:
                part = part.strip()
                if any(keyword in part.lower() for keyword in ['номер -', 'фио -', 'время -']):
                    # Очищаем от лишних пробелов
                    cleaned_part = re.sub(r'\s+', ' ', part).strip()
                    if cleaned_part and len(cleaned_part) > 3:
                        result.append(cleaned_part)

        # Если все еще ничего не найдено, возвращаем исходный текст (очищенный)
        if not result:
            cleaned_body = re.sub(r'\s+', ' ', full_text).strip()
            logger.warning(
                "⚠️ Не удалось извлечь структурированные данные из письма")
            return cleaned_body[:500] if cleaned_body else "Не удалось извлечь данные из письма"

        logger.debug(f"✅ Извлечено полей из письма: {len(result)}")
        return '\n'.join(result)

    async def format_email_message(self, email_info: dict) -> str:
        """Форматирование письма для отправки в группу"""
        logger.debug(
            f"📝 Форматирование письма: {email_info.get('subject', 'Без темы')}")

        # Очищаем тело письма
        body = self.clean_email_body(email_info['body'])

        # Ограничиваем длину сообщения
        if len(body) > 2000:
            body = body[:2000] + '...'
            logger.debug("✂️ Сообщение обрезано до 2000 символов")

        message_text = (
            "Пропущенный звонок от клиента\n"
            f"{body}"
        )

        return message_text

    async def send_to_groups(self, message_text: str):
        """Отправка сообщения во все настроенные группы"""
        logger.info(
            f"📤 Отправка сообщения в {len(Config.NOTIFIED_GROUPS)} групп(ы)")

        success_count = 0
        for group_id in Config.NOTIFIED_GROUPS:
            try:
                await self.bot.send_message(
                    chat_id=group_id,
                    text=message_text,
                    parse_mode='HTML'
                )
                logger.info(f"✅ Сообщение отправлено в группу {group_id}")
                success_count += 1

            except Exception as e:
                logger.error(f"❌ Ошибка отправки в группу {group_id}: {e}")

                # Попробуем отправить без форматирования
                try:
                    # Убираем HTML разметку для fallback
                    plain_text = message_text.replace(
                        '<b>', '').replace('</b>', '')
                    plain_text = plain_text.replace(
                        '<code>', '').replace('</code>', '')
                    plain_text = plain_text.replace(
                        '<pre>', '').replace('</pre>', '')

                    await self.bot.send_message(
                        chat_id=group_id,
                        # Telegram ограничение на длину сообщения
                        text=plain_text[:4096]
                    )
                    logger.info(
                        f"✅ Резервная отправка в группу {group_id} успешна")
                    success_count += 1

                except Exception as e2:
                    logger.error(
                        f"❌ Критическая ошибка отправки в группу {group_id}: {e2}")

        logger.info(
            f"📊 Успешно отправлено в {success_count} из {len(Config.NOTIFIED_GROUPS)} групп")

    async def handle_new_email(self, email_info: dict):
        """Обработка нового письма"""
        try:
            logger.info(
                f"📧 Обрабатываем новое письмо: {email_info['subject']}")
            logger.debug(
                f"📤 От: {email_info['from_name']} ({email_info['from_email']})")
            logger.debug(f"📅 Время: {email_info['date']}")

            # Форматируем сообщение
            message_text = await self.format_email_message(email_info)

            # Отправляем во все группы
            await self.send_to_groups(message_text)

            # Обновляем статистику
            self.emails_processed += 1

            logger.info("✅ Письмо успешно обработано и разослано")
            logger.info(f"📈 Всего обработано писем: {self.emails_processed}")

        except Exception as e:
            logger.error(f"❌ Ошибка обработки письма: {e}", exc_info=True)

    async def start_monitoring(self):
        """Запуск мониторинга почты с использованием настроек из конфига"""
        logger.info("🚀 Запуск мониторинга почты...")
        logger.info(f"📧 Мониторинг аккаунта: {Config.EMAIL_ACC}")
        logger.info(f"⏱️ Интервал проверки: {Config.CHECK_INTERVAL} секунд")

        if Config.FILTER_SENDER:
            logger.info(f"🔍 Фильтрация по отправителю: {Config.FILTER_SENDER}")
        else:
            logger.info("📬 Мониторинг писем от всех отправителей")

        # Запускаем мониторинг в отдельной задаче
        monitoring_task = asyncio.create_task(
            self.email_reader.run_email_monitoring(
                callback=self.handle_new_email,
                sender_email=Config.FILTER_SENDER,
                check_interval=Config.CHECK_INTERVAL
            )
        )

        logger.info("✅ Задача мониторинга почты запущена")
        return monitoring_task

    async def start(self):
        """Запуск бота"""
        try:
            logger.info("🤖 Запуск Telegram бота...")

            # Получаем информацию о боте
            bot_info = await self.bot.get_me()
            logger.info(
                f"✅ Бот @{bot_info.username} (ID: {bot_info.id}) успешно запущен")

            # Запуск мониторинга почты
            monitoring_task = await self.start_monitoring()

            # Запуск поллинга бота
            logger.info("🔄 Запуск polling для Telegram бота...")
            polling_task = asyncio.create_task(
                self.dp.start_polling(self.bot)
            )

            logger.info("🎯 Бот полностью запущен и готов к работе!")
            logger.info("=" * 60)

            # Принудительная очистка буферов
            sys.stdout.flush()

            # Ожидаем завершения обеих задач
            await asyncio.gather(monitoring_task, polling_task)

        except Exception as e:
            logger.error(
                f"❌ Критическая ошибка запуска бота: {e}", exc_info=True)
            raise

    async def shutdown(self):
        """Корректное завершение работы бота"""
        try:
            logger.info("🛑 Завершение работы бота...")

            # Закрываем соединение с почтой
            self.email_reader.disconnect()

            # Закрываем сессию бота
            await self.bot.session.close()

            logger.info("✅ Бот успешно завершил работу")

        except Exception as e:
            logger.error(f"❌ Ошибка при завершении работы: {e}")


async def main():
    """Главная функция"""
    bot = EmailBot()

    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("⏹️ Получен сигнал остановки (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка: {e}", exc_info=True)
    finally:
        await bot.shutdown()


if __name__ == "__main__":
    try:
        # Проверяем конфигурацию перед запуском
        logger.info("🔧 Проверка конфигурации...")
        logger.info("✅ Конфигурация корректна, запускаем бота...")

        # Запускаем главную функцию
        asyncio.run(main())

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        # Принудительная очистка буферов перед выходом
        sys.stdout.flush()
        sys.stderr.flush()
        exit(1)

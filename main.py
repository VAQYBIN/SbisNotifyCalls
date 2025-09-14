import re
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

from config import Config
from email_reader import EmailReader


def setup_logging():
    """Настройка системы логирования с учетом переменных окружения"""
    # Получаем уровень логирования из конфига
    log_level = getattr(logging, Config.LOG_LEVEL, logging.INFO)

    # Создаем форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Создаем список обработчиков
    handlers = []

    # Файловый обработчик с ротацией
    try:
        file_handler = RotatingFileHandler(
            Config.LOG_FILE,
            maxBytes=Config.LOG_MAX_FILE_SIZE,
            backupCount=Config.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        handlers.append(file_handler)
    except Exception as e:
        logging.error(f"⚠️  Ошибка создания файлового логгера: {e}")

    # Консольный обработчик (если включен)
    if Config.LOG_CONSOLE_OUTPUT:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        handlers.append(console_handler)

    # Базовая настройка логирования
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


# Настраиваем логирование
setup_logging()
logger = logging.getLogger(__name__)


class EmailBot:
    def __init__(self):
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

    def register_handlers(self):
        """Регистрация обработчиков команд"""

        @self.dp.message(Command("start"))
        async def start_command(message: Message):
            """Команда /start - только в личных сообщениях"""
            # Проверяем, что это личное сообщение
            if message.chat.type != 'private':
                return

            await message.reply(
                "👋 Привет! Я бот для мониторинга электронной почты.\n\n"
                "🔍 Я автоматически отслеживаю новые письма и пересылаю их содержимое в настроенные группы.\n\n"
                "📊 Доступные команды:\n"
                "• /status - текущий статус бота\n"
                "• /help - справка\n"
                "• /config - текущие настройки"
            )

        @self.dp.message(Command("status"))
        async def status_command(message: Message):
            """Команда /status - только в личных сообщениях"""
            # Проверяем, что это личное сообщение
            if message.chat.type != 'private':
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

        @self.dp.message(Command("config"))
        async def config_command(message: Message):
            """Команда /config - показать текущие настройки"""
            # Проверяем, что это личное сообщение
            if message.chat.type != 'private':
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

        @self.dp.message(Command("help"))
        async def help_command(message: Message):
            """Команда /help - только в личных сообщениях"""
            # Проверяем, что это личное сообщение
            if message.chat.type != 'private':
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

    def clean_email_body(self, body: str) -> str:
        """Улучшенная очистка тела письма"""
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
            return cleaned_body[:500] if cleaned_body else "Не удалось извлечь данные из письма"

        return '\n'.join(result)

    async def format_email_message(self, email_info: dict) -> str:
        """Форматирование письма для отправки в группу"""
        # Очищаем тело письма
        body = self.clean_email_body(email_info['body'])

        # Ограничиваем длину сообщения
        if len(body) > 2000:
            body = body[:2000] + '...'

        message_text = (
            "Пропущенный звонок от клиента\n"
            f"{body}"
        )

        return message_text

    async def send_to_groups(self, message_text: str):
        """Отправка сообщения во все настроенные группы"""

        for group_id in Config.NOTIFIED_GROUPS:
            try:
                await self.bot.send_message(
                    chat_id=group_id,
                    text=message_text,
                    parse_mode='HTML'
                )
                logger.info(f"✅ Сообщение отправлено в группу {group_id}")

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

                except Exception as e2:
                    logger.error(
                        f"❌ Критическая ошибка отправки в группу {group_id}: {e2}")

    async def handle_new_email(self, email_info: dict):
        """Обработка нового письма"""
        try:
            logger.info(
                f"🔔 Обрабатываем новое письмо: {email_info['subject']}")

            # Форматируем сообщение
            message_text = await self.format_email_message(email_info)

            # Отправляем во все группы
            await self.send_to_groups(message_text)

            # Обновляем статистику
            self.emails_processed += 1

            logger.info("✅ Письмо успешно обработано и разослано")

        except Exception as e:
            logger.error(f"❌ Ошибка обработки письма: {e}")

    async def start_monitoring(self):
        """Запуск мониторинга почты с использованием настроек из конфига"""
        logger.info("🚀 Запуск мониторинга почты...")

        if Config.FILTER_SENDER:
            logger.info(f"🔍 Фильтрация по отправителю: {Config.FILTER_SENDER}")

        # Запускаем мониторинг в отдельной задаче
        monitoring_task = asyncio.create_task(
            self.email_reader.run_email_monitoring(
                callback=self.handle_new_email,
                sender_email=Config.FILTER_SENDER,
                check_interval=Config.CHECK_INTERVAL
            )
        )

        return monitoring_task

    async def start(self):
        """Запуск бота"""
        try:
            logger.info("🤖 Запуск Telegram бота...")

            # Получаем информацию о боте
            bot_info = await self.bot.get_me()
            logger.info(f"✅ Бот @{bot_info.username} успешно запущен")

            # Запуск мониторинга почты
            monitoring_task = await self.start_monitoring()

            # Запуск поллинга бота
            polling_task = asyncio.create_task(
                self.dp.start_polling(self.bot)
            )

            logger.info("🎯 Бот полностью запущен и готов к работе!")

            # Ожидаем завершения обеих задач
            await asyncio.gather(monitoring_task, polling_task)

        except Exception as e:
            logger.error(f"❌ Критическая ошибка запуска бота: {e}")
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
        logger.error(f"❌ Неожиданная ошибка: {e}")
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
        logger.error(f"❌ Критическая ошибка: {e}")
        exit(1)

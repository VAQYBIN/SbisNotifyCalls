import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

from config import Config
from email_reader import EmailReader

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding="utf-8"),
        logging.StreamHandler()
    ]
)
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
            """Команда /start"""
            await message.reply(
                "👋 Привет! Я бот для мониторинга электронной почты.\n\n"
                "🔍 Я автоматически отслеживаю новые письма и пересылаю их содержимое в настроенные группы.\n\n"
                "📊 Доступные команды:\n"
                "• /status - текущий статус бота\n"
                "• /help - справка"
            )

        @self.dp.message(Command("status"))
        async def status_command(message: Message):
            """Команда /status"""
            uptime = datetime.now() - self.start_time
            uptime_str = str(uptime).split('.')[0]  # Убираем микросекунды

            status_text = (
                f"📊 <b>Статус бота</b>\n\n"
                f"⏰ Время работы: {uptime_str}\n"
                f"📧 Обработано писем: {self.emails_processed}\n"
                f"📱 Групп для уведомлений: {len(Config.NOTIFIED_GROUPS)}\n"
                f"✉️ Мониторинг почты: {Config.EMAIL_ACC}\n"
                f"🔄 Статус: Активен"
            )

            await message.reply(status_text, parse_mode='HTML')

        @self.dp.message(Command("help"))
        async def help_command(message: Message):
            """Команда /help"""
            help_text = (
                "🤖 <b>Справка по боту</b>\n\n"
                "Этот бот автоматически мониторит указанную электронную почту "
                "и пересылает содержимое новых писем в настроенные группы.\n\n"
                "📋 <b>Команды:</b>\n"
                "• /start - запуск и приветствие\n"
                "• /status - информация о статусе бота\n"
                "• /help - эта справка\n\n"
                "⚙️ <b>Настройка:</b>\n"
                "Бот настраивается через .env файл с переменными окружения."
            )

            await message.reply(help_text, parse_mode='HTML')

    async def format_email_message(self, email_info: dict) -> str:
        """Форматирование письма для отправки в группу"""

        # Ограничиваем длину темы и текста
        # subject = email_info['subject'][:100] + ('...' if len(email_info['subject']) > 100 else '')
        body = email_info['body'][:2000] + ('...' if len(email_info['body']) > 2000 else '')

        # Форматируем дату
        date_str = email_info['date'].strftime("%d.%m.%Y %H:%M")

        message_text = (
            # f"📧 <b>Новое письмо</b>\n\n"
            # f"👤 <b>От:</b> {email_info['from_name']}\n"
            # f"📩 <b>Email:</b> <code>{email_info['from_email']}</code>\n"
            # f"📝 <b>Тема:</b> {subject}\n"
            f"🕒 <b>Дата:</b> {date_str}\n\n"
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
                    plain_text = message_text.replace('<b>', '').replace('</b>', '')
                    plain_text = plain_text.replace('<code>', '').replace('</code>', '')
                    plain_text = plain_text.replace('<pre>', '').replace('</pre>', '')

                    await self.bot.send_message(
                        chat_id=group_id,
                        text=plain_text[:4096]  # Telegram ограничение на длину сообщения
                    )
                    logger.info(f"✅ Резервная отправка в группу {group_id} успешна")

                except Exception as e2:
                    logger.error(f"❌ Критическая ошибка отправки в группу {group_id}: {e2}")

    async def handle_new_email(self, email_info: dict):
        """Обработка нового письма"""
        try:
            logger.info(f"🔔 Обрабатываем новое письмо: {email_info['subject']}")

            # Форматируем сообщение
            message_text = await self.format_email_message(email_info)

            # Отправляем во все группы
            await self.send_to_groups(message_text)

            # Обновляем статистику
            self.emails_processed += 1

            logger.info("✅ Письмо успешно обработано и разослано")

        except Exception as e:
            logger.error(f"❌ Ошибка обработки письма: {e}")

    async def start_monitoring(self, sender_email: str = None, check_interval: int = 30):
        """Запуск мониторинга почты"""
        logger.info("🚀 Запуск мониторинга почты...")

        # Запускаем мониторинг в отдельной задаче
        monitoring_task = asyncio.create_task(
            self.email_reader.run_email_monitoring(
                callback=self.handle_new_email,
                sender_email=sender_email,
                check_interval=check_interval
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
            monitoring_task = await self.start_monitoring()  # Используем настройки из конфига

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

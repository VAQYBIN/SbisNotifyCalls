import asyncio
import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
from typing import List, Dict, Optional
import ssl
from datetime import datetime, timedelta, timezone
from config import Config
import logging

logger = logging.getLogger(__name__)


class EmailReader:
    def __init__(self):
        self.imap = None
        # Начальная проверка за последную минуту
        self.last_check_time = datetime.now(
            timezone.utc) - timedelta(minutes=1)

    async def connect(self) -> bool:
        """Подключение к IMAP серверу Yandex"""
        try:
            # Создаем SSL контекст
            context = ssl.create_default_context()

            # Подключаемся к IMAP серверу
            self.imap = imaplib.IMAP4_SSL(
                Config.IMAP_SERVER, Config.IMAP_PORT, ssl_context=context)

            # Авторизация
            result = self.imap.login(Config.EMAIL_ACC, Config.EMAIL_PASS)

            if result[0] == 'OK':
                logger.info(f"✅ Успешно подключились к {Config.EMAIL_ACC}")
                return True
            else:
                logger.error(f"❌ Ошибка авторизации: {result}")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка подключения к почте: {e}")
            return False

    def disconnect(self):
        """Отключение от IMAP сервера"""
        try:
            if self.imap:
                self.imap.close()
                self.imap.logout()
                self.imap = None
                logger.info("✅ Отключились от почтового сервера")
        except Exception as e:
            logger.error(f"❌ Ошибка при отключении: {e}")

    def decode_mime_header(self, header: str) -> str:
        """Декодирование MIME заголовков"""
        try:
            decoded_parts = decode_header(header)
            decoded_header = ''

            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    decoded_header += part.decode(encoding or 'utf-8')
                else:
                    decoded_header += part

            return decoded_header
        except Exception as e:
            logger.error(f"❌ Ошибка декодирования заголовка: {e}")
            return header

    def get_email_body(self, msg) -> str:
        """Извлечение текста из письма"""
        body = ""

        try:
            if msg.is_multipart():
                # Письмо состоит из нескольких частей
                for part in msg.walk():
                    content_type = part.get_content_type()

                    if content_type == "text/plain":
                        charset = part.get_content_charset() or 'utf-8'
                        body = part.get_payload(decode=True).decode(
                            charset, errors='ignore')
                        break
                    elif content_type == "text/html" and not body:
                        # Если нет plain text, берем HTML
                        charset = part.get_content_charset() or 'utf-8'
                        html_body = part.get_payload(
                            decode=True).decode(charset, errors='ignore')
                        # Простое удаление HTML тегов (для более сложной обработки можно использовать BeautifulSoup)
                        import re
                        body = re.sub('<[^<]+?>', '', html_body)
            else:
                # Письмо состоит из одной части
                charset = msg.get_content_charset() or 'utf-8'
                body = msg.get_payload(decode=True).decode(
                    charset, errors='ignore')

        except Exception as e:
            logger.error(f"❌ Ошибка извлечения текста письма: {e}")
            body = "Ошибка при извлечении текста письма"

        return body.strip()

    async def check_new_emails(self, sender_email: Optional[str] = None) -> List[Dict]:
        """Проверка новых писем"""
        try:
            if not self.imap:
                if not await self.connect():
                    return []

            # Выбираем папку входящих
            self.imap.select('INBOX')

            # Формируем поисковый запрос для новых писем
            search_criteria = f'SINCE "{self.last_check_time.strftime("%d-%b-%Y")}"'

            # Если указан конкретный отправитель, добавляем его в критерий поиска
            if sender_email:
                search_criteria += f' FROM "{sender_email}"'

            # Ищем письма
            result, messages = self.imap.search(None, search_criteria)

            if result != 'OK':
                logger.error("❌ Ошибка поиска писем")
                return []

            email_ids = messages[0].split()
            new_emails = []

            # Обрабатываем каждое найденное письмо
            for email_id in email_ids:
                try:
                    # Получаем письмо
                    result, msg_data = self.imap.fetch(email_id, '(RFC822)')

                    if result != 'OK':
                        continue

                    # Парсим письмо
                    msg = email.message_from_bytes(msg_data[0][1])

                    # Получаем дату письма
                    date_str = msg.get('Date')
                    email_date = email.utils.parsedate_to_datetime(date_str)

                    # Приводим email_date к offset-aware, если нужно
                    if email_date.tzinfo is None:
                        email_date = email_date.replace(tzinfo=timezone.utc)

                    # Проверяем, что письмо действительно новое
                    if email_date <= self.last_check_time:
                        continue

                    # Извлекаем информацию о письме
                    subject = self.decode_mime_header(msg.get('Subject', ''))
                    from_header = msg.get('From', '')
                    from_name, from_email = parseaddr(from_header)
                    from_name = self.decode_mime_header(
                        from_name) if from_name else from_email

                    # Получаем текст письма
                    body = self.get_email_body(msg)

                    email_info = {
                        'id': email_id.decode(),
                        'subject': subject,
                        'from_name': from_name,
                        'from_email': from_email,
                        'body': body,
                        'date': email_date
                    }

                    new_emails.append(email_info)
                    logger.info(f"📧 Новое письмо: {subject} от {from_name}")

                except Exception as e:
                    logger.error(f"❌ Ошибка обработки письма {email_id}: {e}")
                    continue

            # Обновляем время последней проверки
            self.last_check_time = datetime.now(timezone.utc)

            return new_emails

        except Exception as e:
            logger.error(f"❌ Ошибка проверки новых писем: {e}")
            return []

    async def run_email_monitoring(self, callback, sender_email: Optional[str] = None, check_interval: int = 30):
        """Запуск мониторинга почты"""
        logger.info(
            f"🔍 Запуск мониторинга почты (проверка каждые {check_interval} секунд)")

        while True:
            try:
                new_emails = await self.check_new_emails(sender_email)

                for email_info in new_emails:
                    await callback(email_info)

                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.error(f"❌ Ошибка в цикле мониторинга: {e}")
                # Переподключаемся при ошибке
                self.disconnect()
                await asyncio.sleep(check_interval)

    def __del__(self):
        """Деструктор для корректного закрытия соединения"""
        self.disconnect()

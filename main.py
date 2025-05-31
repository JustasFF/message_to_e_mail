import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Filter
from aiogram.types import Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import aiosmtplib
from typing import TypedDict

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

class SenderInfo(TypedDict):
    name: str
    username: str

class SecurityFilter(Filter):
    """Фильтр для проверки безопасности"""
    def __init__(self, allowed_users: list[int]):
        self.allowed_users = allowed_users

    async def __call__(self, message: Message) -> bool:
        if message.from_user.id not in self.allowed_users:
            logger.warning(f"Unauthorized access attempt from {message.from_user.id}")
            return False
        return True

# Конфигурация
CONFIG = {
    "TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
    "SMTP": {
        "SERVER": os.getenv("SMTP_SERVER"),
        "PORT": int(os.getenv("SMTP_PORT", 465)),
        "USER": os.getenv("EMAIL_USER"),
        "PASSWORD": os.getenv("EMAIL_PASSWORD"),
        "RECEIVER": os.getenv("EMAIL_RECEIVER")
    },
    "ALLOWED_USERS": [
        int(uid) for uid in os.getenv("ALLOWED_USERS", "").split(",") if uid.strip().isdigit()
    ],
    "RATE_LIMIT": {
        "MESSAGES": 3,
        "INTERVAL": 60
    }
}

# Инициализация бота
bot = Bot(token=CONFIG["TOKEN"])
dp = Dispatcher()

# Инициализация фильтров
security_filter = SecurityFilter(CONFIG["ALLOWED_USERS"])

def create_email_template(sender: SenderInfo, content: str, is_file: bool = False) -> MIMEMultipart:
    """Создает HTML-шаблон письма"""
    message = MIMEMultipart()
    message["From"] = f'Telegram Bot <{CONFIG["SMTP"]["USER"]}>'
    message["To"] = CONFIG["SMTP"]["RECEIVER"]
    message["Date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .header {{ color: #2c3e50; border-bottom: 1px solid #eee; }}
                .content {{ background: #f9f9f9; padding: 15px; border-radius: 5px; }}
                .footer {{ color: #7f8c8d; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>📨 Новое сообщение из Telegram</h2>
                <p><strong>От:</strong> {sender['name']} (@{sender['username']})</p>
                <p><strong>Время:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <div class="content">
                {f'<p>📎 Прикрепленный файл: <strong>{content}</strong></p>' if is_file else content}
            </div>
            <div class="footer">
                <p>Это сообщение было отправлено автоматически.</p>
            </div>
        </body>
    </html>
    """

    message.attach(MIMEText(html, "html"))
    return message

async def send_email(subject: str, message: MIMEMultipart, attachment_path: str = None):
    """Асинхронная отправка email с возможным вложением"""
    message["Subject"] = subject

    if attachment_path:
        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={Path(attachment_path).name}"
            )
            message.attach(part)

    try:
        async with aiosmtplib.SMTP(
            hostname=CONFIG["SMTP"]["SERVER"],
            port=CONFIG["SMTP"]["PORT"],
            use_tls=True
        ) as smtp:
            await smtp.login(CONFIG["SMTP"]["USER"], CONFIG["SMTP"]["PASSWORD"])
            await smtp.send_message(message)
        logger.info(f"Email sent: {subject}")
    except Exception as e:
        logger.error(f"Email sending failed: {e}")
        raise

@dp.message(security_filter, F.content_type == "text")
async def handle_text(message: types.Message):
    """Обработчик текстовых сообщений"""
    sender = {
        "name": message.from_user.full_name,
        "username": message.from_user.username
    }

    try:
        email = create_email_template(sender, message.text)
        await send_email(
            subject=f"✉️ Сообщение от {sender['name']}",
            message=email
        )
        await message.reply("✅ Сообщение успешно отправлено на email!")
    except Exception as e:
        logger.error(f"Text handling error: {e}")
        await message.reply("❌ Произошла ошибка при отправке сообщения")

@dp.message(security_filter, F.content_type.in_(["photo", "document"]))
async def handle_files(message: types.Message):
    """Обработчик файлов"""
    sender = {
        "name": message.from_user.full_name,
        "username": message.from_user.username
    }

    file_path = None
    try:
        if message.content_type == "photo":
            file = message.photo[-1]
            ext = ".jpg"
        else:
            file = message.document
            ext = Path(file.file_name or "file.bin").suffix

        file_path = Path(f"temp/{file.file_id}{ext}")
        file_path.parent.mkdir(exist_ok=True)

        await bot.download(file, destination=file_path)

        email = create_email_template(
            sender,
            file_path.name,
            is_file=True
        )

        await send_email(
            subject=f"📎 Файл от {sender['name']}",
            message=email,
            attachment_path=str(file_path)
        )

        await message.reply("✅ Файл успешно отправлен на email!")
    except Exception as e:
        logger.error(f"File handling error: {e}")
        await message.reply("❌ Произошла ошибка при отправке файла")
    finally:
        try:
            if file_path and file_path.exists():
                file_path.unlink()
        except Exception as cleanup_error:
            logger.warning(f"Failed to remove file: {cleanup_error}")

@dp.message()
async def handle_unauthorized(message: types.Message):
    """Обработчик неавторизованных запросов"""
    await message.reply(
        "⛔ Доступ запрещен\n\n"
        f"Ваш ID: {message.from_user.id}\n"
        "Обратитесь к администратору для получения доступа"
    )

async def main():
    logger.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

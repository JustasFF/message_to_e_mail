from telebot import TeleBot  # + custom_filters?
import smtplib, ssl
from datetime import datetime
from email.message import EmailMessage
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
import credits

# Telegram bot token
TOKEN = credits.TOKEN

# Email SMTP configurations
SMTP_SERVER = credits.SMTP_SERVER
SMTP_PORT = credits.SMTP_PORT
EMAIL_USER = credits.EMAIL_USER
EMAIL_PASSWORD = credits.EMAIL_PASSWORD
EMAIL_RECEIVER = credits.EMAIL_RECEIVER
USERS = credits.USERS

bot = TeleBot(TOKEN)
current_date_string = datetime.now().strftime('%m/%d/%y %H:%M:%S')


@bot.message_handler(func=lambda message: True, content_types=['text'])  # Отправка простого текстового сообщения
def handle_message(message):
    chat_id = message.chat.id
    text = message.text

    # Sending the message to the email
    email_message = EmailMessage()
    email_message['Subject'] = f'Сообщение из Telegram от {current_date_string}'
    email_message['From'] = f'"{message.from_user.first_name} {message.from_user.last_name}" <{EMAIL_USER}>'
    email_message['To'] = EMAIL_RECEIVER
    email_message['Date'] = datetime.now().strftime('%m/%d/%y')
    email_message.set_content(f'Прислано из из Telegram:\n{text}')

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as smtp_server:
            smtp_server.login(EMAIL_USER, EMAIL_PASSWORD)
            smtp_server.send_message(email_message)
            smtp_server.quit()
            bot.send_message(chat_id, 'Ок!')
    except Exception as e:
        bot.send_message(chat_id, f'Error: {str(e)}')


@bot.message_handler(content_types=['photo', 'document'])  # Отправка изображения или документа
def handle_message(message):
    global src
    chat_id = message.chat.id

    # Sending the message to the email
    email_message = MIMEMultipart()
    email_message['From'] = f'"{message.from_user.first_name} {message.from_user.last_name}" <{EMAIL_USER}>'
    email_message['To'] = EMAIL_RECEIVER
    email_message['Date'] = formatdate(localtime=True)

    from pathlib import Path
    Path(f'files/{message.chat.id}/').mkdir(parents=True, exist_ok=True)
    if message.content_type == 'photo':
        email_message['Subject'] = f'Изображение из Telegram от {current_date_string}'
        file_info = bot.get_file(message.photo[len(message.photo) - 1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        src = file_info.file_path.replace('photos/', '')
        body = f'{message.content_type.upper()} отправлено из Telegram:\n  {src}'
        email_message.attach(MIMEText(body, "plain"))
        with open(src, 'wb') as bc:
            bc.write(downloaded_file)
        with open(src, 'rb') as bc:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(bc.read())

    if message.content_type == 'document':
        email_message['Subject'] = f'Документ из Telegram от {current_date_string}'
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        src = message.document.file_name
        body = f'{message.content_type.upper()} отправлено из Telegram:\n  {src}'
        email_message.attach(MIMEText(body, "plain"))
        with open(src, 'wb') as bc:
            bc.write(downloaded_file)
        with open(src, 'rb') as bc:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(bc.read())

    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f"attachment; filename={src}",
    )
    email_message.attach(part)
    email_messages = email_message.as_string()

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as smtp_server:
            smtp_server.login(EMAIL_USER, EMAIL_PASSWORD)
            smtp_server.sendmail(EMAIL_USER, EMAIL_RECEIVER, email_messages)
            bot.send_message(chat_id, 'Ок!')
    except Exception as e:
        bot.send_message(chat_id, f'Error: {str(e)}')
    finally:
        file = Path(src)
        file.unlink()


bot.infinity_polling(none_stop=True, interval=3)

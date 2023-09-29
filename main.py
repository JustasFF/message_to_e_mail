import telebot
import smtplib, ssl
from datetime import datetime
from email.message import EmailMessage
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

# Telegram bot token
TOKEN = '6596606037:AAFCMj8d3M9zH-outJF35mb4n4coa1N77YM'

# Email SMTP configurations
SMTP_SERVER = 'smtp.yandex.ru'
SMTP_PORT = 465
EMAIL_USER = '79202281910@yandex.ru'
EMAIL_PASSWORD = 'zzvxgzyasfowyvgu'
EMAIL_RECEIVER = 'justasf16@gmail.com' #'SDimintievskiy@uelements.com'

bot = telebot.TeleBot(TOKEN)
current_date_string = datetime.now().strftime('%m/%d/%y %H:%M:%S')


@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_message(message):
    chat_id = message.chat.id
    text = message.text

    # Sending the message to the email
    email_message = EmailMessage()
    email_message['Subject'] = (f'Сообщение из Telegram от {current_date_string}')
    email_message['From'] = EMAIL_USER
    email_message['To'] = EMAIL_RECEIVER
    email_message['Date'] = formatdate(localtime=True)
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

@bot.message_handler(content_types=['photo', 'document'])
def handle_message(message):
    global src
    chat_id = message.chat.id

    # Sending the message to the email
    email_message = MIMEMultipart()
    email_message['Subject'] = (f'Изображение из Telegram от {current_date_string}')
    email_message['From'] = EMAIL_USER
    email_message['To'] = EMAIL_RECEIVER
    email_message['Date'] = formatdate(localtime=True)
    body = (f'Прислано из Telegram:\n######')
    email_message.attach(MIMEText("None", "plain"))

    from pathlib import Path
    Path(f'files/{message.chat.id}/').mkdir(parents=True, exist_ok=True)
    if message.content_type == 'photo':
        file_info = bot.get_file(message.photo[len(message.photo) - 1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        src = file_info.file_path.replace('photos/', '')
        with open(src, 'wb') as bc:
            bc.write(downloaded_file)
        with open(src, 'rb') as bc:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(bc.read())

    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
    f"attachment; filename={src},"
    )
    email_messages = email_message.as_string()

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as smtp_server:
            smtp_server.login(EMAIL_USER, EMAIL_PASSWORD)
            smtp_server.sendmail(EMAIL_USER, EMAIL_RECEIVER, email_messages)
            smtp_server.quit()
            bot.send_message(chat_id, 'Ок!')
    except Exception as e:
        bot.send_message(chat_id, f'Error: {str(e)}')

bot.infinity_polling(none_stop=True, interval=0, timeout=15)
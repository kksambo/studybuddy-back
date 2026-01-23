import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from dotenv import load_dotenv
import logging

load_dotenv()

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=int(os.getenv("MAIL_PORT")),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS") == "true",
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS") == "true",
    TIMEOUT=30
)

async def send_reminder_email(to: str, title: str, start_time):
    message = MessageSchema(
        subject="⏰ Event Reminder",
        recipients=[to],
        body=f"""
Hi 👋

This is a reminder that your event is starting soon.

📌 Event: {title}
🕒 Starts at: {start_time}

Good luck!
""",
        subtype="plain",
    )

    try:
        fm = FastMail(conf)
        await fm.send_message(message)
        print(f"✅ Email sent to {to}")
    except Exception as e:
        logging.error(f"❌ Email failed: {e}")

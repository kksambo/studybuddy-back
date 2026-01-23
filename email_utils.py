import os
import logging
from twilio.rest import Client

# Twilio credentials from environment variables
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM")  # e.g., "whatsapp:+14155238886"

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

async def send_reminder_email(to: str, title: str, start_time):
    """
    Sends a WhatsApp reminder instead of an email.
    'to' should be the recipient's phone number in international format, e.g., '+27831234567'
    """
    try:
        message = f"Hi 👋\n\nThis is a reminder that your event is starting soon.\n\n" \
                  f"📌 Event: {title}\n🕒 Starts at: {start_time}\n\nGood luck! 🚀"

        client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            body=message,
            to=f"whatsapp:{to}"
        )

        logging.info("✅ WhatsApp message sent successfully")

    except Exception as e:
        logging.error(f"❌ WhatsApp message failed: {e}")

import os
import httpx
import logging

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
MAIL_FROM = os.getenv("MAIL_FROM")

async def send_reminder_email(to: str, title: str, start_time):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": BREVO_API_KEY,
                    "Content-Type": "application/json",
                    "accept": "application/json",
                },
                json={
                    "sender": {"email": MAIL_FROM, "name": "StudyBuddy"},
                    "to": [{"email": to}],
                    "subject": "⏰ Event Reminder",
                    "htmlContent": f"""
                        <p>Hi 👋</p>
                        <p>This is a reminder that your event is starting soon.</p>
                        <ul>
                          <li><strong>Event:</strong> {title}</li>
                          <li><strong>Starts at:</strong> {start_time}</li>
                        </ul>
                        <p>Good luck! 🚀</p>
                    """,
                },
            )

            response.raise_for_status()
            logging.info("✅ Email sent successfully")

    except Exception as e:
        logging.error(f"❌ Email failed: {e}")

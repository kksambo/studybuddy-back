from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import timedelta
from email_utils import send_reminder_email

scheduler = AsyncIOScheduler()

def schedule_event_reminder(event, user_email: str):
    # Convert user's SAST time to UTC for scheduling
    reminder_time = event.start_time - timedelta(minutes=15) - timedelta(hours=2)
    event_start_utc = event.start_time - timedelta(hours=2)

    scheduler.add_job(
        send_reminder_email,
        trigger="date",
        run_date=reminder_time,
        args=[user_email, event.title, event_start_utc],
        id=f"event_{event.id}",
        replace_existing=True
    )

"""
Simulated notification service.

In a real deployment this would integrate with an email provider (SES,
SendGrid) and an SMS gateway (Twilio). For this demo we "send" by logging
a structured message and storing it in an in-memory outbox that the UI
can display, so the notification flow is fully visible without needing
real credentials.
"""
import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger("bookit.notifications")

# In-memory outbox (would be a table or queue in production).
_outbox: List[Dict] = []


class NotificationService:
    @staticmethod
    def send_email(to: str, subject: str, body: str) -> None:
        message = {
            "channel": "email",
            "to": to,
            "subject": subject,
            "body": body,
            "sent_at": datetime.utcnow().isoformat(),
        }
        _outbox.append(message)
        logger.info(f"[SIMULATED EMAIL] To={to} Subject='{subject}'")

    @staticmethod
    def send_sms(to: str, body: str) -> None:
        message = {
            "channel": "sms",
            "to": to,
            "body": body,
            "sent_at": datetime.utcnow().isoformat(),
        }
        _outbox.append(message)
        logger.info(f"[SIMULATED SMS] To={to} Body='{body}'")

    @staticmethod
    def booking_confirmation(booking, resource, customer_email: str) -> None:
        subject = f"Booking Confirmed: {resource.name}"
        body = (
            f"Your booking for {resource.name} is confirmed.\n"
            f"From: {booking.start_time}\nTo: {booking.end_time}\n"
            f"Reference: {booking.reference}"
        )
        NotificationService.send_email(customer_email, subject, body)
        NotificationService.send_sms(customer_email, f"Booking {booking.reference} confirmed for {resource.name}.")

    @staticmethod
    def booking_cancellation(booking, resource, customer_email: str) -> None:
        subject = f"Booking Cancelled: {resource.name}"
        body = f"Your booking {booking.reference} for {resource.name} has been cancelled."
        NotificationService.send_email(customer_email, subject, body)

    @staticmethod
    def booking_rescheduled(booking, resource, customer_email: str, old_start, old_end) -> None:
        subject = f"Booking Rescheduled: {resource.name}"
        body = (
            f"Your booking for {resource.name} was moved.\n"
            f"Was: {old_start} to {old_end}\n"
            f"Now: {booking.start_time} to {booking.end_time}\n"
            f"Reference: {booking.reference}"
        )
        NotificationService.send_email(customer_email, subject, body)

    @staticmethod
    def booking_reminder(booking, resource, customer_email: str) -> None:
        subject = f"Reminder: Upcoming booking for {resource.name}"
        body = f"Reminder: your booking {booking.reference} starts at {booking.start_time}."
        NotificationService.send_email(customer_email, subject, body)

    @staticmethod
    def get_outbox() -> List[Dict]:
        return list(reversed(_outbox[-100:]))  # most recent first

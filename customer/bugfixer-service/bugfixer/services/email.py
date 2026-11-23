import smtplib
from email.message import EmailMessage

from django.conf import settings


def notify_fix(report):
    recipient = report.reporter_email or settings.NOTIFY_EMAIL
    if not recipient or not settings.SMTP_HOST:
        return False

    message = EmailMessage()
    message["Subject"] = f"Your bug report #{report.pk} has a fix"
    message["From"] = settings.SMTP_FROM or settings.SMTP_USER
    message["To"] = recipient
    message.set_content(
        "Thanks for your report. An automated fix has been produced and is awaiting review.\n\n"
        f"Report: {report.message[:1000]}\n"
        f"Pull request: {report.pr_url or 'pending approval'}\n"
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
        if settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(message)
    return True

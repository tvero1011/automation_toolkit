import smtplib
import os
from email.mime.text import MIMEText

from devops.formatting import has_findings, format_alert_body


def send_alert_email(alert_data):
    if not has_findings(alert_data):
        return

    subject_parts = []

    if alert_data.get("down"):
        subject_parts.append(f"{len(alert_data.get('down'))} instance(s) down")
    if alert_data.get("unhealthy"):
        subject_parts.append(f"{len(alert_data.get('unhealthy'))} instance(s) unhealthy")
    if alert_data.get("instance_errors"):
        subject_parts.append(f"{len(alert_data.get('instance_errors'))} instance(s) with errors")
    if alert_data.get("log_errors"):
        error_count = sum(len(errors) for errors in alert_data.get("log_errors").values())
        subject_parts.append(f"{error_count} log error(s)")
    if alert_data.get("api_errors"):
        subject_parts.append(f"{len(alert_data.get('api_errors'))} API endpoint(s) with issues")
    if alert_data.get("connection_errors"):
        subject_parts.append(f"{len(alert_data.get('connection_errors'))} connection error(s)")
    if alert_data.get("bucket_object_check"):
        subject_parts.append(f"{len(alert_data.get('bucket_object_check'))} bucket(s) with issues")

    presub = "ALERT: " if alert_data.get("down") else "Warning: "
    subject = f"{presub}{','.join(subject_parts)}"

    body_lines = format_alert_body(alert_data)

    msg = MIMEText("\n".join(body_lines))
    msg["Subject"] = subject
    msg["From"] = os.environ["ALERT_EMAIL_FROM"]
    msg["To"] = os.environ["ALERT_EMAIL_TO"]

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["ALERT_EMAIL_FROM"], os.environ["ALERT_EMAIL_PASSWORD"])
        server.send_message(msg)

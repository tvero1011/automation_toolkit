import smtplib
import os
from email.mime.text import MIMEText

def send_alert_email(alert_data):
    # sends ONE email if there's anything to report, does nothing if all clear
    if not alert_data.get("down") and not alert_data.get("unhealthy") and not alert_data.get("instance_errors") and not alert_data.get("log_errors"):
        return  # nothing to alert about
    
    subject_parts = []
    presub = ""
    
    if alert_data.get("down"):
        subject_parts.append(f"{len(alert_data.get('down'))} instance(s) down")
    if alert_data.get("unhealthy"):
        subject_parts.append(f"{len(alert_data.get('unhealthy'))} instance(s) unhealthy")
    if alert_data.get("instance_errors"):
        subject_parts.append(f"{len(alert_data.get('instance_errors'))} instance(s) with errors")
    if alert_data.get("log_errors"):
        error_count = sum(len(errors) for errors in alert_data.get("log_errors").values())
        subject_parts.append(f"{error_count} log error(s)")

    if alert_data.get("down"):
        presub = "ALERT: "
    else:
        presub = "Warning: "

    subject = (f"{presub}{','.join(subject_parts)}")


    body_lines = []
    if alert_data.get("down"):
        body_lines.append("Down instances:")
        body_lines.extend(alert_data.get("down"))
    if alert_data.get("unhealthy"):
        body_lines.append("Unhealthy:")
        body_lines.extend(alert_data.get("unhealthy"))
    if alert_data.get("instance_errors"):
        body_lines.append("Instances with errors:")
        body_lines.extend(alert_data.get("instance_errors"))
    if alert_data.get("log_errors"):
        body_lines.append("Log errors:")
        for instance_id, error_lines in alert_data.get("log_errors").items():
            body_lines.append(f" {instance_id}:")
            body_lines.extend(error_lines)

    msg = MIMEText("\n".join(body_lines))
    msg["Subject"] = subject
    msg["From"] = os.environ["ALERT_EMAIL_FROM"]
    msg["To"] = os.environ["ALERT_EMAIL_TO"]

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["ALERT_EMAIL_FROM"], os.environ["ALERT_EMAIL_PASSWORD"])
        server.send_message(msg)
   
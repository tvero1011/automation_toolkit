import smtplib
import os
from email.mime.text import MIMEText

def send_alert_email(down_instances, unhealthy_instances, instance_errors):
    # sends ONE email if there's anything to report, does nothing if all clear
    if not down_instances and not unhealthy_instances and not instance_errors:
        return  # nothing to alert about
    
    subject_parts = []
    presub = ""
    
    if down_instances:
        subject_parts.append(f"{len(down_instances)} instance(s) down")
    if unhealthy_instances:
        subject_parts.append(f"{len(unhealthy_instances)} instance(s) unhealthy")
    if instance_errors:
        subject_parts.append(f"{len(instance_errors)} instance(s) with errors")

    if down_instances:
        presub = "ALERT: "
    else:
        presub = "Warning: "

    subject = (f"{presub}{','.join(subject_parts)}")


    body_lines = []
    if down_instances:
        body_lines.append("Down instances:")
        body_lines.extend(down_instances)
    if unhealthy_instances:
        body_lines.append("Unhealthy instances:")
        body_lines.extend(unhealthy_instances)
    if instance_errors:
        body_lines.append("Instances with errors:")
        body_lines.extend(instance_errors)


    msg = MIMEText("\n".join(body_lines))
    msg["Subject"] = subject
    msg["From"] = os.environ["ALERT_EMAIL_FROM"]
    msg["To"] = os.environ["ALERT_EMAIL_TO"]

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["ALERT_EMAIL_FROM"], os.environ["ALERT_EMAIL_PASSWORD"])
        server.send_message(msg)
   
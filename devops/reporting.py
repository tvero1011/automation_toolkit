import json
import csv
from datetime import datetime


def save_json(alert_data):
    if not alert_data.get("down") and not alert_data.get("unhealthy") and not alert_data.get("instance_errors") and not alert_data.get("log_errors") and not alert_data.get("api_errors") and not alert_data.get("connection_errors") and not alert_data.get("bucket_object_check"):
        return

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
    if alert_data.get("api_errors"):
        body_lines.append("API endpoint issues:")
        for endpoint, status in alert_data.get("api_errors").items():
            body_lines.append(f" {endpoint}: {status}")
    if alert_data.get("connection_errors"):
        body_lines.append("Connection errors:")
        for instance_id, error in alert_data.get("connection_errors").items():
            body_lines.append(f" {instance_id}: {error}")
    if alert_data.get("bucket_object_check"):
        body_lines.append("S3 bucket issues:")
        for bucket_name, issues in alert_data.get("bucket_object_check").items():
            body_lines.append(f" {bucket_name}:")
            body_lines.extend(issues)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{timestamp}.json"       

    with open(filename, "w") as f:
        json.dump(body_lines, f)


def save_csv(alert_data):
    if not alert_data.get("down") and not alert_data.get("unhealthy") and not alert_data.get("instance_errors") and not alert_data.get("log_errors") and not alert_data.get("api_errors") and not alert_data.get("connection_errors") and not alert_data.get("bucket_object_check"):
        return

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
    if alert_data.get("api_errors"):
        body_lines.append("API endpoint issues:")
        for endpoint, status in alert_data.get("api_errors").items():
            body_lines.append(f" {endpoint}: {status}")
    if alert_data.get("connection_errors"):
        body_lines.append("Connection errors:")
        for instance_id, error in alert_data.get("connection_errors").items():
            body_lines.append(f" {instance_id}: {error}")
    if alert_data.get("bucket_object_check"):
        body_lines.append("S3 bucket issues:")
        for bucket_name, issues in alert_data.get("bucket_object_check").items():
            body_lines.append(f" {bucket_name}:")
            body_lines.extend(issues)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{timestamp}.csv"       

    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        for line in body_lines:
            writer.writerow([line])

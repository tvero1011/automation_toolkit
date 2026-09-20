def has_findings(alert_data):
    """True if any check found something worth reporting."""
    return any(
        alert_data.get(key)
        for key in (
            "down",
            "unhealthy",
            "instance_errors",
            "log_errors",
            "api_errors",
            "connection_errors",
            "bucket_object_check",
        )
    )


def format_alert_body(alert_data):
    """Build the human-readable body lines shared by the alert email and
    both report formats. Single source of truth so a change to how one
    section is worded doesn't need to be repeated in three places."""
    body_lines = []

    if alert_data.get("down"):
        body_lines.append("Down instances:")
        body_lines.extend(alert_data["down"])

    if alert_data.get("unhealthy"):
        body_lines.append("Unhealthy:")
        body_lines.extend(alert_data["unhealthy"])

    if alert_data.get("instance_errors"):
        body_lines.append("Instances with errors:")
        body_lines.extend(alert_data["instance_errors"])

    if alert_data.get("log_errors"):
        body_lines.append("Log errors:")
        for instance_id, error_lines in alert_data["log_errors"].items():
            body_lines.append(f" {instance_id}:")
            body_lines.extend(error_lines)

    if alert_data.get("api_errors"):
        body_lines.append("API endpoint issues:")
        for endpoint, status in alert_data["api_errors"].items():
            body_lines.append(f" {endpoint}: {status}")

    if alert_data.get("connection_errors"):
        body_lines.append("Connection errors:")
        for instance_id, error in alert_data["connection_errors"].items():
            body_lines.append(f" {instance_id}: {error}")

    if alert_data.get("bucket_object_check"):
        body_lines.append("S3 bucket issues:")
        for bucket_name, issues in alert_data["bucket_object_check"].items():
            body_lines.append(f" {bucket_name}:")
            body_lines.extend(issues)

    return body_lines

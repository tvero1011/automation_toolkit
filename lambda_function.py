from devops.ec2_monitoring import check_all_instances
from devops.alerts import send_alert_email
from devops.log_monitoring import check_all_logs
from devops.api_monitoring import check_all_endpoints
from devops.s3_monitoring import check_all_buckets
from devops.reporting import save_csv, save_json


def lambda_handler(event, context):
    # Lambda invocations don't have a real command line -- `event` is how
    # config actually gets passed in (e.g. from the EventBridge rule, or a
    # manual test invocation in the console). Reading argparse/sys.argv
    # here (the original bug) meant this always silently fell back to
    # running everything, regardless of what you tried to configure.
    event = event or {}
    check = event.get("check", "all")
    report_format = event.get("format", "both")

    valid_checks = {"ec2", "logs", "api", "s3", "all"}
    valid_formats = {"json", "csv", "both"}
    if check not in valid_checks:
        raise ValueError(f"Invalid 'check' value: {check!r}. Must be one of {valid_checks}")
    if report_format not in valid_formats:
        raise ValueError(f"Invalid 'format' value: {report_format!r}. Must be one of {valid_formats}")

    alert_data = {}

    if check in ("ec2", "all"):
        down, unhealthy, errors = check_all_instances()
        alert_data["down"] = down
        alert_data["unhealthy"] = unhealthy
        alert_data["instance_errors"] = errors

    if check in ("logs", "all"):
        log_errors, conn_errors = check_all_logs()
        alert_data["log_errors"] = log_errors
        alert_data["connection_errors"] = conn_errors

    if check in ("api", "all"):
        alert_data["api_errors"] = check_all_endpoints()

    if check in ("s3", "all"):
        alert_data["bucket_object_check"] = check_all_buckets()

    if report_format in ("json", "both"):
        save_json(alert_data)

    if report_format in ("csv", "both"):
        save_csv(alert_data)

    send_alert_email(alert_data)

    return {"statusCode": 200, "checked": check, "alert_data": alert_data}

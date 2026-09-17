from devops.ec2_monitoring import check_all_instances
from devops.alerts import send_alert_email
from devops.log_monitoring import check_all_logs
from devops.api_monitoring import check_all_endpoints
from devops.s3_monitoring import check_all_buckets
from devops.reporting import save_csv, save_json
import argparse

def lambda_handler(event, context):
    parser = argparse.ArgumentParser(description="DevOps Automation Toolkit")
    parser.add_argument("--check", choices=["ec2", "logs", "api", "s3", "all"], default="all")
    parser.add_argument("--format", choices=["json", "csv", "both"], default="both")
    args = parser.parse_args()

    alert_data = {}

    if args.check in ("ec2", "all"):
        down, unhealthy, errors = check_all_instances()
        alert_data["down"] = down
        alert_data["unhealthy"] = unhealthy
        alert_data["instance_errors"] = errors

    if args.check in ("logs", "all"):
        log_errors, conn_errors = check_all_logs()
        alert_data["log_errors"] = log_errors
        alert_data["connection_errors"] = conn_errors

    if args.check in ("api", "all"):
        alert_data["api_errors"] = check_all_endpoints()

    if args.check in ("s3", "all"):
        alert_data["bucket_object_check"] = check_all_buckets()

    if args.format in ("json", "both"):
        save_json(alert_data)

    if args.format in ("csv", "both"):
        save_csv(alert_data)

    send_alert_email(alert_data)      
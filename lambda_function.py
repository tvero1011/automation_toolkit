from devops.ec2_monitoring import check_all_instances
from devops.alerts import send_alert_email
from devops.log_monitoring import check_all_logs
from devops.api_monitoring import check_all_endpoints

def lambda_handler(event, context):
    down_instances, unhealthy_instances, instance_errors = check_all_instances()
    all_log_errors, connection_error_message = check_all_logs()
    all_endpoints_errors = check_all_endpoints()
    alert_data = {
        "down": down_instances,
        "unhealthy": unhealthy_instances,
        "instance_errors": instance_errors,
        "log_errors": all_log_errors,
        "connection_errors": connection_error_message,
        "api_errors": all_endpoints_errors
    }
    send_alert_email(alert_data)
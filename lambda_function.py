from devops.ec2_monitoring import check_all_instances
from devops.alerts import send_alert_email
from devops.log_monitoring import check_all_logs

def lambda_handler(event, context):
    down_instances, unhealthy_instances, instance_errors = check_all_instances()
    all_log_errors = check_all_logs()
    alert_data = {
        "down": down_instances,
        "unhealthy": unhealthy_instances,
        "instance_errors": instance_errors,
        "log_errors": all_log_errors
    }
    send_alert_email(alert_data)

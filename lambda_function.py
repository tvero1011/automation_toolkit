from devops.aws import check_all_instances
from devops.alerts import send_alert_email

def lambda_handler(event, context):
    down_instances, unhealthy_instances, instance_errors = check_all_instances()
    send_alert_email(down_instances, unhealthy_instances, instance_errors) 

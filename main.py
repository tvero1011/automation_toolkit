from devops.aws import check_all_instances
from devops.alerts import send_alert_email
from dotenv import load_dotenv
load_dotenv()

def main():
    down_instances, unhealthy_instances, instance_errors = check_all_instances()
    send_alert_email(down_instances, unhealthy_instances, instance_errors) 

if __name__ == "__main__":
    main()


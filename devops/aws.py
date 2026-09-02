import boto3

ec2 = boto3.client('ec2')

def get_instance_status(instance_id):
    # checks single instance, returns whether it's healthy or not
    try:
        response = ec2.describe_instances(InstanceIds=[instance_id])
        state = response['Reservations'][0]['Instances'][0]['State']['Name']
    
        if state == 'stopped':
            return "down"

        status_response = ec2.describe_instance_status(InstanceIds=[instance_id])
        instance_status = status_response['InstanceStatuses'][0]['InstanceStatus']['Status']
        system_status = status_response['InstanceStatuses'][0]['SystemStatus']['Status']

        is_healthy = instance_status == 'ok' and system_status == 'ok'
        return "healthy" if is_healthy else "unhealthy"
    except Exception as e:
        print(f"Error checking status for instance {instance_id}: {e}")
        return "error"

def check_all_instances():
    # loops through all 4, collects which ones are down
    down_instances = []
    unhealthy_instances = []
    instance_errors = []
    response = ec2.describe_instances(
        Filters=[{"Name":"tag:monitor", "Values":["true"]}]
    )

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            status = get_instance_status(instance_id)
            if status == "down":
                down_instances.append(instance_id)
            elif status== "unhealthy":
                unhealthy_instances.append(instance_id) 
            elif status == "error":
                instance_errors.append(instance_id)
                print(f"Error checking instance {instance_id}.")
    return down_instances, unhealthy_instances, instance_errors
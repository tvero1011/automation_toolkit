import os
import boto3

ec2 = boto3.client('ec2')


def get_storage_dir():
    """Where checkpoints/reports get written.

    Lambda's deployment package directory is read-only, and /tmp is the
    only writable path inside a Lambda execution environment (it's wiped
    whenever the environment is recycled, but at least the write itself
    succeeds). Locally, just use the current directory unless overridden.
    """
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return "/tmp"
    return os.environ.get("STORAGE_DIR", ".")

def get_tagged_instance_ids():
    response = ec2.describe_instances(
           Filters=[{"Name":"tag:monitor", "Values":["true"]}]
        ) 
    instance_ids = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_ids.append(instance['InstanceId'])
    return instance_ids

def get_instance_ip(instance_id):
    try:
        response = ec2.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]
        return instance['PublicIpAddress']
    except Exception as e:
        return None
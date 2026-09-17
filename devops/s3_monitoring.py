import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta, timezone

s3 = boto3.client('s3')

def check_bucket(bucket_name):
    issues = []

    try:
        policy_status = s3.get_bucket_policy_status(Bucket=bucket_name)
        is_public = policy_status['PolicyStatus']['IsPublic']
        if is_public:
            issues.append("public")
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucketPolicy':
            pass  # no policy = not public via policy, nothing to flag
        else:
            print(f"Error checking bucket {bucket_name}: {e}")
            return "error"

    try:
        s3.get_bucket_encryption(Bucket=bucket_name)
    except ClientError as e:
        if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
            issues.append("no encryption")
        else:
            print(f"Error checking bucket {bucket_name}: {e}")
            return "error"

    try:
        s3.get_bucket_lifecycle_configuration(Bucket=bucket_name)
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchLifecycleConfiguration':
            issues.append("no lifecycle policy")
        else:
            print(f"Error checking bucket {bucket_name}: {e}")
            return "error"
    
    return issues

def check_objects(bucket_name):
    old_objects = []
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)
    try:
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket_name):
            for obj in page.get('Contents', []):
                if obj['LastModified'] < cutoff_date:
                    old_objects.append(obj['Key'])
        return old_objects
    except ClientError as e:
        print(f"Error checking objects in bucket {bucket_name}: {e}")
        return []    
        
def check_all_buckets():
    bucket_issues = {}
    response = s3.list_buckets()

    for bucket in response['Buckets']:
        bucket_name = bucket['Name']
        issues = check_bucket(bucket_name)

        if issues == "error":
            bucket_issues[bucket_name] = ["error checking bucket"]
            continue

        old_objects = check_objects(bucket_name)
        if old_objects:
            issues.append(f"{len(old_objects)} old object(s)")

        if issues:
            bucket_issues[bucket_name] = issues

    return bucket_issues
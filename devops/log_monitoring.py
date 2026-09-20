import socket
import re

import paramiko
import json
import os
from devops.utils import get_tagged_instance_ids
from devops.utils import get_instance_ip
from devops.utils import get_storage_dir


client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

ERROR_PATTERN = re.compile(r"\berror\b", re.IGNORECASE)

# If set, checkpoints persist to S3 instead of local disk. This matters in
# Lambda specifically: /tmp is writable, but it's wiped whenever Lambda
# recycles the execution environment, so a local file alone doesn't
# actually survive between runs the way it does when running this locally
# as a long-lived CLI tool. S3 gives it a durable home either way.
CHECKPOINT_S3_BUCKET = os.environ.get("CHECKPOINT_S3_BUCKET")
CHECKPOINT_S3_KEY = os.environ.get("CHECKPOINT_S3_KEY", "checkpoints.json")


def _checkpoint_path():
    return os.path.join(get_storage_dir(), "checkpoints.json")


def _load_checkpoints():
    if CHECKPOINT_S3_BUCKET:
        import boto3
        s3 = boto3.client("s3")
        try:
            obj = s3.get_object(Bucket=CHECKPOINT_S3_BUCKET, Key=CHECKPOINT_S3_KEY)
            return json.loads(obj["Body"].read())
        except s3.exceptions.NoSuchKey:
            return {}

    try:
        with open(_checkpoint_path(), "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _save_checkpoints(checkpoints):
    if CHECKPOINT_S3_BUCKET:
        import boto3
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=CHECKPOINT_S3_BUCKET,
            Key=CHECKPOINT_S3_KEY,
            Body=json.dumps(checkpoints).encode("utf-8"),
        )
        return

    with open(_checkpoint_path(), "w") as f:
        json.dump(checkpoints, f)


def filter_error_lines(log_lines):
    # takes raw lines, returns only the ones containing the WORD "error"
    # (word-boundary match, not substring -- a plain "error" in line.lower()
    # would false-positive on things like "terrorFlag" since "error" is a
    # substring of "terror")
    error_lines = []
    for line in log_lines:
        if ERROR_PATTERN.search(line):
            error_lines.append(line)
    return error_lines

def get_checkpoint(instance_id):
    return _load_checkpoints().get(instance_id, 0)

def save_checkpoint(instance_id, position):
    checkpoints = _load_checkpoints()
    checkpoints[instance_id] = position
    _save_checkpoints(checkpoints)

def read_new_log_lines(instance_ip, checkpoint_position):
    try:
        username = os.environ["SSH_USERNAME"]
        key_path = os.environ["SSH_KEY_PATH"]
        client.connect(hostname=instance_ip, username=username, key_filename=key_path)
        sftp = client.open_sftp()
        with sftp.open("/var/log/app.log", "r") as f:
            f.seek(checkpoint_position)
            new_content = f.read()
            new_lines = new_content.splitlines()
            new_position = f.tell()
            return new_lines, new_position, None
    except (FileNotFoundError, paramiko.AuthenticationException, paramiko.SSHException, socket.timeout) as e:
        return [], checkpoint_position, e
    finally:
        client.close()

def check_all_logs():
    all_error_lines = {}
    connection_errors ={}
    instance_ids = get_tagged_instance_ids()
    for instance_id in instance_ids:
        instance_ip = get_instance_ip(instance_id)
        checkpoint_position = get_checkpoint(instance_id)
        if instance_ip is not None:
            new_lines, new_position, error_message = read_new_log_lines(instance_ip, checkpoint_position)

            error_lines = filter_error_lines(new_lines)
            if error_lines:
                all_error_lines[instance_id] = error_lines

            if error_message:
                connection_errors[instance_id] = error_message
    
            save_checkpoint(instance_id, new_position)

        else:
            connection_errors[instance_id] ="cant get ip address"

    return all_error_lines, connection_errors

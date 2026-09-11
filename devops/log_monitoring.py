import socket

import paramiko
import json
import os
from devops.utils import get_tagged_instance_ids
from devops.utils import get_instance_ip


client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())



def filter_error_lines(log_lines):
    # takes raw lines, returns only the ones containing "ERROR"
    error_lines = []
    for line in log_lines:
        if "error" in line.lower():
            error_lines.append(line)
    return error_lines

def get_checkpoint(instance_id):
    try:
        with open("checkpoints.json", "r") as f:
            checkpoints = json.load(f)
            return checkpoints.get(instance_id, 0)
    except FileNotFoundError:
        return 0
          
def save_checkpoint(instance_id, position): 
    try:
        with open("checkpoints.json", "r") as f:
            checkpoints = json.load(f)
    except FileNotFoundError:
        checkpoints = {}

    checkpoints[instance_id] = position
    with open("checkpoints.json", "w") as f:
        json.dump(checkpoints, f)

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

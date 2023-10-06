import sys
import paramiko
import time
import os

from googleapiclient import discovery
from google.oauth2.service_account import Credentials


def authenticate_vm(path):
    credentials = Credentials.from_service_account_file(path)
    return discovery.build("compute", "v1", credentials=credentials)


def _start_ssh_session(response, creds, username, passphrase):
    external_ip = response["networkInterfaces"][0]["accessConfigs"][0]["natIP"]
    print(external_ip)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh.connect(
        external_ip,
        username=username,
        key_filename=creds,
        passphrase=passphrase,
    )

    # Open an SSH session
    transport = ssh.get_transport()
    channel = transport.open_session()

    # Execute the command on the instance in the background
    command = "cd actions-runner; nohup ./run.sh"
    channel.exec_command(command)

    # Close the SSH channel and session immediately
    ssh.close()


def start_runner(
    creds,
    ssh_creds,
    ssh_user,
    key_passphrase,
    id="gpu-insatnce",
    zone="us-central1-a",
    instance="demos-tests",
):
    compute = authenticate_vm(creds)
    request = compute.instances().start(project=id, zone=zone, instance=instance)
    request.execute()

    max_wait_time = 600
    wait_interval = 10
    waited_time = 0
    response = None

    while waited_time < max_wait_time:
        response = (
            compute.instances().get(project=id, zone=zone, instance=instance).execute()
        )
        status = response.get("status")

        if status == "RUNNING":
            break

        time.sleep(wait_interval)
        waited_time += wait_interval

    if waited_time >= max_wait_time:
        raise Exception(f"Instance {instance} did not start within the expected time.")

    # Once the instance is running, start the SSH session
    _start_ssh_session(response, ssh_creds, ssh_user, key_passphrase)


def stop_runner(creds):
    compute = authenticate_vm(creds)
    request = compute.instances().start(
        project="gpu-insatnce", zone="us-central1-a", instance="demos-tests"
    )
    request.execute()


if __name__ == "__main__":
    ssh_user, key_passphrase, stop_vm = sys.argv[1], sys.argv[2], sys.argv[3]
    gcp_credentials = "gcp_auth.json"
    ssh_credentials = "~/.ssh/id_rsa"

    if stop_vm == "true":
        # Stop the instance
        stop_runner(gcp_credentials)
    else:
        # Start the instance
        ssh_key_path = os.path.expanduser(ssh_credentials)
        start_runner(gcp_credentials, ssh_key_path, ssh_user, key_passphrase)

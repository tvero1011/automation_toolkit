# Setup Guide

Everything you need to configure before running this tool locally.

## 1. AWS Credentials (for `boto3`)

This tool needs read access to EC2 and S3 via `boto3`. `boto3` looks for credentials automatically; you don't pass them in code.

**Option A: AWS SSO (recommended, temporary credentials, no keys stored on disk):**

Log in, then tell your shell which profile and region to use. Do this in **every** terminal window you run the tool from:

```powershell
# Windows PowerShell
aws sso login --profile tf-dev
$env:AWS_PROFILE = "tf-dev"
$env:AWS_DEFAULT_REGION = "us-east-1"
```
```bash
# macOS / Linux
aws sso login --profile tf-dev
export AWS_PROFILE=tf-dev
export AWS_DEFAULT_REGION=us-east-1
```
Then get your public IP by opening https://checkip.amazonaws.com in a browser. Write it down.

Check that it works (it should print your account ID):
```bash
aws sts get-caller-identity
```
If your session has expired, run `aws sso login --profile tf-dev` again.

> **Set the profile and region in the shell, not only in `.env`.** The toolkit creates its boto3 clients when its modules are imported, which happens before `.env` is loaded.

**Option B: AWS CLI with an IAM user:**
```bash
aws configure
```
This prompts for your Access Key ID, Secret Access Key, and default region, and stores them in `~/.aws/credentials`.

**Do not put `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` in `.env` if you use SSO.** Credentials in environment variables take priority over your SSO profile, so placeholder values will cause `InvalidClientTokenId` errors.

**IAM permissions needed (read-only):**
- EC2: `AmazonEC2ReadOnlyAccess`, or a custom policy covering `ec2:DescribeInstances` and `ec2:DescribeInstanceStatus`
- S3 (for the bucket audit): `AmazonS3ReadOnlyAccess`, or a custom policy covering `s3:ListAllMyBuckets`, `s3:ListBucket`, `s3:GetBucketPolicyStatus`, `s3:GetEncryptionConfiguration` and `s3:GetLifecycleConfiguration`

**Tag your instances:** this tool only checks instances tagged for monitoring. On each EC2 instance you want monitored, add a tag:
```
Key: monitor
Value: true
```

## 2. Gmail App Password (for email alerts)

Alerts are sent via Gmail SMTP (`smtplib`). Gmail requires an **app password**, not your regular account password, for this kind of access.

1. Enable 2-Step Verification on the Google account you'll send alerts from (required before app passwords are available)
2. Go to your Google Account → Security → 2-Step Verification → App passwords
3. Generate a new app password (name it something like "devops-toolkit")
4. Copy the 16-character password. You'll use this as `ALERT_EMAIL_PASSWORD`, not your real Gmail password

`ALERT_EMAIL_TO` can be the same address as `ALERT_EMAIL_FROM` if you just want to send alerts to yourself.

## 3. SSH Key (for log monitoring)

The log monitoring feature connects to each EC2 instance over SSH to read its application log (`/var/log/app.log`).

1. Use the `.pem` key pair associated with your EC2 instances, or generate a dedicated one for monitoring. (If you use the test stack in section 6, Terraform generates the key and saves it as `toolkit-test-key.pem` for you.)
2. Save the private key file somewhere accessible locally, e.g. `~/.ssh/devops-toolkit-key.pem`
3. Restrict its permissions on macOS/Linux (required by SSH, or connections will be refused):
   ```bash
   chmod 400 ~/.ssh/devops-toolkit-key.pem
   ```
4. Make sure the EC2 instances' security group allows inbound SSH (port 22) **from your own IP only**, never `0.0.0.0/0`
5. Confirm the SSH username matches the instance's AMI (`ec2-user` for Amazon Linux, `ubuntu` for Ubuntu, etc.)

## 4. Environment Variables

Copy `.env.example` to `.env` and fill in real values:
```bash
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
```

With SSO, your `.env` needs only these values (no AWS access key or secret):
```
# AWS (region only; credentials come from your SSO profile)
AWS_DEFAULT_REGION=us-east-1

# Email alerts
ALERT_EMAIL_FROM=youraddress@gmail.com
ALERT_EMAIL_PASSWORD=your-16-char-app-password
ALERT_EMAIL_TO=recipient@example.com

# SSH / log monitoring
SSH_USERNAME=ec2-user
SSH_KEY_PATH=/absolute/path/to/your-key.pem
```

`.env` is loaded via `python-dotenv` and should **never** be committed to the repo. It's already covered by `.gitignore`. Hide the password if you take screenshots of it.

Add these generated files to `.gitignore` as well:
```
checkpoints.json
report_*.json
report_*.csv
```

## 5. Verify Everything Works

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```
```bash
# macOS / Linux
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

You can also run one check at a time: `python main.py --check ec2` (or `logs`, `api`, `s3`), and choose the report format with `--format json|csv|both`.

If no instances are down/unhealthy and no new log errors are found, the tool runs silently (no email sent). That's expected behavior, not a failure. To confirm alerting itself works end-to-end, you can temporarily stop a tagged test instance or add an `ERROR` line to its log file and re-run.

Notes:
- A freshly launched instance has no status checks for about 5 minutes. Until then it is reported as an instance error rather than healthy.
- The log check remembers how far it has read in `checkpoints.json`. Delete that file to re-scan logs from the start.
- The S3 audit checks **every** bucket in the account, not just test ones.
- The API check currently calls `https://example.com/api/...`, so all endpoints show as down until you change the base URL in `devops/api_monitoring.py`.

To run the test suite instead (no real AWS/SSH/email access required):
```bash
pytest -v
```

## 6. Optional: Disposable Test Infrastructure (apply and destroy)

The `toolkit-test-infra/` Terraform folder creates a tiny test environment so you can prove the toolkit works without touching real systems:
- one `t3.micro` EC2 instance tagged `monitor=true`, with a log file containing an `ERROR` line
- an SSH key (generated by Terraform) and a security group allowing SSH only from your IP
- one S3 bucket for the auditor to find

Cost is roughly a cent per hour. Destroy it the same day.

```powershell
cd toolkit-test-infra
terraform init
terraform apply -var="my_ip_cidr=YOUR.IP.HERE/32"     # find your IP: https://checkip.amazonaws.com
terraform output env_for_toolkit                      # copy the SSH lines into the toolkit's .env
```

Wait about 5 minutes, run the toolkit from the project folder with the venv active, then clean up:

```powershell
terraform destroy -var="my_ip_cidr=YOUR.IP.HERE/32"
```

See `toolkit-test-infra/RUNBOOK.md` for the full proof sequence. Terraform is a separate program, so it does not run inside `.venv` and does not need the venv activated.

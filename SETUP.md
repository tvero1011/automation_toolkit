# Setup Guide

Everything you need to configure before running this tool locally.

## 1. AWS Credentials (for `boto3`)

This tool needs read access to EC2 via `boto3`. `boto3` looks for credentials automatically — you don't pass them in code.

**Option A — AWS CLI (recommended):**
```bash
aws configure
```
This prompts for your Access Key ID, Secret Access Key, and default region, and stores them in `~/.aws/credentials`.

**Option B — Environment variables:**
```
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=us-east-1
```

**IAM permissions needed:** attach `AmazonEC2ReadOnlyAccess` (or a custom least-privilege policy covering `ec2:DescribeInstances` and `ec2:DescribeInstanceStatus`) to whichever IAM user/role you're using.

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
4. Copy the 16-character password — you'll use this as `ALERT_EMAIL_PASSWORD`, not your real Gmail password

## 3. SSH Key (for log monitoring)

The log monitoring feature connects to each EC2 instance over SSH to read its application log.

1. Use the same `.pem` key pair associated with your EC2 instances (created/downloaded when the instances were launched), or generate a dedicated key pair for monitoring
2. Save the private key file somewhere accessible locally, e.g. `~/.ssh/devops-toolkit-key.pem`
3. Restrict its permissions (required by SSH, or connections will be refused):
   ```bash
   chmod 400 ~/.ssh/devops-toolkit-key.pem
   ```
4. Make sure the EC2 instances' security group allows inbound SSH (port 22) from wherever this tool runs
5. Confirm the SSH username matches the instance's AMI (`ec2-user` for Amazon Linux, `ubuntu` for Ubuntu, etc.)

## 4. Environment Variables

Copy `.env.example` to `.env` and fill in real values:
```bash
cp .env.example .env
```

```
# Email alerts
ALERT_EMAIL_FROM=youraddress@gmail.com
ALERT_EMAIL_PASSWORD=your-16-char-app-password
ALERT_EMAIL_TO=recipient@example.com

# SSH / log monitoring
SSH_USERNAME=ec2-user
SSH_KEY_PATH=/absolute/path/to/your-key.pem
```

`.env` is loaded via `python-dotenv` and should **never** be committed to the repo — it's already covered by `.gitignore`.

## 5. Verify Everything Works

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

If no instances are down/unhealthy and no new log errors are found, the tool runs silently (no email sent) — that's expected behavior, not a failure. To confirm alerting itself works end-to-end, you can temporarily stop a tagged test instance or add an `ERROR` line to its log file and re-run.

To run the test suite instead (no real AWS/SSH/email access required):
```bash
pytest -v
```

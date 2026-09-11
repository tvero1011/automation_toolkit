# DevOps Automation Toolkit

A serverless AWS automation tool that monitors infrastructure and application health, and sends automatic email alerts when something needs attention — replacing manual, reactive server checking.

## Architecture

```
EventBridge (every 5 min)
        ↓
   AWS Lambda
        ↓
Check tagged EC2 instances (state + CloudWatch status)
Check each instance's application log over SSH (new errors since last check)
        ↓
Any down / unhealthy / errored / new log errors / unreachable instances?
        ↓
   Yes → send one alert email (severity-based subject)
   No  → do nothing
```

---

## Feature 1: EC2 Health Check & Alert

### The Problem
A small e-commerce startup running on AWS had no automated way to know when a server went down. Outages were discovered reactively — often through customer complaints, sometimes hours later. One undetected 3-hour outage directly cost lost sales.

### What This Does
Automatically checks all tagged EC2 instances every 5 minutes and emails an alert the moment one goes down or becomes unhealthy — cutting detection time from hours to minutes, with zero manual checking required.

### Key Design Decisions
- **Serverless (AWS Lambda + EventBridge)** instead of a cron job on a dedicated server — no infrastructure to provision or maintain. Cost stays near-zero since Lambda only runs (and is only billed) for the few seconds it takes to check instances every 5 minutes.
- **Tag-based instance discovery** (`monitor: true`) instead of hardcoded instance IDs — the tool automatically picks up any newly tagged instance, scaling with the client's infrastructure without requiring code changes.
- **Two health signals, not one** — instance state (stopped/running) *and* CloudWatch's `InstanceStatus`/`SystemStatus` checks. A server can be "running" but still unhealthy underneath, so relying on state alone would miss real problems.
- **One combined alert email**, with subject-line severity (`ALERT` for down instances, `Warning` for unhealthy-only) — rather than separate emails per severity, which would add complexity the client never asked for.
- **Fail-fast vs. fail-gracefully** — unrecoverable setup errors (e.g., can't connect to AWS at all) are allowed to crash loudly and immediately. Per-instance check failures are caught and logged, so one bad instance never prevents the rest from being checked.

---

## Feature 2: Application Log Monitoring

### The Problem
The client's application logs (`/var/log/myapp/app.log` on each instance) could contain real errors — like failed payment transactions — that never show up as an EC2 health issue. Marcus only found out about one such incident when a customer emailed him.

### What This Does
For each tagged instance, resolves its public IP, connects over SSH, and reads its application log via SFTP — picking up only new content since the last checkpoint. New lines are filtered for anything containing "ERROR" (case-insensitive) and included in the same alert email as the EC2 health checks. An instance that can't be reached — no resolvable IP, a failed SSH connection, or an authentication error — is recorded separately and skipped, rather than stopping the check for every other instance.

### Key Design Decisions
- **Checkpoint-based reading (byte offset, stored in `checkpoints.json`)** instead of re-reading the whole file every time — the log file is never rotated or archived, so it only grows; re-scanning it fully on every check would get slower over time and re-report the same old errors repeatedly.
- **One shared checkpoint file, not one per instance** — simpler to manage as the number of monitored instances grows, at the cost of a small, documented risk: if this file is lost or corrupted, the next run re-scans each log from the beginning. Considered a database (SQLite) for this, but chose the simpler file-based approach since the risk is low-severity and easily recoverable — a database would be a reasonable future upgrade, not a requirement for the MVP.
- **SFTP over `exec_command`** for reading the remote log — SFTP exposes a file-like object supporting `.seek()`/`.read()`/`.tell()`, so the existing checkpoint logic (designed around local `open()` semantics) carried over almost unchanged, instead of needing to diff full-file output on every run.
- **Two separate failure trackers, not one** — log content errors (`all_error_lines`) and connection/reachability errors (`all_error_message`) are collected independently. A missing IP or failed SSH login is a fundamentally different problem from a log line that says "ERROR," and conflating them made the alerting logic ambiguous during development.
- **Fail-open per instance, not per run** — an unresolved IP or SSH failure on one instance is caught, recorded, and skipped, so the rest of the fleet is still checked and alerted on in the same run.
- **`finally`-based connection cleanup** — the SSH/SFTP connection is closed in a `finally` block so it's released whether the read succeeds, fails, or hits an unexpected exception, avoiding leaked connections across repeated checks.
- **One combined `alert_data` dictionary** passed into `send_alert_email()`, instead of an ever-growing list of function parameters — keeps the alerting function stable as more alert categories (like this one) get added.
- **Shared `get_tagged_instance_ids()` helper** (`devops/utils.py`), extracted from Feature 1's instance-discovery logic, so both features stay in sync with the same tagging convention without duplicating boto3 filtering code.

---

## Tech Stack

- Python 3
- `boto3` (AWS SDK)
- `paramiko` (SSH/SFTP — remote log file access)
- AWS Lambda + EventBridge (scheduling)
- AWS IAM (least-privilege `AmazonEC2ReadOnlyAccess`)
- `smtplib` (email alerts)
- `python-dotenv` (local credential management)
- `pytest` + `unittest.mock` (testing)

## Setup

See [SETUP.md](./SETUP.md) for full instructions on configuring AWS credentials, Gmail app passwords, SSH keys, and environment variables.

Quick start (local):
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # then fill in your real values
python main.py
```

Required environment variables:
- `ALERT_EMAIL_FROM`, `ALERT_EMAIL_PASSWORD`, `ALERT_EMAIL_TO`
- `SSH_USERNAME`, `SSH_KEY_PATH`

## Testing

This project is tested entirely with mocked AWS, email, filesystem, and SSH/SFTP calls — no real AWS credentials, live SSH access, or running infrastructure required to run the test suite.

```bash
pip install pytest
pytest -v
```

**Coverage (15 tests across 3 files):**
- `tests/test_ec2_monitoring.py` — `get_instance_status()` (down/healthy/unhealthy/error) and `check_all_instances()` sorting logic
- `tests/test_log_monitoring.py` — error-line filtering; checkpoint read/write (found, default, missing-file); SSH/SFTP-based log reading including a simulated authentication failure; and full orchestration via `check_all_logs()`, including the case where an instance's IP can't be resolved
- `tests/test_utils.py` — shared tagged-instance lookup

## Deployment (AWS Lambda)

1. Create a Lambda function with an execution role that has `AmazonEC2ReadOnlyAccess`
2. Set environment variables (`ALERT_EMAIL_FROM`, `ALERT_EMAIL_PASSWORD`, `ALERT_EMAIL_TO`, `SSH_USERNAME`, `SSH_KEY_PATH`) in the Lambda console
3. Upload `lambda_function.py` along with the `devops/` package, and set the handler to `lambda_function.lambda_handler`
4. Add an EventBridge trigger with schedule expression `rate(5 minutes)`

**Note:** SSH access from Lambda requires the monitored instances to be reachable from wherever Lambda runs (VPC networking/security groups) and the private key to be available to the function (e.g., via a securely mounted secret, not bundled in code).

## Lessons Learned

- Mocking (`unittest.mock.patch`) makes it possible to fully test AWS- and SSH-dependent logic without live infrastructure, cost, or flakiness.
- Small architectural decisions (like separating "check one instance" from "check all instances") ripple through a codebase — adding a third status category required updates across three functions, not just one.
- Real client requirements are rarely fully specified upfront; the "5-minute vs. hourly" interval decision changed once actual Lambda cost data was considered instead of an assumption.
- Two categories of failure need to be tracked separately, not merged into one bucket: content the check finds (e.g. an ERROR line in a log) versus the check itself failing to run (e.g. an instance being unreachable over SSH). Conflating them into a single error collection made the alerting logic ambiguous — the fix was two independent dictionaries, one per failure type, mirroring how EC2 health checks already separated "unhealthy" from "errored."

## Future Improvements

- API/website uptime monitoring (confirming the app responds to users, not just that the server is running)
- Configurable alert thresholds (e.g., only alert if down for more than N minutes, to reduce noise from brief blips)
- Checkpoint storage upgrade (e.g., SQLite) if the JSON file's corruption risk becomes an actual issue at scale
- Host key verification for SSH (currently uses `AutoAddPolicy`, which trades stronger security for automation convenience — worth tightening before production use)
- Serialize connection errors as plain strings/structured data rather than raw exception objects, ahead of the planned Reporting feature (JSON/CSV export) and any future inclusion in the alert email body

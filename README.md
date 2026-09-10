# DevOps Automation Toolkit — EC2 Health Check & Alert

A serverless AWS automation tool that monitors EC2 instances and sends automatic email alerts when something goes down or becomes unhealthy — replacing manual, reactive server checking.

## The Problem

A small e-commerce startup running on AWS had no automated way to know when a server went down. Outages were discovered reactively — often through customer complaints, sometimes hours later. One undetected 3-hour outage directly cost lost sales.

## What This Tool Does

Automatically checks all tagged EC2 instances every 5 minutes and emails an alert the moment one goes down or becomes unhealthy — cutting detection time from hours to minutes, with zero manual checking required.

```
EventBridge (every 5 min)
        ↓
   AWS Lambda
        ↓
Check tagged EC2 instances (state + CloudWatch status)
        ↓
Any down / unhealthy / errored?
        ↓
   Yes → send one alert email (severity-based subject)
   No  → do nothing
```

## Key Design Decisions

- **Serverless (AWS Lambda + EventBridge)** instead of a cron job on a dedicated server — no infrastructure to provision or maintain. Cost stays near-zero since Lambda only runs (and is only billed) for the few seconds it takes to check instances every 5 minutes.
- **Tag-based instance discovery** (`monitor: true`) instead of hardcoded instance IDs — the tool automatically picks up any newly tagged instance, scaling with the client's infrastructure without requiring code changes.
- **Two health signals, not one** — instance state (stopped/running) *and* CloudWatch's `InstanceStatus`/`SystemStatus` checks. A server can be "running" but still unhealthy underneath, so relying on state alone would miss real problems.
- **One combined alert email**, with subject-line severity (`ALERT` for down instances, `Warning` for unhealthy-only) — rather than separate emails per severity, which would add complexity the client never asked for.
- **Fail-fast vs. fail-gracefully** — unrecoverable setup errors (e.g., can't connect to AWS at all) are allowed to crash loudly and immediately. Per-instance check failures are caught and logged, so one bad instance never prevents the rest from being checked.

## Tech Stack

- Python 3
- `boto3` (AWS SDK)
- AWS Lambda + EventBridge (scheduling)
- AWS IAM (least-privilege `AmazonEC2ReadOnlyAccess`)
- `smtplib` (email alerts)
- `python-dotenv` (local credential management)
- `paramiko` (planned — SSH-based log file access)
- `pytest` + `unittest.mock` (testing)

## Setup

See [SETUP.md](./SETUP.md) for full instructions on configuring AWS credentials, Gmail app passwords, and environment variables.

Quick start (local):
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # then fill in your real values
python main.py
```

## Testing

This project is tested entirely with mocked AWS/email/file calls — no real AWS credentials, SSH access, or live infrastructure required to run the test suite.

```bash
pip install pytest
pytest -v
```

**Coverage (13 tests across 3 files):**
- `tests/test_ec2_monitoring.py` — `get_instance_status()` (down/healthy/unhealthy/error) and `check_all_instances()` sorting logic
- `tests/test_log_monitoring.py` — error-line filtering, checkpoint read/write (found, default, missing-file), log reading, and full orchestration via `check_all_logs()`
- `tests/test_utils.py` — shared tagged-instance lookup

## Deployment (AWS Lambda)

1. Create a Lambda function with an execution role that has `AmazonEC2ReadOnlyAccess`
2. Set environment variables (`ALERT_EMAIL_FROM`, `ALERT_EMAIL_PASSWORD`, `ALERT_EMAIL_TO`) in the Lambda console
3. Upload `lambda_function.py` along with the `devops/` package, and set the handler to `lambda_function.lambda_handler`
4. Add an EventBridge trigger with schedule expression `rate(5 minutes)`

## Lessons Learned

- Mocking (`unittest.mock.patch`) makes it possible to fully test AWS-dependent logic without live infrastructure, cost, or flakiness.
- Small architectural decisions (like separating "check one instance" from "check all instances") ripple through a codebase — adding a third status category required updates across three functions, not just one.
- Real client requirements are rarely fully specified upfront; the "5-minute vs. hourly" interval decision changed once actual Lambda cost data was considered instead of an assumption.

## Feature 2: Application Log Monitoring

The client's application logs (`/var/log/myapp/app.log` on each instance) could contain real errors — like failed payment transactions — that never show up as an EC2 health issue. Marcus only found out about one such incident when a customer emailed him.

**What it does:** periodically reads each tagged instance's log file, checks for new lines since the last check, filters for anything containing "ERROR" (case-insensitive), and includes any findings in the same alert email as the EC2 health checks.

**Key design decisions:**
- **Checkpoint-based reading (byte offset, stored in `checkpoints.json`)** instead of re-reading the whole file every time — the log file is never rotated or archived, so it only grows; re-scanning it fully on every check would get slower over time and re-report the same old errors repeatedly.
- **One shared checkpoint file, not one per instance** — simpler to manage as the number of monitored instances grows, at the cost of a small, documented risk: if this file is lost or corrupted, the next run re-scans each log from the beginning. Considered a database (SQLite) for this, but chose the simpler file-based approach since the risk is low-severity and easily recoverable — a database would be a reasonable future upgrade, not a requirement for the MVP.
- **One combined `alert_data` dictionary** passed into `send_alert_email()`, instead of an ever-growing list of function parameters — keeps the alerting function stable as more alert categories (like this one) get added.
- **Shared `get_tagged_instance_ids()` helper** (`devops/utils.py`), extracted from Feature 1's instance-discovery logic, so both features stay in sync with the same tagging convention without duplicating boto3 filtering code.

**Known limitation:** log access is designed around SSH (not yet connected to a live instance — built and fully tested against a local file and mocked SSH behavior). Real SSH credentials from the client are still pending.

## Future Improvements

- Real SSH/paramiko connection for live log fetching (currently reads a local file for development/testing)
- API/website uptime monitoring (confirming the app responds to users, not just that the server is running)
- Configurable alert thresholds (e.g., only alert if down for more than N minutes, to reduce noise from brief blips)
- Checkpoint storage upgrade (e.g., SQLite) if the JSON file's corruption risk becomes an actual issue at scale

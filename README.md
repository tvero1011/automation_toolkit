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

This project is tested entirely with mocked AWS/email calls — no real AWS credentials or live infrastructure required to run the test suite.

```bash
pip install pytest
pytest tests/test_aws.py -v
```

**Coverage:**
- `get_instance_status()` — all four possible outcomes: down, healthy, unhealthy, error
- `check_all_instances()` — correct sorting/looping logic across multiple instances

## Deployment (AWS Lambda)

1. Create a Lambda function with an execution role that has `AmazonEC2ReadOnlyAccess`
2. Set environment variables (`ALERT_EMAIL_FROM`, `ALERT_EMAIL_PASSWORD`, `ALERT_EMAIL_TO`) in the Lambda console
3. Upload `lambda_function.py` along with the `devops/` package, and set the handler to `lambda_function.lambda_handler`
4. Add an EventBridge trigger with schedule expression `rate(5 minutes)`

## Lessons Learned

- Mocking (`unittest.mock.patch`) makes it possible to fully test AWS-dependent logic without live infrastructure, cost, or flakiness.
- Small architectural decisions (like separating "check one instance" from "check all instances") ripple through a codebase — adding a third status category required updates across three functions, not just one.
- Real client requirements are rarely fully specified upfront; the "5-minute vs. hourly" interval decision changed once actual Lambda cost data was considered instead of an assumption.

## Future Improvements

- Log analysis (parsing application error logs, not just infrastructure state)
- API/website uptime monitoring (confirming the app responds to users, not just that the server is running)
- Configurable alert thresholds (e.g., only alert if down for more than N minutes, to reduce noise from brief blips)
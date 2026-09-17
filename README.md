# DevOps Automation Toolkit

A small AWS automation tool I built to practice real-world DevOps/cloud skills. It checks EC2 health, reads application logs over SSH, checks API endpoints, and audits S3 buckets — then sends one email alert if anything needs attention, and saves a report of the results.

I built this by simulating real client requests (not from a tutorial), one feature at a time, learning the Python/AWS concepts I needed as each feature actually required them.

## Architecture

```
EventBridge (every 5 min)
        ↓
   AWS Lambda
        ↓
Check tagged EC2 instances (state + CloudWatch status)
Check each instance's application log over SSH/SFTP (new errors since last check)
Check business-critical API endpoints (availability + response time)
Audit S3 buckets (public access, encryption, lifecycle policy, stale objects)
        ↓
Anything wrong?
        ↓
   Yes → send one alert email + save a report (JSON/CSV)
   No  → do nothing
```

Can also be run manually from the command line with flags to check just one thing at a time (see CLI section below).

---

## Feature 1: EC2 Health Check & Alert

**The problem:** the client had no way to know when a server went down except customers complaining. One outage went unnoticed for 3 hours.

**What it does:** checks every tagged EC2 instance every 5 minutes (instance state + CloudWatch status), and emails an alert if one goes down or becomes unhealthy.

**Notes on how it's built:**
- Runs on AWS Lambda + EventBridge instead of a dedicated server running cron — no server to maintain, and Lambda only costs money for the few seconds it actually runs.
- Instances are found by an AWS tag (`monitor: true`), not hardcoded IDs, so new servers get picked up automatically.
- Checks two things per instance (is it stopped? is CloudWatch reporting it healthy?) and combines them into one status: down / healthy / unhealthy.
- If checking one instance fails (AWS error, timeout, etc.), it's caught and logged instead of crashing the whole run — one bad instance doesn't stop the rest from being checked.

---

## Feature 2: Application Log Monitoring

**The problem:** the app itself can have real errors (like failed payments) that don't show up as an EC2 health issue at all.

**What it does:** for each tagged instance, gets its IP, connects over SSH, and reads its log file (`/var/log/app.log`) — but only the *new* part since the last check, using a saved byte position (a "checkpoint") so it doesn't re-read the whole file every time. New lines containing "ERROR" get included in the alert email.

**Notes on how it's built:**
- Checkpoints are stored in one shared `checkpoints.json` file (`{instance_id: byte_position}`). Considered using a small database (SQLite) instead, but a plain JSON file is simpler and the downside (if it's ever lost, the next run just re-scans from the start) is low-risk for this use case.
- Reads the file over SFTP, which gives a file-like object I can `.seek()`/`.read()`/`.tell()` on — basically the same as reading a local file, which made this easier to reuse the checkpoint logic I'd already built.
- If an instance can't be reached (no IP, bad SSH login, etc.), that's tracked *separately* from actual log errors — "couldn't check this" and "found a real error" are different problems and mixing them together made the alert logic confusing.
- SSH connection is always closed in a `finally` block, so it closes even if something goes wrong mid-check.

---

## Feature 3: API Health Checker

**The problem:** the checkout API went down for ~20 minutes and nobody noticed until customers emailed support.

**What it does:** checks 4 endpoints (`/api/checkout`, `/api/login`, `/api/products`, `/api/cart`) every 5 minutes. Flags an endpoint as **down** if it errors out or fails to respond, or **slow** if it responds but takes 5+ seconds.

**Notes on how it's built:**
- One function (`check_endpoint`) checks both "did it respond" and "how long did it take" together, and returns one combined result (up/slow/down) — same pattern as the EC2 check.
- The 5-second "slow" threshold is a parameter with a default, not hardcoded, since the client wasn't even fully sure 5 seconds was the right number.
- Retries a failed request up to 3 times (waiting a bit longer each time) before actually calling it "down" — a single dropped connection shouldn't trigger a false alarm.
- Every request has a timeout, so one hung endpoint can't stall the whole check.

---

## Feature 4: S3 Bucket Auditor

**The problem:** none of the other checks say anything about cost or security risk sitting in storage — a public bucket, unencrypted data, or years of old files nobody's cleaning up.

**What it does:** checks every S3 bucket for public access, missing encryption, and no lifecycle policy, and separately flags objects that haven't been touched in 90+ days.

**Notes on how it's built:**
- Same pattern as Feature 1 — one function checks a single bucket and absorbs its own errors, returning either a list of problems found or `"error"`.
- AWS actually throws an error when a bucket has *no* policy/encryption/lifecycle rule set up at all (instead of just saying "not public" etc.) — those specific "not configured" errors are treated as a normal finding, not a real failure. Any other unexpected error still gets flagged as an actual error.
- Listing objects in a bucket only returns up to 1,000 at a time by default, with no warning if there's more — had to use boto3's paginator to make sure large buckets actually get fully checked instead of silently only checking the first page.
- Old objects are reported as a count ("42 old object(s)"), not a full list of filenames — a bucket with thousands of stale files would make the email unreadable otherwise.

---

## Feature 5: Reporting (JSON/CSV)

**What it does:** after everything runs, saves the same results that went into the alert email as a timestamped `.json` and/or `.csv` file (`report_20260917_143022.json`), so there's a record beyond just the email.

**Notes on how it's built:**
- A new file gets created each run rather than appending to one growing file — simpler, and avoids one big file getting messy or corrupted over time.
- CSV output uses Python's `csv` module properly (not just dumping JSON text into a `.csv` file, which I did by mistake at first) — each line becomes its own row.

---

## CLI Interface

The tool can be run from the command line with flags instead of always checking everything:

```bash
python main.py --check ec2
python main.py --check logs
python main.py --check api
python main.py --check s3
python main.py --check all          # default
python main.py --check ec2 --format json   # only save JSON, not CSV
```

`--check` and `--format` are separate flags on purpose — one controls *what* gets checked, the other controls *how* results get saved. I originally tried cramming both into one flag, which meant picking `--check json` would run zero actual checks and produce an empty, useless report.

---

## One Combined Alert System

All four checking features report into a single dictionary passed to `send_alert_email()`, instead of the function needing a new parameter every time a feature gets added:

```python
alert_data = {
    "down": [...],
    "unhealthy": [...],
    "instance_errors": [...],
    "log_errors": {...},
    "connection_errors": {...},
    "api_errors": {...},
    "bucket_object_check": {...}
}
```

One email only gets sent if at least one of these actually has something in it; the subject line says `ALERT` if any EC2 instance is down, otherwise `Warning`.

---

## Tech Stack

- Python 3
- `boto3` (AWS SDK — EC2 and S3)
- `paramiko` (SSH/SFTP for reading logs)
- `requests` (HTTP calls for the API checker)
- AWS Lambda + EventBridge (scheduling)
- AWS IAM (least-privilege read-only access)
- `smtplib` (sending the alert email)
- `python-dotenv` (loading credentials locally)
- `argparse` (CLI)
- `pytest` + `unittest.mock` (testing)

## Setup

See [SETUP.md](./SETUP.md) for AWS credentials, Gmail app password, SSH key, and environment variable setup.

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # fill in real values
python main.py
```

Required environment variables: `ALERT_EMAIL_FROM`, `ALERT_EMAIL_PASSWORD`, `ALERT_EMAIL_TO`, `SSH_USERNAME`, `SSH_KEY_PATH`

## Testing

Everything is tested with mocked AWS, SSH, HTTP, and file calls — no real AWS account, SSH access, or live servers needed to run the tests.

```bash
pip install pytest
pytest -v
```

**35 tests across 5 files:**
- `test_ec2_monitoring.py` — instance status logic (down/healthy/unhealthy/error) and the sorting across multiple instances
- `test_log_monitoring.py` — error filtering, checkpoint read/write, SSH log reading (including a simulated auth failure), and the full log-checking flow including an instance with no IP
- `test_api_monitoring.py` — up/slow/down states, retries (both giving up after 3 tries and succeeding on a retry), and the filtering logic
- `test_s3_monitoring.py` — each bucket check (public/encryption/lifecycle), the "not configured" vs. "real error" distinction, pagination across multiple pages of objects, and the overall bucket orchestration
- `test_utils.py` — the shared tagged-instance lookup

(Reporting doesn't have tests yet — it's simple file-writing logic and was deprioritized given time constraints.)

## Deployment (AWS Lambda)

1. Create a Lambda function with a role that has EC2 read-only and S3 read access
2. Set the required environment variables in the Lambda console
3. Upload `lambda_function.py` plus the `devops/` folder, set the handler to `lambda_function.lambda_handler`
4. Add an EventBridge trigger set to `rate(5 minutes)`

**Note:** for SSH to actually work from Lambda, the instances need to be reachable from Lambda's network (VPC/security groups), and the SSH key needs to be available to the function some secure way — not just bundled into the code.

## Things I'd still improve

- Configurable "how long down before alerting" threshold, to cut down on noise from short blips
- Maybe move checkpoints to a small database instead of a JSON file if this ever needs to scale to a lot more instances
- Proper SSH host key checking (currently auto-accepts, which is convenient but not great security practice)
- Tests for the reporting module
- CI (GitHub Actions) to run the test suite automatically on every push

## What I learned building this

- Mocking (`unittest.mock`) lets you fully test code that talks to AWS/SSH/HTTP without needing any of those things to actually be running — makes tests fast and doesn't cost anything.
- Small design decisions ripple outward more than expected — adding one new error category to track meant updating three or four different functions, not just one.
- Client requirements are rarely complete on the first message — almost every feature needed a follow-up question or two before I actually understood what was being asked.
- Estimating how long something will take is a real skill on its own, separate from being able to build it — and early on, a lot of "build time" is actually "learning time," which is worth being honest about instead of pretending otherwise.
- Cloud APIs often cap what they return per call (S3 only returns 1,000 objects at a time) and won't necessarily warn you — you have to know to check for that.

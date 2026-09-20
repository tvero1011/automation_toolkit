import json
import csv
import os
from datetime import datetime

from devops.formatting import has_findings, format_alert_body
from devops.utils import get_storage_dir

# If set, finished reports get uploaded to S3 as well as written to local
# storage. This matters in Lambda: writing to /tmp succeeds, but /tmp is
# wiped whenever Lambda recycles the execution environment, so a report
# that's never uploaded anywhere durable effectively vanishes. Locally,
# this is simply skipped and the file just stays on disk.
REPORT_S3_BUCKET = os.environ.get("REPORT_S3_BUCKET")


def _upload_to_s3(filepath):
    if not REPORT_S3_BUCKET:
        return
    import boto3
    s3 = boto3.client("s3")
    s3.upload_file(filepath, REPORT_S3_BUCKET, os.path.basename(filepath))


def save_json(alert_data):
    if not has_findings(alert_data):
        return

    body_lines = format_alert_body(alert_data)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(get_storage_dir(), f"report_{timestamp}.json")

    with open(filename, "w") as f:
        json.dump(body_lines, f)

    _upload_to_s3(filename)
    return filename


def save_csv(alert_data):
    if not has_findings(alert_data):
        return

    body_lines = format_alert_body(alert_data)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(get_storage_dir(), f"report_{timestamp}.csv")

    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        for line in body_lines:
            writer.writerow([line])

    _upload_to_s3(filename)
    return filename

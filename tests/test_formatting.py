from devops.formatting import has_findings, format_alert_body


def test_has_findings_false_when_everything_empty():
    assert has_findings({}) is False
    assert has_findings({"down": [], "log_errors": {}}) is False


def test_has_findings_true_when_something_present():
    assert has_findings({"down": ["i-1001"]}) is True
    assert has_findings({"bucket_object_check": {"my-bucket": ["public"]}}) is True


def test_format_alert_body_includes_all_sections():
    alert_data = {
        "down": ["i-1001"],
        "unhealthy": ["i-1002"],
        "instance_errors": ["i-1003"],
        "log_errors": {"i-1001": ["ERROR disk full"]},
        "api_errors": {"/api/login": "down"},
        "connection_errors": {"i-1002": "cant get ip address"},
        "bucket_object_check": {"my-bucket": ["public", "2 old object(s)"]},
    }

    body = format_alert_body(alert_data)

    assert "Down instances:" in body
    assert "i-1001" in body
    assert "Unhealthy:" in body
    assert "Log errors:" in body
    assert " i-1001:" in body
    assert "ERROR disk full" in body
    assert "API endpoint issues:" in body
    assert " /api/login: down" in body
    assert "S3 bucket issues:" in body


def test_format_alert_body_empty_for_no_findings():
    assert format_alert_body({}) == []

from unittest.mock import patch
import pytest
from lambda_function import lambda_handler


def _patched(**overrides):
    defaults = dict(
        check_all_instances=([], [], []),
        check_all_logs=({}, {}),
        check_all_endpoints={},
        check_all_buckets={},
    )
    defaults.update(overrides)
    return patch.multiple(
        "lambda_function",
        check_all_instances=lambda: defaults["check_all_instances"],
        check_all_logs=lambda: defaults["check_all_logs"],
        check_all_endpoints=lambda: defaults["check_all_endpoints"],
        check_all_buckets=lambda: defaults["check_all_buckets"],
        save_json=lambda data: None,
        save_csv=lambda data: None,
        send_alert_email=lambda data: None,
    )


def test_lambda_handler_reads_check_from_event_not_argv():
    # Regression test for the original bug: the handler used to call
    # argparse.parse_args(), which reads sys.argv and ignores `event`
    # entirely. This confirms `event["check"]` is actually respected.
    with _patched(check_all_instances=(["i-down"], [], [])) as mocks:
        result = lambda_handler({"check": "ec2", "format": "json"}, None)

    assert result["checked"] == "ec2"
    assert result["alert_data"] == {"down": ["i-down"], "unhealthy": [], "instance_errors": []}
    # api/s3/logs keys should NOT be present since check="ec2" only
    assert "api_errors" not in result["alert_data"]


def test_lambda_handler_defaults_to_all_with_no_event():
    with _patched():
        result = lambda_handler({}, None)

    assert result["checked"] == "all"
    assert set(result["alert_data"].keys()) == {
        "down", "unhealthy", "instance_errors",
        "log_errors", "connection_errors",
        "api_errors", "bucket_object_check",
    }


def test_lambda_handler_rejects_invalid_check_value():
    with pytest.raises(ValueError):
        lambda_handler({"check": "not-a-real-check"}, None)

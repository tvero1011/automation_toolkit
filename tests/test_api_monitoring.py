from unittest.mock import patch, MagicMock
from devops.api_monitoring import check_endpoint, check_all_endpoints

def test_check_endpoint_returns_up():
    fake_response = MagicMock()
    fake_response.status_code = 200

    with patch("devops.api_monitoring.requests.get", return_value=fake_response), patch("devops.api_monitoring.time.time", side_effect=[100, 101]
    ):
        result = check_endpoint("https://example.com/api/checkout")

    assert result == "up"

def test_check_endpoint_returns_slow_when_latency_is_high():
    fake_response = MagicMock()
    fake_response.status_code = 200

    with patch("devops.api_monitoring.requests.get", return_value=fake_response), patch("devops.api_monitoring.time.time", side_effect=[100, 106]
    ):
        result = check_endpoint("https://example.com/api/checkout")

    assert result == "slow"

def test_check_endpoint_returns_down_on_http_error():
    fake_response = MagicMock()
    fake_response.status_code = 500

    with patch("devops.api_monitoring.requests.get", return_value=fake_response):
        result = check_endpoint("https://example.com/api/checkout")

    assert result == "down"

def test_check_endpoint_returns_down_on_exception():
    with patch("devops.api_monitoring.requests.get", side_effect=Exception("Connection failed")):
        result = check_endpoint("https://example.com/api/checkout")

    assert result == "down"


def test_check_all_endpoints_filters_only_problems():
    with patch("devops.api_monitoring.check_endpoint") as mock_check:
        mock_check.side_effect = ["up", "down", "slow", "up"]

        result = check_all_endpoints()

    assert result == {
        "/api/login": "down",
        "/api/products": "slow"
    }
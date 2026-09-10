from unittest.mock import patch
from devops.ec2_monitoring import get_instance_status, check_all_instances

def test_get_instance_status_returns_down_when_stopped():
    fake_response = {
        "Reservations": [
            {"Instances": [{"State": {"Name": "stopped"}}]}
        ]
    }

    with patch("devops.ec2_monitoring.ec2") as mock_ec2:
        mock_ec2.describe_instances.return_value = fake_response

        result = get_instance_status("i-fake123")
        assert result == "down"

def test_get_instance_status_returns_healthy_when_running_and_ok():
    fake_instances_response = {
        "Reservations": [
            {"Instances": [{"State": {"Name": "running"}}]}
        ]
    }
    fake_status_response = {
        "InstanceStatuses": [
            {
                "InstanceStatus": {"Status": "ok"},
                "SystemStatus": {"Status": "ok"}
            }
        ]
    }

    with patch("devops.ec2_monitoring.ec2") as mock_ec2:
        mock_ec2.describe_instances.return_value = fake_instances_response
        mock_ec2.describe_instance_status.return_value = fake_status_response

        result = get_instance_status("i-fake123")
        assert result == "healthy"



def test_get_instance_status_returns_unhealthy_when_running_and_impaired():
    fake_instances_response = {
       "Reservations": [
           {"Instances": [{"State": {"Name": "running"}}]}
       ]
    }
    fake_status_response = {
       "InstanceStatuses": [
           {
               "InstanceStatus": {"Status": "ok"},
               "SystemStatus": {"Status": "impaired"}
           }
       ]
    }

    with patch("devops.ec2_monitoring.ec2") as mock_ec2:
        mock_ec2.describe_instances.return_value = fake_instances_response
        mock_ec2.describe_instance_status.return_value = fake_status_response


        result = get_instance_status("i-fake123")
        assert result == "unhealthy"

def test_get_instance_status_returns_error_on_exception():
    with patch("devops.ec2_monitoring.ec2") as mock_ec2:
        mock_ec2.describe_instances.side_effect = Exception("AWS connection timeout")

        result = get_instance_status("i-fake123")
        assert result == "error"

def test_check_all_instances_sorts_correctly():
  with patch("devops.ec2_monitoring.get_tagged_instance_ids") as mock_get_ids:
        mock_get_ids.return_value = ["i-001", "i-002", "i-003"]

        with patch("devops.ec2_monitoring.get_instance_status") as mock_get_status:
            mock_get_status.side_effect = ["down", "unhealthy", "error"]

            down, unhealthy, errors = check_all_instances()
            assert down == ["i-001"]
            assert unhealthy == ["i-002"]
            assert errors == ["i-003"]
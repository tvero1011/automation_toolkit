from unittest.mock import patch

def test_get_instance_status_returns_down_when_stopped():
    fake_response = {
        "Reservations": [
            {"Instances": [{"State": {"Name": "stopped"}}]}
        ]
    }

    with patch("devops.aws.ec2") as mock_ec2:
        mock_ec2.describe_instances.return_value = fake_response

        from devops.aws import get_instance_status
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

    with patch("devops.aws.ec2") as mock_ec2:
        mock_ec2.describe_instances.return_value = fake_instances_response
        mock_ec2.describe_instance_status.return_value = fake_status_response

        from devops.aws import get_instance_status
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

    with patch("devops.aws.ec2") as mock_ec2:
        mock_ec2.describe_instances.return_value = fake_instances_response
        mock_ec2.describe_instance_status.return_value = fake_status_response

        from devops.aws import get_instance_status
        result = get_instance_status("i-fake123")

        assert result == "unhealthy"

def test_get_instance_status_returns_error_on_exception():
    with patch("devops.aws.ec2") as mock_ec2:
        mock_ec2.describe_instances.side_effect = Exception("AWS connection timeout")

        from devops.aws import get_instance_status
        result = get_instance_status("i-fake123")

        assert result == "error"

def test_check_all_instances_sorts_correctly():
    fake_response = {
        "Reservations": [
            {"Instances": [
                {"InstanceId": "i-001"},
                {"InstanceId": "i-002"},
                {"InstanceId": "i-003"}
            ]}
        ]
    }

    with patch("devops.aws.ec2") as mock_ec2:
        mock_ec2.describe_instances.return_value = fake_response

        with patch("devops.aws.get_instance_status") as mock_get_status:
            mock_get_status.side_effect = ["down", "unhealthy", "error"]

            from devops.aws import check_all_instances
            down, unhealthy, errors = check_all_instances()

            assert down == ["i-001"]
            assert unhealthy == ["i-002"]
            assert errors == ["i-003"]
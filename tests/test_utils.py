from unittest.mock import patch
from devops.utils import get_tagged_instance_ids

def test_get_tagged_instance_ids_filter_tags():
    with patch("devops.utils.ec2") as mock_ec2:
        mock_ec2.describe_instances.return_value = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-1001",
                            "Tags": [
                                {"Key": "Monitor", "Value": "true"}
                            ]
                        }
                    ]
                }
            ]
        }

        result = get_tagged_instance_ids()

    assert result == ["i-1001"]
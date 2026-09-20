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
    # The previous version of this test only checked the parsed return
    # value, which would pass even if the tag filter was never actually
    # sent to AWS. This asserts the real filter param was used.
    mock_ec2.describe_instances.assert_called_once_with(
        Filters=[{"Name": "tag:monitor", "Values": ["true"]}]
    )
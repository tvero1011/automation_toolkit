from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError
from devops.s3_monitoring import check_bucket, check_objects, check_all_buckets


def make_client_error(code, operation="SomeOperation"):
    return ClientError(
        error_response={"Error": {"Code": code, "Message": "test error"}},
        operation_name=operation,
    )

def test_check_bucket_flags_public_bucket():
    with patch("devops.s3_monitoring.s3") as mock_s3:
        mock_s3.get_bucket_policy_status.return_value = {"PolicyStatus": {"IsPublic": True}}
        mock_s3.get_bucket_encryption.return_value = {}
        mock_s3.get_bucket_lifecycle_configuration.return_value = {}

        result = check_bucket("my-bucket")

    assert result == ["public"]


def test_check_bucket_no_policy_not_flagged():
    with patch("devops.s3_monitoring.s3") as mock_s3:
        mock_s3.get_bucket_policy_status.side_effect = make_client_error("NoSuchBucketPolicy")
        mock_s3.get_bucket_encryption.return_value = {}
        mock_s3.get_bucket_lifecycle_configuration.return_value = {}

        result = check_bucket("my-bucket")

    assert result == []


def test_check_bucket_policy_unexpected_error_returns_error():
    with patch("devops.s3_monitoring.s3") as mock_s3:
        mock_s3.get_bucket_policy_status.side_effect = make_client_error("AccessDenied")

        result = check_bucket("my-bucket")

    assert result == "error"


def test_check_bucket_flags_no_encryption():
    with patch("devops.s3_monitoring.s3") as mock_s3:
        mock_s3.get_bucket_policy_status.return_value = {"PolicyStatus": {"IsPublic": False}}
        mock_s3.get_bucket_encryption.side_effect = make_client_error(
            "ServerSideEncryptionConfigurationNotFoundError"
        )
        mock_s3.get_bucket_lifecycle_configuration.return_value = {}

        result = check_bucket("my-bucket")

    assert result == ["no encryption"]


def test_check_bucket_encryption_unexpected_error_returns_error():
    with patch("devops.s3_monitoring.s3") as mock_s3:
        mock_s3.get_bucket_policy_status.return_value = {"PolicyStatus": {"IsPublic": False}}
        mock_s3.get_bucket_encryption.side_effect = make_client_error("AccessDenied")

        result = check_bucket("my-bucket")

    assert result == "error"


def test_check_bucket_flags_no_lifecycle():
    with patch("devops.s3_monitoring.s3") as mock_s3:
        mock_s3.get_bucket_policy_status.return_value = {"PolicyStatus": {"IsPublic": False}}
        mock_s3.get_bucket_encryption.return_value = {}
        mock_s3.get_bucket_lifecycle_configuration.side_effect = make_client_error(
            "NoSuchLifecycleConfiguration"
        )

        result = check_bucket("my-bucket")

    assert result == ["no lifecycle policy"]


def test_check_bucket_lifecycle_unexpected_error_returns_error():
    with patch("devops.s3_monitoring.s3") as mock_s3:
        mock_s3.get_bucket_policy_status.return_value = {"PolicyStatus": {"IsPublic": False}}
        mock_s3.get_bucket_encryption.return_value = {}
        mock_s3.get_bucket_lifecycle_configuration.side_effect = make_client_error("AccessDenied")

        result = check_bucket("my-bucket")

    assert result == "error"


def test_check_bucket_clean_bucket_returns_empty_list():
    with patch("devops.s3_monitoring.s3") as mock_s3:
        mock_s3.get_bucket_policy_status.return_value = {"PolicyStatus": {"IsPublic": False}}
        mock_s3.get_bucket_encryption.return_value = {}
        mock_s3.get_bucket_lifecycle_configuration.return_value = {}

        result = check_bucket("my-bucket")

    assert result == []


# --- check_objects (pagination) ---

def test_check_objects_flags_old_objects_across_pages():
    old_date = datetime.now(timezone.utc) - timedelta(days=120)
    recent_date = datetime.now(timezone.utc) - timedelta(days=5)

    page_one = {"Contents": [{"Key": "old-file-1.txt", "LastModified": old_date}]}
    page_two = {"Contents": [{"Key": "recent-file.txt", "LastModified": recent_date}, {"Key": "old-file-2.txt", "LastModified": old_date}]}
    fake_pages = [page_one, page_two]

    with patch("devops.s3_monitoring.s3") as mock_s3:
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = fake_pages
        mock_s3.get_paginator.return_value = mock_paginator

        result = check_objects("my-bucket")

    assert result == ["old-file-1.txt", "old-file-2.txt"]


def test_check_objects_returns_empty_on_error():
    with patch("devops.s3_monitoring.s3") as mock_s3:
        mock_s3.get_paginator.side_effect = make_client_error("AccessDenied")

        result = check_objects("my-bucket")

    assert result == []


# --- check_all_buckets ---

def test_check_all_buckets_skips_object_check_on_bucket_error():
    with patch("devops.s3_monitoring.s3") as mock_s3, patch("devops.s3_monitoring.check_bucket") as mock_check_bucket, patch("devops.s3_monitoring.check_objects") as mock_check_objects:
        mock_s3.list_buckets.return_value = {"Buckets": [{"Name": "bad-bucket"}]}
        mock_check_bucket.return_value = "error"

        result = check_all_buckets()

    assert result == {"bad-bucket": ["error checking bucket"]}
    mock_check_objects.assert_not_called()


def test_check_all_buckets_combines_issues_and_old_objects():
    with patch("devops.s3_monitoring.s3") as mock_s3, patch("devops.s3_monitoring.check_bucket") as mock_check_bucket, patch("devops.s3_monitoring.check_objects") as mock_check_objects:
        mock_s3.list_buckets.return_value = {"Buckets": [{"Name": "my-bucket"}]}
        mock_check_bucket.return_value = ["public"]
        mock_check_objects.return_value = ["old1.txt", "old2.txt"]

        result = check_all_buckets()

    assert result == {"my-bucket": ["public", "2 old object(s)"]}


def test_check_all_buckets_clean_bucket_not_included():
    with patch("devops.s3_monitoring.s3") as mock_s3, patch("devops.s3_monitoring.check_bucket") as mock_check_bucket, patch("devops.s3_monitoring.check_objects") as mock_check_objects:
        mock_s3.list_buckets.return_value = {"Buckets": [{"Name": "clean-bucket"}]}
        mock_check_bucket.return_value = []
        mock_check_objects.return_value = []

        result = check_all_buckets()

    assert result == {}
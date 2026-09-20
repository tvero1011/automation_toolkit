from unittest.mock import patch, mock_open, MagicMock
from devops.log_monitoring import filter_error_lines, get_checkpoint, save_checkpoint, read_new_log_lines, check_all_logs
import json
import paramiko
import socket

def test_filter_error_lines_finds_all_case_variants():
    fake_log_lines = [
        "2026-09-06 10:15:23 INFO User logged in",
        "2026-09-06 10:16:01 ERROR Payment gateway timeout",
        "2026-09-06 10:16:45 INFO Order placed successfully",
        "2026-09-06 10:17:02 error database connection lost"
    ]

    result = filter_error_lines(fake_log_lines)

    assert result == [
        "2026-09-06 10:16:01 ERROR Payment gateway timeout",
        "2026-09-06 10:17:02 error database connection lost"
    ]

def test_filter_error_lines_ignores_substring_false_positives():
    # "terror" contains the letters "error" as a substring, but is not the
    # word "error" -- a plain `"error" in line.lower()` check would
    # incorrectly flag this line.
    fake_log_lines = [
        "2026-09-06 10:15:23 INFO terrorFlag reset to false",
        "2026-09-06 10:16:01 ERROR Payment gateway timeout",
    ]

    result = filter_error_lines(fake_log_lines)

    assert result == ["2026-09-06 10:16:01 ERROR Payment gateway timeout"]

def test_get_checkpoint_returns_saved_value():
    fake_file_content = json.dumps(
        {
        "i-1001": 2048,
        "i-1002": 512,
        "i-1003": 1024
        })

    with patch("builtins.open", mock_open(read_data=fake_file_content)):
        result = get_checkpoint("i-1001")
        assert result == 2048

def test_get_checkpoint_default_value_logic():
    fake_file_content = json.dumps(
        {
        "i-1001": 2048,
        "i-1002": 512,
        "i-1003": 1024
        })

    with patch("builtins.open", mock_open(read_data=fake_file_content)):
        result = get_checkpoint("i-1004")
        assert result == 0

def test_get_checkpoint_file_not_found():
    with patch("builtins.open", side_effect=FileNotFoundError):
        result = get_checkpoint("i-1001")
        assert result == 0    


def test_save_checkpoint_writes_correct_data():
    existing_content = json.dumps({"i-1002": 512})

    m = mock_open(read_data=existing_content)
    with patch("builtins.open", m):
        save_checkpoint("i-1001", 2048)

    handle = m()
    written_data = "".join(call.args[0] for call in handle.write.call_args_list)
    assert json.loads(written_data) == {"i-1002": 512, "i-1001": 2048}


def test_read_new_log_lines_returns_new_content():
    fake_file = MagicMock()
    fake_file.read.return_value = "ERROR something broke\nINFO all fine\n"
    fake_file.tell.return_value = 500
    fake_file.__enter__.return_value = fake_file
    fake_file.__exit__.return_value = False

    fake_sftp = MagicMock()
    fake_sftp.open.return_value = fake_file

    with patch("devops.log_monitoring.client") as fake_client, \
         patch("devops.log_monitoring.os.environ", {"SSH_USERNAME": "user", "SSH_KEY_PATH": "/fake/key"}):
        fake_client.open_sftp.return_value = fake_sftp

        new_lines, new_position, error = read_new_log_lines("10.0.0.5", 200)

    fake_client.connect.assert_called_with(hostname="10.0.0.5", username="user", key_filename="/fake/key")
    fake_file.seek.assert_called_with(200)
    assert new_lines == ["ERROR something broke", "INFO all fine"]
    assert new_position == 500
    assert error is None
    fake_client.close.assert_called_once()


def test_read_new_log_lines_handles_auth_failure():
    with patch("devops.log_monitoring.client") as fake_client, \
         patch("devops.log_monitoring.os.environ", {"SSH_USERNAME": "user", "SSH_KEY_PATH": "/fake/key"}):
        fake_client.connect.side_effect = paramiko.AuthenticationException("bad key")

        new_lines, new_position, error = read_new_log_lines("10.0.0.5", 200)

    assert new_lines == []
    assert new_position == 200
    assert isinstance(error, paramiko.AuthenticationException)
    fake_client.close.assert_called_once()


def test_check_all_logs():
    with patch("devops.log_monitoring.get_tagged_instance_ids") as mock_get_ids, \
         patch("devops.log_monitoring.get_instance_ip") as mock_get_ip, \
         patch("devops.log_monitoring.get_checkpoint") as mock_get_checkpoint, \
         patch("devops.log_monitoring.read_new_log_lines") as mock_read_lines, \
         patch("devops.log_monitoring.filter_error_lines") as mock_filter, \
         patch("devops.log_monitoring.save_checkpoint") as mock_save:

        mock_get_ids.return_value = ["i-1001", "i-1002"]
        mock_get_ip.return_value = "10.0.0.5"
        mock_get_checkpoint.return_value = 100
        mock_read_lines.return_value = (["INFO all good", "ERROR something broke"], 200, None)
        mock_filter.return_value = ["ERROR something broke"]
        mock_save.return_value = None

        all_error_lines, all_error_message = check_all_logs()

    assert all_error_lines == {
        "i-1001": ["ERROR something broke"],
        "i-1002": ["ERROR something broke"],
    }
    assert all_error_message == {}


def test_check_all_logs_skips_instance_with_no_ip():
    with patch("devops.log_monitoring.get_tagged_instance_ids") as mock_get_ids, \
         patch("devops.log_monitoring.get_instance_ip") as mock_get_ip, \
         patch("devops.log_monitoring.read_new_log_lines") as mock_read_lines, \
         patch("devops.log_monitoring.save_checkpoint") as mock_save:

        mock_get_ids.return_value = ["i-1001"]
        mock_get_ip.return_value = None

        all_error_lines, all_error_message = check_all_logs()

    assert all_error_lines == {}
    assert all_error_message == {"i-1001": "cant get ip address"}
    mock_read_lines.assert_not_called()
    mock_save.assert_not_called()
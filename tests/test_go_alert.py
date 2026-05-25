import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import patch, MagicMock


class _FakeTender:
    title = "Système SSI bâtiment A"
    relevance_score = 85
    deadline = None
    url = "https://example.com/tender/1"


_SMTP_CFG = {
    "host": "smtp.test.local",
    "port": 587,
    "user": "test@test.local",
    "password": "secret",
    "to": "dest@test.local",
}


def test_send_go_alert_calls_smtp():
    from email_digest import send_go_alert

    with patch("smtplib.SMTP") as mock_smtp_cls:
        server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        send_go_alert(_FakeTender(), _SMTP_CFG)

        mock_smtp_cls.assert_called_once_with("smtp.test.local", 587)
        server.send_message.assert_called_once()


def test_send_go_alert_subject_contains_title():
    from email_digest import send_go_alert

    sent_msgs = []

    with patch("smtplib.SMTP") as mock_smtp_cls:
        server = MagicMock()
        server.send_message.side_effect = lambda msg: sent_msgs.append(msg)
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        send_go_alert(_FakeTender(), _SMTP_CFG)

    assert len(sent_msgs) == 1
    subject = sent_msgs[0]["Subject"]
    assert "[GO]" in subject
    assert "Système SSI bâtiment A" in subject


def test_send_go_alert_returns_true_on_success():
    from email_digest import send_go_alert

    with patch("smtplib.SMTP") as mock_smtp_cls:
        server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = send_go_alert(_FakeTender(), _SMTP_CFG)

    assert result is True


def test_send_go_alert_returns_false_on_smtp_error():
    from email_digest import send_go_alert

    with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("refused")):
        result = send_go_alert(_FakeTender(), _SMTP_CFG)

    assert result is False

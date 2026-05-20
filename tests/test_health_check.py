from unittest.mock import patch, MagicMock
from health_check import check_source, HealthResult


def test_check_source_ok_returns_healthy():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"results": [{"id": 1}]}'
    mock_resp.json.return_value = {"results": [{"id": 1}]}

    with patch("health_check.requests.get", return_value=mock_resp):
        result = check_source(
            name="BOAMP",
            url="https://boamp-datadila.opendatasoft.com",
            marker_type="json_key",
            marker_value="results",
        )
    assert result.ok is True
    assert result.error is None
    assert result.http_status == 200


def test_check_source_missing_json_marker_returns_unhealthy():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"error": "not found"}'
    mock_resp.json.return_value = {"error": "not found"}

    with patch("health_check.requests.get", return_value=mock_resp):
        result = check_source(
            name="BOAMP",
            url="https://boamp-datadila.opendatasoft.com",
            marker_type="json_key",
            marker_value="results",
        )
    assert result.ok is False
    assert "marqueur" in result.error.lower()


def test_check_source_http_error_returns_unhealthy():
    with patch("health_check.requests.get", side_effect=Exception("Connection refused")):
        result = check_source(
            name="BOAMP",
            url="https://boamp-datadila.opendatasoft.com",
            marker_type="json_key",
            marker_value="results",
        )
    assert result.ok is False
    assert result.http_status is None


def test_check_source_html_marker_found():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '<html><body class="blockNotice">content</body></html>'
    mock_resp.json.side_effect = ValueError("not JSON")

    with patch("health_check.requests.get", return_value=mock_resp):
        result = check_source(
            name="MarchéOnline",
            url="https://www.marchesonline.com",
            marker_type="html_text",
            marker_value="blockNotice",
        )
    assert result.ok is True


def test_check_source_html_marker_missing():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '<html><body>page restructured</body></html>'
    mock_resp.json.side_effect = ValueError("not JSON")

    with patch("health_check.requests.get", return_value=mock_resp):
        result = check_source(
            name="MarchéOnline",
            url="https://www.marchesonline.com",
            marker_type="html_text",
            marker_value="blockNotice",
        )
    assert result.ok is False
    assert "marqueur" in result.error.lower()


def test_run_all_health_checks_returns_dict():
    from health_check import run_all_health_checks

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"results": []}'
    mock_resp.json.return_value = {"results": []}

    with patch("health_check.requests.get", return_value=mock_resp):
        results = run_all_health_checks()

    assert isinstance(results, dict)
    assert len(results) > 0
    for name, r in results.items():
        assert hasattr(r, "ok")
        assert hasattr(r, "checked_at")
        assert hasattr(r, "error")

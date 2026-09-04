import json
from pathlib import Path

import pytest

from alphabeater.publish_run import publish, sanitize


def test_redacts_client_order_id() -> None:
    result = sanitize({"trade_plan": {"client_order_id": "alphabeater-abc123", "quantity": 1}})

    assert result["trade_plan"]["client_order_id"] == "[redacted]"
    assert result["trade_plan"]["quantity"] == 1


def test_redacts_broker_order_identifiers() -> None:
    result = sanitize({"order": {"id": "9f2", "order_id": "abc", "status": "filled"}})

    assert result["order"]["id"] == "[redacted]"
    assert result["order"]["order_id"] == "[redacted]"
    assert result["order"]["status"] == "filled"


def test_redacts_account_and_credential_keys() -> None:
    result = sanitize({"account_number": "PA123", "api_key": "sk-x", "equity": 100000})

    assert result["account_number"] == "[redacted]"
    assert result["api_key"] == "[redacted]"
    assert result["equity"] == 100000


def test_redacts_inside_lists() -> None:
    result = sanitize({"positions": [{"id": "p1", "symbol": "IWM", "unrealized_pl": -12.5}]})

    assert result["positions"][0]["id"] == "[redacted]"
    assert result["positions"][0]["symbol"] == "IWM"
    assert result["positions"][0]["unrealized_pl"] == -12.5


def test_keeps_every_risk_check_intact() -> None:
    record = {"risk": {"approved": False, "checks": [{"name": "quote freshness", "passed": False}]}}

    result = sanitize(record)

    assert result["risk"]["checks"] == [{"name": "quote freshness", "passed": False}]


def test_publish_writes_the_target_file(tmp_path: Path) -> None:
    source = tmp_path / "run.json"
    target = tmp_path / "out" / "sample.json"
    source.write_text(json.dumps({"trade_plan": {"client_order_id": "x", "quantity": 1}}))

    publish(source, target)

    written = json.loads(target.read_text())
    assert written["trade_plan"]["client_order_id"] == "[redacted]"
    assert written["trade_plan"]["quantity"] == 1


def test_publish_reports_a_missing_source(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="no audit record"):
        publish(tmp_path / "missing.json", tmp_path / "out.json")

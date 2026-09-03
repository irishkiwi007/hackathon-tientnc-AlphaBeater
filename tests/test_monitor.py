from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from alphabeater.monitor import PaperPositionMonitor


class MonitorClient:
    def __init__(self) -> None:
        self.submitted = []

    def get_clock(self) -> SimpleNamespace:
        return SimpleNamespace(is_open=True)

    def get_orders(self, *, filter: object) -> list[SimpleNamespace]:
        return []

    def get_all_positions(self) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(
                asset_class=SimpleNamespace(value="us_option"),
                symbol="SPY260925C00500000",
                cost_basis="500",
                market_value="350",
                qty="1",
            )
        ]

    def submit_order(self, *, order_data: object) -> SimpleNamespace:
        self.submitted.append(order_data)
        return SimpleNamespace(id="exit-order-id")


def test_monitor_executes_stop_loss_when_enabled(tmp_path: Path) -> None:
    client = MonitorClient()
    monitor = PaperPositionMonitor(
        client,
        automatic_exits=True,
        journal_path=tmp_path / "journal.jsonl",
    )

    report = monitor.check_once(now=datetime(2026, 9, 2, 15, tzinfo=UTC))

    assert report.events[0].action == "sell_to_close"
    assert report.events[0].automatic_action_taken
    assert len(client.submitted) == 1
    assert (tmp_path / "journal.jsonl").exists()

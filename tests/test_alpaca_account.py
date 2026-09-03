from types import SimpleNamespace

from alphabeater.alpaca import AlpacaPaperAccount


class FakeAccountClient:
    def get_account(self) -> SimpleNamespace:
        return SimpleNamespace(
            id="12345678-1234-5678-1234-567812345678",
            account_number="PA1234567",
            status="ACTIVE",
            currency="USD",
            equity="100000",
            last_equity="99000",
            buying_power="200000",
            options_buying_power="100000",
            options_approved_level=3,
            options_trading_level=3,
            trading_blocked=False,
        )


def test_reads_paper_account_summary() -> None:
    summary = AlpacaPaperAccount(FakeAccountClient()).get_summary()

    assert summary.equity == 100_000
    assert summary.last_equity == 99_000
    assert summary.options_trading_level == 3
    assert not summary.trading_blocked

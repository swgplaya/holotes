from src.transaction_repository import (
    TransactionSummary,
)


def test_calculated_balance_uses_all_history_net() -> None:
    summary = TransactionSummary(
        count=3,
        inflow_kopecks=150_000,
        outflow_kopecks=80_000,
        net_kopecks=70_000,
    )

    assert (
        summary.calculated_balance_kopecks
        == 70_000
    )

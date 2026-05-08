from __future__ import annotations

import unittest

from src.analytics import account_summary, snapshot_trend_frame


class AccountSummaryTests(unittest.TestCase):
    """성과 계산 규칙을 검증한다."""

    def test_account_summary_separates_principal_net_flow_and_actual_profit(self) -> None:
        account = {"cash_balance": 1_000_000}
        holdings = [
            {"quantity": 10, "avg_cost": 10_000, "current_price": 12_000, "asset_type": "risk"},
            {"quantity": 5, "avg_cost": 20_000, "current_price": 18_000, "asset_type": "safe"},
        ]
        trade_logs = [
            {"trade_type": "personal_deposit", "trade_date": "2026-01-01", "total_amount": 1_500_000, "cash_delta": 1_500_000},
            {"trade_type": "employer_deposit", "trade_date": "2026-01-10", "total_amount": 500_000, "cash_delta": 500_000},
            {"trade_type": "transfer_out", "trade_date": "2026-01-20", "total_amount": 200_000, "cash_delta": -200_000},
        ]
        interest_rows = [{"date": "2026-01-31", "interest_amount": 5_000}]

        summary = account_summary(account, holdings, trade_logs=trade_logs, interest_rows=interest_rows)

        self.assertEqual(summary["total_principal"], 2_000_000.0)
        self.assertEqual(summary["net_flow"], 1_800_000.0)
        self.assertEqual(summary["total_interest"], 5_000.0)
        self.assertEqual(summary["profit_loss"], 10_000.0)
        self.assertEqual(summary["actual_profit_loss"], -590_000.0)

    def test_account_summary_falls_back_when_capital_history_is_missing(self) -> None:
        account = {"cash_balance": 500_000}
        holdings = [
            {"quantity": 10, "avg_cost": 10_000, "current_price": 11_000, "asset_type": "risk"},
        ]

        summary = account_summary(account, holdings, trade_logs=[], interest_rows=[])

        self.assertEqual(summary["total_cost"], 100_000.0)
        self.assertEqual(summary["total_principal"], 600_000.0)
        self.assertEqual(summary["net_flow"], 600_000.0)
        self.assertEqual(summary["actual_profit_loss"], 10_000.0)


class SnapshotTrendFrameTests(unittest.TestCase):
    """스냅샷 추이 보조 컬럼을 검증한다."""

    def test_snapshot_trend_frame_carries_forward_cumulative_flow_values(self) -> None:
        snapshots = [
            {
                "snapshot_date": "2026-01-15",
                "cash_balance": 1_400_000,
                "market_value": 200_000,
                "total_value": 1_600_000,
                "total_cost": 180_000,
            },
            {
                "snapshot_date": "2026-01-31",
                "cash_balance": 1_000_000,
                "market_value": 210_000,
                "total_value": 1_210_000,
                "total_cost": 200_000,
            },
        ]
        trade_logs = [
            {"trade_type": "personal_deposit", "trade_date": "2026-01-01", "total_amount": 1_500_000, "cash_delta": 1_500_000},
            {"trade_type": "employer_deposit", "trade_date": "2026-01-10", "total_amount": 500_000, "cash_delta": 500_000},
            {"trade_type": "transfer_out", "trade_date": "2026-01-20", "total_amount": 200_000, "cash_delta": -200_000},
        ]
        interest_rows = [{"date": "2026-01-31", "interest_amount": 5_000}]

        frame = snapshot_trend_frame(snapshots, trade_logs=trade_logs, interest_rows=interest_rows)

        first_row = frame.iloc[0]
        second_row = frame.iloc[1]

        self.assertEqual(first_row["total_principal"], 2_000_000.0)
        self.assertEqual(first_row["net_flow"], 2_000_000.0)
        self.assertEqual(first_row["total_interest"], 0.0)
        self.assertEqual(first_row["actual_profit_loss"], -400_000.0)

        self.assertEqual(second_row["total_principal"], 2_000_000.0)
        self.assertEqual(second_row["net_flow"], 1_800_000.0)
        self.assertEqual(second_row["total_interest"], 5_000.0)
        self.assertEqual(second_row["actual_profit_loss"], -590_000.0)


if __name__ == "__main__":
    unittest.main()

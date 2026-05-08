from __future__ import annotations

from datetime import date
import unittest

from src.analytics import account_summary, cumulative_contribution_frame, projected_today_interest, snapshot_trend_frame


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

        self.assertEqual(summary["company_principal"], 500_000.0)
        self.assertEqual(summary["contribution_principal"], 2_000_000.0)
        self.assertEqual(summary["total_principal"], 2_000_000.0)
        self.assertEqual(summary["net_flow"], 1_800_000.0)
        self.assertEqual(summary["total_interest"], 5_000.0)
        self.assertEqual(summary["profit_loss"], 10_000.0)
        self.assertEqual(summary["principal_profit_loss"], -790_000.0)
        self.assertEqual(summary["principal_profit_rate"], -39.5)
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
        self.assertEqual(summary["principal_profit_loss"], 10_000.0)
        self.assertEqual(summary["actual_profit_loss"], 10_000.0)

    def test_account_summary_keeps_principal_constant_through_buy_and_sell(self) -> None:
        account = {"cash_balance": 350_000}
        holdings = [
            {"quantity": 10, "avg_cost": 50_000, "current_price": 55_000, "asset_type": "risk"},
        ]
        trade_logs = [
            {"trade_type": "employer_deposit", "trade_date": "2026-01-01", "total_amount": 1_000_000, "cash_delta": 1_000_000},
            {"trade_type": "buy", "trade_date": "2026-01-03", "total_amount": 600_000, "cash_delta": -600_000},
            {"trade_type": "sell", "trade_date": "2026-01-20", "total_amount": 150_000, "cash_delta": 150_000},
        ]
        interest_rows = [{"date": "2026-01-31", "interest_amount": 4_000}]

        summary = account_summary(account, holdings, trade_logs=trade_logs, interest_rows=interest_rows)

        self.assertEqual(summary["company_principal"], 1_000_000.0)
        self.assertEqual(summary["total_principal"], 1_000_000.0)
        self.assertEqual(summary["net_flow"], 1_000_000.0)
        self.assertEqual(summary["profit_loss"], 50_000.0)
        self.assertEqual(summary["profit_rate"], 10.0)
        self.assertEqual(summary["principal_profit_loss"], -100_000.0)
        self.assertEqual(summary["principal_profit_rate"], -10.0)

    def test_account_summary_treats_legacy_company_cash_label_as_employer_deposit(self) -> None:
        account = {"cash_balance": 900_000}
        holdings = []
        trade_logs = [
            {"trade_type": "personal_deposit", "product_name": "회사 현금입금", "trade_date": "2026-01-01", "total_amount": 800_000, "cash_delta": 800_000},
        ]

        summary = account_summary(account, holdings, trade_logs=trade_logs, interest_rows=[])

        self.assertEqual(summary["company_principal"], 800_000.0)
        self.assertEqual(summary["contribution_principal"], 800_000.0)
        self.assertEqual(summary["total_principal"], 800_000.0)


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
        self.assertEqual(first_row["principal_profit_loss"], -400_000.0)

        self.assertEqual(second_row["total_principal"], 2_000_000.0)
        self.assertEqual(second_row["net_flow"], 1_800_000.0)
        self.assertEqual(second_row["total_interest"], 5_000.0)
        self.assertEqual(second_row["actual_profit_loss"], -590_000.0)
        self.assertEqual(second_row["principal_profit_loss"], -790_000.0)
        self.assertEqual(second_row["principal_profit_rate"], -39.5)


class ProjectedTodayInterestTests(unittest.TestCase):
    """오늘 예상 이자 계산을 검증한다."""

    def test_projected_today_interest_uses_current_cash_when_today_row_is_missing(self) -> None:
        account = {"cash_balance": 1_000_000}

        value = projected_today_interest(
            account,
            interest_rows=[{"date": "2026-05-07", "interest_amount": 123.4}],
            annual_rate=0.05,
            as_of=date(2026, 5, 8),
        )

        self.assertEqual(value, round(1_000_000 * 0.05 / 365, 4))

    def test_projected_today_interest_returns_zero_when_today_is_already_recorded(self) -> None:
        account = {"cash_balance": 1_000_000}

        value = projected_today_interest(
            account,
            interest_rows=[{"date": "2026-05-08", "interest_amount": 123.4}],
            annual_rate=0.05,
            as_of=date(2026, 5, 8),
        )

        self.assertEqual(value, 0.0)


class CumulativeContributionFrameTests(unittest.TestCase):
    """누적 원금 기록 프레임을 검증한다."""

    def test_cumulative_contribution_frame_appends_current_valuation_row(self) -> None:
        trade_logs = [
            {"trade_type": "personal_deposit", "trade_date": "2026-01-01", "total_amount": 1_500_000, "cash_delta": 1_500_000},
            {"trade_type": "employer_deposit", "trade_date": "2026-01-10", "total_amount": 500_000, "cash_delta": 500_000},
            {"trade_type": "withdraw", "trade_date": "2026-01-20", "total_amount": 200_000, "cash_delta": -200_000},
        ]
        interest_rows = [{"date": "2026-01-31", "interest_amount": 5_000}]

        frame = cumulative_contribution_frame(
            trade_logs=trade_logs,
            interest_rows=interest_rows,
            current_total_value=1_210_000,
            current_market_value=210_000,
            current_cash_balance=1_000_000,
            current_total_cost=200_000,
            current_date="2026-02-01",
        )

        last_row = frame.iloc[-1]

        self.assertEqual(last_row["date"], "2026-02-01")
        self.assertEqual(last_row["company_principal"], 500_000.0)
        self.assertEqual(last_row["total_principal"], 1_800_000.0)
        self.assertEqual(last_row["total_interest"], 5_000.0)
        self.assertEqual(last_row["total_value"], 1_210_000.0)
        self.assertEqual(last_row["principal_profit_loss"], -590_000.0)
        self.assertAlmostEqual(float(last_row["principal_profit_rate"]), -32.7777777778, places=6)


if __name__ == "__main__":
    unittest.main()

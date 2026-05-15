from __future__ import annotations

from datetime import date
import unittest
from unittest.mock import patch

from src.analytics import (
    account_summary,
    allocation_treemap_nodes,
    cumulative_contribution_frame,
    holdings_overview_frame,
    infer_holding_sector_label,
    projected_today_interest,
    realized_summary,
    snapshot_trend_frame,
)


class AccountSummaryTests(unittest.TestCase):
    """성과 계산 규칙을 검증한다."""

    def test_realized_summary_keeps_sell_log_id_for_trade_table_link(self) -> None:
        """실현손익 포지션은 원 매도 거래 ID를 보존한다."""

        trade_logs = [
            {
                "id": 10,
                "trade_type": "buy",
                "trade_date": "2026-05-01",
                "symbol": "005930",
                "product_name": "삼성전자",
                "asset_type": "risk",
                "quantity": 10,
                "total_amount": 700000,
            },
            {
                "id": 11,
                "trade_type": "sell",
                "trade_date": "2026-05-12",
                "symbol": "005930",
                "product_name": "삼성전자",
                "asset_type": "risk",
                "quantity": 4,
                "total_amount": 320000,
            },
        ]

        summary = realized_summary(trade_logs)

        self.assertEqual(summary["sold_count"], 1)
        self.assertEqual(summary["positions"][0]["sell_log_id"], 11)
        self.assertEqual(summary["positions"][0]["profit_rate"], 14.29)

    def test_realized_summary_ignores_scaled_duplicate_trade_logs(self) -> None:
        """같은 매수/매도의 1,000배 총액 중복 행은 실현손익 계산에서 제외한다."""

        trade_logs = [
            {
                "id": 1,
                "trade_type": "buy",
                "trade_date": "2026-01-01",
                "symbol": "K55207BU0715",
                "product_name": "교보악사파워인덱스",
                "asset_type": "risk",
                "quantity": 1000,
                "price": 2,
                "total_amount": 2_000_000,
            },
            {
                "id": 2,
                "trade_type": "buy",
                "trade_date": "2026-01-01",
                "symbol": "K55207BU0715",
                "product_name": "교보악사파워인덱스",
                "asset_type": "risk",
                "quantity": 1000,
                "price": 2,
                "total_amount": 2000,
            },
            {
                "id": 3,
                "trade_type": "sell",
                "trade_date": "2026-02-01",
                "symbol": "K55207BU0715",
                "product_name": "교보악사파워인덱스",
                "asset_type": "risk",
                "quantity": 1000,
                "price": 3,
                "total_amount": 3_000_000,
            },
            {
                "id": 4,
                "trade_type": "sell",
                "trade_date": "2026-02-01",
                "symbol": "K55207BU0715",
                "product_name": "교보악사파워인덱스",
                "asset_type": "risk",
                "quantity": 1000,
                "price": 3,
                "total_amount": 3000,
            },
        ]

        summary = realized_summary(trade_logs)

        self.assertEqual(summary["sold_count"], 1)
        self.assertEqual(summary["positions"][0]["sell_log_id"], 4)
        self.assertEqual(summary["positions"][0]["buy_amount"], 2000)
        self.assertEqual(summary["positions"][0]["sell_amount"], 3000)
        self.assertEqual(summary["positions"][0]["profit_loss"], 1000)
        self.assertEqual(summary["positions"][0]["profit_rate"], 50.0)

    def test_realized_summary_matches_domestic_symbol_suffix(self) -> None:
        """국내 종목 접미사 유무가 달라도 실현손익 lot을 매칭한다."""

        summary = realized_summary(
            [
                {
                    "id": 1,
                    "trade_type": "buy",
                    "trade_date": "2026-01-01",
                    "symbol": "487240",
                    "product_name": "KODEX AI전력핵심설비",
                    "asset_type": "risk",
                    "quantity": 1,
                    "total_amount": 3000,
                },
                {
                    "id": 2,
                    "trade_type": "sell",
                    "trade_date": "2026-01-02",
                    "symbol": "487240.KS",
                    "product_name": "KODEX AI전력핵심설비",
                    "asset_type": "risk",
                    "quantity": 1,
                    "total_amount": 5000,
                },
            ]
        )

        self.assertEqual(summary["sold_count"], 1)
        self.assertEqual(summary["positions"][0]["profit_loss"], 2000)
        self.assertEqual(summary["positions"][0]["profit_rate"], 66.67)

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

    def test_account_summary_ignores_cash_adjustment_logs_in_flow_metrics(self) -> None:
        account = {"cash_balance": 900_000}
        holdings = [
            {"quantity": 5, "avg_cost": 100_000, "current_price": 110_000, "asset_type": "risk"},
        ]
        trade_logs = [
            {"trade_type": "personal_deposit", "trade_date": "2026-01-01", "total_amount": 700_000, "cash_delta": 700_000},
            {"trade_type": "cash_adjustment", "trade_date": "2026-01-02", "total_amount": 200_000, "cash_delta": 200_000},
        ]

        summary = account_summary(account, holdings, trade_logs=trade_logs, interest_rows=[])

        self.assertEqual(summary["total_principal"], 700_000.0)
        self.assertEqual(summary["net_flow"], 700_000.0)
        self.assertEqual(summary["cash_flow"]["net_adjustment"], 0.0)

    def test_allocation_treemap_nodes_groups_holdings_and_cash(self) -> None:
        account = {"cash_balance": 300_000}
        holdings = [
            {"product_name": "KODEX 200", "symbol": "069500", "quantity": 10, "avg_cost": 30_000, "current_price": 35_000, "asset_type": "risk"},
            {"product_name": "국고채 ETF", "symbol": "148070", "quantity": 5, "avg_cost": 50_000, "current_price": 51_000, "asset_type": "safe"},
        ]

        summary = account_summary(account, holdings, trade_logs=[], interest_rows=[])
        nodes = allocation_treemap_nodes(summary, holdings)

        self.assertEqual([node["name"] for node in nodes], ["위험자산", "안전자산", "현금"])
        self.assertEqual(nodes[0]["children"][0]["name"], "주식/ETF")
        self.assertEqual(nodes[0]["children"][0]["children"][0]["name"], "KODEX 200")
        self.assertEqual(nodes[0]["children"][0]["children"][0]["symbol"], "069500")
        self.assertEqual(nodes[1]["children"][0]["name"], "채권")
        self.assertEqual(nodes[1]["children"][0]["children"][0]["name"], "국고채 ETF")
        self.assertEqual(nodes[2]["children"][0]["name"], "예수금")
        self.assertEqual(nodes[2]["children"][0]["value"], 300_000.0)

    def test_allocation_treemap_nodes_marks_selected_symbol(self) -> None:
        account = {"cash_balance": 300_000}
        holdings = [
            {"product_name": "KODEX 200", "symbol": "069500", "quantity": 10, "avg_cost": 30_000, "current_price": 35_000, "asset_type": "risk"},
            {"product_name": "국고채 ETF", "symbol": "148070", "quantity": 5, "avg_cost": 50_000, "current_price": 51_000, "asset_type": "safe"},
        ]

        summary = account_summary(account, holdings, trade_logs=[], interest_rows=[])
        nodes = allocation_treemap_nodes(summary, holdings, selected_symbol="148070")

        self.assertFalse(nodes[0]["children"][0]["children"][0]["is_selected"])
        self.assertTrue(nodes[1]["children"][0]["children"][0]["is_selected"])

    @patch("src.analytics.resolve_kis_sector_label", return_value="전기·전자")
    def test_infer_holding_sector_label_prefers_kis_master_result(self, sector_mock) -> None:
        self.assertEqual(infer_holding_sector_label("삼성전자", "005930", "risk"), "전기·전자")
        sector_mock.assert_called_once_with("005930")

    @patch("src.analytics.resolve_kis_sector_label", return_value=None)
    def test_infer_holding_sector_label_falls_back_to_keyword_rules_when_kis_missing(self, _sector_mock) -> None:
        self.assertEqual(infer_holding_sector_label("TIGER 미국테크TOP10 INDXX", "381170", "risk"), "미국테크")

    def test_holdings_overview_frame_keeps_selected_symbol_inside_limit(self) -> None:
        holdings = [
            {
                "product_name": f"종목 {index}",
                "symbol": f"{index:06d}",
                "quantity": 1,
                "avg_cost": 100 + index,
                "current_price": 100 + index,
                "asset_type": "risk" if index % 2 else "safe",
            }
            for index in range(1, 13)
        ]
        overview = holdings_overview_frame(holdings, selected_symbol="000001", limit=10)

        self.assertEqual(len(overview), 10)
        self.assertIn("000001", overview["selection_symbol"].tolist())
        selected_row = overview.loc[overview["selection_symbol"] == "000001"].iloc[0]
        self.assertTrue(bool(selected_row["is_selected"]))

    def test_holdings_overview_frame_orders_by_profit_rate_descending(self) -> None:
        holdings = [
            {
                "product_name": "고수익",
                "symbol": "HIGH",
                "quantity": 1,
                "avg_cost": 100,
                "current_price": 180,
                "asset_type": "risk",
            },
            {
                "product_name": "중수익",
                "symbol": "MID",
                "quantity": 1,
                "avg_cost": 100,
                "current_price": 130,
                "asset_type": "risk",
            },
            {
                "product_name": "저수익",
                "symbol": "LOW",
                "quantity": 1,
                "avg_cost": 100,
                "current_price": 105,
                "asset_type": "safe",
            },
        ]

        overview = holdings_overview_frame(holdings, limit=10)

        self.assertEqual(overview["selection_symbol"].tolist(), ["HIGH", "MID", "LOW"])


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
    """이자 자동 적립 제거 이후 호환 동작을 검증한다."""

    def test_projected_today_interest_always_returns_zero(self) -> None:
        account = {"cash_balance": 1_000_000}

        value = projected_today_interest(
            account,
            interest_rows=[{"date": "2026-05-07", "interest_amount": 123.4}],
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

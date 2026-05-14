from __future__ import annotations

from datetime import date
import unittest

from src.valuation import build_company_principal_valuation_snapshots


class CompanyPrincipalValuationTests(unittest.TestCase):
    """입금액 기준 일별 평가 스냅샷 계산을 검증한다."""

    def test_company_principal_valuation_uses_implied_cash_until_today(self) -> None:
        """과거 날짜는 거래 원장 기준 현금을 평가 현금값으로 사용한다."""

        account = {"id": 1, "cash_balance": 2000}
        trade_logs = [
            {"id": 1, "trade_date": "2026-01-01", "trade_type": "employer_deposit", "total_amount": 10000},
            {
                "id": 2,
                "trade_date": "2026-01-02",
                "trade_type": "buy",
                "symbol": "AAA",
                "product_name": "테스트상품",
                "quantity": 2,
                "price": 3000,
                "total_amount": 6000,
            },
        ]
        price_lookup = {"AAA": {"2026-01-02": 3100, "2026-01-03": 3200}}

        snapshots = build_company_principal_valuation_snapshots(
            account=account,
            trade_logs=trade_logs,
            price_lookup=price_lookup,
            end_date=date(2026, 1, 3),
            today_date=date(2026, 1, 4),
            calculation_reason="test",
        )

        self.assertEqual(snapshots[0]["company_principal"], 10000)
        self.assertEqual(snapshots[0]["valuation_amount"], 10000)
        self.assertEqual(snapshots[1]["invested_cost"], 6000)
        self.assertEqual(snapshots[1]["implied_cash"], 4000)
        self.assertEqual(snapshots[1]["holdings_market_value"], 6200)
        self.assertEqual(snapshots[1]["valuation_amount"], 10200)
        self.assertEqual(snapshots[2]["holdings_market_value"], 6400)
        self.assertEqual(snapshots[2]["valuation_amount"], 10400)

    def test_today_uses_actual_cash_balance(self) -> None:
        """오늘 날짜만 실제 account.cash_balance를 평가 현금값으로 사용한다."""

        account = {"id": 1, "cash_balance": 1500}
        trade_logs = [
            {"id": 1, "trade_date": "2026-01-01", "trade_type": "employer_deposit", "total_amount": 10000},
            {
                "id": 2,
                "trade_date": "2026-01-02",
                "trade_type": "buy",
                "symbol": "AAA",
                "product_name": "테스트상품",
                "quantity": 2,
                "price": 3000,
            },
        ]
        price_lookup = {"AAA": {"2026-01-02": 3100}}

        snapshots = build_company_principal_valuation_snapshots(
            account=account,
            trade_logs=trade_logs,
            price_lookup=price_lookup,
            end_date=date(2026, 1, 2),
            today_date=date(2026, 1, 2),
            calculation_reason="test",
        )

        today_snapshot = snapshots[-1]
        self.assertEqual(today_snapshot["cash_source"], "actual")
        self.assertEqual(today_snapshot["actual_cash_balance"], 1500)
        self.assertEqual(today_snapshot["cash_value"], 1500)
        self.assertEqual(today_snapshot["valuation_amount"], 7700)

    def test_personal_deposit_starts_series_and_counts_as_principal(self) -> None:
        """개인 입금도 최초 시작일과 원금 누적에 포함한다."""

        snapshots = build_company_principal_valuation_snapshots(
            account={"id": 1, "cash_balance": 0},
            trade_logs=[
                {"id": 1, "trade_date": "2026-01-01", "trade_type": "personal_deposit", "total_amount": 5000},
                {"id": 2, "trade_date": "2026-01-02", "trade_type": "employer_deposit", "total_amount": 10000},
            ],
            price_lookup={},
            end_date=date(2026, 1, 2),
            today_date=date(2026, 1, 3),
            calculation_reason="test",
        )

        self.assertEqual(len(snapshots), 2)
        self.assertEqual(snapshots[0]["valuation_date"], "2026-01-01")
        self.assertEqual(snapshots[0]["company_principal"], 5000)
        self.assertEqual(snapshots[1]["company_principal"], 15000)

    def test_sell_reduces_remaining_cost_by_fifo(self) -> None:
        """매도는 FIFO lot 기준으로 잔여 매입원가를 차감한다."""

        trade_logs = [
            {"id": 1, "trade_date": "2026-01-01", "trade_type": "employer_deposit", "total_amount": 20000},
            {"id": 2, "trade_date": "2026-01-02", "trade_type": "buy", "symbol": "AAA", "product_name": "A", "quantity": 2, "price": 3000},
            {"id": 3, "trade_date": "2026-01-03", "trade_type": "buy", "symbol": "AAA", "product_name": "A", "quantity": 2, "price": 4000},
            {"id": 4, "trade_date": "2026-01-04", "trade_type": "sell", "symbol": "AAA", "product_name": "A", "quantity": 3, "price": 5000},
        ]

        snapshots = build_company_principal_valuation_snapshots(
            account={"id": 1, "cash_balance": 0},
            trade_logs=trade_logs,
            price_lookup={"AAA": {"2026-01-04": 4500}},
            end_date=date(2026, 1, 4),
            today_date=date(2026, 1, 5),
            calculation_reason="test",
        )

        self.assertEqual(snapshots[-1]["invested_cost"], 4000)
        self.assertEqual(snapshots[-1]["holdings_market_value"], 4500)

    def test_sell_realized_profit_increases_ledger_cash(self) -> None:
        """과거 현금은 입금원금-잔여원가가 아니라 매도대금을 포함한 원장 현금을 사용한다."""

        trade_logs = [
            {"id": 1, "trade_date": "2026-01-01", "trade_type": "employer_deposit", "total_amount": 10000},
            {"id": 2, "trade_date": "2026-01-02", "trade_type": "buy", "symbol": "AAA", "product_name": "A", "quantity": 2, "price": 3000},
            {"id": 3, "trade_date": "2026-01-03", "trade_type": "sell", "symbol": "AAA", "product_name": "A", "quantity": 1, "price": 4000},
        ]

        snapshots = build_company_principal_valuation_snapshots(
            account={"id": 1, "cash_balance": 0},
            trade_logs=trade_logs,
            price_lookup={"AAA": {"2026-01-03": 3200}},
            end_date=date(2026, 1, 3),
            today_date=date(2026, 1, 4),
            calculation_reason="test",
        )

        final_snapshot = snapshots[-1]
        self.assertEqual(final_snapshot["invested_cost"], 3000)
        self.assertEqual(final_snapshot["implied_cash"], 8000)
        self.assertEqual(final_snapshot["cash_value"], 8000)
        self.assertEqual(final_snapshot["valuation_amount"], 11200)

    def test_cash_delta_events_change_ledger_cash_without_changing_principal(self) -> None:
        """이자, 배당, 수수료 등 cash_delta 원장 이벤트는 원금이 아니라 현금에 반영한다."""

        trade_logs = [
            {"id": 1, "trade_date": "2026-01-01", "trade_type": "employer_deposit", "total_amount": 10000},
            {"id": 2, "trade_date": "2026-01-02", "trade_type": "dividend", "total_amount": 200, "cash_delta": 200},
            {"id": 3, "trade_date": "2026-01-03", "trade_type": "fee", "total_amount": 30, "cash_delta": -30},
        ]

        snapshots = build_company_principal_valuation_snapshots(
            account={"id": 1, "cash_balance": 0},
            trade_logs=trade_logs,
            price_lookup={},
            end_date=date(2026, 1, 3),
            today_date=date(2026, 1, 4),
            calculation_reason="test",
        )

        self.assertEqual(snapshots[-1]["company_principal"], 10000)
        self.assertEqual(snapshots[-1]["implied_cash"], 10170)
        self.assertEqual(snapshots[-1]["profit_loss"], 170)

    def test_price_lookup_uses_previous_close_before_unit_cost_fallback(self) -> None:
        """해당 날짜 가격이 없으면 직전 종가를 쓰고, 가격 이력이 없으면 매입가 fallback을 기록한다."""

        trade_logs = [
            {"id": 1, "trade_date": "2026-01-01", "trade_type": "employer_deposit", "total_amount": 10000},
            {"id": 2, "trade_date": "2026-01-02", "trade_type": "buy", "symbol": "AAA", "product_name": "A", "quantity": 1, "price": 3000},
            {"id": 3, "trade_date": "2026-01-02", "trade_type": "buy", "symbol": "BBB", "product_name": "B", "quantity": 1, "price": 2000},
        ]

        snapshots = build_company_principal_valuation_snapshots(
            account={"id": 1, "cash_balance": 0},
            trade_logs=trade_logs,
            price_lookup={"AAA": {"2026-01-02": 3200}},
            end_date=date(2026, 1, 3),
            today_date=date(2026, 1, 4),
            calculation_reason="test",
        )

        self.assertEqual(snapshots[-1]["holdings_market_value"], 5200)
        self.assertEqual(snapshots[-1]["missing_price_symbols"], ["BBB"])

    def test_over_invested_amount_tracks_cost_above_company_principal(self) -> None:
        """잔여 매입원가가 입금 원금을 넘으면 초과 매입액을 따로 기록한다."""

        snapshots = build_company_principal_valuation_snapshots(
            account={"id": 1, "cash_balance": 0},
            trade_logs=[
                {"id": 1, "trade_date": "2026-01-01", "trade_type": "employer_deposit", "total_amount": 5000},
                {"id": 2, "trade_date": "2026-01-02", "trade_type": "buy", "symbol": "AAA", "product_name": "A", "quantity": 1, "price": 7000},
            ],
            price_lookup={"AAA": {"2026-01-02": 7000}},
            end_date=date(2026, 1, 2),
            today_date=date(2026, 1, 3),
            calculation_reason="test",
        )

        self.assertEqual(snapshots[-1]["implied_cash"], 0)
        self.assertEqual(snapshots[-1]["over_invested_amount"], 2000)

    def test_personal_deposit_only_creates_snapshots(self) -> None:
        """회사 납입금이 없어도 개인 입금이 있으면 스냅샷을 생성한다."""

        snapshots = build_company_principal_valuation_snapshots(
            account={"id": 1, "cash_balance": 1000},
            trade_logs=[{"id": 1, "trade_date": "2026-01-01", "trade_type": "personal_deposit", "total_amount": 1000}],
            price_lookup={},
            end_date=date(2026, 1, 3),
            today_date=date(2026, 1, 4),
            calculation_reason="test",
        )

        self.assertEqual([row["valuation_date"] for row in snapshots], ["2026-01-01", "2026-01-02", "2026-01-03"])
        self.assertEqual(snapshots[0]["company_principal"], 1000)

    def test_returns_empty_without_deposit(self) -> None:
        """입금성 거래가 없으면 스냅샷을 생성하지 않는다."""

        snapshots = build_company_principal_valuation_snapshots(
            account={"id": 1, "cash_balance": 0},
            trade_logs=[{"id": 1, "trade_date": "2026-01-01", "trade_type": "buy", "symbol": "AAA", "quantity": 1, "price": 1000}],
            price_lookup={},
            end_date=date(2026, 1, 3),
            today_date=date(2026, 1, 4),
            calculation_reason="test",
        )

        self.assertEqual(snapshots, [])


if __name__ == "__main__":
    unittest.main()

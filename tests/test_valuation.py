from __future__ import annotations

from datetime import date
import unittest

from src.valuation import build_company_principal_valuation_snapshots


class CompanyPrincipalValuationTests(unittest.TestCase):
    """회사입금액 기준 일별 평가 스냅샷 계산을 검증한다."""

    def test_company_principal_valuation_uses_implied_cash_until_today(self) -> None:
        """과거 날짜는 회사입금 원금과 잔여 매입원가 차이를 현금간주액으로 사용한다."""

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

    def test_personal_deposit_is_excluded_from_company_principal(self) -> None:
        """개인 입금은 회사입금 원금에 포함하지 않는다."""

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

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["valuation_date"], "2026-01-02")
        self.assertEqual(snapshots[0]["company_principal"], 10000)

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
        """잔여 매입원가가 회사입금 원금을 넘으면 초과 매입액을 따로 기록한다."""

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

    def test_returns_empty_without_company_deposit(self) -> None:
        """회사입금 기록이 없으면 스냅샷을 생성하지 않는다."""

        snapshots = build_company_principal_valuation_snapshots(
            account={"id": 1, "cash_balance": 1000},
            trade_logs=[{"id": 1, "trade_date": "2026-01-01", "trade_type": "personal_deposit", "total_amount": 1000}],
            price_lookup={},
            end_date=date(2026, 1, 3),
            today_date=date(2026, 1, 4),
            calculation_reason="test",
        )

        self.assertEqual(snapshots, [])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_daily_rollup
from src import sqlite_db


class DailyRollupValuationSnapshotTests(unittest.TestCase):
    """일별 롤업의 평가액 기록 재계산 연동을 검증한다."""

    def test_sqlite_rollup_records_company_principal_valuation_snapshots(self) -> None:
        """SQLite daily rollup은 기존 계좌 스냅샷과 평가액 기록을 함께 저장한다."""

        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "rollup.db"
            with patch.object(sqlite_db, "DB_PATH", database_path):
                sqlite_db.initialize_database()
                account_id = sqlite_db.create_account("rollup-test", opening_cash=0)
                sqlite_db.record_cash_flow(
                    account_id,
                    flow_type="employer_deposit",
                    amount=10000,
                    trade_date="2026-01-01",
                )
                sqlite_db.record_trade(
                    account_id,
                    symbol="AAA",
                    product_name="테스트상품",
                    trade_type="buy",
                    asset_type="risk",
                    quantity=2,
                    price=3000,
                    trade_date="2026-01-02",
                )

                with patch(
                    "scripts.run_daily_rollup.build_price_lookup_for_trade_logs",
                    return_value={"AAA": {"2026-01-02": 3100}},
                ):
                    results = run_daily_rollup.run_sqlite_rollup(date(2026, 1, 2), dry_run=False)

                rows = sqlite_db.list_valuation_snapshots(account_id)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].valuation_snapshot_count, 2)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["valuation_amount"], 10200)


if __name__ == "__main__":
    unittest.main()

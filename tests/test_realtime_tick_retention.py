from __future__ import annotations

import importlib.util
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch


def _load_tick_retention_module():
    """tick retention 스크립트를 테스트 모듈로 불러온다."""

    module_name = "test_run_realtime_tick_retention_module"
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_realtime_tick_retention.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("run_realtime_tick_retention.py 모듈을 불러오지 못했습니다.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


tick_retention = _load_tick_retention_module()


class RealtimeTickAggregationTests(unittest.TestCase):
    """실시간 tick OHLC 집계 로직을 검증한다."""

    def test_aggregate_ticks_builds_ohlc_bars_by_interval(self) -> None:
        """1분/5분 bucket 기준으로 open/high/low/close와 tick 수를 계산한다."""

        ticks = [
            {
                "id": 1,
                "account_id": 7,
                "symbol": "005930",
                "price": 100,
                "previous_close": 95,
                "day_change_rate": 5.0,
                "currency": "KRW",
                "quote_time": "2026-05-01T09:00:05",
            },
            {
                "id": 2,
                "account_id": 7,
                "symbol": "005930",
                "price": 103,
                "previous_close": 95,
                "day_change_rate": 8.0,
                "currency": "KRW",
                "quote_time": "2026-05-01T09:00:50",
            },
            {
                "id": 3,
                "account_id": 7,
                "symbol": "005930",
                "price": 101,
                "previous_close": 95,
                "day_change_rate": 6.0,
                "currency": "KRW",
                "quote_time": "2026-05-01T09:01:10",
            },
        ]

        bars = tick_retention.aggregate_ticks(ticks, intervals=("1m", "5m"), timezone_name="Asia/Seoul")
        bar_by_key = {(bar["interval"], bar["bucket_start"]): bar for bar in bars}

        one_minute = bar_by_key[("1m", "2026-05-01T09:00:00")]
        self.assertEqual(one_minute["open_price"], 100)
        self.assertEqual(one_minute["high_price"], 103)
        self.assertEqual(one_minute["low_price"], 100)
        self.assertEqual(one_minute["close_price"], 103)
        self.assertEqual(one_minute["tick_count"], 2)

        five_minute = bar_by_key[("5m", "2026-05-01T09:00:00")]
        self.assertEqual(five_minute["open_price"], 100)
        self.assertEqual(five_minute["high_price"], 103)
        self.assertEqual(five_minute["low_price"], 100)
        self.assertEqual(five_minute["close_price"], 101)
        self.assertEqual(five_minute["tick_count"], 3)


class SQLiteRealtimeTickRetentionTests(unittest.TestCase):
    """SQLite tick retention 실행을 검증한다."""

    def test_run_retention_aggregates_old_ticks_and_deletes_only_after_apply(self) -> None:
        """기본 dry-run은 쓰지 않고, apply 때만 bar 저장과 raw tick 삭제를 수행한다."""

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "portfolio.db"
            with patch.object(tick_retention.sqlite_db, "DB_PATH", db_path):
                tick_retention.sqlite_db.initialize_database()
                self._seed_ticks(db_path)
                store = tick_retention.SQLiteTickRetentionStore()
                policy = tick_retention.RetentionPolicy(
                    raw_retention_days=7,
                    intraday_retention_days=90,
                    timezone_name="Asia/Seoul",
                )
                as_of = tick_retention.parse_timestamp("2026-05-13T00:00:00", "Asia/Seoul")

                dry_summary = tick_retention.run_retention(store, policy, apply_changes=False, as_of=as_of)

                self.assertTrue(dry_summary.dry_run)
                self.assertEqual(dry_summary.raw_ticks_to_delete, 5)
                self.assertEqual(dry_summary.bars_by_interval, {"1m": 2, "5m": 1, "1d": 1})
                self.assertEqual(self._count_rows(db_path, "realtime_price_ticks"), 6)
                self.assertEqual(self._count_rows(db_path, "realtime_price_bars"), 0)

                apply_summary = tick_retention.run_retention(store, policy, apply_changes=True, as_of=as_of)

                self.assertFalse(apply_summary.dry_run)
                self.assertEqual(apply_summary.raw_ticks_deleted, 5)
                self.assertEqual(self._count_rows(db_path, "realtime_price_ticks"), 1)
                self.assertEqual(self._count_rows(db_path, "realtime_price_bars"), 4)

    @staticmethod
    def _seed_ticks(db_path: Path) -> None:
        connection = sqlite3.connect(db_path)
        try:
            connection.execute(
                """
                INSERT INTO accounts (id, name, account_type, cash_balance, created_at, updated_at)
                VALUES (1, 'retention-test', 'retirement', 0, '2026-01-01T00:00:00', '2026-01-01T00:00:00')
                """
            )
            rows = [
                (1, 1, "005930", 100, "2026-05-01T09:00:05"),
                (2, 1, "005930", 103, "2026-05-01T09:00:50"),
                (3, 1, "005930", 101, "2026-05-01T09:01:10"),
                (4, 1, "005930", 90, "2026-01-15T09:00:00"),
                (5, 1, "005930", 92, "2026-01-15T15:00:00"),
                (6, 1, "005930", 110, "2026-05-12T09:00:00"),
            ]
            connection.executemany(
                """
                INSERT INTO realtime_price_ticks (
                    id, account_id, symbol, price, previous_close, day_change_rate,
                    currency, quote_time, ingested_at, source, metadata_json
                )
                VALUES (?, ?, ?, ?, 95, 1.2, 'KRW', ?, ?, 'unit-test', '{}')
                """,
                [(row_id, account_id, symbol, price, quote_time, quote_time) for row_id, account_id, symbol, price, quote_time in rows],
            )
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _count_rows(db_path: Path, table_name: str) -> int:
        connection = sqlite3.connect(db_path)
        try:
            return int(connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()

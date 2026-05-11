from __future__ import annotations

from datetime import date
import importlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import requests

from src import sqlite_db
from src.db import (
    BACKEND_SQLITE,
    BACKEND_SUPABASE,
    _demo_workspace_blueprint,
    _select_initial_backend,
    _sync_legacy_interest_history_for_buy,
    _run_with_fallback,
    _should_fallback,
    _supabase_create_account,
    delete_account,
    is_accounts_hotfix_error,
    seed_demo_workspace,
    sync_account_rollup,
)


def _http_error(status_code: int, detail: str) -> requests.HTTPError:
    """테스트용 HTTPError를 생성한다."""

    response = requests.Response()
    response.status_code = status_code
    response._content = detail.encode("utf-8")
    response.url = "https://example.supabase.co/rest/v1/accounts"
    request = requests.Request("POST", response.url).prepare()
    response.request = request
    return requests.HTTPError(detail, response=response, request=request)


class AccountsHotfixErrorTests(unittest.TestCase):
    """accounts RLS 핫픽스 오류 판별을 검증한다."""

    def test_is_accounts_hotfix_error_matches_hotfix_guidance_message(self) -> None:
        """핫픽스 안내 메시지를 운영 조치 필요 상태로 인식한다."""

        error = RuntimeError(
            "운영 Supabase의 accounts INSERT RLS 정책이 오래된 상태입니다. "
            "setup_supabase.sql의 owner_user_id 핫픽스를 적용한 뒤 다시 시도해 주세요."
        )

        self.assertTrue(is_accounts_hotfix_error(error))
        self.assertFalse(is_accounts_hotfix_error(RuntimeError("일반 입력 오류입니다.")))


class SupabaseCreateAccountTests(unittest.TestCase):
    """Supabase 계좌 생성 payload와 재시도 동작을 검증한다."""

    @patch("src.db._supabase_list_accounts", return_value=[])
    @patch("src.db._storage_account_name", return_value="user-123::IRP")
    @patch("src.db._require_user_id", return_value="user-123")
    @patch("src.db.now_iso", return_value="2026-05-08T11:20:00")
    @patch("src.db._supabase_request")
    def test_create_account_includes_owner_user_id_when_schema_supports_it(
        self,
        request_mock,
        _now_iso_mock,
        _user_id_mock,
        _storage_name_mock,
        _list_accounts_mock,
    ) -> None:
        """신규 스키마에서는 owner_user_id를 포함해 계좌를 생성한다."""

        request_mock.side_effect = [
            None,
            [{"id": 42, "name": "user-123::IRP"}],
        ]

        account_id = _supabase_create_account("IRP", "retirement", 1_000_000)

        self.assertEqual(account_id, 42)
        first_call = request_mock.call_args_list[0]
        self.assertEqual(first_call.args[:2], ("POST", "accounts"))
        self.assertEqual(first_call.kwargs["data"]["owner_user_id"], "user-123")
        self.assertEqual(first_call.kwargs["data"]["cash_balance"], 1_000_000.0)

    @patch("src.db._supabase_list_accounts", return_value=[])
    @patch("src.db._storage_account_name", return_value="user-123::IRP")
    @patch("src.db._require_user_id", return_value="user-123")
    @patch("src.db.now_iso", return_value="2026-05-08T11:20:00")
    @patch("src.db._supabase_request")
    def test_create_account_retries_without_owner_user_id_on_legacy_schema(
        self,
        request_mock,
        _now_iso_mock,
        _user_id_mock,
        _storage_name_mock,
        _list_accounts_mock,
    ) -> None:
        """구형 스키마면 owner_user_id 없이 한 번 재시도한다."""

        request_mock.side_effect = [
            _http_error(400, "Could not find the 'owner_user_id' column of 'accounts' in the schema cache"),
            None,
            [{"id": 77, "name": "user-123::IRP"}],
        ]

        account_id = _supabase_create_account("IRP", "retirement", 0)

        self.assertEqual(account_id, 77)
        first_call = request_mock.call_args_list[0]
        second_call = request_mock.call_args_list[1]
        self.assertIn("owner_user_id", first_call.kwargs["data"])
        self.assertNotIn("owner_user_id", second_call.kwargs["data"])
        self.assertEqual(second_call.args[:2], ("POST", "accounts"))


class BackendFallbackPolicyTests(unittest.TestCase):
    """Supabase 오류별 SQLite fallback 정책을 검증한다."""

    @patch("src.db.app_auth.is_demo_user", return_value=True)
    def test_select_initial_backend_prefers_sqlite_for_demo_session(self, _is_demo_user_mock) -> None:
        """로컬 데모 세션이면 Supabase 설정이 있어도 SQLite를 우선 사용한다."""

        backend, reason = _select_initial_backend()

        self.assertEqual(backend, BACKEND_SQLITE)
        self.assertIn("데모 접속 세션", reason)

    def test_should_not_fallback_on_401_or_403(self) -> None:
        """인증/권한 오류는 로컬 SQLite로 우회하지 않는다."""

        self.assertFalse(_should_fallback(_http_error(401, "JWT expired")))
        self.assertFalse(_should_fallback(_http_error(403, "row-level security policy for table \"accounts\"")))

    @patch("src.db._activate_sqlite")
    @patch("src.db._current_backend", return_value=BACKEND_SUPABASE)
    def test_run_with_fallback_reraises_403_without_switching_to_sqlite(
        self,
        _current_backend_mock,
        activate_sqlite_mock,
    ) -> None:
        """403 권한 오류는 SQLite fallback 없이 그대로 재전파한다."""

        error = _http_error(403, "row-level security policy for table \"accounts\"")

        def supabase_call() -> str:
            raise error

        def sqlite_call() -> str:
            self.fail("403 권한 오류에서는 SQLite fallback이 호출되면 안 됩니다.")

        with self.assertRaises(requests.HTTPError):
            _run_with_fallback(supabase_call=supabase_call, sqlite_call=sqlite_call)

        activate_sqlite_mock.assert_not_called()

    @patch("src.db._activate_sqlite")
    @patch("src.db._current_backend", return_value=BACKEND_SUPABASE)
    def test_run_with_fallback_switches_to_sqlite_on_500(
        self,
        _current_backend_mock,
        activate_sqlite_mock,
    ) -> None:
        """서버 오류는 기존 fallback 동작을 유지한다."""

        error = _http_error(500, "internal server error")

        def supabase_call() -> str:
            raise error

        sqlite_called = {"value": False}

        def sqlite_call() -> str:
            sqlite_called["value"] = True
            return "sqlite-ok"

        result = _run_with_fallback(supabase_call=supabase_call, sqlite_call=sqlite_call)

        self.assertEqual(result, "sqlite-ok")
        self.assertTrue(sqlite_called["value"])
        activate_sqlite_mock.assert_called_once()


class DeleteAccountTests(unittest.TestCase):
    """공개 계좌 삭제 wrapper를 검증한다."""

    @patch("src.db._run_with_fallback")
    def test_delete_account_routes_to_storage_specific_delete(self, run_with_fallback_mock) -> None:
        """계좌 삭제는 내부 fallback 경유로 저장소별 delete 구현을 호출한다."""

        delete_account(77)

        self.assertTrue(run_with_fallback_mock.called)
        _, kwargs = run_with_fallback_mock.call_args
        self.assertEqual(kwargs["supabase_call"].__name__, "<lambda>")
        self.assertEqual(kwargs["sqlite_call"].__name__, "<lambda>")


class DemoWorkspaceSeedTests(unittest.TestCase):
    """데모 워크스페이스 재시드 동작을 검증한다."""

    def _blueprint(self) -> dict[str, object]:
        return {
            "accounts": (
                {
                    "name": "데모 IRP",
                    "account_type": "retirement",
                    "opening_cash": 0.0,
                    "cash_flows": (),
                    "trades": (),
                    "interest": (),
                    "price_updates": {},
                    "snapshot_date": "2026-05-08",
                },
                {
                    "name": "데모 일반계좌",
                    "account_type": "brokerage",
                    "opening_cash": 0.0,
                    "cash_flows": (),
                    "trades": (),
                    "interest": (),
                    "price_updates": {},
                    "snapshot_date": "2026-05-08",
                },
            ),
            "transfers": (),
        }

    @patch("src.db._demo_workspace_blueprint")
    @patch("src.db.list_accounts")
    @patch("src.db._delete_account")
    @patch("src.db.create_account")
    @patch("src.db.record_cash_flow")
    @patch("src.db.record_trade")
    @patch("src.db.record_account_transfer")
    @patch("src.db.set_holding_price")
    @patch("src.db.record_account_snapshot")
    @patch("src.db._demo_account_totals", return_value=(0.0, 0.0, 0.0))
    @patch("src.db.list_holdings", return_value=[])
    def test_seed_demo_workspace_resets_existing_demo_accounts_before_rebuild(
        self,
        _list_holdings_mock,
        _demo_totals_mock,
        record_snapshot_mock,
        _set_holding_price_mock,
        _record_transfer_mock,
        _record_trade_mock,
        _record_cash_flow_mock,
        create_account_mock,
        delete_account_mock,
        list_accounts_mock,
        blueprint_mock,
    ) -> None:
        """데모 계좌가 하나라도 있으면 기존 내부 계좌를 지우고 처음부터 다시 만든다."""

        blueprint_mock.return_value = self._blueprint()
        list_accounts_mock.return_value = [
            {"id": 18, "name": "데모 IRP"},
            {"id": 19, "name": "데모 일반계좌"},
        ]
        create_account_mock.side_effect = [21, 22]

        result = seed_demo_workspace()

        self.assertEqual(
            delete_account_mock.call_args_list,
            [
                unittest.mock.call(19),
                unittest.mock.call(18),
            ],
        )
        self.assertTrue(result["created"])
        self.assertEqual(result["selected_account_id"], 21)
        self.assertEqual(create_account_mock.call_count, 2)
        self.assertEqual(record_snapshot_mock.call_count, 2)
        self.assertIn("초기화", str(result["message"]))

    def test_demo_workspace_blueprint_spans_five_years_with_diverse_activity(self) -> None:
        """기본 데모 블루프린트가 장기 투자 히스토리와 다양한 이벤트를 포함하는지 확인한다."""

        blueprint = _demo_workspace_blueprint()
        accounts = list(blueprint["accounts"])

        self.assertEqual(len(accounts), 2)

        trade_dates: list[str] = []
        trade_types: set[str] = set()
        asset_types: set[str] = set()
        flow_types: set[str] = set()
        traded_symbols: set[str] = set()

        for account_spec in accounts:
            trade_dates.extend(str(item["trade_date"]) for item in account_spec["cash_flows"])
            trade_dates.extend(str(item["trade_date"]) for item in account_spec["trades"])
            trade_types.update(str(item["trade_type"]) for item in account_spec["trades"])
            asset_types.update(str(item["asset_type"]) for item in account_spec["trades"])
            flow_types.update(str(item["flow_type"]) for item in account_spec["cash_flows"])
            traded_symbols.update(str(item["symbol"]) for item in account_spec["trades"])

        earliest_date = min(date.fromisoformat(item) for item in trade_dates)
        latest_date = max(date.fromisoformat(item) for item in trade_dates)

        self.assertGreaterEqual((latest_date - earliest_date).days, 365 * 4 + 180)
        self.assertIn("sell", trade_types)
        self.assertIn("withdraw", flow_types)
        self.assertEqual(asset_types, {"risk", "safe"})
        self.assertGreaterEqual(len(traded_symbols), 10)
        all_product_names = {
            str(item["product_name"])
            for account_spec in accounts
            for item in account_spec["trades"]
        }
        self.assertIn("삼성전자", all_product_names)
        self.assertIn("SK하이닉스", all_product_names)
        self.assertIn("두산에너빌리티", all_product_names)
        self.assertTrue(any("원자력" in name for name in all_product_names))
        self.assertGreaterEqual(len(blueprint["transfers"]), 2)


class SyncAccountRollupTests(unittest.TestCase):
    """이자 적립 없이 당일 스냅샷만 갱신하는 동작을 검증한다."""

    @patch("src.db.record_account_snapshot")
    @patch("src.db.list_account_snapshots", return_value=[])
    @patch("src.db.list_daily_interest", return_value=[])
    @patch("src.db.list_trade_logs", return_value=[])
    @patch("src.db._demo_account_totals", return_value=(802.6028, 200.0, 200.0))
    @patch("src.db.get_account")
    def test_sync_account_rollup_records_today_snapshot_when_missing(
        self,
        get_account_mock,
        _demo_account_totals_mock,
        _list_trade_logs_mock,
        _list_daily_interest_mock,
        _list_account_snapshots_mock,
        record_snapshot_mock,
    ) -> None:
        """당일 스냅샷이 없으면 현재 평가값으로 한 건 저장한다."""

        get_account_mock.return_value = {"id": 7, "cash_balance": 800.0}

        result = sync_account_rollup(7, today_date="2026-05-09")

        record_snapshot_mock.assert_called_once_with(
            7,
            snapshot_date="2026-05-09",
            cash_balance=802.6028,
            market_value=200.0,
            total_value=1002.6028,
            total_cost=200.0,
        )
        self.assertEqual(result["interest_rows_added"], 0)
        self.assertEqual(result["interest_rows_updated"], 0)
        self.assertEqual(result["interest_rows_removed"], 0)
        self.assertEqual(result["historical_snapshots_updated"], 0)
        self.assertEqual(result["interest_amount_added"], 0.0)
        self.assertEqual(result["snapshot_date"], "2026-05-09")
        self.assertTrue(result["snapshot_updated"])

    @patch("src.db.record_account_snapshot")
    @patch(
        "src.db.list_account_snapshots",
        return_value=[
            {
                "snapshot_date": "2026-05-09",
                "cash_balance": 802.6028,
                "market_value": 200.0,
                "total_value": 1002.6028,
                "total_cost": 200.0,
            }
        ],
    )
    @patch("src.db.list_daily_interest", return_value=[])
    @patch("src.db.list_trade_logs", return_value=[])
    @patch("src.db._demo_account_totals", return_value=(802.6028, 200.0, 200.0))
    @patch("src.db.get_account")
    def test_sync_account_rollup_skips_snapshot_when_same_day_values_match(
        self,
        get_account_mock,
        _demo_account_totals_mock,
        _list_trade_logs_mock,
        _list_daily_interest_mock,
        _list_account_snapshots_mock,
        record_snapshot_mock,
    ) -> None:
        """당일 스냅샷이 이미 최신 값과 같으면 다시 저장하지 않는다."""

        get_account_mock.return_value = {"id": 7, "cash_balance": 800.0}

        result = sync_account_rollup(7, today_date="2026-05-09")

        record_snapshot_mock.assert_not_called()
        self.assertFalse(result["snapshot_updated"])

    @patch("src.db.record_account_snapshot")
    @patch(
        "src.db.list_account_snapshots",
        return_value=[
            {
                "snapshot_date": "2026-05-06",
                "cash_balance": 999.0,
                "market_value": 0.0,
                "total_value": 999.0,
                "total_cost": 0.0,
            },
            {
                "snapshot_date": "2026-05-07",
                "cash_balance": 700.0,
                "market_value": 200.0,
                "total_value": 900.0,
                "total_cost": 0.0,
            },
            {
                "snapshot_date": "2026-05-08",
                "cash_balance": 700.0,
                "market_value": 200.0,
                "total_value": 900.0,
                "total_cost": 0.0,
            },
        ],
    )
    @patch("src.db.list_daily_interest", return_value=[])
    @patch(
        "src.db.list_trade_logs",
        return_value=[
            {"trade_type": "personal_deposit", "trade_date": "2026-05-06", "cash_delta": 1000.0, "total_amount": 1000.0},
            {"trade_type": "buy", "trade_date": "2026-05-07", "cash_delta": -200.0, "total_amount": 200.0, "quantity": 1.0, "price": 200.0, "symbol": "AAA"},
        ],
    )
    @patch("src.db._demo_account_totals", return_value=(800.0, 200.0, 200.0))
    @patch("src.db.get_account")
    def test_sync_account_rollup_refreshes_existing_historical_snapshots_when_ledger_changed(
        self,
        get_account_mock,
        _demo_account_totals_mock,
        _list_trade_logs_mock,
        _list_daily_interest_mock,
        _list_account_snapshots_mock,
        record_snapshot_mock,
    ) -> None:
        """기존 과거 스냅샷이 현재 원장과 다르면 가능한 범위에서 다시 맞춘다."""

        get_account_mock.return_value = {
            "id": 7,
            "cash_balance": 800.0,
            "created_at": "2026-05-06T09:00:00",
        }

        result = sync_account_rollup(7, today_date="2026-05-09")

        self.assertEqual(
            record_snapshot_mock.call_args_list,
            [
                unittest.mock.call(
                    7,
                    snapshot_date="2026-05-06",
                    cash_balance=1000.0,
                    market_value=0.0,
                    total_value=1000.0,
                    total_cost=0.0,
                ),
                unittest.mock.call(
                    7,
                    snapshot_date="2026-05-07",
                    cash_balance=800.0,
                    market_value=200.0,
                    total_value=1000.0,
                    total_cost=200.0,
                ),
                unittest.mock.call(
                    7,
                    snapshot_date="2026-05-08",
                    cash_balance=800.0,
                    market_value=200.0,
                    total_value=1000.0,
                    total_cost=200.0,
                ),
                unittest.mock.call(
                    7,
                    snapshot_date="2026-05-09",
                    cash_balance=800.0,
                    market_value=200.0,
                    total_value=1000.0,
                    total_cost=200.0,
                ),
            ],
        )
        self.assertEqual(result["historical_snapshots_updated"], 3)
        self.assertTrue(result["snapshot_updated"])


class LegacyInterestSyncTests(unittest.TestCase):
    """기존 이자 원장 계좌의 매수 전 재동기화 동작을 검증한다."""

    @patch("src.db._replace_interest_history")
    @patch("src.db._interest_sync_diff")
    @patch("src.db._build_interest_schedule")
    @patch("src.db.list_daily_interest")
    @patch("src.db.list_trade_logs")
    @patch("src.db.get_account")
    def test_sync_legacy_interest_history_for_buy_rebuilds_when_interest_history_exists(
        self,
        get_account_mock,
        list_trade_logs_mock,
        list_daily_interest_mock,
        build_interest_schedule_mock,
        interest_sync_diff_mock,
        replace_interest_history_mock,
    ) -> None:
        """기존 이자 이력이 남아 있으면 매수 전에 이자 원장을 재구성한다."""

        get_account_mock.return_value = {"id": 7, "cash_balance": 1000.0}
        list_trade_logs_mock.return_value = [
            {
                "trade_type": "interest",
                "product_name": "일별 이자",
                "trade_date": "2026-05-10",
                "cash_delta": 2.5,
            }
        ]
        list_daily_interest_mock.return_value = [{"date": "2026-05-10", "interest_amount": 2.5}]
        build_interest_schedule_mock.return_value = [("2026-05-10", 2.5), ("2026-05-11", 2.6)]
        interest_sync_diff_mock.return_value = {
            "added_dates": ["2026-05-11"],
            "requires_rebuild": False,
            "net_amount_delta": 2.6,
        }

        _sync_legacy_interest_history_for_buy(7, trade_type="buy")

        replace_interest_history_mock.assert_called_once()
        self.assertEqual(replace_interest_history_mock.call_args.args[0], 7)
        self.assertEqual(
            replace_interest_history_mock.call_args.kwargs["desired_entries"],
            [("2026-05-10", 2.5), ("2026-05-11", 2.6)],
        )

    @patch("src.db._replace_interest_history")
    @patch("src.db.list_daily_interest", return_value=[])
    @patch("src.db.list_trade_logs", return_value=[])
    @patch("src.db.get_account", return_value={"id": 7, "cash_balance": 1000.0})
    def test_sync_legacy_interest_history_for_buy_skips_accounts_without_interest_history(
        self,
        _get_account_mock,
        _list_trade_logs_mock,
        _list_daily_interest_mock,
        replace_interest_history_mock,
    ) -> None:
        """이자 이력이 없는 계좌는 기존 매수 경로를 그대로 사용한다."""

        _sync_legacy_interest_history_for_buy(7, trade_type="buy")

        replace_interest_history_mock.assert_not_called()


class SQLiteRealtimeQuotePersistenceTests(unittest.TestCase):
    """SQLite 실시간 quote overwrite/append 동작을 검증한다."""

    def test_record_realtime_price_tick_updates_holding_and_appends_tick_history(self) -> None:
        """tick 저장 시 holdings 현재가와 실시간 이력 테이블이 함께 갱신된다."""

        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "portfolio.db"
            with patch.dict(os.environ, {"RETIREMENT_DB_PATH": str(database_path)}, clear=False):
                sqlite_module = importlib.reload(sqlite_db)
                sqlite_module.initialize_database()
                account_id = sqlite_module.create_account("user-1::테스트 계좌", opening_cash=500000)
                sqlite_module.record_trade(
                    account_id,
                    symbol="005930",
                    product_name="삼성전자",
                    trade_type="buy",
                    asset_type="risk",
                    quantity=2,
                    price=65000,
                    trade_date="2026-05-10",
                    notes="테스트 매수",
                )
                holding = sqlite_module.list_holdings(account_id)[0]

                sqlite_module.record_realtime_price_tick(
                    account_id=account_id,
                    holding_id=int(holding["id"]),
                    symbol="005930",
                    price=71200,
                    previous_close=70000,
                    day_change_rate=1.7143,
                    currency="KRW",
                    quote_time="2026-05-10T09:15:00",
                    metadata_json={"source": "unit-test"},
                )

                updated_holding = sqlite_module.list_holdings(account_id)[0]
                ticks = sqlite_module.list_realtime_price_ticks(account_id, limit=5)

                self.assertEqual(float(updated_holding["current_price"]), 71200.0)
                self.assertEqual(str(updated_holding["price_updated_at"]), "2026-05-10T09:15:00")
                self.assertEqual(len(ticks), 1)
                self.assertEqual(float(ticks[0]["price"]), 71200.0)
                self.assertEqual(float(ticks[0]["previous_close"]), 70000.0)
                self.assertEqual(float(ticks[0]["day_change_rate"]), 1.7143)
                self.assertEqual(str(ticks[0]["metadata_json"]), '{"source":"unit-test"}')
                self.assertEqual(sqlite_module.latest_realtime_quote_time(account_id), "2026-05-10T09:15:00")


if __name__ == "__main__":
    unittest.main()

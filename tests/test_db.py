from __future__ import annotations

from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import requests

import src.db as db_module
from src import sqlite_db
from src.db import (
    BACKEND_SQLITE,
    BACKEND_SUPABASE,
    _demo_workspace_blueprint,
    _select_initial_backend,
    _sqlite_delete_trade_log,
    _sqlite_update_trade_log,
    _supabase_adjust_cash_balance,
    _supabase_delete_trade_log,
    _sync_legacy_interest_history_for_buy,
    _run_with_fallback,
    _should_fallback,
    _supabase_create_account,
    _supabase_record_trade,
    _supabase_record_valuation_snapshots,
    _supabase_replace_interest_history,
    _supabase_update_trade_log,
    clear_data_cache,
    delete_account,
    is_accounts_hotfix_error,
    mark_data_dirty,
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

    def test_default_supabase_url_is_empty(self) -> None:
        """운영 Supabase URL은 코드 기본값으로 하드코딩하지 않는다."""

        self.assertEqual(db_module.DEFAULT_SUPABASE_URL, "")

    def test_has_supabase_config_requires_valid_url_and_key(self) -> None:
        """Supabase 활성화는 유효한 프로젝트 URL과 키가 모두 있을 때만 허용한다."""

        with (
            patch("src.db._supabase_url", return_value=""),
            patch("src.db._supabase_key", return_value="configured-key"),
        ):
            self.assertFalse(db_module._has_supabase_config())

        with (
            patch("src.db._supabase_url", return_value="http://demo.supabase.co"),
            patch("src.db._supabase_key", return_value="configured-key"),
        ):
            self.assertFalse(db_module._has_supabase_config())

        with (
            patch("src.db._supabase_url", return_value="https://demo.supabase.co"),
            patch("src.db._supabase_key", return_value="configured-key"),
        ):
            self.assertTrue(db_module._has_supabase_config())

    @patch("src.db._sqlite_has_user_data", return_value=False)
    @patch("src.db._has_supabase_config", return_value=False)
    @patch("src.db._normalized_backend_override", return_value=BACKEND_SUPABASE)
    @patch("src.db.app_auth.is_demo_user", return_value=False)
    def test_select_initial_backend_disables_forced_supabase_without_config(
        self,
        _is_demo_user_mock,
        _backend_override_mock,
        _has_supabase_config_mock,
        _sqlite_has_user_data_mock,
    ) -> None:
        """강제 Supabase 설정이어도 URL/키가 유효하지 않으면 SQLite로 남긴다."""

        backend, reason = _select_initial_backend()

        self.assertEqual(backend, BACKEND_SQLITE)
        self.assertIn("Supabase URL 또는 키", reason)

    def test_backend_status_marks_missing_url_when_only_key_exists(self) -> None:
        """SUPABASE_KEY만 있는 환경은 Supabase 설정 미완성으로 진단한다."""

        def fake_read_config(name: str, default: str = "") -> tuple[str, str]:
            values = {
                "SUPABASE_URL": ("", "missing"),
                "SUPABASE_KEY": ("configured-key", "env"),
                "PORTFOLIO_BACKEND": ("auto", "default"),
            }
            return values.get(name, (default, "default" if default else "missing"))

        with (
            patch("src.db._read_config_value", side_effect=fake_read_config),
            patch("src.db._current_backend", return_value=BACKEND_SQLITE),
        ):
            status = db_module.backend_status()

        self.assertFalse(status["has_supabase_config"])
        self.assertIn("SUPABASE_URL", status["missing_config"])
        self.assertIn("비활성화", " ".join(status["notices"]))

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


class TemporalSchemaTests(unittest.TestCase):
    """Supabase 날짜/시각 컬럼 타입과 앱 파서를 검증한다."""

    def test_setup_supabase_uses_native_temporal_types(self) -> None:
        """신규 Supabase 스키마는 핵심 날짜/시각 컬럼을 TEXT로 만들지 않는다."""

        setup_sql = (Path(__file__).resolve().parents[1] / "setup_supabase.sql").read_text(encoding="utf-8")

        expected_fragments = [
            "created_at TIMESTAMPTZ NOT NULL",
            "updated_at TIMESTAMPTZ NOT NULL",
            "price_updated_at TIMESTAMPTZ",
            "trade_date DATE NOT NULL",
            "quote_time TIMESTAMPTZ NOT NULL",
            "ingested_at TIMESTAMPTZ NOT NULL",
            "bucket_start TIMESTAMPTZ NOT NULL",
            "last_seen_at TIMESTAMPTZ",
            "last_quote_at TIMESTAMPTZ",
        ]
        forbidden_fragments = [
            "created_at TEXT NOT NULL",
            "updated_at TEXT NOT NULL",
            "price_updated_at TEXT",
            "trade_date TEXT NOT NULL",
            "quote_time TEXT NOT NULL",
            "ingested_at TEXT NOT NULL",
            "bucket_start TEXT NOT NULL",
            "last_seen_at TEXT",
            "last_quote_at TEXT",
        ]

        for fragment in expected_fragments:
            self.assertIn(fragment, setup_sql)
        for fragment in forbidden_fragments:
            self.assertNotIn(fragment, setup_sql)

    def test_temporal_normalization_migration_is_present(self) -> None:
        """기존 Supabase DB용 temporal 컬럼 변환 migration을 보관한다."""

        migration_sql = (
            Path(__file__).resolve().parents[1] / "migrations" / "2026-05-14_normalize_temporal_columns.sql"
        ).read_text(encoding="utf-8")

        self.assertIn("ALTER TABLE public.trade_logs", migration_sql)
        self.assertIn("ALTER COLUMN trade_date TYPE DATE USING left(trade_date, 10)::date", migration_sql)
        self.assertIn("ALTER TABLE public.realtime_price_ticks", migration_sql)
        self.assertIn("ALTER COLUMN quote_time TYPE TIMESTAMPTZ USING quote_time::timestamptz", migration_sql)
        self.assertIn("ALTER TABLE public.realtime_worker_status", migration_sql)
        self.assertIn("nullif(last_quote_at, '')::timestamptz", migration_sql)

    def test_parse_iso_date_uses_timestamp_parser(self) -> None:
        """앱 날짜 파서는 ISO date/datetime/timestamptz 값을 같은 날짜로 해석한다."""

        self.assertEqual(db_module._parse_iso_date("2026-05-14"), date(2026, 5, 14))
        self.assertEqual(db_module._parse_iso_date("2026-05-14T09:00:00+09:00"), date(2026, 5, 14))
        self.assertEqual(db_module._parse_iso_date("2026/05/14 09:00:00"), date(2026, 5, 14))
        self.assertIsNone(db_module._parse_iso_date(""))
        self.assertIsNone(db_module._parse_iso_date(None))
        self.assertIsNone(db_module._parse_iso_date("not-a-date"))


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


class DataCacheTests(unittest.TestCase):
    """사용자별 조회 캐시와 refresh token 무효화를 검증한다."""

    def setUp(self) -> None:
        clear_data_cache()
        db_module._FALLBACK_STATE.pop(db_module.DATA_REFRESH_TOKEN_KEY, None)

    def tearDown(self) -> None:
        clear_data_cache()
        db_module._FALLBACK_STATE.pop(db_module.DATA_REFRESH_TOKEN_KEY, None)

    @patch("src.db._current_backend", return_value=BACKEND_SQLITE)
    @patch("src.db.app_auth.is_demo_user", return_value=False)
    @patch("src.db._sqlite_list_accounts", return_value=[{"id": 1, "name": "테스트 계좌"}])
    def test_list_accounts_cache_is_scoped_by_user_and_refresh_token(
        self,
        list_accounts_mock,
        _is_demo_user_mock,
        _current_backend_mock,
    ) -> None:
        """같은 사용자/토큰은 재사용하고, 사용자 또는 refresh token이 바뀌면 다시 조회한다."""

        with patch("src.db.app_auth.get_user_id", return_value="user-a"):
            first = db_module.list_accounts()
            second = db_module.list_accounts()

        self.assertEqual(first, second)
        self.assertEqual(list_accounts_mock.call_count, 1)

        with patch("src.db.app_auth.get_user_id", return_value="user-b"):
            third = db_module.list_accounts()

        self.assertEqual(third, first)
        self.assertEqual(list_accounts_mock.call_count, 2)

        with patch("src.db.app_auth.get_user_id", return_value="user-a"):
            mark_data_dirty()
            fourth = db_module.list_accounts()

        self.assertEqual(fourth, first)
        self.assertEqual(list_accounts_mock.call_count, 3)

    def test_delete_trade_log_clears_data_cache_after_success(self) -> None:
        """거래 삭제 성공 후 세션 토큰과 DB 조회 캐시를 즉시 무효화한다."""

        call_order = unittest.mock.Mock()
        with (
            patch("src.db._delete_trade_log_original", return_value="deleted") as delete_original_mock,
            patch("src.db.mark_data_dirty") as mark_data_dirty_mock,
            patch("src.db.clear_data_cache") as clear_data_cache_mock,
        ):
            call_order.attach_mock(delete_original_mock, "delete_original")
            call_order.attach_mock(mark_data_dirty_mock, "mark_dirty")
            call_order.attach_mock(clear_data_cache_mock, "clear_cache")

            result = db_module.delete_trade_log(7, 9)

        self.assertEqual(result, "deleted")
        self.assertEqual(
            call_order.mock_calls,
            [
                unittest.mock.call.delete_original(7, 9),
                unittest.mock.call.mark_dirty(),
                unittest.mock.call.clear_cache(),
            ],
        )

    def test_delete_trade_log_keeps_cache_when_delete_fails(self) -> None:
        """거래 삭제 실패 시 성공 후처리 캐시 무효화를 실행하지 않는다."""

        with (
            patch("src.db._delete_trade_log_original", side_effect=ValueError("삭제 실패")),
            patch("src.db.mark_data_dirty") as mark_data_dirty_mock,
            patch("src.db.clear_data_cache") as clear_data_cache_mock,
        ):
            with self.assertRaisesRegex(ValueError, "삭제 실패"):
                db_module.delete_trade_log(7, 9)

        mark_data_dirty_mock.assert_not_called()
        clear_data_cache_mock.assert_not_called()


class RealtimeWorkerStatusPersistenceTests(unittest.TestCase):
    """실시간 worker 상태의 마지막 quote 시각 보존을 검증한다."""

    @patch("src.db._require_user_id", return_value="user-123")
    @patch("src.db._supabase_request")
    def test_supabase_upsert_realtime_worker_status_preserves_last_quote_at_when_omitted(
        self,
        request_mock,
        _require_user_id_mock,
    ) -> None:
        """Supabase PATCH 상태 갱신은 새 quote 시각이 없으면 기존 값을 유지한다."""

        request_mock.side_effect = [
            [{"account_id": 24, "last_quote_at": "2026-05-12T15:59:50"}],
            None,
        ]

        db_module._supabase_upsert_realtime_worker_status(
            account_id=24,
            worker_name="kis-quote-worker",
            connection_state="disconnected",
            last_seen_at="2026-05-12T16:00:10",
            metadata_json={"reason": "ping/pong timed out"},
        )

        patch_call = request_mock.call_args_list[1]
        self.assertEqual(patch_call.args[:2], ("PATCH", "realtime_worker_status"))
        self.assertNotIn("last_quote_at", patch_call.kwargs["data"])

    def test_sqlite_upsert_realtime_worker_status_preserves_last_quote_at_when_omitted(self) -> None:
        """SQLite 상태 갱신은 last_quote_at 인자가 없을 때 기존 값을 유지한다."""

        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "worker-status.db"
            with patch.object(sqlite_db, "DB_PATH", database_path):
                sqlite_db.initialize_database()
                with sqlite_db.connect() as connection:
                    timestamp = sqlite_db.now_iso()
                    connection.execute(
                        """
                        INSERT INTO accounts (name, account_type, cash_balance, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        ("테스트 계좌", "retirement", 0.0, timestamp, timestamp),
                    )
                    connection.commit()

                sqlite_db.upsert_realtime_worker_status(
                    account_id=1,
                    worker_name="kis-quote-worker",
                    connection_state="connected",
                    last_seen_at="2026-05-12T15:59:55",
                    last_quote_at="2026-05-12T15:59:50",
                    metadata_json={"backend": "sqlite"},
                )
                sqlite_db.upsert_realtime_worker_status(
                    account_id=1,
                    worker_name="kis-quote-worker",
                    connection_state="disconnected",
                    last_seen_at="2026-05-12T16:00:10",
                    metadata_json={"reason": "ping/pong timed out"},
                )

                status = sqlite_db.get_realtime_worker_status(1)

        self.assertIsNotNone(status)
        self.assertEqual(status["connection_state"], "disconnected")
        self.assertEqual(status["last_quote_at"], "2026-05-12T15:59:50")


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
        self.assertEqual(tuple(blueprint["transfers"]), ())


class ExportTradeLogFilterTests(unittest.TestCase):
    """데이터 화면 거래 기록 export 필터를 검증한다."""

    def test_filter_exportable_trade_logs_keeps_deposits_buys_and_sells_only(self) -> None:
        """회사/개인 입금, 매수, 매도 외 거래 유형은 데이터 거래 기록에서 제외한다."""

        rows = [
            {"id": 1, "trade_type": "personal_deposit"},
            {"id": 2, "trade_type": "employer_deposit"},
            {"id": 3, "trade_type": "deposit"},
            {"id": 4, "trade_type": "buy"},
            {"id": 5, "trade_type": "sell"},
            {"id": 6, "trade_type": "withdraw"},
            {"id": 7, "trade_type": "cash_adjustment"},
            {"id": 8, "trade_type": "transfer_in"},
            {"id": 9, "trade_type": "interest"},
        ]

        filtered = db_module._filter_exportable_trade_logs(rows)

        self.assertEqual([row["id"] for row in filtered], [1, 2, 3, 4, 5])


class ValuationSnapshotStorageTests(unittest.TestCase):
    """입금 기준 평가 스냅샷 저장 계층을 검증한다."""

    def test_sqlite_records_lists_and_deletes_valuation_snapshots(self) -> None:
        """SQLite는 평가 스냅샷을 upsert하고 fallback 종목 JSON을 list로 복원한다."""

        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "valuation.db"
            with patch.object(sqlite_db, "DB_PATH", database_path):
                sqlite_db.initialize_database()
                account_id = sqlite_db.create_account("user-1::평가 테스트", opening_cash=0)
                snapshots = [
                    {
                        "account_id": account_id,
                        "valuation_date": "2026-01-01",
                        "company_principal": 10000,
                        "invested_cost": 6000,
                        "implied_cash": 4000,
                        "actual_cash_balance": None,
                        "cash_value": 4000,
                        "cash_source": "implied",
                        "holdings_market_value": 6100,
                        "valuation_amount": 10100,
                        "profit_loss": 100,
                        "profit_rate": 1.0,
                        "over_invested_amount": 0,
                        "missing_price_symbols": ["AAA"],
                        "source_hash": "hash-1",
                        "calculation_reason": "test",
                    }
                ]

                sqlite_db.record_valuation_snapshots(account_id, snapshots)
                rows = sqlite_db.list_valuation_snapshots(account_id)

                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["valuation_date"], "2026-01-01")
                self.assertEqual(rows[0]["missing_price_symbols"], ["AAA"])

                updated = dict(snapshots[0], valuation_amount=10200, missing_price_symbols=[])
                sqlite_db.record_valuation_snapshots(account_id, [updated])
                rows = sqlite_db.list_valuation_snapshots(account_id)

                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["valuation_amount"], 10200)
                self.assertEqual(rows[0]["missing_price_symbols"], [])

                sqlite_db.delete_valuation_snapshots(account_id)
                self.assertEqual(sqlite_db.list_valuation_snapshots(account_id), [])

    def test_sqlite_lists_valuation_snapshots_newest_first(self) -> None:
        """평가 스냅샷 조회는 최근 기준일이 먼저 오도록 정렬한다."""

        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "valuation-order.db"
            with patch.object(sqlite_db, "DB_PATH", database_path):
                sqlite_db.initialize_database()
                account_id = sqlite_db.create_account("user-1::평가 정렬", opening_cash=0)
                base_snapshot = {
                    "account_id": account_id,
                    "company_principal": 10000,
                    "invested_cost": 0,
                    "implied_cash": 10000,
                    "actual_cash_balance": None,
                    "cash_value": 10000,
                    "cash_source": "implied",
                    "holdings_market_value": 0,
                    "valuation_amount": 10000,
                    "profit_loss": 0,
                    "profit_rate": 0,
                    "over_invested_amount": 0,
                    "missing_price_symbols": [],
                    "source_hash": "hash",
                    "calculation_reason": "test",
                }
                sqlite_db.record_valuation_snapshots(
                    account_id,
                    [
                        dict(base_snapshot, valuation_date="2026-01-01"),
                        dict(base_snapshot, valuation_date="2026-01-03"),
                        dict(base_snapshot, valuation_date="2026-01-02"),
                    ],
                )

                rows = sqlite_db.list_valuation_snapshots(account_id)

                self.assertEqual(
                    [row["valuation_date"] for row in rows],
                    ["2026-01-03", "2026-01-02", "2026-01-01"],
                )

    @patch("src.db.now_iso", return_value="2026-05-14T00:00:00")
    @patch("src.db._supabase_request")
    def test_supabase_record_valuation_snapshots_uses_batch_upsert(
        self,
        request_mock,
        _now_iso_mock,
    ) -> None:
        """Supabase 저장은 on_conflict 기반 batch upsert를 사용한다."""

        _supabase_record_valuation_snapshots(
            7,
            [
                {
                    "account_id": 7,
                    "valuation_date": "2026-01-01",
                    "company_principal": 10000,
                    "invested_cost": 0,
                    "implied_cash": 10000,
                    "actual_cash_balance": None,
                    "cash_value": 10000,
                    "cash_source": "implied",
                    "holdings_market_value": 0,
                    "valuation_amount": 10000,
                    "profit_loss": 0,
                    "profit_rate": 0,
                    "over_invested_amount": 0,
                    "missing_price_symbols": [],
                    "source_hash": "hash-1",
                    "calculation_reason": "test",
                }
            ],
        )

        request_mock.assert_called_once()
        call_args = request_mock.call_args
        self.assertEqual(call_args.args[:2], ("POST", "daily_valuation_snapshot"))
        self.assertEqual(call_args.kwargs["filters"], {"on_conflict": "account_id,valuation_date"})
        self.assertEqual(call_args.kwargs["prefer_resolution"], "merge-duplicates")
        self.assertEqual(call_args.kwargs["prefer_return"], "minimal")
        self.assertEqual(call_args.kwargs["data"][0]["updated_at"], "2026-05-14T00:00:00")


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

    @patch("src.db.record_account_snapshot")
    @patch(
        "src.db.list_account_snapshots",
        return_value=[
            {
                "snapshot_date": "2026-05-09",
                "cash_balance": 750.0,
                "market_value": 0.0,
                "total_value": 750.0,
                "total_cost": 0.0,
            },
            {
                "snapshot_date": "2026-05-10",
                "cash_balance": 750.0,
                "market_value": 0.0,
                "total_value": 750.0,
                "total_cost": 0.0,
            },
        ],
    )
    @patch("src.db.list_daily_interest", return_value=[])
    @patch(
        "src.db.list_trade_logs",
        return_value=[
            {"trade_type": "personal_deposit", "trade_date": "2026-05-09", "cash_delta": 1000.0, "total_amount": 1000.0},
            {"trade_type": "buy", "trade_date": "2026-05-11", "cash_delta": -250.0, "total_amount": 250.0, "quantity": 1.0, "price": 250.0, "symbol": "AAA"},
        ],
    )
    @patch("src.db._demo_account_totals", return_value=(750.0, 250.0, 250.0))
    @patch("src.db.get_account")
    def test_sync_account_rollup_keeps_future_trade_deltas_out_of_prior_cash_snapshots(
        self,
        get_account_mock,
        _demo_account_totals_mock,
        _list_trade_logs_mock,
        _list_daily_interest_mock,
        _list_account_snapshots_mock,
        record_snapshot_mock,
    ) -> None:
        """기준일 이후 거래는 과거 현금 스냅샷 재계산에 섞이면 안 된다."""

        get_account_mock.return_value = {
            "id": 7,
            "cash_balance": 750.0,
            "created_at": "2026-05-09T09:00:00",
        }

        result = sync_account_rollup(7, today_date="2026-05-11")

        self.assertEqual(
            record_snapshot_mock.call_args_list,
            [
                unittest.mock.call(
                    7,
                    snapshot_date="2026-05-09",
                    cash_balance=1000.0,
                    market_value=0.0,
                    total_value=1000.0,
                    total_cost=0.0,
                ),
                unittest.mock.call(
                    7,
                    snapshot_date="2026-05-10",
                    cash_balance=1000.0,
                    market_value=0.0,
                    total_value=1000.0,
                    total_cost=0.0,
                ),
                unittest.mock.call(
                    7,
                    snapshot_date="2026-05-11",
                    cash_balance=750.0,
                    market_value=250.0,
                    total_value=1000.0,
                    total_cost=250.0,
                ),
            ],
        )
        self.assertEqual(result["historical_snapshots_updated"], 2)
        self.assertTrue(result["snapshot_updated"])

    @patch("src.db.record_account_snapshot")
    @patch(
        "src.db.list_account_snapshots",
        return_value=[
            {
                "snapshot_date": "2026-05-09",
                "cash_balance": 0.0,
                "market_value": 200.0,
                "total_value": 200.0,
                "total_cost": 0.0,
            },
        ],
    )
    @patch("src.db.list_daily_interest", return_value=[])
    @patch(
        "src.db.list_trade_logs",
        return_value=[
            {"trade_type": "personal_deposit", "trade_date": "2026-05-01", "cash_delta": 1000.0, "total_amount": 1000.0},
            {"trade_type": "buy", "trade_date": "2026-05-02", "cash_delta": -200.0, "total_amount": 200.0, "quantity": 1.0, "price": 200.0, "symbol": "AAA"},
        ],
    )
    @patch("src.db._demo_account_totals", return_value=(800.0, 200.0, 200.0))
    @patch("src.db.get_account")
    def test_sync_account_rollup_includes_backdated_trades_before_account_created_at(
        self,
        get_account_mock,
        _demo_account_totals_mock,
        _list_trade_logs_mock,
        _list_daily_interest_mock,
        _list_account_snapshots_mock,
        record_snapshot_mock,
    ) -> None:
        """계좌 생성 이후에 입력했더라도 거래일이 더 과거면 스냅샷 재계산에 포함해야 한다."""

        get_account_mock.return_value = {
            "id": 7,
            "cash_balance": 800.0,
            "created_at": "2026-05-09T09:00:00",
        }

        result = sync_account_rollup(7, today_date="2026-05-10")

        self.assertEqual(
            record_snapshot_mock.call_args_list,
            [
                unittest.mock.call(
                    7,
                    snapshot_date="2026-05-09",
                    cash_balance=800.0,
                    market_value=200.0,
                    total_value=1000.0,
                    total_cost=200.0,
                ),
                unittest.mock.call(
                    7,
                    snapshot_date="2026-05-10",
                    cash_balance=800.0,
                    market_value=200.0,
                    total_value=1000.0,
                    total_cost=200.0,
                ),
            ],
        )
        self.assertEqual(result["historical_snapshots_updated"], 1)
        self.assertTrue(result["snapshot_updated"])


class RecordTradeInterestRemovalTests(unittest.TestCase):
    """매수 저장 경로에서 legacy 이자 재동기화가 제거되었는지 검증한다."""

    @patch("src.db.mark_data_dirty")
    @patch("src.db._run_with_fallback")
    @patch("src.db._sync_legacy_interest_history_for_buy")
    def test_record_trade_no_longer_triggers_legacy_interest_sync(
        self,
        sync_interest_mock,
        run_with_fallback_mock,
        mark_data_dirty_mock,
    ) -> None:
        """매수 저장은 더 이상 이자 원장 재구성 훅을 호출하지 않는다."""

        db_module.record_trade(
            7,
            symbol="AAPL",
            product_name="Apple",
            trade_type="buy",
            asset_type="risk",
            quantity=1,
            price=1000,
            trade_date="2026-05-11",
            notes="테스트 매수",
        )

        sync_interest_mock.assert_not_called()
        run_with_fallback_mock.assert_called_once()
        mark_data_dirty_mock.assert_called_once()


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


class SupabaseTradeCashRuleTests(unittest.TestCase):
    """Supabase 거래/현금 규칙을 검증한다."""

    @patch("src.db._supabase_insert_trade_log")
    @patch("src.db._supabase_update_cash_balance")
    @patch("src.db._supabase_request")
    @patch("src.db._supabase_get_account", return_value={"id": 7, "cash_balance": 0.0})
    @patch("src.db.now_iso", return_value="2026-05-11T09:35:00")
    def test_supabase_record_trade_keeps_manual_cash_balance_unchanged(
        self,
        _now_iso_mock,
        _get_account_mock,
        request_mock,
        update_cash_balance_mock,
        insert_trade_log_mock,
    ) -> None:
        """매수/매도 저장은 보유현금을 자동으로 바꾸지 않아야 한다."""

        request_mock.side_effect = [
            [],
            None,
        ]

        _supabase_record_trade(
            7,
            symbol="AAPL",
            product_name="Apple",
            trade_type="buy",
            asset_type="risk",
            quantity=1,
            price=1000,
            trade_date="2026-05-11",
            notes="음수 현금 허용 매수",
        )

        update_cash_balance_mock.assert_not_called()
        insert_trade_log_mock.assert_called_once()

    @patch("src.db._supabase_record_daily_interest")
    @patch("src.db._supabase_update_cash_balance")
    @patch("src.db._supabase_delete_rows_by_ids")
    @patch("src.db._supabase_list_daily_interest", return_value=[])
    @patch("src.db._supabase_list_trade_logs", return_value=[])
    @patch("src.db._supabase_get_account", return_value={"id": 7, "cash_balance": -40000.0})
    def test_supabase_replace_interest_history_preserves_negative_cash_balance(
        self,
        _get_account_mock,
        _trade_logs_mock,
        _interest_rows_mock,
        _delete_rows_mock,
        update_cash_balance_mock,
        _record_daily_interest_mock,
    ) -> None:
        """이자 재동기화는 이미 음수인 현금 잔액을 다시 0 이상으로 강제하지 않는다."""

        _supabase_replace_interest_history(
            7,
            target_date="2026-05-11",
            desired_entries=[],
        )

        update_cash_balance_mock.assert_called_once_with(7, -40000.0, allow_negative=True)

    @patch("src.db._supabase_insert_trade_log")
    @patch("src.db._supabase_update_cash_balance")
    @patch("src.db._supabase_get_account", return_value={"id": 7, "cash_balance": 1000.0})
    def test_supabase_adjust_cash_balance_records_cash_adjustment_log(
        self,
        _get_account_mock,
        update_cash_balance_mock,
        insert_trade_log_mock,
    ) -> None:
        _supabase_adjust_cash_balance(
            7,
            target_amount=1300.0,
            trade_date="2026-05-11",
            notes="대시보드 현금 카드 조정",
        )

        update_cash_balance_mock.assert_called_once_with(7, 1300.0)
        insert_trade_log_mock.assert_called_once()
        self.assertEqual(insert_trade_log_mock.call_args.kwargs["trade_type"], "cash_adjustment")
        self.assertEqual(insert_trade_log_mock.call_args.kwargs["total_amount"], 300.0)
        self.assertEqual(insert_trade_log_mock.call_args.kwargs["cash_delta"], 300.0)


class SQLiteRealtimeQuotePersistenceTests(unittest.TestCase):
    """SQLite 실시간 quote overwrite/append 동작을 검증한다."""

    def test_record_realtime_price_tick_updates_holding_and_appends_tick_history(self) -> None:
        """tick 저장 시 holdings 현재가와 실시간 이력 테이블이 함께 갱신된다."""

        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "portfolio.db"
            with patch.object(sqlite_db, "DB_PATH", database_path):
                sqlite_module = sqlite_db
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

    def test_record_trade_keeps_manual_cash_balance_unchanged_after_buy(self) -> None:
        """상품 매수는 보유 종목만 반영하고 보유현금은 직접 수정값을 유지한다."""

        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "portfolio.db"
            with patch.object(sqlite_db, "DB_PATH", database_path):
                sqlite_module = sqlite_db
                sqlite_module.initialize_database()
                account_id = sqlite_module.create_account("user-1::테스트 계좌", opening_cash=100000)

                sqlite_module.record_trade(
                    account_id,
                    symbol="005930",
                    product_name="삼성전자",
                    trade_type="buy",
                    asset_type="risk",
                    quantity=2,
                    price=70000,
                    trade_date="2026-05-10",
                    notes="현금 부족 허용 매수",
                )

                account = sqlite_module.get_account(account_id)
                holdings = sqlite_module.list_holdings(account_id)

                self.assertEqual(float(account["cash_balance"]), 100000.0)
                self.assertEqual(len(holdings), 1)
                self.assertEqual(float(holdings[0]["quantity"]), 2.0)

    def test_adjust_cash_balance_records_cash_adjustment_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "portfolio.db"
            with patch.object(sqlite_db, "DB_PATH", database_path):
                sqlite_module = sqlite_db
                sqlite_module.initialize_database()
                account_id = sqlite_module.create_account("user-1::테스트 계좌", opening_cash=500000)

                sqlite_module.adjust_cash_balance(
                    account_id,
                    target_amount=620000,
                    trade_date="2026-05-11",
                    notes="현금 카드 수정",
                )

                account = sqlite_module.get_account(account_id)
                trade_logs = sqlite_module.list_trade_logs(account_id)

                self.assertEqual(float(account["cash_balance"]), 620000.0)
                self.assertEqual(len(trade_logs), 1)
                self.assertEqual(trade_logs[0]["trade_type"], "cash_adjustment")
                self.assertEqual(float(trade_logs[0]["total_amount"]), 120000.0)
                self.assertEqual(float(trade_logs[0]["cash_delta"]), 120000.0)


class SQLiteTradeLogEditDeleteTests(unittest.TestCase):
    """SQLite 거래 기록 수정/삭제 후 원장 재계산을 검증한다."""

    def test_update_trade_log_rebuilds_holdings_without_touching_cash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "portfolio.db"
            with patch.object(sqlite_db, "DB_PATH", database_path):
                sqlite_module = sqlite_db
                sqlite_module.initialize_database()
                account_id = sqlite_module.create_account("user-1::수정 테스트", opening_cash=500000)
                sqlite_module.record_trade(
                    account_id,
                    symbol="005930",
                    product_name="삼성전자",
                    trade_type="buy",
                    asset_type="risk",
                    quantity=10,
                    price=100,
                    trade_date="2026-05-10",
                    notes="원본",
                )
                log_id = int(sqlite_module.list_trade_logs(account_id)[0]["id"])

                _sqlite_update_trade_log(
                    account_id,
                    log_id,
                    trade_type="buy",
                    symbol="005930",
                    product_name="삼성전자 수정",
                    asset_type="risk",
                    quantity=4,
                    price=150,
                    trade_date="2026-05-11",
                    notes="수정 완료",
                )

                account = sqlite_module.get_account(account_id)
                holding = sqlite_module.list_holdings(account_id)[0]
                log = sqlite_module.list_trade_logs(account_id)[0]

                self.assertEqual(float(account["cash_balance"]), 500000.0)
                self.assertEqual(str(holding["product_name"]), "삼성전자 수정")
                self.assertEqual(float(holding["quantity"]), 4.0)
                self.assertEqual(float(holding["avg_cost"]), 150.0)
                self.assertEqual(str(log["trade_type"]), "buy")
                self.assertEqual(float(log["total_amount"]), 600.0)
                self.assertEqual(float(log["cash_delta"]), -600.0)
                self.assertEqual(str(log["notes"]), "수정 완료")

    def test_delete_trade_log_clears_active_holding_without_touching_cash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "portfolio.db"
            with patch.object(sqlite_db, "DB_PATH", database_path):
                sqlite_module = sqlite_db
                sqlite_module.initialize_database()
                account_id = sqlite_module.create_account("user-1::삭제 테스트", opening_cash=500000)
                sqlite_module.record_trade(
                    account_id,
                    symbol="AAPL",
                    product_name="Apple",
                    trade_type="buy",
                    asset_type="risk",
                    quantity=2,
                    price=1000,
                    trade_date="2026-05-10",
                    notes="삭제 대상",
                )
                log_id = int(sqlite_module.list_trade_logs(account_id)[0]["id"])

                _sqlite_delete_trade_log(account_id, log_id)

                account = sqlite_module.get_account(account_id)
                holdings = sqlite_module.list_holdings(account_id)
                all_holdings = sqlite_module.list_holdings(account_id, include_closed=True)
                trade_logs = sqlite_module.list_trade_logs(account_id)

                self.assertEqual(float(account["cash_balance"]), 500000.0)
                self.assertEqual(holdings, [])
                self.assertEqual(len(all_holdings), 1)
                self.assertEqual(float(all_holdings[0]["quantity"]), 0.0)
                self.assertEqual(trade_logs, [])

    def test_update_cash_flow_trade_log_recomputes_cash_balance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "portfolio.db"
            with patch.object(sqlite_db, "DB_PATH", database_path):
                sqlite_module = sqlite_db
                sqlite_module.initialize_database()
                account_id = sqlite_module.create_account("user-1::현금 수정 테스트", opening_cash=500000)
                sqlite_module.record_cash_flow(
                    account_id,
                    flow_type="personal_deposit",
                    amount=100000,
                    trade_date="2026-05-10",
                    notes="원본 입금",
                )
                log_id = int(sqlite_module.list_trade_logs(account_id)[0]["id"])

                _sqlite_update_trade_log(
                    account_id,
                    log_id,
                    trade_type="withdraw",
                    amount=50000,
                    trade_date="2026-05-11",
                    notes="수정 출금",
                )

                account = sqlite_module.get_account(account_id)
                log = sqlite_module.list_trade_logs(account_id)[0]

                self.assertEqual(float(account["cash_balance"]), 450000.0)
                self.assertEqual(str(log["trade_type"]), "withdraw")
                self.assertEqual(float(log["total_amount"]), 50000.0)
                self.assertEqual(float(log["cash_delta"]), -50000.0)
                self.assertEqual(str(log["product_name"]), "일반 출금")

    def test_delete_cash_flow_trade_log_restores_cash_balance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "portfolio.db"
            with patch.object(sqlite_db, "DB_PATH", database_path):
                sqlite_module = sqlite_db
                sqlite_module.initialize_database()
                account_id = sqlite_module.create_account("user-1::현금 삭제 테스트", opening_cash=500000)
                sqlite_module.record_cash_flow(
                    account_id,
                    flow_type="personal_deposit",
                    amount=100000,
                    trade_date="2026-05-10",
                    notes="삭제할 입금",
                )
                log_id = int(sqlite_module.list_trade_logs(account_id)[0]["id"])

                _sqlite_delete_trade_log(account_id, log_id)

                account = sqlite_module.get_account(account_id)
                trade_logs = sqlite_module.list_trade_logs(account_id)

                self.assertEqual(float(account["cash_balance"]), 500000.0)
                self.assertEqual(trade_logs, [])


class SupabaseTradeLogEditDeleteTests(unittest.TestCase):
    """Supabase 거래 기록 수정/삭제 경로를 검증한다."""

    @patch("src.db.now_iso", return_value="2026-05-11T09:35:00")
    @patch("src.db._supabase_update_cash_balance")
    @patch("src.db._supabase_apply_holding_state")
    @patch("src.db._supabase_request")
    @patch("src.db._supabase_list_trade_logs")
    @patch("src.db._supabase_get_account", return_value={"id": 7, "cash_balance": 1000.0})
    @patch("src.db._supabase_get_trade_log")
    def test_supabase_update_trade_log_rebuilds_holdings_without_touching_cash(
        self,
        get_trade_log_mock,
        _get_account_mock,
        list_trade_logs_mock,
        request_mock,
        apply_holding_state_mock,
        update_cash_balance_mock,
        _now_iso_mock,
    ) -> None:
        existing_log = {
            "id": 5,
            "trade_type": "buy",
            "symbol": "AAPL",
            "product_name": "Apple",
            "asset_type": "risk",
            "quantity": 1.0,
            "price": 100.0,
            "trade_date": "2026-05-10",
            "created_at": "2026-05-10T09:00:00",
            "cash_delta": -100.0,
            "total_amount": 100.0,
            "notes": "원본",
        }
        get_trade_log_mock.return_value = dict(existing_log)
        list_trade_logs_mock.return_value = [dict(existing_log)]

        _supabase_update_trade_log(
            7,
            5,
            trade_type="buy",
            symbol="AAPL",
            product_name="Apple 수정",
            asset_type="risk",
            quantity=2,
            price=120,
            trade_date="2026-05-11",
            notes="수정",
        )

        update_cash_balance_mock.assert_not_called()
        apply_holding_state_mock.assert_called_once()
        request_mock.assert_called_once()
        self.assertEqual(request_mock.call_args.args[:2], ("PATCH", "trade_logs"))
        self.assertEqual(request_mock.call_args.kwargs["data"]["total_amount"], 240.0)

    @patch("src.db._supabase_update_cash_balance")
    @patch("src.db._supabase_request")
    @patch("src.db._supabase_get_account", return_value={"id": 7, "cash_balance": 120000.0})
    @patch(
        "src.db._supabase_get_trade_log",
        return_value={
            "id": 9,
            "trade_type": "personal_deposit",
            "cash_delta": 20000.0,
            "total_amount": 20000.0,
        },
    )
    def test_supabase_delete_cash_flow_trade_log_updates_cash_balance(
        self,
        _get_trade_log_mock,
        _get_account_mock,
        request_mock,
        update_cash_balance_mock,
    ) -> None:
        _supabase_delete_trade_log(7, 9)

        request_mock.assert_called_once_with("DELETE", "trade_logs", filters={"id": "eq.9"})
        update_cash_balance_mock.assert_called_once_with(7, 100000.0)


if __name__ == "__main__":
    unittest.main()

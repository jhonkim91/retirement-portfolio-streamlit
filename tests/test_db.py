from __future__ import annotations

import unittest
from unittest.mock import patch

import requests

from src.db import (
    BACKEND_SUPABASE,
    _run_with_fallback,
    _should_fallback,
    _supabase_create_account,
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
    @patch("src.db.list_account_snapshots")
    @patch("src.db.list_daily_interest", return_value=[])
    @patch("src.db.list_holdings", return_value=[])
    @patch("src.db.create_account")
    def test_seed_demo_workspace_reuses_complete_existing_workspace(
        self,
        create_account_mock,
        _list_holdings_mock,
        _list_daily_interest_mock,
        list_snapshots_mock,
        list_accounts_mock,
        blueprint_mock,
    ) -> None:
        """데모 계좌와 스냅샷이 모두 있으면 재생성하지 않는다."""

        blueprint_mock.return_value = self._blueprint()
        list_accounts_mock.return_value = [
            {"id": 10, "name": "데모 IRP"},
            {"id": 11, "name": "데모 일반계좌"},
        ]
        list_snapshots_mock.return_value = [{"snapshot_date": "2026-05-08"}]

        result = seed_demo_workspace()

        self.assertFalse(result["created"])
        self.assertEqual(result["selected_account_id"], 10)
        create_account_mock.assert_not_called()

    @patch("src.db._demo_workspace_blueprint")
    @patch("src.db.list_accounts")
    @patch("src.db._delete_account")
    @patch("src.db.create_account")
    @patch("src.db.record_cash_flow")
    @patch("src.db.record_trade")
    @patch("src.db.record_account_transfer")
    @patch("src.db.record_daily_interest")
    @patch("src.db.set_holding_price")
    @patch("src.db.record_account_snapshot")
    @patch("src.db._demo_account_totals", return_value=(0.0, 0.0, 0.0))
    @patch("src.db.list_holdings", return_value=[])
    def test_seed_demo_workspace_rebuilds_partial_workspace(
        self,
        _list_holdings_mock,
        _demo_totals_mock,
        record_snapshot_mock,
        _set_holding_price_mock,
        _record_daily_interest_mock,
        _record_transfer_mock,
        _record_trade_mock,
        _record_cash_flow_mock,
        create_account_mock,
        delete_account_mock,
        list_accounts_mock,
        blueprint_mock,
    ) -> None:
        """데모 계좌가 일부만 남아 있으면 정리 후 처음부터 다시 만든다."""

        blueprint_mock.return_value = self._blueprint()
        list_accounts_mock.return_value = [{"id": 18, "name": "데모 IRP"}]
        create_account_mock.side_effect = [21, 22]

        result = seed_demo_workspace()

        delete_account_mock.assert_called_once_with(18)
        self.assertTrue(result["created"])
        self.assertEqual(result["selected_account_id"], 21)
        self.assertEqual(create_account_mock.call_count, 2)
        self.assertEqual(record_snapshot_mock.call_count, 2)


class SyncAccountRollupTests(unittest.TestCase):
    """원장 기준 누락 이자 자동 보정 동작을 검증한다."""

    @patch("src.db.record_account_snapshot")
    @patch("src.db.list_account_snapshots", return_value=[])
    @patch("src.db._demo_account_totals", return_value=(802.6028, 200.0, 200.0))
    @patch("src.db.record_daily_interest")
    @patch("src.db.list_daily_interest", return_value=[])
    @patch("src.db.list_trade_logs")
    @patch("src.db.get_account")
    def test_sync_account_rollup_backfills_missing_interest_to_previous_day(
        self,
        get_account_mock,
        list_trade_logs_mock,
        _list_daily_interest_mock,
        record_daily_interest_mock,
        _demo_account_totals_mock,
        _list_account_snapshots_mock,
        record_snapshot_mock,
    ) -> None:
        """입금/매매 원장을 바탕으로 전일까지의 누락 이자를 순차 적립한다."""

        get_account_mock.return_value = {
            "id": 7,
            "cash_balance": 800.0,
            "created_at": "2026-05-06T09:00:00",
        }
        list_trade_logs_mock.return_value = [
            {"trade_type": "personal_deposit", "trade_date": "2026-05-06", "cash_delta": 1000.0, "total_amount": 1000.0},
            {"trade_type": "buy", "trade_date": "2026-05-07", "cash_delta": -200.0, "total_amount": 200.0},
        ]

        result = sync_account_rollup(7, annual_rate=0.365, today_date="2026-05-09")

        self.assertEqual(
            record_daily_interest_mock.call_args_list,
            [
                unittest.mock.call(7, interest_date="2026-05-06", amount=1.0),
                unittest.mock.call(7, interest_date="2026-05-07", amount=0.801),
                unittest.mock.call(7, interest_date="2026-05-08", amount=0.8018),
            ],
        )
        record_snapshot_mock.assert_called_once_with(
            7,
            snapshot_date="2026-05-09",
            cash_balance=802.6028,
            market_value=200.0,
            total_value=1002.6028,
            total_cost=200.0,
        )
        self.assertEqual(result["interest_rows_added"], 3)
        self.assertEqual(result["historical_snapshots_updated"], 0)
        self.assertEqual(result["interest_amount_added"], 2.6028)
        self.assertEqual(result["snapshot_date"], "2026-05-09")
        self.assertTrue(result["snapshot_updated"])

    @patch("src.db.record_account_snapshot")
    @patch("src.db.list_account_snapshots")
    @patch("src.db._demo_account_totals", return_value=(802.6028, 200.0, 200.0))
    @patch("src.db.record_daily_interest")
    @patch("src.db.list_daily_interest")
    @patch("src.db.list_trade_logs")
    @patch("src.db.get_account")
    def test_sync_account_rollup_updates_existing_historical_snapshots_after_backfill(
        self,
        get_account_mock,
        list_trade_logs_mock,
        list_daily_interest_mock,
        record_daily_interest_mock,
        _demo_account_totals_mock,
        list_account_snapshots_mock,
        record_snapshot_mock,
    ) -> None:
        """누락 이자를 채운 뒤 기존 historical snapshot도 원장 기준 값으로 다시 맞춘다."""

        get_account_mock.side_effect = [
            {
                "id": 7,
                "cash_balance": 800.0,
                "created_at": "2026-05-06T09:00:00",
            },
            {
                "id": 7,
                "cash_balance": 802.6028,
                "created_at": "2026-05-06T09:00:00",
            },
        ]
        list_trade_logs_mock.side_effect = [
            [
                {"trade_type": "personal_deposit", "trade_date": "2026-05-06", "cash_delta": 1000.0, "total_amount": 1000.0},
                {"trade_type": "buy", "trade_date": "2026-05-07", "cash_delta": -200.0, "total_amount": 200.0, "quantity": 1.0, "price": 200.0, "symbol": "AAA"},
            ],
            [
                {"trade_type": "personal_deposit", "trade_date": "2026-05-06", "cash_delta": 1000.0, "total_amount": 1000.0},
                {"trade_type": "buy", "trade_date": "2026-05-07", "cash_delta": -200.0, "total_amount": 200.0, "quantity": 1.0, "price": 200.0, "symbol": "AAA"},
                {"trade_type": "interest", "trade_date": "2026-05-06", "cash_delta": 1.0, "total_amount": 1.0, "notes": "일별 이자 적립"},
                {"trade_type": "interest", "trade_date": "2026-05-07", "cash_delta": 0.801, "total_amount": 0.801, "notes": "일별 이자 적립"},
                {"trade_type": "interest", "trade_date": "2026-05-08", "cash_delta": 0.8018, "total_amount": 0.8018, "notes": "일별 이자 적립"},
            ],
        ]
        list_daily_interest_mock.side_effect = [
            [],
            [
                {"date": "2026-05-06", "interest_amount": 1.0},
                {"date": "2026-05-07", "interest_amount": 0.801},
                {"date": "2026-05-08", "interest_amount": 0.8018},
            ],
        ]

        def snapshot_side_effect(account_id: int, start_date: str | None = None) -> list[dict[str, float | str]]:
            if start_date == "2026-05-06":
                return [
                    {"snapshot_date": "2026-05-06", "cash_balance": 1000.0, "market_value": 0.0, "total_value": 1000.0, "total_cost": 0.0},
                    {"snapshot_date": "2026-05-07", "cash_balance": 801.0, "market_value": 200.0, "total_value": 1001.0, "total_cost": 0.0},
                    {"snapshot_date": "2026-05-08", "cash_balance": 802.0, "market_value": 200.0, "total_value": 1002.0, "total_cost": 0.0},
                ]
            if start_date == "2026-05-09":
                return []
            return []

        list_account_snapshots_mock.side_effect = snapshot_side_effect

        result = sync_account_rollup(7, annual_rate=0.365, today_date="2026-05-09")

        self.assertEqual(
            record_daily_interest_mock.call_args_list,
            [
                unittest.mock.call(7, interest_date="2026-05-06", amount=1.0),
                unittest.mock.call(7, interest_date="2026-05-07", amount=0.801),
                unittest.mock.call(7, interest_date="2026-05-08", amount=0.8018),
            ],
        )
        self.assertEqual(
            record_snapshot_mock.call_args_list,
            [
                unittest.mock.call(
                    7,
                    snapshot_date="2026-05-06",
                    cash_balance=1001.0,
                    market_value=0.0,
                    total_value=1001.0,
                    total_cost=0.0,
                ),
                unittest.mock.call(
                    7,
                    snapshot_date="2026-05-07",
                    cash_balance=801.801,
                    market_value=200.0,
                    total_value=1001.801,
                    total_cost=200.0,
                ),
                unittest.mock.call(
                    7,
                    snapshot_date="2026-05-08",
                    cash_balance=802.6028,
                    market_value=200.0,
                    total_value=1002.6028,
                    total_cost=200.0,
                ),
                unittest.mock.call(
                    7,
                    snapshot_date="2026-05-09",
                    cash_balance=802.6028,
                    market_value=200.0,
                    total_value=1002.6028,
                    total_cost=200.0,
                ),
            ],
        )
        self.assertEqual(result["interest_rows_added"], 3)
        self.assertEqual(result["historical_snapshots_updated"], 3)
        self.assertEqual(result["interest_amount_added"], 2.6028)
        self.assertEqual(result["snapshot_date"], "2026-05-09")
        self.assertTrue(result["snapshot_updated"])

    @patch("src.db.record_account_snapshot")
    @patch("src.db.list_account_snapshots", return_value=[])
    @patch("src.db._demo_account_totals", return_value=(802.6028, 200.0, 200.0))
    @patch("src.db._replace_interest_history")
    @patch(
        "src.db.list_daily_interest",
        return_value=[
            {"date": "2026-05-06", "interest_amount": 1.0},
            {"date": "2026-05-07", "interest_amount": 1.001},
            {"date": "2026-05-08", "interest_amount": 1.002},
        ],
    )
    @patch("src.db.list_trade_logs")
    @patch("src.db.get_account")
    def test_sync_account_rollup_rebuilds_interest_when_backdated_trade_changes_existing_days(
        self,
        get_account_mock,
        list_trade_logs_mock,
        _list_daily_interest_mock,
        replace_interest_history_mock,
        _demo_account_totals_mock,
        _list_account_snapshots_mock,
        record_snapshot_mock,
    ) -> None:
        """과거 거래가 추가되어 기존 이자 금액이 틀어지면 기간 이자를 재구성한다."""

        get_account_mock.return_value = {
            "id": 7,
            "cash_balance": 803.003,
            "created_at": "2026-05-06T09:00:00",
        }
        list_trade_logs_mock.return_value = [
            {"trade_type": "personal_deposit", "trade_date": "2026-05-06", "cash_delta": 1000.0, "total_amount": 1000.0, "notes": ""},
            {"trade_type": "buy", "trade_date": "2026-05-07", "cash_delta": -200.0, "total_amount": 200.0, "notes": ""},
            {"trade_type": "interest", "trade_date": "2026-05-06", "cash_delta": 1.0, "total_amount": 1.0, "notes": "일별 이자 적립"},
            {"trade_type": "interest", "trade_date": "2026-05-07", "cash_delta": 1.001, "total_amount": 1.001, "notes": "일별 이자 적립"},
            {"trade_type": "interest", "trade_date": "2026-05-08", "cash_delta": 1.002, "total_amount": 1.002, "notes": "일별 이자 적립"},
        ]

        result = sync_account_rollup(7, annual_rate=0.365, today_date="2026-05-09")

        replace_interest_history_mock.assert_called_once_with(
            7,
            target_date="2026-05-08",
            desired_entries=[
                ("2026-05-06", 1.0),
                ("2026-05-07", 0.801),
                ("2026-05-08", 0.8018),
            ],
        )
        record_snapshot_mock.assert_called_once_with(
            7,
            snapshot_date="2026-05-09",
            cash_balance=802.6028,
            market_value=200.0,
            total_value=1002.6028,
            total_cost=200.0,
        )
        self.assertEqual(result["interest_rows_added"], 0)
        self.assertEqual(result["interest_rows_updated"], 2)
        self.assertEqual(result["interest_rows_removed"], 0)
        self.assertEqual(result["historical_snapshots_updated"], 0)
        self.assertEqual(result["interest_amount_added"], -0.4002)
        self.assertEqual(result["snapshot_date"], "2026-05-09")
        self.assertTrue(result["snapshot_updated"])


if __name__ == "__main__":
    unittest.main()

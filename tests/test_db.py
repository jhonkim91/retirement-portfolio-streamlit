from __future__ import annotations

import unittest
from unittest.mock import patch

import requests

from src.db import _supabase_create_account, is_accounts_hotfix_error, seed_demo_workspace


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


if __name__ == "__main__":
    unittest.main()

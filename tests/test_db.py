from __future__ import annotations

import unittest
from unittest.mock import patch

import requests

from src.db import _supabase_create_account, is_accounts_hotfix_error


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


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from unittest.mock import patch

from src import auth


class DemoAuthHelperTests(unittest.TestCase):
    """초기 화면 데모 접속용 인증 helper를 검증한다."""

    def test_default_supabase_url_is_empty(self) -> None:
        """인증 클라이언트도 운영 Supabase URL을 코드 기본값으로 갖지 않는다."""

        self.assertEqual(auth.DEFAULT_SUPABASE_URL, "")

    def test_is_enabled_requires_valid_supabase_url_and_key(self) -> None:
        """SUPABASE_KEY만 있거나 URL 형식이 틀리면 인증을 비활성화한다."""

        with (
            patch("src.auth._supabase_url", return_value=""),
            patch("src.auth._supabase_key", return_value="configured-key"),
        ):
            self.assertFalse(auth.is_enabled())

        with (
            patch("src.auth._supabase_url", return_value="http://demo.supabase.co"),
            patch("src.auth._supabase_key", return_value="configured-key"),
        ):
            self.assertFalse(auth.is_enabled())

        with (
            patch("src.auth._supabase_url", return_value="https://demo.supabase.co"),
            patch("src.auth._supabase_key", return_value="configured-key"),
        ):
            self.assertTrue(auth.is_enabled())

    def test_get_demo_credentials_prefers_demo_login_keys(self) -> None:
        """전용 데모 자격 증명이 있으면 검증용 자격 증명보다 우선 사용한다."""

        values = {
            "DEMO_LOGIN_EMAIL": "demo@example.com",
            "DEMO_LOGIN_PASSWORD": "demo-password",
            "STREAMLIT_VERIFY_EMAIL": "verify@example.com",
            "STREAMLIT_VERIFY_PASSWORD": "verify-password",
        }
        with patch("src.auth._get_config_value", side_effect=lambda name, default="": values.get(name, default)):
            self.assertEqual(auth.get_demo_credentials(), ("demo@example.com", "demo-password"))

    def test_get_demo_credentials_ignores_verify_credentials(self) -> None:
        """데모 진입은 운영 검증 계정 대신 전용 데모 자격 증명만 사용한다."""

        values = {
            "DEMO_LOGIN_EMAIL": "",
            "DEMO_LOGIN_PASSWORD": "",
            "STREAMLIT_VERIFY_EMAIL": "verify@example.com",
            "STREAMLIT_VERIFY_PASSWORD": "verify-password",
        }
        with patch("src.auth._get_config_value", side_effect=lambda name, default="": values.get(name, default)):
            self.assertEqual(auth.get_demo_credentials(), ("", ""))
            self.assertFalse(auth.has_demo_credentials())

    def test_sign_in_demo_user_uses_resolved_credentials_when_available(self) -> None:
        """설정된 데모 계정이 있으면 일반 로그인 흐름으로 진입한다."""

        with patch("src.auth.get_demo_credentials", return_value=("demo@example.com", "demo-password")):
            with patch("src.auth.sign_in") as sign_in_mock:
                result = auth.sign_in_demo_user()

        sign_in_mock.assert_called_once_with(email="demo@example.com", password="demo-password")
        self.assertEqual(result, {"email": "demo@example.com", "mode": "supabase"})

    def test_sign_in_demo_user_falls_back_to_local_demo_session(self) -> None:
        """데모 계정 설정이 없어도 로컬 데모 세션으로 바로 진입한다."""

        with patch("src.auth.get_demo_credentials", return_value=("", "")):
            with patch("src.auth._save_demo_session") as save_demo_session_mock:
                result = auth.sign_in_demo_user()

        save_demo_session_mock.assert_called_once_with()
        self.assertEqual(result, {"email": auth.DEMO_USER_EMAIL, "mode": auth.DEMO_SESSION_MODE})

    def test_is_demo_user_checks_saved_session_mode(self) -> None:
        """세션의 mode 값으로 로컬 데모 여부를 판별한다."""

        with patch("src.auth._raw_session", return_value={"mode": auth.DEMO_SESSION_MODE}):
            self.assertTrue(auth.is_demo_user())
        with patch("src.auth._raw_session", return_value={"mode": "supabase"}):
            self.assertFalse(auth.is_demo_user())


if __name__ == "__main__":
    unittest.main()

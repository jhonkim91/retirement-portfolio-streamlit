from __future__ import annotations

import unittest
from unittest.mock import patch

from src import auth


class DemoAuthHelperTests(unittest.TestCase):
    """초기 화면 데모 접속용 인증 helper를 검증한다."""

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

    def test_get_demo_credentials_falls_back_to_verify_credentials(self) -> None:
        """전용 데모 자격 증명이 없으면 기존 검증 자격 증명을 재사용한다."""

        values = {
            "DEMO_LOGIN_EMAIL": "",
            "DEMO_LOGIN_PASSWORD": "",
            "STREAMLIT_VERIFY_EMAIL": "verify@example.com",
            "STREAMLIT_VERIFY_PASSWORD": "verify-password",
        }
        with patch("src.auth._get_config_value", side_effect=lambda name, default="": values.get(name, default)):
            self.assertEqual(auth.get_demo_credentials(), ("verify@example.com", "verify-password"))
            self.assertTrue(auth.has_demo_credentials())

    def test_sign_in_demo_user_uses_resolved_credentials(self) -> None:
        """데모 접속 helper가 해석된 자격 증명으로 일반 로그인 함수를 호출한다."""

        with patch("src.auth.get_demo_credentials", return_value=("demo@example.com", "demo-password")):
            with patch("src.auth.sign_in") as sign_in_mock:
                result = auth.sign_in_demo_user()

        sign_in_mock.assert_called_once_with(email="demo@example.com", password="demo-password")
        self.assertEqual(result, {"email": "demo@example.com"})

    def test_sign_in_demo_user_raises_when_credentials_are_missing(self) -> None:
        """데모 자격 증명이 없으면 설정 가이드를 포함한 오류를 반환한다."""

        with patch("src.auth.get_demo_credentials", return_value=("", "")):
            with self.assertRaisesRegex(RuntimeError, "DEMO_LOGIN_EMAIL/DEMO_LOGIN_PASSWORD"):
                auth.sign_in_demo_user()


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import textwrap
import unittest

from scripts.verify_streamlit_deployment import build_summary, normalize_backend_code


class DeploymentSummaryParserTests(unittest.TestCase):
    """배포 검증 스크립트의 텍스트 파서를 검증한다."""

    def test_build_summary_detects_onboarding_with_supabase_backend(self) -> None:
        """온보딩 화면에서 Supabase 저장소와 인증 상태를 판별한다."""

        text = textwrap.dedent(
            """
            현재 저장소: Supabase
            첫 계좌 만들기
            계좌 이름
            시작 현금
            데모 데이터 불러오기
            """
        ).strip()

        summary = build_summary("https://example.streamlit.app", "data", text)

        self.assertTrue(summary.logged_in)
        self.assertTrue(summary.onboarding_visible)
        self.assertFalse(summary.workspace_visible)
        self.assertEqual(summary.backend_storage, "Supabase")
        self.assertEqual(summary.backend_storage_code, "supabase")
        self.assertEqual(summary.onboarding_error, "")
        self.assertFalse(summary.hotfix_required)
        self.assertFalse(summary.demo_seeded)

    def test_build_summary_extracts_rls_hotfix_error_from_onboarding(self) -> None:
        """온보딩 화면의 RLS 403 오류를 핫픽스 필요 상태로 판별한다."""

        text = textwrap.dedent(
            """
            현재 저장소: Supabase
            첫 계좌 만들기
            계좌 이름
            시작 현금
            Supabase POST accounts 요청에 실패했습니다 (403): new row violates row-level security policy for table "accounts" owner_user_id hotfix 필요
            """
        ).strip()

        summary = build_summary("https://example.streamlit.app", "data", text)

        self.assertTrue(summary.onboarding_visible)
        self.assertIn("row-level security", summary.onboarding_error.lower())
        self.assertTrue(summary.hotfix_required)
        self.assertFalse(summary.demo_seeded)

    def test_build_summary_extracts_workspace_status_panel_values(self) -> None:
        """작업공간 화면에서 운영 상태 패널 값을 추출한다."""

        text = textwrap.dedent(
            """
            로그인 계정
            jhonkim2025@gmail.com
            로그아웃
            운영 상태
            데이터 저장소
            Supabase
            누적 이자
            12,345원
            이자 롤업
            7건
            2026-05-07
            자산 스냅샷
            9건
            2026-05-07
            Supabase 설정 감지: 예
            SUPABASE_URL 설정: secret
            SUPABASE_KEY 설정: secret
            Supabase 프로젝트: demo-project.supabase.co
            누락 설정: 없음
            백엔드 강제 설정: auto
            감지 사유: secrets configured
            현재 배포본은 Supabase 운영 모드입니다.
            """
        ).strip()

        summary = build_summary("https://example.streamlit.app", "data", text)

        self.assertTrue(summary.logged_in)
        self.assertTrue(summary.workspace_visible)
        self.assertTrue(summary.status_panel_visible)
        self.assertFalse(summary.onboarding_visible)
        self.assertEqual(summary.backend_storage_code, "supabase")
        self.assertEqual(summary.total_interest, "12,345원")
        self.assertEqual(summary.interest_rollup, "7건")
        self.assertEqual(summary.latest_interest_date, "2026-05-07")
        self.assertEqual(summary.snapshot_count, "9건")
        self.assertEqual(summary.latest_snapshot_date, "2026-05-07")
        self.assertEqual(summary.supabase_config_status, "예")
        self.assertEqual(summary.supabase_url_status, "secret")
        self.assertEqual(summary.supabase_key_status, "secret")
        self.assertEqual(summary.supabase_project, "demo-project.supabase.co")
        self.assertEqual(summary.missing_config, "없음")
        self.assertEqual(summary.backend_override, "auto")
        self.assertEqual(summary.reason, "secrets configured")
        self.assertEqual(summary.status_message, "현재 배포본은 Supabase 운영 모드입니다.")
        self.assertTrue(summary.demo_seeded)


class BackendNormalizationTests(unittest.TestCase):
    """저장소 표시 문자열 정규화를 검증한다."""

    def test_normalize_backend_code_maps_known_labels(self) -> None:
        """Supabase, SQLite, 기타 문자열을 기대 코드로 변환한다."""

        self.assertEqual(normalize_backend_code("Supabase"), "supabase")
        self.assertEqual(normalize_backend_code("로컬 SQLite"), "sqlite")
        self.assertEqual(normalize_backend_code("unknown backend"), "unknown")


if __name__ == "__main__":
    unittest.main()

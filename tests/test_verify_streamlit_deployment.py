from __future__ import annotations

import textwrap
import unittest

from scripts.verify_streamlit_deployment import (
    build_summary,
    format_debug_dir_hint,
    has_target_page_content,
    normalize_backend_code,
    resolve_optional_output_path,
)


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
            test
            로그아웃
            운영 상태
            데이터 저장소
            Supabase
            거래 기록
            42건
            2026-05-07
            현금 수정 순반영
            -15,000원
            자산 스냅샷
            9건
            2026-05-07
            Supabase 설정 감지: 예
            SUPABASE_URL 설정: 예 (secret)
            SUPABASE_KEY 설정: 예 (secret)
            Supabase 프로젝트: demo-project.supabase.co
            누락 설정: 없음
            백엔드 강제 설정: auto
            감지 사유: secrets configured
            현재 배포본은 Supabase를 사용 중입니다.
            """
        ).strip()

        summary = build_summary("https://example.streamlit.app", "data", text)

        self.assertTrue(summary.logged_in)
        self.assertTrue(summary.workspace_visible)
        self.assertTrue(summary.status_panel_visible)
        self.assertFalse(summary.onboarding_visible)
        self.assertEqual(summary.backend_storage_code, "supabase")
        self.assertEqual(summary.trade_log_count, "42건")
        self.assertEqual(summary.latest_trade_date, "2026-05-07")
        self.assertEqual(summary.cash_adjustment_net, "-15,000원")
        self.assertEqual(summary.snapshot_count, "9건")
        self.assertEqual(summary.latest_snapshot_date, "2026-05-07")
        self.assertEqual(summary.supabase_config_status, "예")
        self.assertEqual(summary.supabase_url_status, "secret")
        self.assertEqual(summary.supabase_key_status, "secret")
        self.assertEqual(summary.supabase_project, "demo-project.supabase.co")
        self.assertEqual(summary.missing_config, "없음")
        self.assertEqual(summary.backend_override, "auto")
        self.assertEqual(summary.reason, "secrets configured")
        self.assertEqual(summary.status_message, "현재 배포본은 Supabase를 사용 중입니다.")
        self.assertEqual(summary.allocation_status, "")
        self.assertTrue(summary.demo_seeded)

    def test_build_summary_extracts_dashboard_allocation_status(self) -> None:
        """대시보드 화면에서 자산 배분 상태 칩 텍스트를 추출한다."""

        text = textwrap.dedent(
            """
            로그인 계정
            test
            로그아웃
            현재 보기: 대시보드
            현재 저장소: Supabase
            자산 배분
            실시간 연동 중
            -
            +
            선택 종목 트렌드
            """
        ).strip()

        summary = build_summary("https://example.streamlit.app", "dashboard", text)

        self.assertTrue(summary.logged_in)
        self.assertTrue(summary.workspace_visible)
        self.assertEqual(summary.allocation_status, "실시간 연동 중")
        self.assertEqual(summary.backend_storage_code, "supabase")

    def test_build_summary_detects_auth_rate_limit_error(self) -> None:
        """로그인 화면의 rate limit 오류를 별도 필드로 추출한다."""

        text = textwrap.dedent(
            """
            자산관리 대장
            이메일
            비밀번호
            로그인
            새 계정 만들기
            데모 모드
            Request rate limit reached
            """
        ).strip()

        summary = build_summary("https://example.streamlit.app", "data", text)

        self.assertFalse(summary.logged_in)
        self.assertEqual(summary.auth_error, "Request rate limit reached")
        self.assertTrue(summary.rate_limited)
        self.assertFalse(summary.workspace_visible)


class BackendNormalizationTests(unittest.TestCase):
    """저장소 표시 문자열 정규화를 검증한다."""

    def test_normalize_backend_code_maps_known_labels(self) -> None:
        """Supabase, SQLite, 기타 문자열을 기대 코드로 변환한다."""

        self.assertEqual(normalize_backend_code("Supabase"), "supabase")
        self.assertEqual(normalize_backend_code("로컬 SQLite"), "sqlite")
        self.assertEqual(normalize_backend_code("unknown backend"), "unknown")


class PageMarkerTests(unittest.TestCase):
    """페이지별 핵심 마커 판별을 검증한다."""

    def test_has_target_page_content_detects_dashboard_markers(self) -> None:
        """대시보드 핵심 마커가 모두 있으면 준비 완료로 본다."""

        text = "자산 배분\n실시간 연동 중\n선택 종목 트렌드"

        self.assertTrue(has_target_page_content(text, "dashboard"))

    def test_has_target_page_content_requires_all_dashboard_markers(self) -> None:
        """대시보드 마커가 하나라도 없으면 아직 준비되지 않은 것으로 본다."""

        text = "자산관리 대장\n로그인되었습니다."

        self.assertFalse(has_target_page_content(text, "dashboard"))


class DebugHelperTests(unittest.TestCase):
    """디버그 경로 헬퍼를 검증한다."""

    def test_resolve_optional_output_path_returns_none_for_empty_input(self) -> None:
        """빈 경로는 `None`으로 처리한다."""

        self.assertIsNone(resolve_optional_output_path(""))
        self.assertIsNone(resolve_optional_output_path(None))

    def test_format_debug_dir_hint_includes_resolved_path(self) -> None:
        """디버그 디렉터리 힌트는 절대 경로를 포함한다."""

        hint = format_debug_dir_hint("artifacts/debug-verify")

        self.assertIn("디버그 산출물:", hint)
        self.assertIn("artifacts/debug-verify", hint)


if __name__ == "__main__":
    unittest.main()

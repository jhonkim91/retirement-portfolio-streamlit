from __future__ import annotations

import inspect
import importlib.util
from datetime import date
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import pandas as pd


def load_app_module():
    """대시보드 헬퍼 테스트용으로 앱 모듈을 동적으로 불러온다."""

    stub_module = types.ModuleType("streamlit_echarts")

    class StubJsCode(str):
        """테스트에서 JsCode 자리를 대신하는 간단한 문자열 래퍼."""

        def __new__(cls, js_code: str):
            return str.__new__(cls, js_code)

    stub_module.JsCode = StubJsCode
    stub_module.st_echarts = lambda *args, **kwargs: None
    sys.modules["streamlit_echarts"] = stub_module

    module_path = Path(__file__).resolve().parents[1] / "app.py"
    spec = importlib.util.spec_from_file_location("app_dashboard_test_module", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


dashboard_app = load_app_module()


class ThemeStylesheetTests(unittest.TestCase):
    """디자인 토큰과 외부 전역 CSS 연결을 검증한다."""

    def test_load_design_tokens_uses_streamlit_theme_values(self) -> None:
        """Streamlit theme 기본 색상을 토큰의 기준값으로 읽는다."""

        tokens = dashboard_app.load_design_tokens()

        self.assertEqual(tokens["theme_primary_color"], "#5DBB92")
        self.assertEqual(tokens["theme_background_color"], "#F7F8F4")
        self.assertEqual(tokens["theme_secondary_background_color"], "#EEF5F1")
        self.assertEqual(tokens["theme_text_color"], "#172033")
        self.assertEqual(tokens["brand_deep_color"], "#172033")
        self.assertEqual(tokens["brand_accent_color"], "#5DBB92")
        self.assertEqual(tokens["brand_hover_color"], "#479A78")
        self.assertEqual(tokens["status_good_color"], "#16A46C")
        self.assertEqual(tokens["chart_up_color"], "#16A46C")
        self.assertEqual(tokens["chart_down_color"], "#E85D75")
        self.assertEqual(tokens["chart_line_color"], "#5DBB92")
        self.assertEqual(tokens["chart_accent_color"], "#5DBB92")
        self.assertEqual(tokens["chart_accent_strong_color"], "#479A78")

    def test_render_app_stylesheet_substitutes_theme_variables(self) -> None:
        """외부 CSS 템플릿의 플레이스홀더가 실제 토큰 값으로 치환된다."""

        stylesheet = dashboard_app.render_app_stylesheet()

        self.assertIn("--theme-primary: #5DBB92;", stylesheet)
        self.assertIn("--theme-bg: #F7F8F4;", stylesheet)
        self.assertIn("--theme-secondary-bg: #EEF5F1;", stylesheet)
        self.assertIn("--brand-deep: #172033;", stylesheet)
        self.assertIn("--chart-up: #16A46C;", stylesheet)
        self.assertIn("--chart-down: #E85D75;", stylesheet)
        self.assertIn("--chart-line: #5DBB92;", stylesheet)
        self.assertIn(".soft-wealth-hero", stylesheet)
        self.assertIn("#5DBB92", stylesheet)
        self.assertIn("#F7F8F4", stylesheet)
        self.assertIn("#EEF5F1", stylesheet)
        self.assertIn(".dashboard-metric-card", stylesheet)
        self.assertIn(".dashboard-reference-time", stylesheet)
        self.assertIn(".holdings-table-shell", stylesheet)
        self.assertIn(".holdings-mobile-card-list", stylesheet)
        self.assertIn(".st-key-dashboard-panel-allocation", stylesheet)
        self.assertIn(".st-key-dashboard-panel-holdings-table", stylesheet)
        self.assertIn(".returns-chart", stylesheet)
        self.assertIn(".returns-chart__filter-pill", stylesheet)
        self.assertIn(".returns-chart__sort-pill", stylesheet)
        self.assertIn(".returns-chart__bar-outer--pos", stylesheet)
        self.assertIn(".returns-chart__bar-outer--neg", stylesheet)
        self.assertIn("@keyframes returns-chart-bar-in", stylesheet)
        self.assertIn(".st-key-sidebar-account-panel", stylesheet)
        self.assertIn(".sidebar-brand", stylesheet)
        self.assertIn(".st-key-trade-product-entry", stylesheet)
        self.assertIn(".trade-total-preview", stylesheet)
        self.assertIn(".cash-flow-preview", stylesheet)
        self.assertIn(".product-code-status-row", stylesheet)
        self.assertIn(".st-key-dashboard-summary-primary", stylesheet)
        self.assertIn(".st-key-dashboard-summary-secondary", stylesheet)
        self.assertIn(".st-key-trade-realized-summary", stylesheet)
        self.assertIn(".realized-contribution", stylesheet)
        self.assertIn(".st-key-trade-log-filter-panel", stylesheet)
        self.assertIn(".trade-log-result-summary", stylesheet)
        self.assertIn(".trade-log-pagination", stylesheet)
        self.assertIn(".trade-log-profit-rate--positive", stylesheet)
        self.assertIn(".st-key-trade-log-panel [data-testid=\"stVerticalBlockBorderWrapper\"]", stylesheet)
        self.assertIn("border-radius: 12px !important;", stylesheet)
        self.assertIn('.st-key-trade-log-panel [data-testid="stDownloadButton"] > button', stylesheet)
        self.assertIn("background: #FFFFFF !important;", stylesheet)
        self.assertIn("padding: 6px 10px !important;", stylesheet)
        self.assertIn(".st-key-trade-log-panel .trade-log-result-summary span + span::before", stylesheet)
        self.assertIn('[class*="st-key-trade-log-actions"] [data-testid="stVerticalBlock"]', stylesheet)
        self.assertIn('[class*="st-key-trade-log-actions"][data-testid="stVerticalBlock"]', stylesheet)
        self.assertIn("flex-direction: row !important;", stylesheet)
        self.assertIn("white-space: nowrap !important;", stylesheet)
        self.assertIn("min-width: 2.8rem !important;", stylesheet)
        self.assertIn("background: #EEF4FF !important;", stylesheet)
        self.assertIn("background: #FDF0F3 !important;", stylesheet)
        self.assertIn("background: #5DBB92;", stylesheet)
        self.assertNotIn("background: linear-gradient(90deg, #F0FDF4 0%, #FFFFFF 100%);", stylesheet)
        self.assertNotIn("background: linear-gradient(90deg, #FEF2F2 0%, #FFFFFF 100%);", stylesheet)
        self.assertIn("--radius-lg: 18px;", stylesheet)
        self.assertIn("--shadow-card: 0 18px 42px rgba(23, 32, 51, 0.07);", stylesheet)
        self.assertIn("--panel-radius: var(--radius-lg);", stylesheet)
        self.assertIn("--dashboard-summary-card-height: 128px;", stylesheet)
        self.assertIn("--dashboard-secondary-panel-min-height: 560px;", stylesheet)
        self.assertNotIn("--card-shadow:", stylesheet)
        self.assertIn('[data-testid="stSidebar"] {\n    background: rgba(255, 255, 255, 0.94);', stylesheet)
        self.assertIn('[data-testid="stVerticalBlockBorderWrapper"] {\n    background: var(--surface-strong);', stylesheet)
        self.assertIn('[data-testid="stMetric"] {\n    background: var(--surface-strong);', stylesheet)
        self.assertIn(".dashboard-summary-card,\n.dashboard-metric-card", stylesheet)
        self.assertIn("border-radius: var(--radius-xl);", stylesheet)
        self.assertIn("box-shadow: var(--shadow-card);", stylesheet)
        self.assertIn("rgba(255, 255, 255, 0.94)", stylesheet)
        self.assertIn("linear-gradient(135deg, #DDF7EA 0%, #E4F5FF 58%, #F8FBF6 100%)", stylesheet)
        self.assertIn(".dashboard-summary-card::before,\n.dashboard-metric-card::before", stylesheet)
        self.assertIn("box-shadow: var(--shadow-hover);", stylesheet)
        self.assertIn(".dashboard-summary-card--positive .dashboard-summary-card__delta", stylesheet)
        self.assertIn(".dashboard-summary-card--negative .dashboard-summary-card__delta", stylesheet)
        self.assertIn(".dashboard-summary-card--accent .dashboard-summary-card__delta", stylesheet)
        self.assertIn('@media (max-width: 1180px) {\n    .dashboard-metric-strip {\n        grid-template-columns: repeat(3, minmax(0, 1fr));', stylesheet)
        self.assertIn('@media (max-width: 820px) {\n    .dashboard-metric-strip {\n        grid-template-columns: repeat(2, minmax(0, 1fr));', stylesheet)
        self.assertIn(".dashboard-section-header__top {\n        align-items: flex-start;\n        flex-direction: column;", stylesheet)
        self.assertIn(".dashboard-section-header__status-group {\n        justify-content: flex-start;", stylesheet)
        self.assertIn(".dashboard-summary-card,\n    .dashboard-metric-card {\n        min-height: auto;", stylesheet)
        self.assertIn(".dashboard-summary-card__value,\n    .dashboard-metric-card__value,\n    .st-key-dashboard-summary-strip .dashboard-summary-card__value {\n        font-size: 1.65rem;", stylesheet)
        self.assertIn(".block-container {\n        padding-left: 0.9rem;\n        padding-right: 0.9rem;", stylesheet)
        self.assertIn(".st-key-dashboard-card-principal,\n.st-key-dashboard-card-cash", stylesheet)
        self.assertIn(".st-key-dashboard-panel-selected-trend,\n.st-key-dashboard-panel-holdings {\n    min-height", stylesheet)
        self.assertIn(".st-key-dashboard-panel-allocation,\n.st-key-dashboard-panel-selected-trend,\n.st-key-dashboard-panel-holdings,\n.st-key-dashboard-panel-holdings-table {\n    background:", stylesheet)
        self.assertIn("border-radius: var(--radius-xl) !important;\n    box-shadow: var(--shadow-card) !important;", stylesheet)
        self.assertIn(".st-key-dashboard-panel-allocation [data-testid=\"stVerticalBlockBorderWrapper\"],\n.st-key-dashboard-panel-selected-trend [data-testid=\"stVerticalBlockBorderWrapper\"],\n.st-key-dashboard-panel-holdings [data-testid=\"stVerticalBlockBorderWrapper\"],\n.st-key-dashboard-panel-holdings-table [data-testid=\"stVerticalBlockBorderWrapper\"]", stylesheet)
        self.assertIn("box-shadow: none !important;\n    border: none !important;\n    background: transparent !important;", stylesheet)
        self.assertIn(".dashboard-section-header {\n    display: flex;\n    flex-direction: column;\n    gap: 0.28rem;\n    margin-bottom: var(--section-gap);\n    padding: 0.15rem 0.1rem 0.25rem;", stylesheet)
        self.assertIn(".dashboard-section-header__title {\n    color: var(--brand-deep);\n    font-size: 1.22rem;\n    font-weight: 900;\n    line-height: 1.1;\n    letter-spacing: 0;", stylesheet)
        self.assertIn(".dashboard-section-header__caption {\n    color: var(--text-muted);\n    font-size: 0.88rem;", stylesheet)
        self.assertIn(".st-key-dashboard-summary-strip .dashboard-summary-card__value", stylesheet)
        self.assertIn(".st-key-dashboard-card-principal .dashboard-summary-card__action--ghost", stylesheet)
        self.assertIn('.st-key-dashboard-secondary-grid [data-testid="stHorizontalBlock"]', stylesheet)
        self.assertIn('.st-key-dashboard-summary-strip [data-testid="stHorizontalBlock"] > div {\n    display: flex;', stylesheet)
        self.assertIn('.st-key-dashboard-summary-strip [data-testid="stHorizontalBlock"] > div > div {\n    flex: 1 1 auto;', stylesheet)
        self.assertNotIn('.st-key-dashboard-card-principal [data-testid="stVerticalBlockBorderWrapper"]', stylesheet)
        self.assertIn('.st-key-dashboard-panel-selected-trend [data-testid="stVerticalBlockBorderWrapper"]', stylesheet)
        self.assertIn('.st-key-dashboard-trend-controls [data-testid="column"] {\n    min-width: 0 !important;', stylesheet)
        self.assertIn('.st-key-dashboard-trend-controls [data-baseweb="select"] > div {\n    min-width: 0;', stylesheet)
        self.assertIn('@media (max-width: 768px) {\n    .st-key-trade-form-cols [data-testid="stHorizontalBlock"]', stylesheet)
        self.assertIn('.st-key-trade-form-cols [data-testid="stHorizontalBlock"] > div,\n    .st-key-trade-form-cols [data-testid="column"] {\n        width: 100% !important;', stylesheet)
        self.assertIn('.st-key-trade-product-entry [data-testid="stHorizontalBlock"],\n    .st-key-trade-cash-flow-entry [data-testid="stHorizontalBlock"]', stylesheet)
        self.assertIn('@media (max-width: 640px) {\n    .st-key-dashboard-panel-holdings-table .holdings-table-shell--desktop', stylesheet)
        self.assertIn(".st-key-dashboard-panel-holdings-table .holdings-mobile-card-list {\n        display: grid !important;", stylesheet)
        self.assertIn('div[role="dialog"] [data-testid="stForm"]', stylesheet)
        self.assertNotIn(".st-key-trade-log-inline-editor-shell", stylesheet)
        self.assertNotIn("${theme_primary_color}", stylesheet)

    def test_stylesheet_keeps_soft_wealth_light_surfaces(self) -> None:
        """Soft Wealth 테마는 밝은 화이트 카드와 다크 자동 전환 제거를 유지한다."""

        stylesheet = dashboard_app.render_app_stylesheet()

        self.assertNotIn("@media (prefers-color-scheme: dark)", stylesheet)
        self.assertIn("background: rgba(255, 255, 255, 0.94)", stylesheet)
        self.assertIn("background: #FFFFFF", stylesheet)
        self.assertIn("#F7F8F4", stylesheet)
        self.assertIn("#EEF5F1", stylesheet)

    def test_render_app_stylesheet_uses_local_system_font_stack(self) -> None:
        """초기 렌더 지연을 줄이기 위해 외부 CDN 폰트 import 없이 시스템 폰트를 사용한다."""

        stylesheet = dashboard_app.render_app_stylesheet()

        self.assertNotIn("cdn.jsdelivr.net", stylesheet)
        self.assertNotIn("Pretendard", stylesheet)
        self.assertIn('font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI"', stylesheet)

    def test_render_app_stylesheet_returns_empty_string_when_css_missing(self) -> None:
        """CSS 템플릿 파일이 없어도 앱 렌더링을 중단하지 않는다."""

        original_css_path = dashboard_app.APP_CSS_PATH

        with tempfile.TemporaryDirectory() as temp_dir:
            dashboard_app.render_app_stylesheet.clear()
            dashboard_app.APP_CSS_PATH = Path(temp_dir) / "missing-app.css"

            try:
                self.assertEqual(dashboard_app.render_app_stylesheet(), "")
            finally:
                dashboard_app.APP_CSS_PATH = original_css_path
                dashboard_app.render_app_stylesheet.clear()

    def test_trade_page_wraps_form_columns_for_mobile_styles(self) -> None:
        """거래 페이지 상단 2열 입력 영역은 모바일 CSS 적용용 key 컨테이너로 감싼다."""

        source = inspect.getsource(dashboard_app.trade_entry_page)

        self.assertIn('st.container(key="trade-form-cols")', source)
        self.assertIn('st.container(border=True, key="trade-product-entry")', source)
        self.assertIn('st.container(border=True, key="trade-cash-flow-entry")', source)

    def test_dashboard_secondary_panel_chart_heights_match(self) -> None:
        """선택 종목 트렌드와 보유 종목 수익률 차트 높이는 같은 값을 사용한다."""

        self.assertEqual(
            dashboard_app.DASHBOARD_DETAIL_CHART_HEIGHT,
            dashboard_app.DASHBOARD_HOLDINGS_COMPARE_CHART_HEIGHT,
        )

    def test_dashboard_card_renderers_add_tone_and_delta_classes(self) -> None:
        """KPI 카드 렌더러는 카드/tone/delta 클래스를 HTML에 포함한다."""

        class FakeColumn:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback) -> bool:
                return False

        class FakeStreamlit:
            def __init__(self) -> None:
                self.markdowns: list[str] = []

            def markdown(self, body: str, **kwargs) -> None:
                self.markdowns.append(body)

            def columns(self, count: int, **kwargs) -> list[FakeColumn]:
                return [FakeColumn() for _ in range(count)]

        original_st = dashboard_app.st
        fake_st = FakeStreamlit()
        dashboard_app.st = fake_st
        try:
            dashboard_app.render_dashboard_summary_card("원금 대비 수익률", "+1.20%", tone="positive", delta="+120")
            dashboard_app.render_dashboard_metric_strip(
                [{"label": "평가손익", "value": "-10,000", "tone": "negative", "delta": "-10,000"}]
            )
        finally:
            dashboard_app.st = original_st

        summary_html = fake_st.markdowns[0]
        metric_html = fake_st.markdowns[1]
        self.assertIn("dashboard-summary-card dashboard-summary-card__field dashboard-summary-card--positive", summary_html)
        self.assertIn("dashboard-summary-card__value dashboard-summary-card__value--positive", summary_html)
        self.assertIn('dashboard-summary-card__delta">+120', summary_html)
        self.assertIn('dashboard-metric-card dashboard-metric-card--negative', metric_html)
        self.assertIn("dashboard-metric-card__value dashboard-metric-card__value--negative", metric_html)
        self.assertIn('dashboard-metric-card__delta">-10,000', metric_html)


class TradeFormResetTests(unittest.TestCase):
    """거래 페이지의 rerun 기반 폼 초기화 헬퍼를 검증한다."""

    def test_apply_pending_form_reset_restores_defaults_only_when_flagged(self) -> None:
        """pending 플래그가 있을 때만 기본값을 세션 상태에 다시 쓴다."""

        session_state = {
            dashboard_app.TRADE_FORM_RESET_PENDING_KEY: True,
            dashboard_app.TRADE_SYMBOL_KEY: "AAPL",
            dashboard_app.TRADE_PRICE_KEY: 1000.0,
        }

        dashboard_app.apply_pending_form_reset(
            session_state,
            pending_key=dashboard_app.TRADE_FORM_RESET_PENDING_KEY,
            reset_values={
                dashboard_app.TRADE_SYMBOL_KEY: "",
                dashboard_app.TRADE_PRICE_KEY: 0.0,
            },
        )

        self.assertNotIn(dashboard_app.TRADE_FORM_RESET_PENDING_KEY, session_state)
        self.assertEqual(session_state[dashboard_app.TRADE_SYMBOL_KEY], "")
        self.assertEqual(session_state[dashboard_app.TRADE_PRICE_KEY], 0.0)

    def test_consume_session_message_returns_message_once(self) -> None:
        """세션 메시지는 한 번 읽으면 비워져야 한다."""

        session_state = {dashboard_app.TRADE_PAGE_SUCCESS_MESSAGE_KEY: "거래를 저장했습니다."}

        first = dashboard_app.consume_session_message(session_state, dashboard_app.TRADE_PAGE_SUCCESS_MESSAGE_KEY)
        second = dashboard_app.consume_session_message(session_state, dashboard_app.TRADE_PAGE_SUCCESS_MESSAGE_KEY)

        self.assertEqual(first, "거래를 저장했습니다.")
        self.assertEqual(second, "")

    def test_prefill_latest_trade_price_clears_stale_price_before_failed_lookup(self) -> None:
        """새 종목 현재가 조회에 실패하면 이전 종목의 자동 단가를 남기지 않는다."""

        fake_st = types.SimpleNamespace(
            session_state={
                dashboard_app.TRADE_PRICE_KEY: 12345.0,
                dashboard_app.TRADE_PRICE_AUTO_FILLED_KEY: True,
            }
        )
        original_st = dashboard_app.st
        dashboard_app.st = fake_st
        try:
            with patch.object(dashboard_app, "fetch_latest_price", side_effect=RuntimeError("quote unavailable")):
                result = dashboard_app.prefill_latest_trade_price("UNSUPPORTED")
        finally:
            dashboard_app.st = original_st

        self.assertFalse(result)
        self.assertEqual(fake_st.session_state[dashboard_app.TRADE_PRICE_KEY], 0.0)
        self.assertFalse(fake_st.session_state[dashboard_app.TRADE_PRICE_AUTO_FILLED_KEY])

    def test_prefill_latest_trade_price_marks_successful_autofill(self) -> None:
        """현재가 조회에 성공한 경우에만 단가와 자동 입력 플래그를 채운다."""

        fake_st = types.SimpleNamespace(
            session_state={
                dashboard_app.TRADE_PRICE_KEY: 12345.0,
                dashboard_app.TRADE_PRICE_AUTO_FILLED_KEY: False,
            }
        )
        original_st = dashboard_app.st
        dashboard_app.st = fake_st
        try:
            with patch.object(dashboard_app, "fetch_latest_price", return_value={"price": "67890"}):
                result = dashboard_app.prefill_latest_trade_price("005930")
        finally:
            dashboard_app.st = original_st

        self.assertTrue(result)
        self.assertEqual(fake_st.session_state[dashboard_app.TRADE_PRICE_KEY], 67890.0)
        self.assertTrue(fake_st.session_state[dashboard_app.TRADE_PRICE_AUTO_FILLED_KEY])

    def test_trade_price_manual_edit_callback_clears_autofill_flag(self) -> None:
        """사용자가 단가를 직접 수정하면 자동 입력 상태를 해제한다."""

        fake_st = types.SimpleNamespace(session_state={dashboard_app.TRADE_PRICE_AUTO_FILLED_KEY: True})
        original_st = dashboard_app.st
        dashboard_app.st = fake_st
        try:
            dashboard_app.mark_trade_price_manually_edited()
        finally:
            dashboard_app.st = original_st

        self.assertFalse(fake_st.session_state[dashboard_app.TRADE_PRICE_AUTO_FILLED_KEY])

    def test_trade_price_number_input_uses_manual_edit_callback(self) -> None:
        """거래 단가 입력 위젯은 수동 수정 callback을 연결한다."""

        source = inspect.getsource(dashboard_app.trade_entry_page)

        self.assertIn("on_change=mark_trade_price_manually_edited", source)

    def test_is_visible_trade_log_keeps_core_transaction_types_only(self) -> None:
        """거래 기록 화면에는 입금/매수/매도 핵심 유형만 남긴다."""

        self.assertFalse(dashboard_app.is_visible_trade_log({"trade_type": "cash_adjustment"}))
        self.assertFalse(dashboard_app.is_visible_trade_log({"trade_type": "transfer_out"}))
        self.assertFalse(dashboard_app.is_visible_trade_log({"trade_type": "withdraw"}))
        self.assertTrue(dashboard_app.is_visible_trade_log({"trade_type": "personal_deposit"}))
        self.assertTrue(dashboard_app.is_visible_trade_log({"trade_type": "employer_deposit"}))
        self.assertTrue(dashboard_app.is_visible_trade_log({"trade_type": "buy"}))

    def test_is_trade_log_editable_allows_supported_types_only(self) -> None:
        self.assertTrue(dashboard_app.is_trade_log_editable({"trade_type": "buy"}))
        self.assertTrue(dashboard_app.is_trade_log_editable({"trade_type": "personal_deposit"}))
        self.assertFalse(dashboard_app.is_trade_log_editable({"trade_type": "withdraw"}))
        self.assertFalse(dashboard_app.is_trade_log_editable({"trade_type": "transfer_out"}))

    def test_trade_log_selection_helpers_normalize_ids(self) -> None:
        session_state = {"selected": [1, "2", "2", None, "bad", -1]}

        self.assertEqual(dashboard_app.selected_trade_log_ids(session_state, "selected"), [1, 2])

        selected_ids = dashboard_app.set_selected_trade_log_ids(session_state, "selected", ["3", 3, 4])

        self.assertEqual(selected_ids, [3, 4])
        self.assertEqual(session_state["selected"], [3, 4])

    def test_trade_log_row_selection_callback_updates_bulk_ids(self) -> None:
        session_state = {"selected": [1], "checkbox:2": True}

        dashboard_app.sync_trade_log_row_selection(session_state, "selected", "checkbox:2", 2)
        self.assertEqual(session_state["selected"], [1, 2])

        session_state["checkbox:1"] = False
        dashboard_app.sync_trade_log_row_selection(session_state, "selected", "checkbox:1", 1)
        self.assertEqual(session_state["selected"], [2])

    def test_trade_log_bulk_delete_plan_includes_dependent_sells(self) -> None:
        logs = [
            {"id": 1, "trade_date": "2025-01-01", "trade_type": "buy", "symbol": "ABC", "quantity": 10},
            {"id": 2, "trade_date": "2025-01-02", "trade_type": "sell", "symbol": "ABC", "quantity": 7},
            {"id": 3, "trade_date": "2025-01-03", "trade_type": "buy", "symbol": "ABC", "quantity": 2},
            {"id": 4, "trade_date": "2025-01-04", "trade_type": "sell", "symbol": "ABC", "quantity": 2},
        ]

        plan = dashboard_app.build_trade_log_bulk_delete_plan(logs, [1])

        self.assertEqual(plan.selected_ids, (1,))
        self.assertEqual(plan.dependent_ids, (2,))
        self.assertEqual(set(plan.delete_ids), {1, 2})
        self.assertFalse(plan.invalid_existing_ids)

    def test_trade_log_bulk_delete_plan_blocks_already_invalid_ledger(self) -> None:
        logs = [
            {"id": 1, "trade_date": "2025-01-01", "trade_type": "buy", "symbol": "ABC", "quantity": 1},
            {"id": 2, "trade_date": "2025-01-02", "trade_type": "sell", "symbol": "ABC", "quantity": 2},
        ]

        plan = dashboard_app.build_trade_log_bulk_delete_plan(logs, [1])

        self.assertEqual(plan.selected_ids, (1,))
        self.assertEqual(plan.delete_ids, (1,))
        self.assertEqual(plan.invalid_existing_ids, (2,))

    def test_trade_log_table_fields_exclude_cash_delta_column(self) -> None:
        """거래 기록 표 구성에서 현금증감 컬럼을 제외한다."""

        self.assertNotIn("현금증감", dashboard_app.TRADE_LOG_TABLE_HEADER_LABELS)
        self.assertNotIn("cash_delta", dashboard_app.TRADE_LOG_TABLE_DISPLAY_FIELDS)
        self.assertNotIn("코드", dashboard_app.TRADE_LOG_TABLE_HEADER_LABELS)
        self.assertNotIn("자산군", dashboard_app.TRADE_LOG_TABLE_HEADER_LABELS)
        self.assertNotIn("asset_type", dashboard_app.TRADE_LOG_TABLE_DISPLAY_FIELDS)
        self.assertIn("수익률", dashboard_app.TRADE_LOG_TABLE_HEADER_LABELS)
        self.assertIn("realized_profit_rate", dashboard_app.TRADE_LOG_TABLE_DISPLAY_FIELDS)
        self.assertEqual(
            len(dashboard_app.TRADE_LOG_TABLE_HEADER_LABELS),
            len(dashboard_app.TRADE_LOG_TABLE_COLUMN_WEIGHTS),
        )

    def test_trade_log_editor_option_label_formats_one_line_summary(self) -> None:
        label = dashboard_app.trade_log_editor_option_label(
            {
                "trade_date": "2026-05-11",
                "trade_type": "buy",
                "product_name": "삼성전자",
                "total_amount": 150000,
            }
        )

        self.assertIn("2026-05-11", label)
        self.assertIn("매수", label)
        self.assertIn("삼성전자", label)
        self.assertIn("150,000원", label)

    def test_trade_and_cash_flow_copy_helpers_match_requested_labels(self) -> None:
        """거래/현금흐름 카드 문구 헬퍼가 현재 화면 표기를 유지한다."""

        self.assertEqual(dashboard_app.trade_submit_button_label("buy"), "+ 상품 추가")
        self.assertEqual(dashboard_app.trade_submit_button_label("sell"), "상품 저장")
        self.assertEqual(dashboard_app.trade_price_label("buy"), "매입가")
        self.assertEqual(dashboard_app.trade_price_label("sell"), "매도가")
        self.assertEqual(dashboard_app.trade_date_label("sell"), "거래일자")
        self.assertEqual(dashboard_app.cash_flow_panel_title("employer_deposit"), "회사 현금입금")
        self.assertIn("퇴직금 원금", dashboard_app.cash_flow_panel_caption("employer_deposit"))
        self.assertEqual(dashboard_app.cash_flow_submit_label("withdraw"), "✓ 출금 기록")
        self.assertEqual(dashboard_app.cash_flow_amount_label("personal_deposit"), "입금액 (₩)")
        self.assertEqual(dashboard_app.cash_flow_amount_label("withdraw"), "출금액 (₩)")
        self.assertEqual(dashboard_app.cash_flow_tab_label("personal_deposit"), "💰 개인 입금")
        self.assertEqual(dashboard_app.cash_flow_quick_button_label("withdraw", "50만"), "-50만")

    def test_trade_total_and_cash_flow_preview_helpers(self) -> None:
        """거래 총액과 현금 흐름 미리보기 헬퍼는 0 입력 방지 기준을 제공한다."""

        self.assertEqual(dashboard_app.calculate_trade_total(15000, 3), 45000)
        self.assertTrue(dashboard_app.is_trade_submit_disabled(0, 3))
        self.assertTrue(dashboard_app.is_trade_submit_disabled(15000, 0))
        self.assertFalse(dashboard_app.is_trade_submit_disabled(15000, 3))
        self.assertEqual(
            dashboard_app.cash_flow_balance_preview(1_000_000, "personal_deposit", 500_000),
            (1_000_000.0, 1_500_000.0),
        )
        self.assertEqual(
            dashboard_app.cash_flow_balance_preview(1_000_000, "withdraw", 200_000),
            (1_000_000.0, 800_000.0),
        )
        self.assertIn("예상 매입금액", dashboard_app.build_trade_total_preview_html(45000))
        self.assertIn("예상 원금 잔액", dashboard_app.build_cash_flow_preview_html(1_000_000, "withdraw", 200_000))

    def test_cash_flow_tab_keys_are_scoped_by_flow_type(self) -> None:
        """현금 흐름 탭 위젯 key는 유형별로 분리된다."""

        self.assertEqual(
            dashboard_app.cash_flow_widget_key(dashboard_app.CASH_FLOW_AMOUNT_KEY, "personal_deposit"),
            "cash_flow_amount:personal_deposit",
        )
        reset_values = dashboard_app.cash_flow_reset_values()

        self.assertIn("cash_flow_amount:personal_deposit", reset_values)
        self.assertIn("cash_flow_amount:employer_deposit", reset_values)
        self.assertIn("cash_flow_amount:withdraw", reset_values)

    def test_trade_page_source_uses_new_trade_and_cash_flow_layout(self) -> None:
        """거래 페이지는 총액 미리보기, 탭형 현금 흐름, 비활성화 조건을 사용한다."""

        source = inspect.getsource(dashboard_app.trade_entry_page)

        self.assertIn("build_trade_total_preview_html(trade_total)", source)
        self.assertIn("build_product_code_status_html(st.session_state.get(TRADE_SYMBOL_KEY))", source)
        self.assertIn("trade_disabled = is_trade_submit_disabled(price, quantity)", source)
        self.assertIn("disabled=trade_disabled", source)
        self.assertIn("st.tabs([cash_flow_tab_label(flow_type) for flow_type in CASH_FLOW_TYPES])", source)
        self.assertIn("cash_flow_widget_key(CASH_FLOW_AMOUNT_KEY, flow_type)", source)
        self.assertIn("build_cash_flow_preview_html(current_principal, flow_type, amount)", source)

    def test_sidebar_source_uses_account_popover_and_delete_dialog(self) -> None:
        """사이드바 계좌 영역은 새 계좌 popover와 삭제 확인 다이얼로그를 사용한다."""

        sidebar_source = inspect.getsource(dashboard_app.sidebar)
        dialog_source = inspect.getsource(dashboard_app.render_account_delete_dialog)

        self.assertIn("render_sidebar_navigation()", sidebar_source)
        self.assertIn("render_new_account_form()", sidebar_source)
        self.assertIn("render_account_delete_dialog(selected_account, account_ids)", sidebar_source)
        self.assertIn("if len(account_ids) > 1:", sidebar_source)
        self.assertIn("sidebar_account_name_html(single_account)", sidebar_source)
        self.assertNotIn("account_type_badge_html(selected_account)", sidebar_source)
        self.assertIn('@st.dialog("계좌 삭제 확인")', dialog_source)

    def test_navigation_uses_custom_sidebar_links(self) -> None:
        """기본 내비게이션은 생성하되 CSS로 숨기고 커스텀 링크를 사용한다."""

        main_source = inspect.getsource(dashboard_app._load_app_core().main)
        sidebar_nav_source = inspect.getsource(dashboard_app.render_sidebar_navigation)
        stylesheet = dashboard_app.render_app_stylesheet()

        self.assertIn("st.navigation(build_navigation_pages(), expanded=True)", main_source)
        self.assertIn('[data-testid="stSidebarNav"] {\n    display: none;', stylesheet)
        self.assertIn('st.page_link("pages/trades.py"', sidebar_nav_source)
        self.assertIn('st.page_link("pages/valuation.py"', sidebar_nav_source)
        self.assertNotIn('st.page_link("pages/data.py"', sidebar_nav_source)

    def test_navigation_pages_exclude_data_page(self) -> None:
        """현재 앱 내비게이션은 대시보드, 거래, 평가액 기록만 노출한다."""

        pages_source = inspect.getsource(dashboard_app.build_navigation_pages)
        page_name_source = inspect.getsource(dashboard_app.navigation_page_name)

        self.assertEqual(dashboard_app.PAGES, ("Dashboard", "Trades", "Valuation"))
        self.assertNotIn("Data", dashboard_app.PAGE_LABELS)
        self.assertIn('st.Page("pages/dashboard.py"', pages_source)
        self.assertIn('st.Page("pages/trades.py"', pages_source)
        self.assertIn('st.Page("pages/valuation.py"', pages_source)
        self.assertNotIn('st.Page("pages/data.py"', pages_source)
        self.assertIn('endswith("/valuation")', page_name_source)
        self.assertNotIn('endswith("/data")', page_name_source)

    def test_soft_wealth_dashboard_hero_renderer_exists(self) -> None:
        """대시보드에는 제안 2번 Overview Panel 렌더러가 포함된다."""

        dashboard_source = inspect.getsource(dashboard_app.dashboard_page)
        hero_source = inspect.getsource(dashboard_app.render_soft_wealth_dashboard_hero)
        overview_source = inspect.getsource(dashboard_app.render_dashboard_top_overview_option2)
        stylesheet = dashboard_app.render_app_stylesheet()

        self.assertIn("render_soft_wealth_dashboard_hero(", dashboard_source)
        self.assertIn("render_dashboard_top_overview_option2(", hero_source)
        self.assertIn("dashboard-overview-option2", overview_source)
        self.assertIn("dashboard-overview-hero", overview_source)
        self.assertIn("dashboard-overview-card-grid", overview_source)
        self.assertIn("dashboard-overview-period-button", overview_source)
        self.assertIn("보유 평가액", overview_source)
        self.assertIn("총 자산 평가액", overview_source)
        self.assertIn("dashboard-overview-card", stylesheet)
        self.assertIn("dashboard-overview-sparkline", stylesheet)
        self.assertIn("dashboard-overview-sparkline__glow", stylesheet)
        self.assertIn("dashboard-overview-toolbar__combined", overview_source)
        self.assertIn("dashboard-overview-toolbar__combined", stylesheet)
        self.assertIn("dashboard-overview-toolbar__status", stylesheet)
        self.assertIn("dashboard-overview-card--no-sparkline", stylesheet)
        self.assertIn("dashboard-overview-card--profit .dashboard-overview-card__sparkline", stylesheet)
        self.assertIn("dashboard_previous_day_change", overview_source)

    def test_dashboard_previous_day_change_uses_last_two_total_values(self) -> None:
        """히어로 증감값은 입금 대비 손익이 아니라 전일 대비 총자산 변화로 계산한다."""

        frame = pd.DataFrame(
            [
                {"date": "2026-05-13", "total_value": 1_000_000},
                {"date": "2026-05-12", "total_value": 900_000},
                {"date": "2026-05-14", "total_value": 1_050_000},
            ]
        )

        amount_delta, rate_delta = dashboard_app.dashboard_previous_day_change(frame)

        self.assertEqual(amount_delta, 50_000)
        self.assertAlmostEqual(rate_delta, 5.0)

    def test_dashboard_overview_metric_labels_use_profit_rate(self) -> None:
        """Overview KPI는 목표 달성률 대신 수익률 라벨을 사용한다."""

        specs = dashboard_app.build_dashboard_metric_specs(
            {
                "total_value": 12_000_000,
                "total_principal": 10_000_000,
                "cash": 1_500_000,
                "principal_profit_loss": 2_000_000,
                "principal_profit_rate": 20.0,
            },
            trend_values=[10_000_000, 11_000_000, 12_000_000],
        )
        labels = [str(spec["label"]) for spec in specs]

        self.assertIn("수익률", labels)
        self.assertNotIn("목표 달성률", labels)

    def test_dashboard_overview_metric_labels_use_deposit_valuation_mode(self) -> None:
        """평가 스냅샷 기준 Dashboard는 입금 기준 문구를 사용한다."""

        specs = dashboard_app.build_dashboard_metric_specs(
            {
                "_valuation_mode": True,
                "total_value": 12_000_000,
                "total_principal": 10_000_000,
                "cash": 1_500_000,
                "principal_profit_loss": 2_000_000,
                "principal_profit_rate": 20.0,
            },
            trend_values=[10_000_000, 11_000_000, 12_000_000],
        )
        labels = [str(spec["label"]) for spec in specs]

        self.assertEqual(labels, ["입금 원금", "현재 보유현금", "입금 대비 손익", "입금 대비 수익률"])

    def test_dashboard_summary_from_valuation_prefers_today_snapshot(self) -> None:
        """오늘 평가 스냅샷이 있으면 Dashboard 상단 요약값을 평가액 기준으로 바꾼다."""

        with patch.object(dashboard_app, "valuation_today", return_value=date(2026, 5, 14)):
            summary = dashboard_app.dashboard_summary_from_valuation(
                {
                    "total_value": 1,
                    "market_value": 1,
                    "cash": 1,
                    "total_cost": 1,
                    "total_principal": 1,
                    "principal_profit_loss": 0,
                    "principal_profit_rate": 0,
                    "allocation": {"cash": 1},
                },
                {
                    "valuation_date": "2026-05-14",
                    "valuation_amount": 12000,
                    "holdings_market_value": 9000,
                    "cash_value": 3000,
                    "invested_cost": 8000,
                    "company_principal": 10000,
                    "profit_loss": 2000,
                    "profit_rate": 20.0,
                },
            )

        self.assertTrue(summary["_valuation_mode"])
        self.assertEqual(summary["total_value"], 12000)
        self.assertEqual(summary["total_principal"], 10000)
        self.assertEqual(summary["cash"], 3000)
        self.assertEqual(summary["principal_profit_loss"], 2000)

    def test_dashboard_overview_period_limits(self) -> None:
        """Overview 기간 버튼은 그래프 표시 범위만 선택한다."""

        self.assertEqual(dashboard_app.dashboard_overview_period_limit("1W"), 7)
        self.assertEqual(dashboard_app.dashboard_overview_period_limit("1M"), 30)
        self.assertEqual(dashboard_app.dashboard_overview_period_limit("3M"), 90)
        self.assertEqual(dashboard_app.dashboard_overview_period_limit("1Y"), 365)
        self.assertIsNone(dashboard_app.dashboard_overview_period_limit("ALL"))
        self.assertEqual(dashboard_app.dashboard_overview_period_limit("unknown"), 30)

    def test_dashboard_overview_principal_and_cash_cards_hide_sparkline(self) -> None:
        """입금 원금과 보유 현금 KPI는 sparkline 없이 중앙 금액형 카드로 렌더링한다."""

        specs = dashboard_app.build_dashboard_metric_specs(
            {
                "total_value": 12_000_000,
                "total_principal": 10_000_000,
                "cash": 1_500_000,
                "principal_profit_loss": 2_000_000,
                "principal_profit_rate": 20.0,
            },
            trend_values=[10_000_000, 11_000_000, 12_000_000],
        )
        principal_html = dashboard_app.render_dashboard_metric_card_option2(specs[0])
        cash_html = dashboard_app.render_dashboard_metric_card_option2(specs[1])
        profit_html = dashboard_app.render_dashboard_metric_card_option2(specs[2])

        self.assertFalse(specs[0]["show_sparkline"])
        self.assertFalse(specs[1]["show_sparkline"])
        self.assertIn("dashboard-overview-card--no-sparkline", principal_html)
        self.assertIn("dashboard-overview-card--no-sparkline", cash_html)
        self.assertNotIn("dashboard-overview-card__sparkline", principal_html)
        self.assertNotIn("dashboard-overview-card__sparkline", cash_html)
        self.assertIn("dashboard-overview-card__sparkline", profit_html)

    def test_trade_page_uses_three_soft_wealth_tabs(self) -> None:
        """거래 페이지는 입력/기록/실현 손익 3개 탭을 사용한다."""

        source = inspect.getsource(dashboard_app.trade_entry_page)

        self.assertIn('st.tabs(["거래 입력", "거래 기록", "실현 손익"])', source)
        self.assertIn("with trade_input_tab:", source)
        self.assertIn("with trade_log_tab:", source)
        self.assertIn("with realized_tab:", source)

    def test_trade_type_toggle_precedes_product_search(self) -> None:
        """거래 입력 카드의 매수/매도 토글은 상품 검색보다 먼저 표시한다."""

        source = inspect.getsource(dashboard_app.trade_entry_page)

        self.assertLess(source.index("trade_type = st.radio("), source.index("상품명 또는 코드 검색"))
        self.assertLess(source.index("trade_type = st.radio("), source.index("build_trade_total_preview_html(trade_total)"))

    def test_dashboard_selected_trend_period_options_exclude_today(self) -> None:
        """대시보드 선택 종목 트렌드 기간에서는 당일 옵션을 숨긴다."""

        self.assertIn("today", dashboard_app.SELECTED_TREND_PERIOD_OPTIONS)
        self.assertNotIn("today", dashboard_app.DASHBOARD_SELECTED_TREND_PERIOD_OPTIONS)
        self.assertEqual(
            dashboard_app.DASHBOARD_SELECTED_TREND_PERIOD_OPTIONS,
            ("1mo", "3mo", "6mo", "1y"),
        )
        self.assertEqual(
            [dashboard_app.label_dashboard_period(value) for value in dashboard_app.DASHBOARD_SELECTED_TREND_PERIOD_OPTIONS],
            ["1M", "3M", "6M", "1Y"],
        )
        self.assertEqual(dashboard_app.label_period("1mo"), "1개월")

    def test_format_trade_log_cell_formats_numeric_values(self) -> None:
        """거래 기록 표 숫자 컬럼은 천 단위 구분으로 노출한다."""

        log = {
            "quantity": 12.5,
            "price": 10400,
            "total_amount": 130000,
            "cash_delta": -130000,
        }

        self.assertEqual(dashboard_app.format_trade_log_cell(log, "quantity", {}), "12.5")
        self.assertEqual(dashboard_app.format_trade_log_cell(log, "price", {}), "10,400")
        self.assertEqual(dashboard_app.format_trade_log_cell(log, "total_amount", {}), "130,000")
        self.assertEqual(dashboard_app.format_trade_log_cell(log, "cash_delta", {}), "-130,000")

    def test_trade_type_badge_styles_use_soft_wealth_palette(self) -> None:
        """거래 기록 배지는 Soft Wealth 민트/블루/레드 팔레트를 사용한다."""

        expected_styles = {
            "buy": {"background": "#EEF5F1", "border": "#BFE7D5", "color": "#16A46C", "label": "매수"},
            "sell": {"background": "#FDF0F3", "border": "#F7C7D1", "color": "#E85D75", "label": "매도"},
            "personal_deposit": {"background": "#EEF5F1", "border": "#BFE7D5", "color": "#16A46C", "label": "개인 입금"},
            "employer_deposit": {"background": "#EEF4FF", "border": "#C7D9FF", "color": "#4E7EDC", "label": "회사 납입금"},
            "withdraw": {"background": "#FDF0F3", "border": "#F7C7D1", "color": "#C94861", "label": "일반 출금"},
        }

        for trade_type, expected in expected_styles.items():
            with self.subTest(trade_type=trade_type):
                self.assertEqual(
                    dashboard_app.TRADE_TYPE_BADGE_STYLES[trade_type],
                    {
                        "background": expected["background"],
                        "border": expected["border"],
                        "color": expected["color"],
                    },
                )

                badge_html = dashboard_app.format_trade_log_cell({"trade_type": trade_type}, "trade_type", {})
                self.assertIn("<span", badge_html)
                self.assertIn(f"background:{expected['background']}", badge_html)
                self.assertIn(f"border:1px solid {expected['border']}", badge_html)
                self.assertIn(f"color:{expected['color']}", badge_html)
                self.assertIn(str(expected["label"]), badge_html)

    def test_realized_period_filter_uses_sell_date_boundaries(self) -> None:
        """실현손익 기간 필터는 매도일 기준으로 월/분기/연도 범위를 적용한다."""

        positions = [
            {"product_name": "이번 달", "sell_date": "2026-05-02", "profit_loss": 100},
            {"product_name": "이번 분기", "sell_date": "2026-04-10", "profit_loss": 200},
            {"product_name": "올해", "sell_date": "2026-01-15", "profit_loss": 300},
            {"product_name": "작년", "sell_date": "2025-12-30", "profit_loss": 400},
        ]
        today = date(2026, 5, 13)

        self.assertEqual(
            [item["product_name"] for item in dashboard_app.filter_realized_positions_by_period(positions, "month", today=today)],
            ["이번 달"],
        )
        self.assertEqual(
            [item["product_name"] for item in dashboard_app.filter_realized_positions_by_period(positions, "quarter", today=today)],
            ["이번 달", "이번 분기"],
        )
        self.assertEqual(
            [item["product_name"] for item in dashboard_app.filter_realized_positions_by_period(positions, "year", today=today)],
            ["이번 달", "이번 분기", "올해"],
        )
        self.assertEqual(len(dashboard_app.filter_realized_positions_by_period(positions, "all", today=today)), 4)

    def test_trade_log_filters_and_pagination_apply_user_controls(self) -> None:
        """거래 기록 필터는 검색/유형/자산/기간 조건을 함께 적용하고 페이지를 보정한다."""

        logs = [
            {"id": 1, "trade_date": "2026-05-11", "product_name": "삼성전자", "symbol": "005930", "trade_type": "buy", "asset_type": "risk"},
            {"id": 2, "trade_date": "2026-05-12", "product_name": "삼성전자", "symbol": "005930", "trade_type": "sell", "asset_type": "risk"},
            {"id": 3, "trade_date": "2026-02-01", "product_name": "회사 납입금", "symbol": "", "trade_type": "employer_deposit", "asset_type": "cash"},
            {"id": 4, "trade_date": "2025-12-31", "product_name": "채권 ETF", "symbol": "BOND", "trade_type": "buy", "asset_type": "safe"},
        ]

        filtered = dashboard_app.filter_trade_logs(
            logs,
            search="삼성",
            trade_type="sell",
            asset_type="risk",
            date_filter="month",
            today=date(2026, 5, 13),
        )
        page_items, current_page, total_pages, page_start, page_end = dashboard_app.paginate_trade_logs(
            filtered,
            page=3,
            page_size=1,
        )

        self.assertEqual([row["id"] for row in filtered], [2])
        self.assertEqual([row["id"] for row in page_items], [2])
        self.assertEqual((current_page, total_pages, page_start, page_end), (1, 1, 1, 1))

    def test_trade_log_premium_date_range_and_pagination_helpers(self) -> None:
        """프리미엄 거래 기록 UI는 날짜 범위 필터와 번호 페이지네이션을 사용한다."""

        logs = [
            {"id": 1, "trade_date": "2026-05-01"},
            {"id": 2, "trade_date": "2026-05-12"},
            {"id": 3, "trade_date": "2026-04-30"},
        ]

        self.assertEqual(dashboard_app.trade_log_default_date_range(logs), (date(2026, 4, 30), date(2026, 5, 12)))
        self.assertEqual(
            [row["id"] for row in dashboard_app.filter_trade_logs_by_date_range(logs, start_date=date(2026, 5, 1), end_date=date(2026, 5, 31))],
            [1, 2],
        )
        self.assertEqual(dashboard_app.trade_log_pagination_pages(5, 9), [3, 4, 5, 6, 7])
        self.assertEqual(dashboard_app.compact_trade_log_date_text({"trade_date": "2026-05-12"}), "05/12")

    def test_trade_log_editor_date_parser_accepts_iso_date_and_datetime(self) -> None:
        """거래 기록 편집 날짜는 ISO 날짜와 ISO datetime의 날짜 부분만 허용한다."""

        self.assertEqual(dashboard_app._parse_trade_date_for_editor("2026-05-14"), date(2026, 5, 14))
        self.assertEqual(dashboard_app._parse_trade_date_for_editor("2026-05-14T09:00:00+09:00"), date(2026, 5, 14))
        self.assertIsNone(dashboard_app._parse_trade_date_for_editor("2026/05/14"))

    def test_trade_log_date_value_raises_on_invalid_date(self) -> None:
        """잘못된 거래일은 오늘 날짜로 대체하지 않고 명시적으로 실패한다."""

        with self.assertRaisesRegex(ValueError, "지원하지 않는 거래일 형식"):
            dashboard_app._trade_log_date_value({"trade_date": "not-a-date"})

    def test_trade_log_list_helpers_do_not_hide_invalid_date_as_today(self) -> None:
        """목록 helper는 잘못된 날짜를 오늘로 위장하지 않고 원문 표시 또는 필터 제외한다."""

        logs = [
            {"id": 1, "trade_date": "2026-05-12"},
            {"id": 2, "trade_date": "not-a-date"},
        ]

        self.assertEqual(dashboard_app.trade_log_default_date_range(logs), (date(2026, 5, 12), date(2026, 5, 12)))
        self.assertEqual(
            [row["id"] for row in dashboard_app.filter_trade_logs_by_date_range(logs, start_date=date(2026, 5, 1), end_date=date(2026, 5, 31))],
            [1],
        )
        self.assertEqual(dashboard_app.compact_trade_log_date_text(logs[1]), "not-a-date")

    def test_trade_log_edit_dialog_blocks_invalid_trade_date(self) -> None:
        """수정 모달은 파싱할 수 없는 거래일을 오늘 날짜로 보여 주지 않고 저장 경로를 차단한다."""

        fake_st = types.SimpleNamespace(errors=[], captions=[])
        fake_st.error = fake_st.errors.append
        fake_st.caption = fake_st.captions.append
        original_st = dashboard_app.st
        dashboard_app.st = fake_st
        try:
            dashboard_app.render_trade_log_edit_dialog_body(
                {"id": 1},
                {"id": 9, "trade_date": "broken-date", "trade_type": "buy"},
                edit_state_key="editing",
            )
        finally:
            dashboard_app.st = original_st

        self.assertIn("지원하지 않는 거래일 형식입니다: broken-date", fake_st.errors)
        self.assertIn("거래일을 ISO 형식(YYYY-MM-DD)으로 정리한 뒤 다시 수정하세요.", fake_st.captions)

    def test_trade_log_edit_flow_uses_dialog_not_inline_editor(self) -> None:
        """거래 기록 수정은 행 아래 inline editor 대신 dialog 호출 경로를 사용한다."""

        edit_dialog_source = inspect.getsource(dashboard_app.render_trade_log_edit_dialog)
        edit_body_source = inspect.getsource(dashboard_app.render_trade_log_edit_dialog_body)
        trade_page_source = inspect.getsource(dashboard_app.trade_entry_page)

        self.assertIn('@st.dialog("거래 기록 수정", width="large")', edit_dialog_source)
        self.assertIn("render_trade_log_edit_dialog_body(account, selected_log, edit_state_key=edit_state_key)", edit_dialog_source)
        self.assertIn("render_trade_log_edit_dialog(account, selected_log, edit_state_key=edit_state_key)", trade_page_source)
        self.assertIn("st.form_submit_button(\"취소\"", edit_body_source)
        self.assertIn("st.form_submit_button(\"저장\"", edit_body_source)
        self.assertNotIn("render_trade_log_edit_form", trade_page_source)
        self.assertNotIn("trade-log-inline-editor-shell", trade_page_source)

    def test_trade_log_premium_cells_match_reference_markup(self) -> None:
        """거래 기록 행 셀은 premium_ui.html 스타일의 아이콘, 배지, 원화 표기를 만든다."""

        log = {
            "id": 42,
            "trade_date": "2026-05-12",
            "product_name": "KODEX AI반도체",
            "symbol": "KODEX",
            "trade_type": "buy",
            "quantity": 10,
            "price": 15200,
            "total_amount": 152000,
        }

        self.assertIn("trade-log-product-icon", dashboard_app.format_trade_log_premium_cell(log, "product_name", {}))
        self.assertIn("trade-log-badge--buy", dashboard_app.format_trade_log_premium_cell(log, "trade_type", {}))
        self.assertIn("₩15,200", dashboard_app.format_trade_log_premium_cell(log, "price", {}))
        self.assertIn("10주", dashboard_app.format_trade_log_premium_cell(log, "quantity", {}))

    def test_won_format_uses_half_up_rounding(self) -> None:
        """원화 표시는 소수점 이하를 원 단위로 일반 반올림한다."""

        self.assertEqual(dashboard_app.format_won(1000.5), "₩1,001")
        self.assertEqual(dashboard_app.dashboard_format_won(2000.5), "₩2,001")
        self.assertEqual(dashboard_app.format_trade_log_cell({"price": 15200.5}, "price", {}), "15,201")

    def test_trade_log_actions_use_compact_icon_buttons(self) -> None:
        """거래 기록 액션은 행 선택과 수정 버튼을 제공한다."""

        source = inspect.getsource(dashboard_app.trade_entry_page)

        self.assertIn('st.checkbox(', source)
        self.assertIn('"선택"', source)
        self.assertIn('help="선택 삭제 대상"', source)
        self.assertIn('st.button("수정"', source)
        self.assertIn('help="거래 기록 수정"', source)
        self.assertIn('"선택 삭제"', source)
        self.assertIn('help="선택한 거래 기록 삭제"', source)

    def test_trade_log_bulk_delete_flow_uses_dialog_and_existing_delete_path(self) -> None:
        """선택 삭제는 확인 dialog에서 기존 삭제/재계산 경로를 사용한다."""

        page_source = inspect.getsource(dashboard_app.trade_entry_page)
        dialog_source = inspect.getsource(dashboard_app.render_trade_log_bulk_delete_dialog)

        self.assertIn('@st.dialog("선택 거래 기록 삭제 확인")', dialog_source)
        self.assertIn("render_trade_log_bulk_delete_dialog(", page_source)
        self.assertIn("selected_logs_for_delete", page_source)
        self.assertIn("build_trade_log_bulk_delete_plan(", page_source)
        self.assertIn("연관 매도", dialog_source)
        self.assertIn("delete_trade_log(int(account_id), int(log_id))", dialog_source)
        self.assertIn("affected_start_date=earliest_trade_log_date(selected_logs)", dialog_source)

    def test_trade_log_mutations_rebuild_valuation_from_affected_date(self) -> None:
        """거래 변경 후 평가액 기록 재계산은 영향 시작일 이후로 제한한다."""

        page_source = inspect.getsource(dashboard_app.trade_entry_page)
        edit_source = inspect.getsource(dashboard_app.render_trade_log_edit_dialog_body)
        bulk_delete_source = inspect.getsource(dashboard_app.render_trade_log_bulk_delete_dialog)
        single_delete_source = inspect.getsource(dashboard_app.render_trade_log_delete_dialog)
        valuation_source = inspect.getsource(dashboard_app.valuation_page)

        self.assertIn("affected_start_date=trade_date", page_source)
        self.assertIn("affected_start_date=min(selected_trade_date, edit_trade_date)", edit_source)
        self.assertIn("affected_start_date=earliest_trade_log_date(selected_logs)", bulk_delete_source)
        self.assertIn("affected_start_date=earliest_trade_log_date([selected_log])", single_delete_source)
        self.assertIn('rebuild_valuation_snapshots_for_account(account_id, "manual_rebuild")', valuation_source)

    def test_trade_log_import_parses_export_csv_format(self) -> None:
        """CSV 불러오기는 내보내기와 같은 컬럼을 저장 가능한 행으로 변환한다."""

        frame = pd.DataFrame(
            [
                {
                    "거래일": "2026-05-12",
                    "종목명": "KODEX AI반도체",
                    "코드": "KODEX",
                    "유형": "매수",
                    "자산군": "위험자산",
                    "수량": "10",
                    "단가": "15,200",
                    "총액": "152,000",
                    "실현수익률": "-",
                    "메모": "신규",
                },
                {
                    "거래일": "2026-05-13",
                    "종목명": "회사 납입금",
                    "코드": "",
                    "유형": "회사 납입금",
                    "자산군": "현금",
                    "수량": "0",
                    "단가": "0",
                    "총액": "1,000,000",
                    "실현수익률": "-",
                    "메모": "월 납입",
                },
            ]
        )

        rows, errors = dashboard_app.parse_trade_log_import_frame(frame)

        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["trade_type"], "buy")
        self.assertEqual(rows[0]["asset_type"], "risk")
        self.assertEqual(rows[0]["price"], 15200)
        self.assertEqual(rows[1]["trade_type"], "employer_deposit")
        self.assertEqual(rows[1]["asset_type"], "cash")
        self.assertEqual(rows[1]["total_amount"], 1_000_000)

    def test_trade_log_import_detects_duplicates_and_replays_export_order(self) -> None:
        """CSV import는 기존/파일 내부 중복을 표시하고 최신순 export를 과거순으로 저장한다."""

        rows = [
            {
                "source_row": 2,
                "trade_date": "2026-05-12",
                "product_name": "삼성전자",
                "symbol": "005930",
                "trade_type": "sell",
                "asset_type": "risk",
                "quantity": 1,
                "price": 80000,
                "total_amount": 80000,
                "notes": "",
            },
            {
                "source_row": 3,
                "trade_date": "2026-05-12",
                "product_name": "삼성전자",
                "symbol": "005930",
                "trade_type": "buy",
                "asset_type": "risk",
                "quantity": 1,
                "price": 70000,
                "total_amount": 70000,
                "notes": "",
            },
            {
                "source_row": 4,
                "trade_date": "2026-05-12",
                "product_name": "삼성전자",
                "symbol": "005930",
                "trade_type": "buy",
                "asset_type": "risk",
                "quantity": 1,
                "price": 70000,
                "total_amount": 70000,
                "notes": "",
            },
        ]

        marked = dashboard_app.mark_trade_log_import_duplicates(rows, existing_logs=[])
        sorted_rows = sorted(rows[:2], key=dashboard_app.trade_log_import_sort_key)
        preview = dashboard_app.build_trade_log_import_preview_frame(marked)

        self.assertFalse(marked[1]["is_duplicate"])
        self.assertTrue(marked[2]["is_duplicate"])
        self.assertEqual([row["trade_type"] for row in sorted_rows], ["buy", "sell"])
        self.assertIn("중복 제외 예정", set(preview["상태"]))

    def test_trade_log_import_requires_export_columns(self) -> None:
        """CSV import는 내보내기 양식의 필수 컬럼 누락을 오류로 안내한다."""

        rows, errors = dashboard_app.parse_trade_log_import_frame(pd.DataFrame([{"거래일": "2026-05-12"}]))

        self.assertEqual(rows, [])
        self.assertIn("필수 컬럼 누락", errors[0]["error"])

    def test_trade_page_source_includes_trade_log_csv_import(self) -> None:
        """거래 기록 탭은 CSV 불러오기 업로드와 저장 흐름을 제공한다."""

        page_source = inspect.getsource(dashboard_app.trade_entry_page)
        import_source = inspect.getsource(dashboard_app.render_trade_log_import_panel)
        action_source = inspect.getsource(dashboard_app.render_trade_log_import_action)

        self.assertIn("header_cols = st.columns((1, 0.34, 0.34)", page_source)
        self.assertIn("render_trade_log_import_action(account, visible_logs)", page_source)
        self.assertNotIn('with st.expander("↑ CSV 불러오기", expanded=False):', page_source)
        self.assertIn("↑ CSV 불러오기", action_source)
        self.assertIn("popover", action_source)
        self.assertIn("render_trade_log_import_panel(account, existing_logs)", action_source)
        self.assertIn("st.file_uploader", import_source)
        self.assertIn("trade_logs_import_template.csv", import_source)
        self.assertIn("save_trade_log_import_rows(account_id, rows_to_save)", import_source)

    def test_valuation_snapshot_export_and_import_allows_manual_edits(self) -> None:
        """평가액 기록 CSV는 저장 후 편집값을 다시 스냅샷 payload로 변환한다."""

        export_frame = dashboard_app.build_valuation_snapshot_export_frame(
            [
                {
                    "valuation_date": "2026-05-14",
                    "company_principal": 800000,
                    "invested_cost": 600000,
                    "implied_cash": 200000,
                    "actual_cash_balance": None,
                    "cash_value": 200000,
                    "cash_source": "implied",
                    "holdings_market_value": 650000,
                    "valuation_amount": 850000,
                    "profit_loss": 50000,
                    "profit_rate": 6.25,
                    "over_invested_amount": 0,
                    "missing_price_symbols": ["AAA"],
                    "calculation_reason": "manual_rebuild",
                }
            ]
        ).astype(object)
        export_frame.loc[0, "보유 평가액"] = "900,000"
        export_frame.loc[0, "손익"] = ""
        export_frame.loc[0, "수익률"] = ""
        export_frame.loc[0, "가격 fallback"] = "AAA, BBB"

        rows, errors = dashboard_app.parse_valuation_snapshot_import_frame(export_frame, account_id=24)

        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["account_id"], 24)
        self.assertEqual(rows[0]["valuation_date"], "2026-05-14")
        self.assertEqual(rows[0]["valuation_amount"], 900000)
        self.assertEqual(rows[0]["profit_loss"], 100000)
        self.assertEqual(rows[0]["profit_rate"], 12.5)
        self.assertEqual(rows[0]["missing_price_symbols"], ["AAA", "BBB"])

    def test_valuation_snapshot_import_computes_missing_derived_values(self) -> None:
        """CSV 불러오기에서 비어 있는 파생값은 저장 전에 계산한다."""

        frame = pd.DataFrame(
            [
                {
                    "기준일": "2026-05-15",
                    "입금 원금": "800,000",
                    "잔여 매입원가": "600,000",
                    "현금간주액": "",
                    "실제 보유현금": "",
                    "현금값": "",
                    "현금 기준": "간주",
                    "상품 평가액": "650,000",
                    "보유 평가액": "",
                    "손익": "",
                    "수익률": "",
                    "원금초과 매입": "",
                    "가격 fallback": "",
                    "계산 사유": "",
                }
            ]
        )

        rows, errors = dashboard_app.parse_valuation_snapshot_import_frame(frame, account_id=24)

        self.assertEqual(errors, [])
        self.assertEqual(rows[0]["implied_cash"], 200000)
        self.assertEqual(rows[0]["cash_value"], 200000)
        self.assertEqual(rows[0]["valuation_amount"], 850000)
        self.assertEqual(rows[0]["profit_loss"], 50000)
        self.assertEqual(rows[0]["profit_rate"], 6.25)
        self.assertEqual(rows[0]["calculation_reason"], "manual_edit")

    def test_valuation_page_source_includes_csv_editor(self) -> None:
        """평가액 기록 페이지는 CSV 저장/불러오기와 수정 저장 UI를 제공한다."""

        page_source = inspect.getsource(dashboard_app.valuation_page)
        editor_source = inspect.getsource(dashboard_app.render_valuation_snapshot_csv_editor)

        self.assertIn("render_valuation_snapshot_csv_editor(account_id, snapshots)", page_source)
        self.assertIn("↓ CSV 저장", editor_source)
        self.assertIn("valuation_snapshots_import_template.csv", editor_source)
        self.assertIn("st.file_uploader", editor_source)
        self.assertIn("st.data_editor", editor_source)
        self.assertIn("record_valuation_snapshots(account_id, parsed_rows)", editor_source)

    def test_trade_log_realized_profit_rate_cell_uses_sell_log_lookup(self) -> None:
        """거래 기록의 실현수익률 컬럼은 매도 거래 ID lookup으로 표시한다."""

        sell_log = {"id": 42, "trade_type": "sell"}
        buy_log = {"id": 41, "trade_type": "buy"}
        context = {"realized_profit_rate_by_sell_log_id": {42: 8.125}}

        self.assertEqual(dashboard_app.format_trade_log_cell(sell_log, "realized_profit_rate", context), "+8.12%")
        self.assertEqual(dashboard_app.format_trade_log_cell(buy_log, "realized_profit_rate", context), "-")
        self.assertIn("trade-log-profit-rate--positive", dashboard_app.trade_log_realized_rate_html("+8.12%"))
        self.assertIn("trade-log-profit-rate--empty", dashboard_app.trade_log_realized_rate_html("-"))

    def test_product_search_option_label_builds_two_line_summary(self) -> None:
        """자동완성 후보 라벨은 이름과 부가 정보를 두 줄로 묶는다."""

        label = dashboard_app.product_search_option_label(
            {
                "name": "삼성전자",
                "code": "005930",
                "exchange": "KRX",
                "source": "Naver",
            }
        )

        self.assertIn("삼성전자", label)
        self.assertIn("\n", label)
        self.assertIn("005930", label)
        self.assertIn("국내", label)
        self.assertIn("Naver", label)


class HoldingsTableDisplayTests(unittest.TestCase):
    """현재 보유 종목 표 표시 포맷과 컬러 스타일을 검증한다."""

    def test_build_holdings_table_display_formats_price_updated_at_with_seconds(self) -> None:
        """가격 갱신 시각은 초 단위까지 보이도록 포맷한다."""

        frame = pd.DataFrame(
            [
                {
                    "product_name": "삼성전자",
                    "symbol": "005930",
                    "asset_type": "risk",
                    "quantity": 10,
                    "avg_cost": 70000,
                    "current_price": 71200,
                    "cost_basis": 700000,
                    "current_value": 712000,
                    "profit_loss": 12000,
                    "profit_rate": 1.7142857,
                    "price_updated_at": "2026-05-11T09:15:27+09:00",
                }
            ]
        )

        display = dashboard_app.build_holdings_table_display(frame)

        self.assertEqual(display.iloc[0]["가격갱신"], "2026-05-11 09:15:27")
        self.assertEqual(display.iloc[0]["손익"], "12,000")
        self.assertEqual(display.iloc[0]["수익률(%)"], "+1.71")

    def test_style_holdings_table_colors_profit_and_rate_cells(self) -> None:
        """손익과 수익률 셀은 부호에 따라 색상을 다르게 적용한다."""

        display = pd.DataFrame(
            [
                {"손익": "12,000", "수익률(%)": "+1.71"},
                {"손익": "-8,000", "수익률(%)": "-3.25"},
                {"손익": "0", "수익률(%)": "+0.00"},
            ]
        )

        styled = dashboard_app.style_holdings_table(display)
        html = styled.to_html()

        self.assertIn(dashboard_app.FEARGREED_UP_COLOR, html)
        self.assertIn(dashboard_app.FEARGREED_DOWN_COLOR, html)
        self.assertIn(dashboard_app.FEARGREED_MUTED_TEXT_COLOR, html)

    def test_style_holdings_table_parses_comma_separated_profit_loss(self) -> None:
        """손익 문자열에 천 단위 콤마가 있어도 부호에 맞는 색상을 적용한다."""

        display = pd.DataFrame([{"손익": "12,000", "수익률(%)": "-3.25"}])

        styled = dashboard_app.style_holdings_table(display)
        html = styled.to_html()

        self.assertIn(dashboard_app.FEARGREED_UP_COLOR, html)
        self.assertIn(dashboard_app.FEARGREED_DOWN_COLOR, html)

    def test_build_holdings_table_html_uses_custom_theme_classes(self) -> None:
        """현재 보유 종목 표는 커스텀 HTML 테이블 테마 클래스를 사용한다."""

        display = pd.DataFrame(
            [
                {
                    "상품명": "TIGER 미국S&P500",
                    "코드": "360750",
                    "자산군": "위험자산",
                    "수량": "27",
                    "평단가": "128,259",
                    "현재가": "177,500",
                    "원금": "3,463,000",
                    "평가금액": "4,792,500",
                    "손익": "1,329,500",
                    "수익률(%)": "+38.39",
                    "가격갱신": "2026-05-11 00:00:00",
                },
                {
                    "상품명": "KOSEF 국고채10년",
                    "코드": "148070",
                    "자산군": "안전자산",
                    "수량": "17",
                    "평단가": "112,000",
                    "현재가": "107,000",
                    "원금": "1,904,000",
                    "평가금액": "1,819,000",
                    "손익": "-85,000",
                    "수익률(%)": "-4.46",
                    "가격갱신": "2026-05-11 00:00:00",
                },
            ]
        )

        html = dashboard_app.build_holdings_table_html(display, max_height=380)

        self.assertIn("holdings-table-shell", html)
        self.assertIn("holdings-table__value--positive", html)
        self.assertIn("holdings-table__value--negative", html)
        self.assertIn("max-height:380px", html)

    def test_build_holdings_mobile_cards_html_uses_required_fields_and_tone_classes(self) -> None:
        """모바일 보유 종목 카드는 핵심 필드와 기존 손익 tone class를 사용한다."""

        display = pd.DataFrame(
            [
                {
                    "상품명": "TIGER 미국S&P500",
                    "코드": "360750",
                    "자산군": "위험자산",
                    "수량": "27",
                    "평단가": "128,259",
                    "현재가": "177,500",
                    "원금": "3,463,000",
                    "평가금액": "4,792,500",
                    "손익": "1,329,500",
                    "수익률(%)": "+38.39",
                    "가격갱신": "2026-05-11 00:00:00",
                },
                {
                    "상품명": "KOSEF <국고채10년>",
                    "코드": "148070",
                    "자산군": "안전자산",
                    "수량": "17",
                    "평단가": "112,000",
                    "현재가": "107,000",
                    "원금": "1,904,000",
                    "평가금액": "1,819,000",
                    "손익": "-85,000",
                    "수익률(%)": "-4.46",
                    "가격갱신": "2026-05-11 00:00:00",
                },
            ]
        )

        html = dashboard_app.build_holdings_mobile_cards_html(display)

        self.assertIn("holdings-mobile-card-list", html)
        self.assertIn('style="display:none;"', html)
        self.assertIn("TIGER 미국S&amp;P500", html)
        self.assertIn("KOSEF &lt;국고채10년&gt;", html)
        for text in ("360750", "위험자산", "4,792,500", "1,329,500", "+38.39%", "27", "177,500", "128,259"):
            self.assertIn(text, html)
        self.assertIn("holdings-table__value--positive", html)
        self.assertIn("holdings-table__value--negative", html)
        self.assertNotIn("가격갱신", html)
        self.assertNotIn("원금", html)

    def test_build_data_export_table_html_reuses_theme_for_holdings(self) -> None:
        """데이터 페이지 보유 종목 미리보기는 대시보드 테이블 테마를 재사용한다."""

        holdings = [
            {
                "product_name": "삼성전자",
                "symbol": "005930",
                "asset_type": "risk",
                "quantity": 10,
                "avg_cost": 70000,
                "current_price": 71200,
                "price_updated_at": "2026-05-11T09:15:27+09:00",
            }
        ]

        html = dashboard_app.build_data_export_table_html(
            "holdings",
            pd.DataFrame(holdings),
            current_holdings=holdings,
            max_height=220,
        )

        self.assertIn("holdings-table-shell", html)
        self.assertIn("holdings-table__value--positive", html)
        self.assertIn("삼성전자", html)
        self.assertIn("max-height:220px", html)

    def test_build_data_export_table_html_reuses_theme_for_trade_logs(self) -> None:
        """CSV export 거래 기록 미리보기는 배지와 테이블 테마를 함께 사용한다."""

        frame = pd.DataFrame(
            [
                {
                    "trade_date": "2026-05-11",
                    "product_name": "개인 입금",
                    "symbol": "",
                    "trade_type": "personal_deposit",
                    "asset_type": "cash",
                    "quantity": 0,
                    "price": 0,
                    "total_amount": 1000000,
                    "notes": "월 납입",
                }
            ]
        )

        html = dashboard_app.build_data_export_table_html("trade_logs", frame, max_height=220)

        self.assertIn("holdings-table-shell", html)
        self.assertIn("개인 입금", html)
        self.assertIn("background:#EEF5F1", html)
        self.assertIn("holdings-table__cell--numeric", html)
        self.assertIn("max-height:220px", html)

    def test_build_holdings_mix_bar_html_includes_cash_inside_safe_ratio(self) -> None:
        """현재 보유 종목 박스 비중 막대는 보유현금을 안전자산에 합산한다."""

        summary = {
            "cash": 200000,
            "allocation": {
                "risk": 500000,
                "safe": 300000,
                "cash": 200000,
            },
        }

        html = dashboard_app.build_holdings_mix_bar_html(summary)

        self.assertIn("위험자산", html)
        self.assertIn("안전자산", html)
        self.assertIn("50.0%", html)
        self.assertIn("50.0%", html)
        self.assertIn(dashboard_app.FEARGREED_DOWN_COLOR, html)
        self.assertIn(dashboard_app.FEARGREED_UP_COLOR, html)
        self.assertIn("보유현금 ₩200,000 포함", html)
        self.assertNotIn(">보유현금<", html)


class DashboardSummaryToneTests(unittest.TestCase):
    """원금 대비 손익 카드 강조 톤을 검증한다."""

    def test_dashboard_return_metric_tone_tracks_sign(self) -> None:
        """평가손익/수익률 요약 카드는 값 부호에 따라 초록/빨강 톤을 사용한다."""

        self.assertEqual(dashboard_app.dashboard_return_metric_tone(150000), "positive")
        self.assertEqual(dashboard_app.dashboard_return_metric_tone(-2.35), "negative")
        self.assertEqual(dashboard_app.dashboard_return_metric_tone(0), "accent")


class DashboardSelectionPayloadTests(unittest.TestCase):
    """선택 종목 트렌드와 연결되는 selection payload 해석을 검증한다."""

    def test_extract_dashboard_chart_symbol_reads_nested_selection_points(self) -> None:
        """컴포넌트 state 내부 selection payload에서도 종목명을 읽는다."""

        payload = {
            "selection": {
                "points": [
                    {
                        "name": "삼성전자",
                    }
                ]
            }
        }

        result = dashboard_app.extract_dashboard_chart_symbol(payload)

        self.assertEqual(result, "삼성전자")

    def test_resolve_dashboard_selected_symbol_supports_nested_selection_payload(self) -> None:
        """중첩 selection payload를 현재 보유 심볼로 해석한다."""

        holdings = [
            {"symbol": "005930", "product_name": "삼성전자"},
            {"symbol": "AAPL", "product_name": "애플"},
        ]
        payload = {
            "selection": {
                "points": [
                    {
                        "name": "애플",
                    }
                ]
            }
        }

        result = dashboard_app.resolve_dashboard_selected_symbol(holdings, payload)

        self.assertEqual(result, "AAPL")


class ReturnsChartHtmlTests(unittest.TestCase):
    """returns_chart.html 기반 보유 종목 수익률 HTML 렌더러를 검증한다."""

    def test_build_returns_chart_html_matches_reference_structure(self) -> None:
        """보유 종목 수익률 차트는 목업의 카드, 필터, 요약, 바 리스트 구조를 출력한다."""

        frame = pd.DataFrame(
            [
                {
                    "product_name": "HANARO 원자재iS.",
                    "symbol": "411060",
                    "selection_symbol": "411060",
                    "asset_type": "risk",
                    "quantity": 10,
                    "current_value": 1500000,
                    "profit_rate": 234.67,
                    "price_updated_at": "2026-05-13T15:30:00",
                },
                {
                    "product_name": "TIGER 미국S&P500",
                    "symbol": "360750",
                    "selection_symbol": "360750",
                    "asset_type": "safe",
                    "quantity": 20,
                    "current_value": 900000,
                    "profit_rate": -78.48,
                    "price_updated_at": "2026-05-13T15:30:00",
                },
            ]
        )

        html = dashboard_app.build_returns_chart_html(frame, selected_symbol="360750")

        self.assertIn('class="returns-chart"', html)
        self.assertIn("보유 종목 수익률", html)
        self.assertIn("현재 보유 상위 종목의 수익률 흐름을 비교합니다", html)
        self.assertIn("returns-chart__filter-pill", html)
        self.assertIn('data-filter="profit"', html)
        self.assertIn('data-filter="loss"', html)
        self.assertIn("returns-chart__sort-pill", html)
        self.assertIn('data-sort="rate"', html)
        self.assertIn('data-sort="amount"', html)
        self.assertIn("renderReturnsChart", html)
        self.assertIn("returnsChartBarGeometry", html)
        self.assertIn("Math.min(width, 100 - left)", html)
        self.assertIn("최고 수익", html)
        self.assertIn("+234.67%", html)
        self.assertIn("최대 손실", html)
        self.assertIn("-78.48%", html)
        self.assertIn("수익 종목", html)
        self.assertIn("1 / 2", html)
        self.assertIn("returns-chart__divider", html)
        self.assertIn("returns-chart__bar-outer--pos", html)
        self.assertIn("returns-chart__bar-outer--neg", html)
        self.assertIn("returns-chart__bar-item--selected", html)
        self.assertIn("⟳ 기준일: 2026-05-13", html)

    def test_dashboard_uses_returns_chart_html_renderer(self) -> None:
        """대시보드 보유 종목 수익률 패널은 ECharts 대신 HTML 렌더러를 사용한다."""

        source = inspect.getsource(dashboard_app.dashboard_page)

        self.assertIn("render_returns_chart(overview_frame", source)
        self.assertIn("components.html(", inspect.getsource(dashboard_app.render_returns_chart))
        self.assertNotIn("holdings-profit-bar", source)

    def test_returns_chart_component_height_is_bounded(self) -> None:
        """보유 종목 수익률 컴포넌트 높이는 행 수에 맞추되 과도하게 커지지 않는다."""

        self.assertEqual(dashboard_app.returns_chart_component_height(0), dashboard_app.RETURNS_CHART_MIN_HEIGHT)
        self.assertGreater(dashboard_app.returns_chart_component_height(5, 1), dashboard_app.RETURNS_CHART_MIN_HEIGHT)
        self.assertGreaterEqual(dashboard_app.returns_chart_component_height(4, 1), 720)
        self.assertEqual(dashboard_app.returns_chart_component_height(50), dashboard_app.RETURNS_CHART_MAX_HEIGHT)


class HoldingsBarLabelTests(unittest.TestCase):
    """보유 종목 수익률 막대 라벨 표시를 검증한다."""

    def test_holdings_bar_options_shows_profit_rate_labels_for_all_bars(self) -> None:
        """모든 막대가 상단/하단에 수익률 라벨을 가진다."""

        frame = pd.DataFrame(
            [
                {
                    "product_name": "애플",
                    "symbol": "AAPL",
                    "selection_symbol": "AAPL",
                    "current_value": 1500000,
                    "profit_rate": 12.34,
                },
                {
                    "product_name": "테슬라",
                    "symbol": "TSLA",
                    "selection_symbol": "TSLA",
                    "current_value": 900000,
                    "profit_rate": -5.67,
                },
            ]
        )

        options = dashboard_app.holdings_bar_options(frame, selected_symbol="AAPL")

        self.assertIsNotNone(options)
        assert options is not None
        series_data = options["series"][0]["data"]
        self.assertEqual([item["label"]["show"] for item in series_data], [True, True])
        self.assertEqual(series_data[0]["label"]["formatter"], "+12.34%")
        self.assertEqual(series_data[1]["label"]["formatter"], "-5.67%")
        self.assertEqual(series_data[0]["itemStyle"]["borderRadius"], [10, 10, 0, 0])
        self.assertEqual(series_data[1]["itemStyle"]["borderRadius"], [0, 0, 10, 10])

    def test_holdings_bar_options_keeps_positive_only_axis_above_zero(self) -> None:
        """모든 종목 수익률이 플러스면 Y축 최소값은 0 아래로 내려가지 않는다."""

        frame = pd.DataFrame(
            [
                {
                    "product_name": "고배당 ETF",
                    "symbol": "ETF1",
                    "selection_symbol": "ETF1",
                    "current_value": 1500000,
                    "profit_rate": 69.75,
                },
                {
                    "product_name": "월배당 ETF",
                    "symbol": "ETF2",
                    "selection_symbol": "ETF2",
                    "current_value": 900000,
                    "profit_rate": 8.51,
                },
                {
                    "product_name": "채권 혼합",
                    "symbol": "ETF3",
                    "selection_symbol": "ETF3",
                    "current_value": 600000,
                    "profit_rate": 3.11,
                },
            ]
        )

        options = dashboard_app.holdings_bar_options(frame)

        self.assertIsNotNone(options)
        assert options is not None
        self.assertEqual(options["yAxis"]["min"], 0.0)
        self.assertNotIn("max", options["yAxis"])

    def test_holdings_bar_options_uses_auto_bounds_for_mixed_rates(self) -> None:
        """양수/음수가 섞이면 ECharts가 자연스러운 축 범위를 자동 계산한다."""

        frame = pd.DataFrame(
            [
                {
                    "product_name": "성장 ETF",
                    "symbol": "ETF1",
                    "selection_symbol": "ETF1",
                    "current_value": 1500000,
                    "profit_rate": 38.39,
                },
                {
                    "product_name": "방어 ETF",
                    "symbol": "ETF2",
                    "selection_symbol": "ETF2",
                    "current_value": 900000,
                    "profit_rate": -7.00,
                },
                {
                    "product_name": "혼합 ETF",
                    "symbol": "ETF3",
                    "selection_symbol": "ETF3",
                    "current_value": 600000,
                    "profit_rate": -4.46,
                },
            ]
        )

        options = dashboard_app.holdings_bar_options(frame)

        self.assertIsNotNone(options)
        assert options is not None
        self.assertNotIn("min", options["yAxis"])
        self.assertNotIn("max", options["yAxis"])


class RealizedProfitBarTests(unittest.TestCase):
    """실현손익 막대차트 옵션을 검증한다."""

    def test_realized_profit_bar_options_match_dashboard_holdings_style(self) -> None:
        """실현손익 차트도 양수/음수에 따라 같은 라운드/라벨 규칙을 사용한다."""

        frame = pd.DataFrame(
            [
                {
                    "product_name": "미국 ETF",
                    "profit_loss": 325000,
                    "sell_amount": 1825000,
                    "profit_rate": 18.45,
                },
                {
                    "product_name": "채권 ETF",
                    "profit_loss": -85000,
                    "sell_amount": 1315000,
                    "profit_rate": -4.22,
                },
            ]
        )

        options = dashboard_app.realized_profit_bar_options(frame)

        self.assertIsNotNone(options)
        assert options is not None
        series_data = options["series"][0]["data"]
        self.assertEqual(series_data[0]["label"]["formatter"], "₩325,000")
        self.assertEqual(series_data[1]["label"]["formatter"], "₩-85,000")
        self.assertEqual(series_data[0]["itemStyle"]["borderRadius"], [10, 10, 0, 0])
        self.assertEqual(series_data[1]["itemStyle"]["borderRadius"], [0, 0, 10, 10])
        self.assertEqual(options["yAxis"]["name"], "실현손익")

    def test_realized_monthly_profit_frame_and_options_group_by_sell_month(self) -> None:
        """월별 실현손익 차트는 매도월 기준으로 손익과 포지션 수를 집계한다."""

        positions = [
            {"sell_date": "2026-05-01", "profit_loss": 100000},
            {"sell_date": "2026-05-12", "profit_loss": -30000},
            {"sell_date": "2026-04-20", "profit_loss": 50000},
        ]

        frame = dashboard_app.realized_monthly_profit_frame(positions)
        options = dashboard_app.realized_monthly_profit_bar_options(frame)

        self.assertEqual(frame["month"].tolist(), ["2026-04", "2026-05"])
        self.assertEqual(frame["profit_loss"].tolist(), [50000.0, 70000.0])
        self.assertEqual(frame["sold_count"].tolist(), [1, 2])
        self.assertIsNotNone(options)
        assert options is not None
        self.assertEqual(options["yAxis"]["name"], "월별 실현손익")
        self.assertEqual(options["series"][0]["data"][1]["value"], 70000.0)

    def test_realized_contribution_html_marks_positive_and_negative_rows(self) -> None:
        """상품별 기여 HTML은 수익/손실 tone과 폭 스타일을 포함한다."""

        html = dashboard_app.build_realized_contribution_html(
            [
                {"product_name": "수익 ETF", "profit_loss": 200000, "profit_rate": 10.0},
                {"product_name": "손실 ETF", "profit_loss": -50000, "profit_rate": -4.0},
            ]
        )

        self.assertIn("상품별 손익 기여 Top 5", html)
        self.assertIn("realized-contribution__bar--positive", html)
        self.assertIn("realized-contribution__bar--negative", html)
        self.assertIn("수익 ETF", html)
        self.assertIn("손실 ETF", html)


class AllocationTreemapVisualMapTests(unittest.TestCase):
    """자산 배분 트리맵 수익률 바 기준과 범위 밖 표시를 검증한다."""

    def test_allocation_treemap_uses_current_profit_rate_bounds(self) -> None:
        """수익률 바 최대/최소는 현재 보유 종목 실제 수익률을 따른다."""

        holdings = [
            {
                "product_name": "고수익 ETF",
                "symbol": "HIGH",
                "asset_type": "risk",
                "quantity": 1,
                "avg_cost": 100,
                "current_price": 250,
            },
            {
                "product_name": "안전자산",
                "symbol": "LOW",
                "asset_type": "safe",
                "quantity": 1,
                "avg_cost": 100,
                "current_price": 90,
            },
        ]
        summary = {
            "allocation": {
                "risk": 250,
                "safe": 90,
                "cash": 0,
            },
            "cash": 0,
        }

        original = dashboard_app.fetch_intraday_price_snapshot
        dashboard_app.fetch_intraday_price_snapshot = lambda symbol, interval="5m": {}
        try:
            options = dashboard_app.allocation_treemap_options(summary, holdings)
        finally:
            dashboard_app.fetch_intraday_price_snapshot = original

        self.assertIsNotNone(options)
        assert options is not None
        self.assertEqual(options["visualMap"]["min"], -10.0)
        self.assertEqual(options["visualMap"]["max"], 150.0)
        self.assertEqual(options["visualMap"]["dimension"], 1)
        self.assertEqual(options["series"][0]["visualDimension"], 1)
        self.assertEqual(options["visualMap"]["inRange"]["color"], dashboard_app.FEARGREED_TREEMAP_PALETTE)
        self.assertEqual(options["backgroundColor"], dashboard_app.TREEMAP_CANVAS_BG_COLOR)
        self.assertEqual(options["title"]["textStyle"]["color"], dashboard_app.TREEMAP_TITLE_TEXT_COLOR)

    def test_allocation_treemap_out_of_range_tiles_are_transparent(self) -> None:
        """선택 범위 밖 타일은 흐리게가 아니라 투명 fill로 처리한다."""

        holdings = [
            {
                "product_name": "고수익 ETF",
                "symbol": "HIGH",
                "asset_type": "risk",
                "quantity": 1,
                "avg_cost": 100,
                "current_price": 250,
            }
        ]
        summary = {
            "allocation": {
                "risk": 250,
                "safe": 0,
                "cash": 0,
            },
            "cash": 0,
        }

        original = dashboard_app.fetch_intraday_price_snapshot
        dashboard_app.fetch_intraday_price_snapshot = lambda symbol, interval="5m": {}
        try:
            options = dashboard_app.allocation_treemap_options(summary, holdings)
        finally:
            dashboard_app.fetch_intraday_price_snapshot = original

        self.assertIsNotNone(options)
        assert options is not None
        self.assertEqual(options["visualMap"]["outOfRange"]["colorAlpha"], 0.0)

    def test_allocation_treemap_uses_zero_gap_and_fixed_upper_labels(self) -> None:
        """트리맵 경계는 gap 없이 1px border와 고정 높이 upperLabel로 정렬한다."""

        holdings = [
            {
                "product_name": "고수익 ETF",
                "symbol": "HIGH",
                "asset_type": "risk",
                "quantity": 1,
                "avg_cost": 100,
                "current_price": 250,
            },
            {
                "product_name": "안전자산",
                "symbol": "LOW",
                "asset_type": "safe",
                "quantity": 1,
                "avg_cost": 100,
                "current_price": 90,
            },
        ]
        summary = {
            "allocation": {
                "risk": 250,
                "safe": 90,
                "cash": 0,
            },
            "cash": 0,
        }

        original = dashboard_app.fetch_intraday_price_snapshot
        dashboard_app.fetch_intraday_price_snapshot = lambda symbol, interval="5m": {}
        try:
            options = dashboard_app.allocation_treemap_options(summary, holdings)
        finally:
            dashboard_app.fetch_intraday_price_snapshot = original

        self.assertIsNotNone(options)
        assert options is not None
        series = options["series"][0]

        self.assertEqual(series["upperLabel"]["height"], dashboard_app.TREEMAP_UPPER_LABEL_HEIGHT)
        self.assertEqual(series["upperLabel"]["fontSize"], dashboard_app.TREEMAP_UPPER_LABEL_FONT_SIZE)
        self.assertEqual(series["itemStyle"]["gapWidth"], dashboard_app.TREEMAP_NODE_GAP_WIDTH)
        self.assertEqual(series["itemStyle"]["borderWidth"], dashboard_app.TREEMAP_NODE_BORDER_WIDTH)

        for level in series["levels"]:
            item_style = level.get("itemStyle")
            if item_style:
                self.assertEqual(item_style["gapWidth"], dashboard_app.TREEMAP_NODE_GAP_WIDTH)
                self.assertEqual(item_style["borderWidth"], dashboard_app.TREEMAP_NODE_BORDER_WIDTH)

            upper_label = level.get("upperLabel")
            if upper_label:
                self.assertEqual(upper_label["height"], dashboard_app.TREEMAP_UPPER_LABEL_HEIGHT)
                self.assertEqual(upper_label["fontSize"], dashboard_app.TREEMAP_UPPER_LABEL_FONT_SIZE)

        def iter_nodes(nodes):
            for node in nodes:
                yield node
                yield from iter_nodes(node.get("children") or [])

        leaf_styles = [
            node["itemStyle"]
            for node in iter_nodes(series["data"])
            if not node.get("children") and node.get("itemStyle")
        ]
        self.assertTrue(leaf_styles)
        for item_style in leaf_styles:
            self.assertEqual(item_style["gapWidth"], dashboard_app.TREEMAP_NODE_GAP_WIDTH)
            self.assertEqual(item_style["borderWidth"], dashboard_app.TREEMAP_NODE_BORDER_WIDTH)

    def test_allocation_treemap_groups_holdings_by_sector_and_attaches_intraday_details(self) -> None:
        """트리맵은 자산군 아래 섹터를 만들고 hover용 intraday 정보를 leaf에 붙인다."""

        holdings = [
            {
                "product_name": "TIGER 미국S&P500",
                "symbol": "360750",
                "asset_type": "risk",
                "quantity": 1,
                "avg_cost": 100,
                "current_price": 110,
            },
            {
                "product_name": "TIGER 미국테크TOP10 INDXX",
                "symbol": "381170",
                "asset_type": "risk",
                "quantity": 1,
                "avg_cost": 100,
                "current_price": 120,
            },
            {
                "product_name": "KOSEF 국고채10년",
                "symbol": "148070",
                "asset_type": "safe",
                "quantity": 1,
                "avg_cost": 100,
                "current_price": 101,
            },
        ]
        summary = {
            "allocation": {
                "risk": 230,
                "safe": 101,
                "cash": 0,
            },
            "cash": 0,
        }

        def snapshot_stub(symbol: str, interval: str = "5m") -> dict[str, object]:
            return {
                "symbol": symbol,
                "series": [100.0, 102.0, 104.0],
                "current_price": 104.0,
                "previous_close": 100.0,
                "day_change_rate": 4.0,
                "as_of": "2026-05-10T14:55:00+09:00",
                "currency": "KRW",
            }

        original = dashboard_app.fetch_intraday_price_snapshot
        dashboard_app.fetch_intraday_price_snapshot = snapshot_stub
        try:
            options = dashboard_app.allocation_treemap_options(summary, holdings)
        finally:
            dashboard_app.fetch_intraday_price_snapshot = original

        self.assertIsNotNone(options)
        assert options is not None
        self.assertEqual(options["title"]["text"], "자산군 → 섹터 → 보유 종목")

        root_nodes = options["series"][0]["data"]
        risk_node = next(node for node in root_nodes if node["name"] == "위험자산")
        risk_sectors = {child["name"]: child for child in risk_node["children"]}
        self.assertIn("미국지수", risk_sectors)
        self.assertIn("미국테크", risk_sectors)

        us_index_leaf = risk_sectors["미국지수"]["children"][0]
        self.assertEqual(us_index_leaf["sector_name"], "미국지수")
        self.assertEqual(us_index_leaf["current_price_text"], "₩104")
        self.assertEqual(us_index_leaf["day_change_text"], "+4.00%")
        self.assertEqual(us_index_leaf["holding_profit_text"], "+10.00%")
        self.assertEqual(us_index_leaf["intraday_as_of"], "기준시각 2026-05-10 14:55:00")
        self.assertIn("<svg", us_index_leaf["sparkline_svg"])


class DashboardAllocationStatusTests(unittest.TestCase):
    """자산 배분 헤더의 실시간 상태 문구를 검증한다."""

    def test_format_dashboard_reference_time_formats_full_seconds(self) -> None:
        """대시보드 기준시각은 초 단위까지 표기한다."""

        formatted = dashboard_app.format_dashboard_reference_time("2026-05-11T11:24:15+09:00")

        self.assertEqual(formatted, "2026-05-11 11:24:15")

    def test_dashboard_allocation_status_returns_idle_when_data_missing(self) -> None:
        """배분 데이터가 없으면 대기 상태를 표시한다."""

        result = dashboard_app.dashboard_allocation_status(1, [], has_allocation_data=False)

        self.assertEqual(result, ("데이터 대기", "idle"))

    def test_dashboard_allocation_status_returns_live_when_worker_connected_with_quote(self) -> None:
        """worker가 연결되고 quote가 있으면 실시간 연동 중으로 표시한다."""

        original_status = dashboard_app.get_realtime_worker_status
        original_latest_quote = dashboard_app.latest_realtime_quote_time
        dashboard_app.get_realtime_worker_status = lambda account_id: {"connection_state": "connected"}
        dashboard_app.latest_realtime_quote_time = lambda account_id: "2026-05-11T09:25:00+09:00"
        try:
            result = dashboard_app.dashboard_allocation_status(
                1,
                [{"symbol": "005930", "product_name": "삼성전자"}],
                has_allocation_data=True,
            )
        finally:
            dashboard_app.get_realtime_worker_status = original_status
            dashboard_app.latest_realtime_quote_time = original_latest_quote

        self.assertEqual(result, ("실시간 연동 중", "live"))

    def test_dashboard_allocation_status_returns_stale_when_worker_not_connected(self) -> None:
        """보유 종목은 있지만 worker 연결이 없으면 지연 데이터 상태를 표시한다."""

        original_status = dashboard_app.get_realtime_worker_status
        original_latest_quote = dashboard_app.latest_realtime_quote_time
        dashboard_app.get_realtime_worker_status = lambda account_id: {"connection_state": "disconnected"}
        dashboard_app.latest_realtime_quote_time = lambda account_id: ""
        try:
            result = dashboard_app.dashboard_allocation_status(
                1,
                [{"symbol": "005930", "product_name": "삼성전자"}],
                has_allocation_data=True,
            )
        finally:
            dashboard_app.get_realtime_worker_status = original_status
            dashboard_app.latest_realtime_quote_time = original_latest_quote

        self.assertEqual(result, ("지연 데이터 표시 중", "stale"))

    def test_dashboard_allocation_status_returns_live_when_recent_quote_exists(self) -> None:
        """worker 상태가 늦게 내려와도 최근 quote가 있으면 live 톤으로 표시한다."""

        original_status = dashboard_app.get_realtime_worker_status
        original_latest_quote = dashboard_app.latest_realtime_quote_time
        original_now = dashboard_app.datetime
        dashboard_app.get_realtime_worker_status = lambda account_id: {"connection_state": "stopped"}
        dashboard_app.latest_realtime_quote_time = lambda account_id: "2026-05-11T11:24:15"

        class FrozenDateTime:
            """테스트용 현재 시각 제공자."""

            @staticmethod
            def now(tz=None):
                current = original_now.fromisoformat("2026-05-11T11:25:30")
                return current.replace(tzinfo=tz) if tz is not None else current

            @staticmethod
            def fromisoformat(value: str):
                return original_now.fromisoformat(value)

        dashboard_app.datetime = FrozenDateTime
        try:
            result = dashboard_app.dashboard_allocation_status(
                1,
                [{"symbol": "251600", "product_name": "KODEX"}],
                has_allocation_data=True,
            )
        finally:
            dashboard_app.get_realtime_worker_status = original_status
            dashboard_app.latest_realtime_quote_time = original_latest_quote
            dashboard_app.datetime = original_now

        self.assertEqual(result, ("실시간 반영 중", "live"))

    def test_dashboard_allocation_status_returns_idle_when_only_cash_is_visible(self) -> None:
        """보유 종목이 없으면 실시간 대상이 없음을 표시한다."""

        result = dashboard_app.dashboard_allocation_status(1, [], has_allocation_data=True)

        self.assertEqual(result, ("실시간 대상 없음", "idle"))

    def test_dashboard_live_refresh_interval_returns_fast_poll_when_connected(self) -> None:
        """worker 연결 시 대시보드 자동 새로고침은 10초 주기를 사용한다."""

        original_status = dashboard_app.get_realtime_worker_status
        dashboard_app.get_realtime_worker_status = lambda account_id: {"connection_state": "connected"}
        try:
            result = dashboard_app.dashboard_live_refresh_interval(1, [{"symbol": "005930"}])
        finally:
            dashboard_app.get_realtime_worker_status = original_status

        self.assertEqual(result, "10s")

    def test_dashboard_live_refresh_interval_polls_slowly_for_domestic_holdings_while_stale(self) -> None:
        """연결 전이더라도 국내 종목이 있으면 30초 주기로 상태 변화를 재확인한다."""

        original_status = dashboard_app.get_realtime_worker_status
        dashboard_app.get_realtime_worker_status = lambda account_id: {"connection_state": "disconnected"}
        try:
            result = dashboard_app.dashboard_live_refresh_interval(
                1,
                [{"symbol": "005930"}, {"symbol": "AAPL"}],
            )
        finally:
            dashboard_app.get_realtime_worker_status = original_status

        self.assertEqual(result, "30s")

    def test_dashboard_live_refresh_interval_returns_fast_poll_when_recent_quote_exists(self) -> None:
        """worker 상태가 늦더라도 최근 quote가 있으면 빠른 재확인을 유지한다."""

        original_status = dashboard_app.get_realtime_worker_status
        original_latest_quote = dashboard_app.latest_realtime_quote_time
        original_now = dashboard_app.datetime
        dashboard_app.get_realtime_worker_status = lambda account_id: {"connection_state": "stopped"}
        dashboard_app.latest_realtime_quote_time = lambda account_id: "2026-05-11T11:24:15"

        class FrozenDateTime:
            """테스트용 현재 시각 제공자."""

            @staticmethod
            def now(tz=None):
                current = original_now.fromisoformat("2026-05-11T11:25:00")
                return current.replace(tzinfo=tz) if tz is not None else current

            @staticmethod
            def fromisoformat(value: str):
                return original_now.fromisoformat(value)

        dashboard_app.datetime = FrozenDateTime
        try:
            result = dashboard_app.dashboard_live_refresh_interval(1, [{"symbol": "251600"}])
        finally:
            dashboard_app.get_realtime_worker_status = original_status
            dashboard_app.latest_realtime_quote_time = original_latest_quote
            dashboard_app.datetime = original_now

        self.assertEqual(result, "10s")

    def test_dashboard_live_refresh_interval_skips_poll_without_domestic_holdings(self) -> None:
        """국내 실시간 대상이 없으면 상태 전이 폴링을 켜지 않는다."""

        original_status = dashboard_app.get_realtime_worker_status
        dashboard_app.get_realtime_worker_status = lambda account_id: {"connection_state": "disconnected"}
        try:
            result = dashboard_app.dashboard_live_refresh_interval(
                1,
                [{"symbol": "AAPL"}, {"symbol": "CASH"}],
            )
        finally:
            dashboard_app.get_realtime_worker_status = original_status

        self.assertIsNone(result)


class RealtimeStatusFragmentTests(unittest.TestCase):
    """실시간 상태 영역의 fragment 적용 범위를 검증한다."""

    def test_realtime_status_fragments_use_fixed_poll_interval(self) -> None:
        """실시간 상태 조각은 10초 주기로 독립 갱신한다."""

        self.assertEqual(dashboard_app.REALTIME_STATUS_FRAGMENT_INTERVAL, "10s")
        fragment_functions = (
            dashboard_app.render_dashboard_reference_time_fragment,
            dashboard_app.render_dashboard_allocation_status_header_fragment,
            dashboard_app.render_realtime_worker_status_panel,
        )

        for fragment_function in fragment_functions:
            source = inspect.getsource(fragment_function)
            self.assertIn("@st.fragment(run_every=REALTIME_STATUS_FRAGMENT_INTERVAL)", source)

    def test_dashboard_uses_status_fragments_without_page_fragment(self) -> None:
        """대시보드 전체가 아니라 상태 표시 영역만 fragment로 갱신한다."""

        navigation_source = inspect.getsource(dashboard_app.render_navigation_page)
        dashboard_source = inspect.getsource(dashboard_app.dashboard_page)

        self.assertNotIn("render_dashboard_fragment", navigation_source)
        self.assertIn("reference_time_text=format_dashboard_overview_reference_time(latest_quote_time)", dashboard_source)
        self.assertIn("is_live=is_recent_realtime_quote(latest_quote_time)", dashboard_source)
        self.assertIn("render_dashboard_allocation_status_header_fragment(", dashboard_source)

    def test_data_page_worker_status_uses_fragment(self) -> None:
        """데이터 페이지 worker 상태 metric은 별도 fragment 함수로 분리한다."""

        source = inspect.getsource(dashboard_app.data_page)

        self.assertIn("render_realtime_worker_status_panel(account_id, market_status)", source)
        self.assertNotIn("worker_status = get_realtime_worker_status(account_id)", source)


class SelectedHoldingTrendFrameTests(unittest.TestCase):
    """선택 종목 트렌드 원천 프레임 구성을 검증한다."""

    def test_build_selected_holding_trend_frame_uses_intraday_timeline_for_today(self) -> None:
        """`당일` 기간은 intraday 타임라인을 장 시작부터 시간순으로 사용한다."""

        holding = {
            "symbol": "005930",
            "product_name": "삼성전자",
            "quantity": 10,
            "avg_cost": 100.0,
        }
        snapshot = {
            "timeline": [
                {"datetime": "2026-05-11T09:00:00+09:00", "close": 101.0},
                {"datetime": "2026-05-11T15:30:00+09:00", "close": 105.0},
            ]
        }

        original = dashboard_app.fetch_intraday_price_snapshot
        dashboard_app.fetch_intraday_price_snapshot = lambda symbol, interval="5m": snapshot
        try:
            frame = dashboard_app.build_selected_holding_trend_frame([holding], period="today")
        finally:
            dashboard_app.fetch_intraday_price_snapshot = original

        self.assertEqual(frame["date"].dt.strftime("%H:%M").tolist(), ["09:00", "15:30"])
        self.assertEqual(frame["product_name"].tolist(), ["삼성전자", "삼성전자"])
        self.assertEqual(frame["market_value"].tolist(), [1010.0, 1050.0])
        self.assertEqual(frame["cost_basis"].tolist(), [1000.0, 1000.0])
        self.assertEqual(frame["profit_loss"].tolist(), [10.0, 50.0])
        self.assertEqual(frame["profit_rate"].tolist(), [1.0, 5.0])

    def test_build_selected_holding_trend_frame_falls_back_to_allocation_current_price_for_today(self) -> None:
        """타임라인이 비어도 자산 배분 카드가 쓰는 금일 시세로 `당일` 1포인트를 만든다."""

        holding = {
            "symbol": "005930",
            "product_name": "삼성전자",
            "quantity": 10,
            "avg_cost": 100.0,
            "current_price": 107.0,
        }
        snapshot = {
            "timeline": [],
            "current_price": 108.5,
            "as_of": "2026-05-11T15:30:00+09:00",
        }

        original = dashboard_app.fetch_intraday_price_snapshot
        dashboard_app.fetch_intraday_price_snapshot = lambda symbol, interval="5m": snapshot
        try:
            frame = dashboard_app.build_selected_holding_trend_frame([holding], period="today")
        finally:
            dashboard_app.fetch_intraday_price_snapshot = original

        self.assertEqual(frame["date"].dt.strftime("%H:%M").tolist(), ["15:30"])
        self.assertEqual(frame["close"].tolist(), [108.5])
        self.assertEqual(frame["market_value"].tolist(), [1085.0])
        self.assertEqual(frame["profit_rate"].tolist(), [8.5])


class SelectedHoldingTrendOptionTests(unittest.TestCase):
    """선택 종목 트렌드 ECharts 옵션 구성을 검증한다."""

    def test_selected_holding_trend_options_matches_echarts_layout(self) -> None:
        """제목, toolbox, zoom, 스무스 area line 구성을 포함한다."""

        frame = pd.DataFrame(
            [
                {
                    "date": "2026-01-31",
                    "product_name": "삼성전자",
                    "market_value": 1200000,
                    "profit_rate": 3.25,
                    "close": 60100,
                },
                {
                    "date": "2026-02-28",
                    "product_name": "삼성전자",
                    "market_value": 1265000,
                    "profit_rate": 8.40,
                    "close": 63500,
                },
            ]
        )

        options = dashboard_app.selected_holding_trend_options(
            frame,
            selected_holding_name="삼성전자",
            selected_symbol_code="005930",
            measure="market_value",
            period_label="6개월",
        )

        self.assertIsNotNone(options)
        assert options is not None
        self.assertEqual(options["title"]["text"], "삼성전자")
        self.assertIn("005930", options["title"]["subtext"])
        self.assertNotIn("삼성전자", options["title"]["subtext"])
        self.assertIn("평가금액", options["title"]["subtext"])
        self.assertEqual(len(options["dataZoom"]), 2)
        self.assertIn("saveAsImage", options["toolbox"]["feature"])
        self.assertIn("dataView", options["toolbox"]["feature"])
        self.assertIn("dataZoom", options["toolbox"]["feature"])
        self.assertIn("restore", options["toolbox"]["feature"])
        self.assertIn("magicType", options["toolbox"]["feature"])
        self.assertEqual(options["series"][0]["type"], "line")
        self.assertTrue(options["series"][0]["smooth"])
        self.assertIn("areaStyle", options["series"][0])

    def test_selected_holding_trend_options_adds_zero_reference_for_profit_rate(self) -> None:
        """수익률 차트는 0% 기준선을 함께 표시한다."""

        frame = pd.DataFrame(
            [
                {
                    "date": "2026-01-31",
                    "product_name": "애플",
                    "market_value": 1000000,
                    "profit_rate": -2.5,
                    "close": 190.25,
                },
                {
                    "date": "2026-02-28",
                    "product_name": "애플",
                    "market_value": 1100000,
                    "profit_rate": 4.75,
                    "close": 201.50,
                },
            ]
        )

        options = dashboard_app.selected_holding_trend_options(
            frame,
            selected_holding_name="애플",
            selected_symbol_code="AAPL",
            measure="profit_rate",
            period_label="3개월",
        )

        self.assertIsNotNone(options)
        assert options is not None
        self.assertIn("markLine", options["series"][0])
        self.assertEqual(options["series"][0]["markLine"]["data"], [{"yAxis": 0}])

    def test_selected_holding_trend_options_shows_time_axis_for_today(self) -> None:
        """`당일` 옵션은 시간 축과 데이터 보기 시간 컬럼을 함께 노출한다."""

        frame = pd.DataFrame(
            [
                {
                    "date": "2026-05-11T09:00:00+09:00",
                    "product_name": "삼성전자",
                    "market_value": 1010000,
                    "profit_rate": 1.0,
                    "close": 101.0,
                },
                {
                    "date": "2026-05-11T15:30:00+09:00",
                    "product_name": "삼성전자",
                    "market_value": 1050000,
                    "profit_rate": 5.0,
                    "close": 105.0,
                },
            ]
        )

        options = dashboard_app.selected_holding_trend_options(
            frame,
            selected_holding_name="삼성전자",
            selected_symbol_code="005930",
            measure="close",
            period_label="당일",
        )

        self.assertIsNotNone(options)
        assert options is not None
        self.assertEqual(options["xAxis"]["data"], ["09:00", "15:30"])
        first_point = options["series"][0]["data"][0]
        self.assertEqual(first_point["time"], "09:00")
        self.assertEqual(first_point["date"], "2026-05-11 09:00")
        option_to_content = str(options["toolbox"]["feature"]["dataView"]["optionToContent"])
        self.assertIn("시간", option_to_content)

    def test_selected_holding_trend_options_data_view_shows_full_daily_columns(self) -> None:
        """데이터 보기는 년월일, 종가, 수익률, 평가금액 컬럼을 함께 노출한다."""

        frame = pd.DataFrame(
            [
                {
                    "date": "2026-01-31",
                    "product_name": "삼성전자",
                    "market_value": 1200000,
                    "profit_rate": 3.25,
                    "close": 60100,
                },
                {
                    "date": "2026-02-28",
                    "product_name": "삼성전자",
                    "market_value": 1265000,
                    "profit_rate": 8.40,
                    "close": 63500,
                },
            ]
        )

        options = dashboard_app.selected_holding_trend_options(
            frame,
            selected_holding_name="삼성전자",
            selected_symbol_code="005930",
            measure="profit_rate",
            period_label="6개월",
        )

        self.assertIsNotNone(options)
        assert options is not None
        data_view = options["toolbox"]["feature"]["dataView"]
        self.assertIn("optionToContent", data_view)
        option_to_content = str(data_view["optionToContent"])
        for label in ("년", "월", "일", "기준가(종가)", "수익률", "평가금액"):
            self.assertIn(label, option_to_content)

        first_point = options["series"][0]["data"][0]
        self.assertEqual(first_point["year"], "2026")
        self.assertEqual(first_point["month"], "01")
        self.assertEqual(first_point["day"], "31")
        self.assertEqual(first_point["close"], 60100.0)
        self.assertEqual(first_point["profit_rate"], 3.25)
        self.assertEqual(first_point["market_value"], 1200000.0)


if __name__ == "__main__":
    unittest.main()

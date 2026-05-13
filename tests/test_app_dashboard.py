from __future__ import annotations

import inspect
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest

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

        self.assertEqual(tokens["theme_primary_color"], "#3B5BDB")
        self.assertEqual(tokens["theme_background_color"], "#F6F8FB")
        self.assertEqual(tokens["theme_secondary_background_color"], "#EEF2F7")
        self.assertEqual(tokens["theme_text_color"], "#0F172A")
        self.assertEqual(tokens["brand_deep_color"], "#0F172A")
        self.assertEqual(tokens["brand_accent_color"], "#3B5BDB")
        self.assertEqual(tokens["brand_hover_color"], "#2F47B8")
        self.assertEqual(tokens["status_good_color"], "#0F766E")
        self.assertEqual(tokens["chart_up_color"], "#0F766E")
        self.assertEqual(tokens["chart_down_color"], "#DC2626")
        self.assertEqual(tokens["chart_line_color"], "#1E3A8A")
        self.assertEqual(tokens["chart_accent_color"], "#3B5BDB")
        self.assertEqual(tokens["chart_accent_strong_color"], "#2F47B8")

    def test_render_app_stylesheet_substitutes_theme_variables(self) -> None:
        """외부 CSS 템플릿의 플레이스홀더가 실제 토큰 값으로 치환된다."""

        stylesheet = dashboard_app.render_app_stylesheet()

        self.assertIn("--theme-primary: #3B5BDB;", stylesheet)
        self.assertIn("--brand-deep: #0F172A;", stylesheet)
        self.assertIn("--chart-up: #0F766E;", stylesheet)
        self.assertIn("--chart-down: #DC2626;", stylesheet)
        self.assertIn("--chart-line: #1E3A8A;", stylesheet)
        self.assertIn(".dashboard-metric-card", stylesheet)
        self.assertIn(".dashboard-reference-time", stylesheet)
        self.assertIn(".holdings-table-shell", stylesheet)
        self.assertIn(".st-key-dashboard-panel-allocation", stylesheet)
        self.assertIn(".st-key-dashboard-panel-holdings-table", stylesheet)
        self.assertIn("--radius-lg: 18px;", stylesheet)
        self.assertIn("--shadow-card: 0 14px 38px rgba(15, 23, 42, 0.08);", stylesheet)
        self.assertIn("--panel-radius: var(--radius-lg);", stylesheet)
        self.assertIn("--dashboard-summary-card-height: 128px;", stylesheet)
        self.assertIn("--dashboard-secondary-panel-min-height: 560px;", stylesheet)
        self.assertNotIn("--card-shadow:", stylesheet)
        self.assertIn(
            '[data-testid="stSidebar"] {\n    background: linear-gradient(180deg, var(--surface-strong) 0%, var(--theme-secondary-bg) 100%);',
            stylesheet,
        )
        self.assertIn('[data-testid="stVerticalBlockBorderWrapper"] {\n    background: var(--surface-strong);', stylesheet)
        self.assertIn('[data-testid="stMetric"] {\n    background: var(--surface-strong);', stylesheet)
        self.assertIn(".dashboard-summary-card,\n.dashboard-metric-card", stylesheet)
        self.assertIn("border-radius: var(--radius-xl);", stylesheet)
        self.assertIn("box-shadow: var(--shadow-card);", stylesheet)
        self.assertIn("color-mix(in srgb, var(--surface-strong) 98%, transparent)", stylesheet)
        self.assertIn("color-mix(in srgb, var(--surface) 94%, var(--theme-secondary-bg))", stylesheet)
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
        self.assertIn(".st-key-trade-log-inline-editor-shell", stylesheet)
        self.assertNotIn("${theme_primary_color}", stylesheet)

    def test_priority_surface_blocks_do_not_hardcode_white_backgrounds(self) -> None:
        """우선 교체 대상 CSS 블록은 흰색 배경 하드코딩 대신 surface 토큰을 사용한다."""

        stylesheet = dashboard_app.render_app_stylesheet()
        ranges = [
            ('[data-testid="stSidebar"] {', '[data-testid="stVerticalBlockBorderWrapper"] {'),
            ('[data-testid="stVerticalBlockBorderWrapper"] {', '[data-testid="stSidebar"] [data-testid="stVerticalBlock"]'),
            ('[data-testid="stMetric"] {', '[data-testid="stMetricLabel"]'),
            ('.auth-feature-card {', '.auth-feature-card__index'),
            ('.st-key-auth-card-shell {', '.st-key-auth-card-shell [data-testid="stTextInput"] [data-baseweb="input"]:focus-within'),
            ('.st-key-dashboard-panel-allocation,\n.st-key-dashboard-panel-selected-trend,', '.st-key-dashboard-panel-allocation [data-testid="stVerticalBlockBorderWrapper"],'),
            ('.dashboard-summary-card,\n.dashboard-metric-card {', '.dashboard-summary-card {'),
        ]

        for start_marker, end_marker in ranges:
            with self.subTest(start_marker=start_marker):
                start = stylesheet.index(start_marker)
                end = stylesheet.index(end_marker, start + len(start_marker))
                block = stylesheet[start:end].lower()

                self.assertNotIn("#ffffff", block)
                self.assertNotIn("rgba(255, 255, 255", block)

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

    def test_trade_log_table_fields_exclude_cash_delta_column(self) -> None:
        """거래 기록 표 구성에서 현금증감 컬럼을 제외한다."""

        self.assertNotIn("현금증감", dashboard_app.TRADE_LOG_TABLE_HEADER_LABELS)
        self.assertNotIn("cash_delta", dashboard_app.TRADE_LOG_TABLE_DISPLAY_FIELDS)
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

        self.assertEqual(dashboard_app.trade_submit_button_label("buy"), "상품 추가")
        self.assertEqual(dashboard_app.trade_submit_button_label("sell"), "상품 저장")
        self.assertEqual(dashboard_app.trade_price_label("buy"), "매입가/기준가")
        self.assertEqual(dashboard_app.trade_date_label("sell"), "매매일")
        self.assertEqual(dashboard_app.cash_flow_panel_title("employer_deposit"), "회사 현금입금")
        self.assertIn("퇴직금 원금", dashboard_app.cash_flow_panel_caption("employer_deposit"))
        self.assertEqual(dashboard_app.cash_flow_submit_label("withdraw"), "출금 기록")

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

    def test_trade_type_badge_styles_include_cash_flow_types(self) -> None:
        """입금/회사납입/출금 거래유형도 거래 기록 표에서 배지로 표시한다."""

        expected_styles = {
            "personal_deposit": {"background": "#EFF6FF", "border": "#BFDBFE", "color": "#1D4ED8", "label": "개인 입금"},
            "employer_deposit": {"background": "#F0FDF4", "border": "#BBF7D0", "color": "#15803D", "label": "회사 납입금"},
            "withdraw": {"background": "#FFF7ED", "border": "#FED7AA", "color": "#C2410C", "label": "일반 출금"},
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
        """데이터 페이지 거래 기록 미리보기는 배지와 테이블 테마를 함께 사용한다."""

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
        self.assertIn("background:#EFF6FF", html)
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
        self.assertIn("render_dashboard_reference_time_fragment(account_id)", dashboard_source)
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

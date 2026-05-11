from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
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

        self.assertEqual(tokens["theme_primary_color"], "#0F766E")
        self.assertEqual(tokens["theme_background_color"], "#F6F7F2")
        self.assertEqual(tokens["theme_secondary_background_color"], "#E4EFE8")
        self.assertEqual(tokens["theme_text_color"], "#15281F")

    def test_render_app_stylesheet_substitutes_theme_variables(self) -> None:
        """외부 CSS 템플릿의 플레이스홀더가 실제 토큰 값으로 치환된다."""

        stylesheet = dashboard_app.render_app_stylesheet()

        self.assertIn("--theme-primary: #0F766E;", stylesheet)
        self.assertIn(".dashboard-metric-card", stylesheet)
        self.assertNotIn("${theme_primary_color}", stylesheet)

    def test_render_app_stylesheet_uses_local_system_font_stack(self) -> None:
        """초기 렌더 지연을 줄이기 위해 외부 CDN 폰트 import 없이 시스템 폰트를 사용한다."""

        stylesheet = dashboard_app.render_app_stylesheet()

        self.assertNotIn("cdn.jsdelivr.net", stylesheet)
        self.assertNotIn("Pretendard", stylesheet)
        self.assertIn('font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI"', stylesheet)


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

    def test_is_visible_trade_log_hides_cash_adjustment_rows(self) -> None:
        self.assertFalse(dashboard_app.is_visible_trade_log({"trade_type": "cash_adjustment"}))
        self.assertTrue(dashboard_app.is_visible_trade_log({"trade_type": "buy"}))


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
        self.assertIn("보유현금 ₩200,000 포함", html)
        self.assertNotIn(">보유현금<", html)


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
        self.assertIn("<svg", us_index_leaf["sparkline_svg"])


class DashboardAllocationStatusTests(unittest.TestCase):
    """자산 배분 헤더의 실시간 상태 문구를 검증한다."""

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

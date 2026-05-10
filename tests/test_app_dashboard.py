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

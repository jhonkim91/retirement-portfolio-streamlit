from __future__ import annotations

from datetime import datetime, timezone
import unittest
from unittest.mock import patch

import pandas as pd

import src.market as market
from src.kis import KST_TIMEZONE, _domestic_intraday_query_time
from src.market import (
    clean_code,
    fetch_intraday_price_snapshot,
    fetch_latest_price,
    fetch_price_history,
    is_krx_code,
    is_krx_symbol,
    normalize_symbol,
    resolve_kis_sector_label,
    search_products,
)


class MarketCodeNormalizationTests(unittest.TestCase):
    """국내 상장 코드 정규화 규칙을 검증한다."""

    def test_is_krx_code_accepts_numeric_listing_code(self) -> None:
        self.assertTrue(is_krx_code("005930"))

    def test_is_krx_code_accepts_alphanumeric_etf_code(self) -> None:
        self.assertTrue(is_krx_code("0113D0"))

    def test_is_krx_symbol_accepts_exchange_suffix(self) -> None:
        self.assertTrue(is_krx_symbol("0113D0.KS"))

    def test_normalize_symbol_appends_ks_for_alphanumeric_etf_code(self) -> None:
        self.assertEqual(normalize_symbol("0113D0"), "0113D0.KS")

    def test_normalize_symbol_keeps_existing_exchange_suffix(self) -> None:
        self.assertEqual(normalize_symbol("0113D0.KS"), "0113D0.KS")

    def test_clean_code_strips_exchange_suffix_from_alphanumeric_etf_code(self) -> None:
        self.assertEqual(clean_code("0113D0.KS"), "0113D0")


class MarketProviderSelectionTests(unittest.TestCase):
    """KIS 우선/fallback provider 선택을 검증한다."""

    def tearDown(self) -> None:
        getattr(fetch_intraday_price_snapshot, "clear", lambda: None)()
        getattr(fetch_latest_price, "clear", lambda: None)()
        getattr(fetch_price_history, "clear", lambda: None)()

    @patch("src.market._fetch_latest_price_from_yfinance")
    @patch("src.market._fetch_latest_price_from_kis")
    @patch("src.market.is_kis_enabled", return_value=True)
    def test_fetch_latest_price_prefers_kis_for_domestic_symbol(
        self,
        _is_kis_enabled_mock,
        kis_mock,
        yahoo_mock,
    ) -> None:
        kis_mock.return_value = {"symbol": "005930.KS", "price": 70000.0, "as_of": "2026-05-10T09:10:00", "source": "KIS REST"}

        result = fetch_latest_price("005930")

        self.assertEqual(result["source"], "KIS REST")
        kis_mock.assert_called_once()
        yahoo_mock.assert_not_called()

    @patch("src.market._fetch_latest_price_from_yfinance")
    @patch("src.market._fetch_latest_price_from_naver", side_effect=ValueError("Naver unavailable"))
    @patch("src.market._fetch_latest_price_from_kis", side_effect=ValueError("KIS unavailable"))
    @patch("src.market.is_kis_enabled", return_value=True)
    def test_fetch_latest_price_falls_back_to_yfinance_when_kis_fails(
        self,
        _is_kis_enabled_mock,
        _kis_mock,
        _naver_mock,
        yahoo_mock,
    ) -> None:
        yahoo_mock.return_value = {"symbol": "005930.KS", "price": 70100.0, "as_of": "2026-05-10", "source": "Yahoo"}

        result = fetch_latest_price("005930")

        self.assertEqual(result["source"], "Yahoo")
        yahoo_mock.assert_called_once()

    @patch("src.market._fetch_latest_price_from_yfinance")
    @patch("src.market._fetch_latest_price_from_naver")
    @patch("src.market._fetch_latest_price_from_kis")
    @patch("src.market.is_kis_enabled", return_value=True)
    def test_fetch_latest_price_uses_naver_for_alphanumeric_krx_symbol(
        self,
        _is_kis_enabled_mock,
        kis_mock,
        naver_mock,
        yahoo_mock,
    ) -> None:
        naver_mock.return_value = {"symbol": "0162Z0.KS", "price": 13375.0, "as_of": "2026-05-12", "source": "Naver"}

        result = fetch_latest_price("0162Z0")

        self.assertEqual(result["source"], "Naver")
        kis_mock.assert_not_called()
        naver_mock.assert_called_once()
        yahoo_mock.assert_not_called()

    @patch("src.market._fetch_latest_price_from_yfinance")
    @patch("src.market._fetch_latest_price_from_kis")
    @patch("src.market.is_kis_enabled", return_value=True)
    def test_fetch_latest_price_keeps_global_symbol_on_existing_fallback_path(
        self,
        _is_kis_enabled_mock,
        kis_mock,
        yahoo_mock,
    ) -> None:
        yahoo_mock.return_value = {"symbol": "AAPL", "price": 199.5, "as_of": "2026-05-10", "source": "Yahoo"}

        result = fetch_latest_price("AAPL")

        self.assertEqual(result["source"], "Yahoo")
        kis_mock.assert_not_called()
        yahoo_mock.assert_called_once()

    @patch("src.market._fetch_price_history_from_yfinance")
    @patch("src.market._fetch_price_history_from_naver", return_value=pd.DataFrame(columns=["date", "close", "symbol"]))
    @patch("src.market._fetch_price_history_from_kis")
    @patch("src.market.is_kis_enabled", return_value=True)
    def test_fetch_price_history_uses_kis_only_for_supported_domestic_periods(
        self,
        _is_kis_enabled_mock,
        kis_mock,
        naver_mock,
        yahoo_mock,
    ) -> None:
        kis_mock.return_value = pd.DataFrame([{"date": pd.Timestamp("2026-05-01").date(), "close": 70000.0, "symbol": "005930.KS"}])
        yahoo_mock.return_value = pd.DataFrame(columns=["date", "close", "symbol"])

        fetch_price_history("005930", period="1mo")
        fetch_price_history("005930", period="6mo")

        kis_mock.assert_called_once()
        naver_mock.assert_called_once()
        self.assertEqual(yahoo_mock.call_count, 1)

    @patch("src.market._fetch_price_history_from_yfinance")
    @patch("src.market._fetch_price_history_from_naver")
    @patch("src.market._fetch_price_history_from_kis")
    @patch("src.market.is_kis_enabled", return_value=True)
    def test_fetch_price_history_uses_naver_for_alphanumeric_krx_symbol(
        self,
        _is_kis_enabled_mock,
        kis_mock,
        naver_mock,
        yahoo_mock,
    ) -> None:
        naver_frame = pd.DataFrame(
            [
                {"date": pd.Timestamp("2026-05-11").date(), "close": 13430.0, "symbol": "0162Z0.KS"},
                {"date": pd.Timestamp("2026-05-12").date(), "close": 13375.0, "symbol": "0162Z0.KS"},
            ]
        )
        naver_mock.return_value = naver_frame

        result = fetch_price_history("0162Z0", period="6mo")

        self.assertEqual(result["symbol"].tolist(), ["0162Z0.KS", "0162Z0.KS"])
        kis_mock.assert_not_called()
        naver_mock.assert_called_once()
        yahoo_mock.assert_not_called()

    @patch("src.market._fetch_intraday_price_snapshot_from_yfinance")
    @patch("src.market._fetch_intraday_price_snapshot_from_naver")
    @patch("src.market._fetch_intraday_price_snapshot_from_kis")
    @patch("src.market.is_kis_enabled", return_value=True)
    def test_fetch_intraday_price_snapshot_uses_naver_for_alphanumeric_krx_symbol(
        self,
        _is_kis_enabled_mock,
        kis_mock,
        naver_mock,
        yahoo_mock,
    ) -> None:
        naver_mock.return_value = {
            "symbol": "0162Z0.KS",
            "series": [13370.0, 13375.0],
            "timeline": [{"datetime": "2026-05-12T15:58:00", "close": 13375.0}],
            "current_price": 13375.0,
            "source": "Naver",
        }

        result = fetch_intraday_price_snapshot("0162Z0")

        self.assertEqual(result["source"], "Naver")
        kis_mock.assert_not_called()
        naver_mock.assert_called_once()
        yahoo_mock.assert_not_called()

    @patch("src.market._fetch_intraday_price_snapshot_from_yfinance")
    @patch("src.market._fetch_intraday_price_snapshot_from_naver")
    @patch("src.market._fetch_intraday_price_snapshot_from_kis")
    @patch("src.market.is_kis_enabled", return_value=True)
    def test_fetch_intraday_price_snapshot_prefers_naver_full_day_chart_for_numeric_krx_symbol(
        self,
        _is_kis_enabled_mock,
        kis_mock,
        naver_mock,
        yahoo_mock,
    ) -> None:
        naver_mock.return_value = {
            "symbol": "005930.KS",
            "series": [70000.0, 70100.0, 70200.0],
            "timeline": [
                {"datetime": "2026-05-13T09:00:00", "close": 70000.0},
                {"datetime": "2026-05-13T09:01:00", "close": 70100.0},
                {"datetime": "2026-05-13T09:02:00", "close": 70200.0},
            ],
            "current_price": 70200.0,
            "source": "Naver",
        }
        kis_mock.return_value = {
            "symbol": "005930.KS",
            "series": [70150.0],
            "timeline": [{"datetime": "2026-05-13T23:59:00", "close": 70150.0}],
            "current_price": 70150.0,
            "source": "KIS REST",
        }

        result = fetch_intraday_price_snapshot("005930")

        self.assertEqual(result["source"], "Naver")
        self.assertEqual(len(result["timeline"]), 3)
        naver_mock.assert_called_once()
        kis_mock.assert_not_called()
        yahoo_mock.assert_not_called()

    @patch("src.market._fetch_intraday_price_snapshot_from_yfinance")
    @patch("src.market._fetch_intraday_price_snapshot_from_naver")
    @patch("src.market._fetch_intraday_price_snapshot_from_kis")
    @patch("src.market.is_kis_enabled", return_value=True)
    def test_fetch_intraday_price_snapshot_falls_back_to_kis_when_naver_chart_is_empty(
        self,
        _is_kis_enabled_mock,
        kis_mock,
        naver_mock,
        yahoo_mock,
    ) -> None:
        naver_mock.return_value = {
            "symbol": "005930.KS",
            "series": [],
            "timeline": [],
            "source": "",
        }
        kis_mock.return_value = {
            "symbol": "005930.KS",
            "series": [70150.0],
            "timeline": [{"datetime": "2026-05-13T14:22:00", "close": 70150.0}],
            "current_price": 70150.0,
            "source": "KIS REST",
        }

        result = fetch_intraday_price_snapshot("005930")

        self.assertEqual(result["source"], "KIS REST")
        naver_mock.assert_called_once()
        kis_mock.assert_called_once()
        yahoo_mock.assert_not_called()

    @patch("src.market._fetch_intraday_price_snapshot_from_yfinance")
    @patch("src.market._fetch_intraday_price_snapshot_from_naver", side_effect=ValueError("Naver unavailable"))
    @patch("src.market._fetch_intraday_price_snapshot_from_kis")
    @patch("src.market.is_kis_enabled", return_value=True)
    def test_fetch_intraday_price_snapshot_falls_back_to_kis_when_naver_raises(
        self,
        _is_kis_enabled_mock,
        kis_mock,
        naver_mock,
        yahoo_mock,
    ) -> None:
        kis_mock.return_value = {
            "symbol": "005930.KS",
            "series": [70150.0],
            "timeline": [{"datetime": "2026-05-13T14:22:00", "close": 70150.0}],
            "current_price": 70150.0,
            "source": "KIS REST",
        }

        result = fetch_intraday_price_snapshot("005930")

        self.assertEqual(result["source"], "KIS REST")
        naver_mock.assert_called_once()
        kis_mock.assert_called_once()
        yahoo_mock.assert_not_called()


class KisIntradayQueryTimeTests(unittest.TestCase):
    """KIS 국내 분봉 기준 시각 보정을 검증한다."""

    def test_domestic_intraday_query_time_uses_current_kst_during_market_hours(self) -> None:
        current = datetime(2026, 5, 13, 14, 22, 33, tzinfo=KST_TIMEZONE)

        self.assertEqual(_domestic_intraday_query_time(current), "142233")

    def test_domestic_intraday_query_time_caps_future_after_market_close(self) -> None:
        current = datetime(2026, 5, 13, 23, 59, 0, tzinfo=KST_TIMEZONE)

        self.assertEqual(_domestic_intraday_query_time(current), "153000")

    def test_domestic_intraday_query_time_converts_aware_datetime_to_kst(self) -> None:
        current = datetime(2026, 5, 13, 5, 22, 33, tzinfo=timezone.utc)

        self.assertEqual(_domestic_intraday_query_time(current), "142233")


class MarketSectorResolutionTests(unittest.TestCase):
    """KIS 마스터 기반 섹터 조회를 검증한다."""

    @patch("src.market.resolve_kis_sector_name", return_value="전기·전자")
    def test_resolve_kis_sector_label_returns_master_sector_name(self, sector_mock) -> None:
        self.assertEqual(resolve_kis_sector_label("005930"), "전기·전자")
        sector_mock.assert_called_once_with("005930")


class MarketSearchCacheTests(unittest.TestCase):
    """검색 캐시가 정규화된 질의값 기준으로 동작하는지 검증한다."""

    def tearDown(self) -> None:
        getattr(market._search_products_cached, "clear", lambda: None)()

    @patch("src.market.search_funds_from_funetf", return_value=[])
    @patch("src.market.search_products_from_naver_etf_list", return_value=[])
    @patch(
        "src.market.search_products_from_naver_search",
        return_value=[
            {
                "name": "삼성전자",
                "code": "005930",
                "symbol": "005930.KS",
                "exchange": "KRX",
                "type": "stock/ETF",
                "source": "Naver",
            }
        ],
    )
    @patch("src.market.search_master_products", return_value=[])
    def test_search_products_reuses_cache_for_normalized_query(
        self,
        search_master_mock,
        naver_search_mock,
        naver_etf_mock,
        funetf_mock,
    ) -> None:
        first = search_products(" 삼성전자 ", limit=5)
        second = search_products("삼성전자", limit=5)

        self.assertEqual(first, second)
        self.assertEqual(first[0]["code"], "005930")
        search_master_mock.assert_called_once_with("삼성전자", limit=5)
        naver_search_mock.assert_called_once_with("삼성전자", 5)
        naver_etf_mock.assert_not_called()
        funetf_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()

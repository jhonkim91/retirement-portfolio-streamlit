from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from src.market import (
    clean_code,
    fetch_latest_price,
    fetch_price_history,
    is_krx_code,
    normalize_symbol,
    resolve_kis_sector_label,
)


class MarketCodeNormalizationTests(unittest.TestCase):
    """국내 상장 코드 정규화 규칙을 검증한다."""

    def test_is_krx_code_accepts_numeric_listing_code(self) -> None:
        self.assertTrue(is_krx_code("005930"))

    def test_is_krx_code_accepts_alphanumeric_etf_code(self) -> None:
        self.assertTrue(is_krx_code("0113D0"))

    def test_normalize_symbol_appends_ks_for_alphanumeric_etf_code(self) -> None:
        self.assertEqual(normalize_symbol("0113D0"), "0113D0.KS")

    def test_normalize_symbol_keeps_existing_exchange_suffix(self) -> None:
        self.assertEqual(normalize_symbol("0113D0.KS"), "0113D0.KS")

    def test_clean_code_strips_exchange_suffix_from_alphanumeric_etf_code(self) -> None:
        self.assertEqual(clean_code("0113D0.KS"), "0113D0")


class MarketProviderSelectionTests(unittest.TestCase):
    """KIS 우선/fallback provider 선택을 검증한다."""

    def tearDown(self) -> None:
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
    @patch("src.market._fetch_latest_price_from_kis", side_effect=ValueError("KIS unavailable"))
    @patch("src.market.is_kis_enabled", return_value=True)
    def test_fetch_latest_price_falls_back_to_yfinance_when_kis_fails(
        self,
        _is_kis_enabled_mock,
        _kis_mock,
        yahoo_mock,
    ) -> None:
        yahoo_mock.return_value = {"symbol": "005930.KS", "price": 70100.0, "as_of": "2026-05-10", "source": "Yahoo"}

        result = fetch_latest_price("005930")

        self.assertEqual(result["source"], "Yahoo")
        yahoo_mock.assert_called_once()

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
    @patch("src.market._fetch_price_history_from_kis")
    @patch("src.market.is_kis_enabled", return_value=True)
    def test_fetch_price_history_uses_kis_only_for_supported_domestic_periods(
        self,
        _is_kis_enabled_mock,
        kis_mock,
        yahoo_mock,
    ) -> None:
        kis_mock.return_value = pd.DataFrame([{"date": pd.Timestamp("2026-05-01").date(), "close": 70000.0, "symbol": "005930.KS"}])
        yahoo_mock.return_value = pd.DataFrame(columns=["date", "close", "symbol"])

        fetch_price_history("005930", period="1mo")
        fetch_price_history("005930", period="6mo")

        kis_mock.assert_called_once()
        self.assertEqual(yahoo_mock.call_count, 1)


class MarketSectorResolutionTests(unittest.TestCase):
    """KIS 마스터 기반 섹터 조회를 검증한다."""

    @patch("src.market.resolve_kis_sector_name", return_value="전기·전자")
    def test_resolve_kis_sector_label_returns_master_sector_name(self, sector_mock) -> None:
        self.assertEqual(resolve_kis_sector_label("005930"), "전기·전자")
        sector_mock.assert_called_once_with("005930")


if __name__ == "__main__":
    unittest.main()

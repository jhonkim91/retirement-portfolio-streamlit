from __future__ import annotations

import unittest

from src.market import clean_code, is_krx_code, normalize_symbol


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


if __name__ == "__main__":
    unittest.main()

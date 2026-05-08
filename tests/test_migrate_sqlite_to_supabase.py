from __future__ import annotations

import unittest

from scripts.migrate_sqlite_to_supabase import normalize_trade_type_with_context


class MigrationNormalizationTests(unittest.TestCase):
    """SQLite -> Supabase 이관 시 레거시 입금 라벨 정규화를 검증한다."""

    def test_normalize_trade_type_with_context_promotes_company_cash_label(self) -> None:
        row = {
            "trade_type": "personal_deposit",
            "product_name": "회사 현금입금",
        }

        self.assertEqual(normalize_trade_type_with_context(row), "employer_deposit")

    def test_normalize_trade_type_with_context_keeps_regular_personal_deposit(self) -> None:
        row = {
            "trade_type": "personal_deposit",
            "product_name": "개인 입금",
        }

        self.assertEqual(normalize_trade_type_with_context(row), "personal_deposit")


if __name__ == "__main__":
    unittest.main()

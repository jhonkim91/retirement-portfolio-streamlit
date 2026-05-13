from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import unittest


SQL_PATH = Path(__file__).resolve().parents[1] / "setup_supabase.sql"


def read_setup_sql() -> str:
    """`setup_supabase.sql` 전체 내용을 읽는다."""

    return SQL_PATH.read_text(encoding="utf-8")


def extract_policy_statement(sql_text: str, policy_name: str) -> str:
    """지정한 정책의 `CREATE POLICY` 구문 전체를 추출한다."""

    pattern = re.compile(rf"CREATE POLICY {re.escape(policy_name)}\b[\s\S]*?;", re.MULTILINE)
    match = pattern.search(sql_text)
    if not match:
        raise AssertionError(f"{policy_name} 정책 구문을 찾지 못했습니다.")
    return match.group(0)


class SetupSupabaseSqlTests(unittest.TestCase):
    """`setup_supabase.sql`의 RLS 정책 회귀를 검증한다."""

    def test_create_policy_names_are_unique(self) -> None:
        """동일한 정책명이 여러 번 `CREATE POLICY` 되지 않는지 확인한다."""

        sql_text = read_setup_sql()
        policy_names = re.findall(r"CREATE POLICY ([a-zA-Z0-9_]+)", sql_text)
        duplicate_names = sorted(name for name, count in Counter(policy_names).items() if count > 1)

        self.assertEqual(
            duplicate_names,
            [],
            msg=f"중복 CREATE POLICY 정의 발견: {', '.join(duplicate_names)}",
        )

    def test_holdings_update_policy_has_local_drop_before_create(self) -> None:
        """`holdings_update_own`은 블록 재실행 전용 DROP 구문을 바로 앞에 둔다."""

        sql_text = read_setup_sql()
        pattern = re.compile(
            r"DROP POLICY IF EXISTS holdings_update_own ON public\.holdings;\s+CREATE POLICY holdings_update_own",
            re.MULTILINE,
        )

        self.assertRegex(sql_text, pattern)

    def test_daily_interest_update_policy_has_local_drop_before_create(self) -> None:
        """`daily_interest_update_own`은 블록 재실행 전용 DROP 구문을 바로 앞에 둔다."""

        sql_text = read_setup_sql()
        pattern = re.compile(
            r"DROP POLICY IF EXISTS daily_interest_update_own ON public\.daily_interest;\s+CREATE POLICY daily_interest_update_own",
            re.MULTILINE,
        )

        self.assertRegex(sql_text, pattern)

    def test_update_policy_blocks_have_balanced_parentheses(self) -> None:
        """문제 후보였던 UPDATE 정책 블록의 괄호 수가 균형인지 확인한다."""

        sql_text = read_setup_sql()
        policy_names = (
            "holdings_update_own",
            "daily_interest_update_own",
        )

        for policy_name in policy_names:
            with self.subTest(policy_name=policy_name):
                statement = extract_policy_statement(sql_text, policy_name)
                self.assertEqual(statement.count("("), statement.count(")"))
                self.assertIn("USING (", statement)
                self.assertIn("WITH CHECK (", statement)


if __name__ == "__main__":
    unittest.main()

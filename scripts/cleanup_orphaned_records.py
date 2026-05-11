#!/usr/bin/env python3
"""
cleanup_orphaned_records.py
===========================

이 스크립트는 기존 거래 기록 삭제 처리 이전에 잔존했던 대시보드 잔상을 정리하기 위해
모든 계좌에 대해 holdings를 재계산하는 도구입니다. 기존 패치에서 추가된
`rebuild_account_holdings_from_trade_logs` 함수를 호출하여 각 계좌의 보유 종목을
현재 원장 기준으로 다시 계산합니다.

실행 방법:
    python cleanup_orphaned_records.py

스크립트는 `src.sqlite_db` 모듈의 `list_accounts`와
`rebuild_account_holdings_from_trade_logs` 함수를 사용하며, 작업 완료 후
`src.db.mark_data_dirty()`를 호출해 Streamlit 캐시를 무효화합니다.
"""

from __future__ import annotations

import sys


def main() -> None:
    try:
        # 로컬 모듈 import. 프로젝트 루트에서 실행해야 함.
        from src import sqlite_db  # type: ignore
        from src.db import mark_data_dirty  # type: ignore
    except Exception as exc:
        print("❌ 모듈을 불러오지 못했습니다. 프로젝트 루트에서 실행했는지 확인하세요.")
        print(f"세부 오류: {exc}")
        sys.exit(1)

    try:
        accounts = sqlite_db.list_accounts()
    except Exception as exc:
        print("❌ 계좌 목록을 불러오는 데 실패했습니다.")
        print(f"세부 오류: {exc}")
        sys.exit(1)

    if not accounts:
        print("ℹ️ 재계산할 계좌가 없습니다.")
        return

    total_rebuilt = 0
    for account in accounts:
        try:
            account_id = int(account.get("id"))
        except Exception:
            continue
        try:
            sqlite_db.rebuild_account_holdings_from_trade_logs(account_id)
            total_rebuilt += 1
        except Exception as exc:
            print(f"⚠️ 계좌 {account_id} 재계산 중 오류 발생: {exc}")
            continue

    try:
        # 데이터 캐시 무효화
        mark_data_dirty()
    except Exception:
        pass

    print(f"✅ {total_rebuilt}개의 계좌에 대해 holdings를 재계산했습니다.")
    print("대시보드를 새로고침하여 변경 사항을 확인하세요.")


if __name__ == "__main__":
    main()
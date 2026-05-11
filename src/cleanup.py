"""
cleanup.py
==========

보유 종목 정리 유틸리티입니다.
거래 기록 삭제 처리 후 발생할 수 있는 orphaned holdings를 정리합니다.
"""

from __future__ import annotations

from typing import Any


def cleanup_orphaned_holdings() -> dict[str, Any]:
    """모든 계좌에 대해 holdings를 재계산합니다.
    
    거래 기록 삭제 처리 이전에 잔존했던 대시보드 잔상을 정리하기 위해
    holdings 테이블을 현재 원장 기준으로 다시 계산합니다.
    
    Returns:
        dict: 작업 결과 요약
            - success: 성공 여부
            - rebuilt_count: 재계산된 계좌 수
            - message: 결과 메시지
            - errors: 발생한 오류 목록
    """
    try:
        from src import sqlite_db  # type: ignore
        from src.db import mark_data_dirty  # type: ignore
    except Exception as exc:
        return {
            "success": False,
            "rebuilt_count": 0,
            "message": f"❌ 모듈 로딩 실패: {exc}",
            "errors": [str(exc)],
        }

    try:
        accounts = sqlite_db.list_accounts()
    except Exception as exc:
        return {
            "success": False,
            "rebuilt_count": 0,
            "message": f"❌ 계좌 목록 조회 실패: {exc}",
            "errors": [str(exc)],
        }

    if not accounts:
        return {
            "success": True,
            "rebuilt_count": 0,
            "message": "ℹ️ 재계산할 계좌가 없습니다.",
            "errors": [],
        }

    total_rebuilt = 0
    errors: list[str] = []

    for account in accounts:
        try:
            account_id = int(account.get("id"))
        except Exception:
            continue

        try:
            sqlite_db.rebuild_account_holdings_from_trade_logs(account_id)
            total_rebuilt += 1
        except Exception as exc:
            error_msg = f"계좌 {account_id} 재계산 중 오류: {exc}"
            errors.append(error_msg)
            continue

    try:
        mark_data_dirty()
    except Exception:
        pass

    message = f"✅ {total_rebuilt}개의 계좌에 대해 holdings를 재계산했습니다."
    if errors:
        message += f"\n⚠️ {len(errors)}개의 오류 발생"

    return {
        "success": True,
        "rebuilt_count": total_rebuilt,
        "message": message,
        "errors": errors,
    }

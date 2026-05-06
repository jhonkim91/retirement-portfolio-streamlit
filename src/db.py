from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import requests
import streamlit as st


DEFAULT_SUPABASE_URL = "https://iyszkybxostbjfzbbymq.supabase.co"


def _get_config_value(name: str, default: str = "") -> str:
    try:
        secret_value = st.secrets.get(name)
    except Exception:
        secret_value = None
    if secret_value not in (None, ""):
        return str(secret_value).strip()
    return str(os.getenv(name, default)).strip()


SUPABASE_URL = _get_config_value("SUPABASE_URL", DEFAULT_SUPABASE_URL)
SUPABASE_KEY = _get_config_value("SUPABASE_KEY")


def _ensure_supabase_config() -> None:
    missing: list[str] = []
    if not SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not SUPABASE_KEY:
        missing.append("SUPABASE_KEY")
    if missing:
        raise RuntimeError(
            "Supabase 설정이 누락되었습니다. Streamlit Secrets 또는 환경 변수에 "
            + ", ".join(missing)
            + " 값을 추가해 주세요."
        )


def _build_headers() -> dict[str, str]:
    _ensure_supabase_config()
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


def _supabase_request(
    method: str,
    table: str,
    data: dict[str, Any] | None = None,
    filters: dict[str, str | int] | None = None,
) -> list[dict[str, Any]] | dict[str, Any] | None:
    """Supabase REST API 요청"""
    _ensure_supabase_config()
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = _build_headers()

    if method == "GET":
        params = ""
        if filters:
            for key, value in filters.items():
                if params:
                    params += "&"
                params += f'{key}=eq.{value}'
        if params:
            url += f"?{params}"

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()

    elif method == "POST":
        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()
        return result[0] if isinstance(result, list) and result else result

    elif method == "PATCH":
        if filters:
            params = ""
            for key, value in filters.items():
                if params:
                    params += "&"
                params += f'{key}=eq.{value}'
            if params:
                url += f"?{params}"

        response = requests.patch(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()
        return result[0] if isinstance(result, list) and result else result

    elif method == "DELETE":
        if filters:
            params = ""
            for key, value in filters.items():
                if params:
                    params += "&"
                params += f'{key}=eq.{value}'
            if params:
                url += f"?{params}"

        response = requests.delete(url, headers=headers, timeout=10)
        response.raise_for_status()
        return None


def initialize_database() -> None:
    """테이블 초기화 (Supabase는 수동으로 생성 필요)"""
    # Supabase SQL Editor에서 setup_supabase.sql 실행 필요
    try:
        # 테이블 존재 여부 확인
        _supabase_request("GET", "accounts", filters={})
    except Exception as e:
        st.error(
            f"""
            ⚠️ Supabase 테이블을 초기화해야 합니다.
            
            1. https://app.supabase.com 에서 프로젝트 선택
            2. SQL Editor > New query 클릭
            3. setup_supabase.sql 파일의 내용 복사 & 실행
            
            에러: {e}
            """
        )


def list_accounts() -> list[dict[str, Any]]:
    try:
        result = _supabase_request("GET", "accounts", filters={})
        return sorted(result or [], key=lambda x: x.get("name", "").lower())
    except Exception as e:
        st.error(f"계좌 목록 조회 실패: {e}")
        return []


def get_account(account_id: int) -> dict[str, Any] | None:
    try:
        result = _supabase_request("GET", "accounts", filters={"id": account_id})
        return result[0] if isinstance(result, list) and result else result
    except Exception as e:
        st.error(f"계좌 조회 실패: {e}")
        return None


def create_account(name: str, account_type: str = "retirement", opening_cash: float = 0) -> int:
    cleaned_name = str(name or "").strip()
    if not cleaned_name:
        raise ValueError("계좌 이름을 입력해 주세요.")

    cleaned_type = str(account_type or "retirement").strip().lower()
    if cleaned_type not in {"retirement", "brokerage"}:
        raise ValueError("계좌 유형은 retirement 또는 brokerage만 지원합니다.")

    timestamp = now_iso()
    try:
        result = _supabase_request(
            "POST",
            "accounts",
            data={
                "name": cleaned_name,
                "account_type": cleaned_type,
                "cash_balance": float(opening_cash or 0),
                "created_at": timestamp,
                "updated_at": timestamp,
            },
        )
        return int(result.get("id") if isinstance(result, dict) else result[0]["id"])
    except Exception as e:
        if "unique" in str(e).lower():
            raise ValueError("같은 이름의 계좌가 이미 있습니다.") from e
        raise


def update_cash_balance(account_id: int, amount: float) -> None:
    if float(amount) < 0:
        raise ValueError("현금은 0 이상이어야 합니다.")
    try:
        _supabase_request(
            "PATCH",
            "accounts",
            data={"cash_balance": float(amount), "updated_at": now_iso()},
            filters={"id": account_id},
        )
    except Exception as e:
        raise ValueError(f"현금 잔액 업데이트 실패: {e}") from e


def list_holdings(account_id: int, include_closed: bool = False) -> list[dict[str, Any]]:
    try:
        result = _supabase_request("GET", "holdings", filters={"account_id": account_id})
        holdings = result or []
        if not include_closed:
            holdings = [h for h in holdings if float(h.get("quantity", 0)) > 0]
        return sorted(
            holdings,
            key=lambda x: float(x.get("current_price", 0)) * float(x.get("quantity", 0)),
            reverse=True,
        )
    except Exception as e:
        st.error(f"보유 종목 조회 실패: {e}")
        return []


def set_holding_price(holding_id: int, current_price: float, as_of: str | None = None) -> None:
    try:
        _supabase_request(
            "PATCH",
            "holdings",
            data={
                "current_price": float(current_price or 0),
                "price_updated_at": as_of or now_iso(),
                "updated_at": now_iso(),
            },
            filters={"id": holding_id},
        )
    except Exception as e:
        raise ValueError(f"시세 업데이트 실패: {e}") from e


def list_trade_logs(account_id: int) -> list[dict[str, Any]]:
    try:
        result = _supabase_request("GET", "trade_logs", filters={"account_id": account_id})
        logs = result or []
        return sorted(logs, key=lambda x: (x.get("trade_date", ""), x.get("id", 0)), reverse=True)
    except Exception as e:
        st.error(f"거래 기록 조회 실패: {e}")
        return []


def export_dataframe_rows(table_name: str) -> list[dict[str, Any]]:
    if table_name not in {"accounts", "holdings", "trade_logs"}:
        raise ValueError("지원하지 않는 테이블입니다.")
    try:
        result = _supabase_request("GET", table_name, filters={})
        return sorted(result or [], key=lambda x: x.get("id", 0))
    except Exception as e:
        st.error(f"테이블 조회 실패: {e}")
        return []


def record_trade(
    account_id: int,
    *,
    symbol: str,
    product_name: str,
    trade_type: str,
    asset_type: str,
    quantity: float,
    price: float,
    trade_date: str,
    notes: str = "",
) -> None:
    cleaned_symbol = str(symbol or "").strip().upper()
    cleaned_name = str(product_name or "").strip()
    cleaned_type = str(trade_type or "").strip().lower()
    cleaned_asset_type = str(asset_type or "risk").strip().lower()

    if cleaned_type not in {"buy", "sell"}:
        raise ValueError("매수/매도 거래만 기록할 수 있습니다.")
    if cleaned_asset_type not in {"risk", "safe"}:
        raise ValueError("자산군은 risk 또는 safe만 지원합니다.")
    if not cleaned_symbol:
        raise ValueError("종목 코드를 입력해 주세요.")
    if not cleaned_name:
        raise ValueError("종목명을 입력해 주세요.")

    share_count = float(quantity or 0)
    trade_price = float(price or 0)
    if share_count <= 0 or trade_price <= 0:
        raise ValueError("수량과 가격은 모두 0보다 커야 합니다.")

    total_amount = share_count * trade_price
    timestamp = now_iso()

    try:
        # 계좌 확인
        account = get_account(account_id)
        if not account:
            raise ValueError("계좌를 찾을 수 없습니다.")

        # 보유 종목 확인
        holdings = _supabase_request("GET", "holdings", filters={"account_id": account_id})
        holdings = [h for h in (holdings or []) if h.get("symbol") == cleaned_symbol]
        holding_row = holdings[0] if holdings else None

        cash_balance = float(account.get("cash_balance", 0))

        if cleaned_type == "buy":
            if cash_balance + 0.000001 < total_amount:
                raise ValueError("현금이 부족합니다. 현금 입금 후 다시 시도해 주세요.")

            if holding_row:
                previous_quantity = float(holding_row.get("quantity", 0))
                previous_cost = float(holding_row.get("avg_cost", 0))
                next_quantity = previous_quantity + share_count
                weighted_avg_cost = ((previous_quantity * previous_cost) + total_amount) / next_quantity
                _supabase_request(
                    "PATCH",
                    "holdings",
                    data={
                        "product_name": cleaned_name,
                        "asset_type": cleaned_asset_type,
                        "quantity": next_quantity,
                        "avg_cost": weighted_avg_cost,
                        "updated_at": timestamp,
                    },
                    filters={"id": holding_row["id"]},
                )
            else:
                _supabase_request(
                    "POST",
                    "holdings",
                    data={
                        "account_id": account_id,
                        "symbol": cleaned_symbol,
                        "product_name": cleaned_name,
                        "asset_type": cleaned_asset_type,
                        "quantity": share_count,
                        "avg_cost": trade_price,
                        "current_price": trade_price,
                        "price_updated_at": timestamp,
                        "created_at": timestamp,
                        "updated_at": timestamp,
                    },
                )

            update_cash_balance(account_id, cash_balance - total_amount)
        else:  # sell
            if not holding_row:
                raise ValueError("매도할 보유 종목이 없습니다.")

            previous_quantity = float(holding_row.get("quantity", 0))
            if previous_quantity + 0.000001 < share_count:
                raise ValueError("보유 수량보다 많은 수량을 매도할 수 없습니다.")

            next_quantity = previous_quantity - share_count
            avg_cost = float(holding_row.get("avg_cost", 0))
            _supabase_request(
                "PATCH",
                "holdings",
                data={
                    "quantity": max(next_quantity, 0),
                    "avg_cost": avg_cost if next_quantity > 0 else 0,
                    "updated_at": timestamp,
                },
                filters={"id": holding_row["id"]},
            )
            update_cash_balance(account_id, cash_balance + total_amount)

        # 거래 기록
        _supabase_request(
            "POST",
            "trade_logs",
            data={
                "account_id": account_id,
                "symbol": cleaned_symbol,
                "product_name": cleaned_name,
                "trade_type": cleaned_type,
                "asset_type": cleaned_asset_type,
                "quantity": share_count,
                "price": trade_price,
                "total_amount": total_amount,
                "trade_date": trade_date,
                "notes": str(notes or "").strip(),
                "created_at": timestamp,
            },
        )
    except Exception as e:
        raise ValueError(f"거래 기록 실패: {e}") from e


def record_cash_flow(
    account_id: int,
    *,
    flow_type: str,
    amount: float,
    trade_date: str,
    notes: str = "",
) -> None:
    """현금 입출금 기록"""
    cleaned_type = str(flow_type or "").strip().lower()
    if cleaned_type not in {"deposit", "withdraw"}:
        raise ValueError("입금/출금만 기록할 수 있습니다.")

    flow_amount = float(amount or 0)
    if flow_amount <= 0:
        raise ValueError("금액은 0보다 커야 합니다.")

    account = get_account(account_id)
    if not account:
        raise ValueError("계좌를 찾을 수 없습니다.")

    cash_balance = float(account.get("cash_balance", 0))

    if cleaned_type == "deposit":
        new_balance = cash_balance + flow_amount
    else:
        if cash_balance + 0.000001 < flow_amount:
            raise ValueError("출금 금액이 현금 잔액을 초과합니다.")
        new_balance = cash_balance - flow_amount

    timestamp = now_iso()
    try:
        update_cash_balance(account_id, new_balance)

        # 현금 흐름 기록 (별도 테이블이 없으면 trade_logs에 기록)
        _supabase_request(
            "POST",
            "trade_logs",
            data={
                "account_id": account_id,
                "product_name": "현금 입출금",
                "trade_type": cleaned_type,
                "asset_type": "cash",
                "quantity": flow_amount,
                "price": 1,
                "total_amount": flow_amount,
                "trade_date": trade_date,
                "notes": str(notes or "").strip(),
                "created_at": timestamp,
            },
        )
    except Exception as e:
        raise ValueError(f"현금 흐름 기록 실패: {e}") from e

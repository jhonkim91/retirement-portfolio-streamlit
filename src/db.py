from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Callable, TypeVar

import requests
import streamlit as st

from . import sqlite_db


T = TypeVar("T")

DEFAULT_SUPABASE_URL = "https://iyszkybxostbjfzbbymq.supabase.co"
DEFAULT_BACKEND = "supabase"
BACKEND_SQLITE = "sqlite"
BACKEND_SUPABASE = "supabase"


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
BACKEND_OVERRIDE = _get_config_value("PORTFOLIO_BACKEND", DEFAULT_BACKEND).lower()

_BACKEND_STATE: dict[str, str] = {
    "name": "",
    "reason": "",
}


def _set_backend(name: str, reason: str = "") -> None:
    _BACKEND_STATE["name"] = name
    _BACKEND_STATE["reason"] = reason


def _has_supabase_config() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def _select_initial_backend() -> str:
    if BACKEND_OVERRIDE in {BACKEND_SQLITE, BACKEND_SUPABASE}:
        return BACKEND_OVERRIDE
    return BACKEND_SUPABASE if _has_supabase_config() else BACKEND_SQLITE


def _current_backend() -> str:
    backend = _BACKEND_STATE["name"]
    if backend:
        return backend

    backend = _select_initial_backend()
    reason = ""
    if backend == BACKEND_SQLITE and not _has_supabase_config():
        reason = "Supabase secrets are missing, so the app is using local SQLite storage."
    _set_backend(backend, reason)
    return backend


def backend_status() -> dict[str, str]:
    return {
        "name": _current_backend(),
        "reason": _BACKEND_STATE["reason"],
    }


def _activate_sqlite(reason: str) -> None:
    sqlite_db.initialize_database()
    _set_backend(BACKEND_SQLITE, reason)


def _build_headers() -> dict[str, str]:
    if not _has_supabase_config():
        raise RuntimeError("SUPABASE_URL or SUPABASE_KEY is missing.")

    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


def _query_string(filters: dict[str, str | int] | None) -> str:
    if not filters:
        return ""
    return "&".join(f"{key}=eq.{value}" for key, value in filters.items())


def _supabase_request(
    method: str,
    table: str,
    data: dict[str, Any] | None = None,
    filters: dict[str, str | int] | None = None,
) -> list[dict[str, Any]] | dict[str, Any] | None:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    query = _query_string(filters)
    if query:
        url = f"{url}?{query}"

    response = requests.request(
        method=method,
        url=url,
        json=data,
        headers=_build_headers(),
        timeout=10,
    )

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = response.text.strip().replace("\n", " ")
        raise requests.HTTPError(
            f"Supabase {method} {table} failed ({response.status_code}): {detail}",
            response=response,
            request=response.request,
        ) from exc

    if method == "DELETE":
        return None

    payload = response.json()
    if method in {"POST", "PATCH"}:
        return payload[0] if isinstance(payload, list) and payload else payload
    return payload


def _fallback_reason(exc: Exception) -> str:
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        response = exc.response
        detail = response.text.strip().replace("\n", " ")
        detail = detail[:180] if detail else "Supabase rejected the request."
        return f"Supabase HTTP {response.status_code}: {detail}"

    message = str(exc).strip() or exc.__class__.__name__
    return message[:180]


def _should_fallback(exc: Exception) -> bool:
    if isinstance(exc, (RuntimeError, requests.RequestException)):
        return True

    message = str(exc).lower()
    markers = (
        "permission denied",
        "row-level security",
        "not found",
        "could not find the table",
        "relation",
        "schema cache",
        "duplicate key value",
        "failed to connect",
        "timed out",
    )
    return any(marker in message for marker in markers)


def _run_with_fallback(
    *,
    supabase_call: Callable[[], T],
    sqlite_call: Callable[[], T],
) -> T:
    if _current_backend() == BACKEND_SQLITE:
        return sqlite_call()

    try:
        return supabase_call()
    except Exception as exc:
        if not _should_fallback(exc):
            raise

        _activate_sqlite(_fallback_reason(exc))
        return sqlite_call()


def _supabase_initialize_database() -> None:
    _supabase_request("GET", "accounts")


def _supabase_list_accounts() -> list[dict[str, Any]]:
    result = _supabase_request("GET", "accounts")
    return sorted(result or [], key=lambda row: str(row.get("name", "")).lower())


def _supabase_get_account(account_id: int) -> dict[str, Any] | None:
    result = _supabase_request("GET", "accounts", filters={"id": account_id})
    return result[0] if isinstance(result, list) and result else result


def _supabase_create_account(name: str, account_type: str = "retirement", opening_cash: float = 0) -> int:
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
        if isinstance(result, dict):
            return int(result["id"])
        return int(result[0]["id"])
    except Exception as exc:
        if "unique" in str(exc).lower():
            raise ValueError("같은 이름의 계좌가 이미 있습니다.") from exc
        raise


def _supabase_update_cash_balance(account_id: int, amount: float) -> None:
    if float(amount) < 0:
        raise ValueError("현금은 0 이상이어야 합니다.")

    _supabase_request(
        "PATCH",
        "accounts",
        data={"cash_balance": float(amount), "updated_at": now_iso()},
        filters={"id": account_id},
    )


def _supabase_list_holdings(account_id: int, include_closed: bool = False) -> list[dict[str, Any]]:
    result = _supabase_request("GET", "holdings", filters={"account_id": account_id})
    holdings = result or []
    if not include_closed:
        holdings = [row for row in holdings if float(row.get("quantity", 0) or 0) > 0]
    return sorted(
        holdings,
        key=lambda row: float(row.get("current_price", 0) or 0) * float(row.get("quantity", 0) or 0),
        reverse=True,
    )


def _supabase_set_holding_price(holding_id: int, current_price: float, as_of: str | None = None) -> None:
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


def _supabase_list_trade_logs(account_id: int) -> list[dict[str, Any]]:
    result = _supabase_request("GET", "trade_logs", filters={"account_id": account_id})
    logs = result or []
    return sorted(logs, key=lambda row: (row.get("trade_date", ""), row.get("id", 0)), reverse=True)


def _supabase_export_dataframe_rows(table_name: str) -> list[dict[str, Any]]:
    if table_name not in {"accounts", "holdings", "trade_logs"}:
        raise ValueError("지원하지 않는 테이블입니다.")
    result = _supabase_request("GET", table_name)
    return sorted(result or [], key=lambda row: row.get("id", 0))


def _supabase_record_trade(
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

    account = _supabase_get_account(account_id)
    if not account:
        raise ValueError("계좌를 찾을 수 없습니다.")

    holdings = _supabase_request("GET", "holdings", filters={"account_id": account_id}) or []
    holdings = [row for row in holdings if row.get("symbol") == cleaned_symbol]
    holding_row = holdings[0] if holdings else None
    cash_balance = float(account.get("cash_balance", 0) or 0)

    if cleaned_type == "buy":
        if cash_balance + 0.000001 < total_amount:
            raise ValueError("현금이 부족합니다. 현금 입금 후 다시 시도해 주세요.")

        if holding_row:
            previous_quantity = float(holding_row.get("quantity", 0) or 0)
            previous_cost = float(holding_row.get("avg_cost", 0) or 0)
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

        _supabase_update_cash_balance(account_id, cash_balance - total_amount)
    else:
        if not holding_row:
            raise ValueError("매도할 보유 종목이 없습니다.")

        previous_quantity = float(holding_row.get("quantity", 0) or 0)
        if previous_quantity + 0.000001 < share_count:
            raise ValueError("보유 수량보다 많은 수량을 매도할 수 없습니다.")

        next_quantity = previous_quantity - share_count
        avg_cost = float(holding_row.get("avg_cost", 0) or 0)
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
        _supabase_update_cash_balance(account_id, cash_balance + total_amount)

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


def _supabase_record_cash_flow(
    account_id: int,
    *,
    flow_type: str,
    amount: float,
    trade_date: str,
    notes: str = "",
) -> None:
    cleaned_type = str(flow_type or "").strip().lower()
    if cleaned_type not in {"deposit", "withdraw"}:
        raise ValueError("입금 또는 출금만 기록할 수 있습니다.")

    flow_amount = float(amount or 0)
    if flow_amount <= 0:
        raise ValueError("금액은 0보다 커야 합니다.")

    account = _supabase_get_account(account_id)
    if not account:
        raise ValueError("계좌를 찾을 수 없습니다.")

    cash_balance = float(account.get("cash_balance", 0) or 0)
    if cleaned_type == "deposit":
        new_balance = cash_balance + flow_amount
    else:
        if cash_balance + 0.000001 < flow_amount:
            raise ValueError("출금 금액이 현금 잔액을 초과합니다.")
        new_balance = cash_balance - flow_amount

    timestamp = now_iso()
    _supabase_update_cash_balance(account_id, new_balance)
    _supabase_request(
        "POST",
        "trade_logs",
        data={
            "account_id": account_id,
            "symbol": "",
            "product_name": "Cash Flow",
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


def initialize_database() -> None:
    sqlite_db.initialize_database()
    _run_with_fallback(
        supabase_call=_supabase_initialize_database,
        sqlite_call=sqlite_db.initialize_database,
    )


def list_accounts() -> list[dict[str, Any]]:
    return _run_with_fallback(
        supabase_call=_supabase_list_accounts,
        sqlite_call=sqlite_db.list_accounts,
    )


def get_account(account_id: int) -> dict[str, Any] | None:
    return _run_with_fallback(
        supabase_call=lambda: _supabase_get_account(account_id),
        sqlite_call=lambda: sqlite_db.get_account(account_id),
    )


def create_account(name: str, account_type: str = "retirement", opening_cash: float = 0) -> int:
    return _run_with_fallback(
        supabase_call=lambda: _supabase_create_account(name, account_type, opening_cash),
        sqlite_call=lambda: sqlite_db.create_account(name, account_type, opening_cash),
    )


def update_cash_balance(account_id: int, amount: float) -> None:
    _run_with_fallback(
        supabase_call=lambda: _supabase_update_cash_balance(account_id, amount),
        sqlite_call=lambda: sqlite_db.update_cash_balance(account_id, amount),
    )


def list_holdings(account_id: int, include_closed: bool = False) -> list[dict[str, Any]]:
    return _run_with_fallback(
        supabase_call=lambda: _supabase_list_holdings(account_id, include_closed),
        sqlite_call=lambda: sqlite_db.list_holdings(account_id, include_closed),
    )


def set_holding_price(holding_id: int, current_price: float, as_of: str | None = None) -> None:
    _run_with_fallback(
        supabase_call=lambda: _supabase_set_holding_price(holding_id, current_price, as_of),
        sqlite_call=lambda: sqlite_db.set_holding_price(holding_id, current_price, as_of),
    )


def list_trade_logs(account_id: int) -> list[dict[str, Any]]:
    return _run_with_fallback(
        supabase_call=lambda: _supabase_list_trade_logs(account_id),
        sqlite_call=lambda: sqlite_db.list_trade_logs(account_id),
    )


def export_dataframe_rows(table_name: str) -> list[dict[str, Any]]:
    return _run_with_fallback(
        supabase_call=lambda: _supabase_export_dataframe_rows(table_name),
        sqlite_call=lambda: sqlite_db.export_dataframe_rows(table_name),
    )


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
    _run_with_fallback(
        supabase_call=lambda: _supabase_record_trade(
            account_id,
            symbol=symbol,
            product_name=product_name,
            trade_type=trade_type,
            asset_type=asset_type,
            quantity=quantity,
            price=price,
            trade_date=trade_date,
            notes=notes,
        ),
        sqlite_call=lambda: sqlite_db.record_trade(
            account_id,
            symbol=symbol,
            product_name=product_name,
            trade_type=trade_type,
            asset_type=asset_type,
            quantity=quantity,
            price=price,
            trade_date=trade_date,
            notes=notes,
        ),
    )


def record_cash_flow(
    account_id: int,
    *,
    flow_type: str,
    amount: float,
    trade_date: str,
    notes: str = "",
) -> None:
    _run_with_fallback(
        supabase_call=lambda: _supabase_record_cash_flow(
            account_id,
            flow_type=flow_type,
            amount=amount,
            trade_date=trade_date,
            notes=notes,
        ),
        sqlite_call=lambda: sqlite_db.record_cash_flow(
            account_id,
            flow_type=flow_type,
            amount=amount,
            trade_date=trade_date,
            notes=notes,
        ),
    )

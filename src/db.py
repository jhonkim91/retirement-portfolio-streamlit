from __future__ import annotations

import base64
import os
from datetime import datetime
from urllib.parse import urlparse
from typing import Any, Callable, TypeVar

import requests
import streamlit as st

from . import auth as app_auth
from . import sqlite_db


T = TypeVar("T")

DEFAULT_SUPABASE_URL = "https://iyszkybxostbjfzbbymq.supabase.co"
BACKEND_AUTO = "auto"
DEFAULT_BACKEND = BACKEND_AUTO
BACKEND_SQLITE = "sqlite"
BACKEND_SUPABASE = "supabase"
BACKEND_STATE_KEY = "db_backend_state"
ACCOUNT_NAMESPACE_SEPARATOR = "::"
_FALLBACK_STATE: dict[str, Any] = {}
BUY_SELL_TRADE_TYPES = {"buy", "sell"}
LEGACY_CASH_FLOW_TYPE_MAP = {
    "deposit": "personal_deposit",
    "withdraw": "withdraw",
}
CASH_EVENT_LABELS = {
    "personal_deposit": "개인 입금",
    "employer_deposit": "회사 납입금",
    "withdraw": "일반 출금",
    "interest": "일별 이자",
    "transfer_out": "계좌 이체 출금",
    "transfer_in": "계좌 이체 입금",
    "cash_adjustment": "현금 조정",
}
EXPORTABLE_TABLES = {"accounts", "holdings", "trade_logs", "daily_interest", "daily_account_snapshot"}


def _state_store() -> dict[str, Any]:
    try:
        return st.session_state
    except Exception:
        return _FALLBACK_STATE


def _get_config_value(name: str, default: str = "") -> str:
    try:
        secret_value = st.secrets.get(name)
    except Exception:
        secret_value = None
    if secret_value not in (None, ""):
        return str(secret_value).strip()
    return str(os.getenv(name, default)).strip()


def _read_config_value(name: str, default: str = "") -> tuple[str, str]:
    """설정값과 값의 출처를 함께 반환한다."""

    try:
        secret_value = st.secrets.get(name)
    except Exception:
        secret_value = None
    if secret_value not in (None, ""):
        return str(secret_value).strip(), "secret"

    env_value = os.getenv(name)
    if env_value not in (None, ""):
        return str(env_value).strip(), "env"

    default_value = str(default).strip()
    if default_value:
        return default_value, "default"
    return "", "missing"


def _supabase_url() -> str:
    """현재 세션에서 사용할 Supabase URL을 반환한다."""

    return _read_config_value("SUPABASE_URL", DEFAULT_SUPABASE_URL)[0]


def _supabase_key() -> str:
    """현재 세션에서 사용할 Supabase 키를 반환한다."""

    return _read_config_value("SUPABASE_KEY")[0]


def _backend_override_value() -> str:
    """현재 세션의 백엔드 강제 설정값을 반환한다."""

    return _read_config_value("PORTFOLIO_BACKEND", DEFAULT_BACKEND)[0].lower()


def _config_source_label(source: str) -> str:
    """설정값 출처를 사용자 친화적인 한글 라벨로 바꾼다."""

    return {
        "secret": "streamlit_secret",
        "env": "environment",
        "default": "default",
        "missing": "missing",
    }.get(source, source or "unknown")


def _masked_supabase_project() -> str:
    """운영 상태 패널에 보여줄 Supabase 프로젝트 호스트를 반환한다."""

    url = _supabase_url()
    if not url:
        return ""
    return urlparse(url).netloc or url


def _backend_state() -> dict[str, str]:
    store = _state_store()
    state = store.get(BACKEND_STATE_KEY)
    if isinstance(state, dict) and {"name", "reason"} <= set(state):
        return state
    state = {"name": "", "reason": ""}
    store[BACKEND_STATE_KEY] = state
    return state


def _set_backend(name: str, reason: str = "") -> None:
    state = _backend_state()
    state["name"] = name
    state["reason"] = reason


def _has_supabase_config() -> bool:
    return bool(_supabase_url() and _supabase_key())


def _normalized_backend_override() -> str:
    """지원하는 백엔드 강제 설정값만 반환한다."""

    normalized = str(_backend_override_value() or "").strip().lower()
    if normalized in {BACKEND_AUTO, BACKEND_SQLITE, BACKEND_SUPABASE}:
        return normalized
    return BACKEND_AUTO


def _sqlite_has_user_data() -> bool:
    try:
        user_id = app_auth.get_user_id()
    except Exception:
        return False
    if not user_id:
        return False

    prefix = f"{user_id}{ACCOUNT_NAMESPACE_SEPARATOR}"
    try:
        sqlite_db.initialize_database()
        return any(str(account.get("name") or "").startswith(prefix) for account in sqlite_db.list_accounts())
    except Exception:
        return False


def _select_initial_backend() -> tuple[str, str]:
    """현재 환경에서 우선 사용할 저장소와 선택 사유를 반환한다."""

    override = _normalized_backend_override()
    if override == BACKEND_SUPABASE:
        return BACKEND_SUPABASE, "PORTFOLIO_BACKEND=supabase 설정으로 Supabase 저장소를 강제 사용 중입니다."
    if override == BACKEND_SQLITE:
        return BACKEND_SQLITE, "PORTFOLIO_BACKEND=sqlite 설정으로 로컬 SQLite 저장소를 강제 사용 중입니다."
    if _has_supabase_config():
        return BACKEND_SUPABASE, "Supabase 설정을 감지해 Supabase 저장소를 우선 사용합니다."
    if _sqlite_has_user_data():
        return BACKEND_SQLITE, "Supabase 설정이 없어 기존 로컬 SQLite 데이터를 사용 중입니다."
    return BACKEND_SQLITE, "Supabase 설정이 없어 로컬 SQLite 저장소를 사용 중입니다."


def _current_backend() -> str:
    state = _backend_state()
    backend = state["name"]
    if backend:
        return backend

    backend, reason = _select_initial_backend()
    _set_backend(backend, reason)
    return backend


def backend_status() -> dict[str, Any]:
    """현재 세션의 저장소 선택 상태와 설정 진단 정보를 반환한다."""

    state = _backend_state()
    supabase_url, supabase_url_source = _read_config_value("SUPABASE_URL", DEFAULT_SUPABASE_URL)
    supabase_key, supabase_key_source = _read_config_value("SUPABASE_KEY")
    missing_items: list[str] = []
    notices: list[str] = []

    if not supabase_url:
        missing_items.append("SUPABASE_URL")
    if not supabase_key:
        missing_items.append("SUPABASE_KEY")
    if supabase_url_source == "default":
        notices.append("SUPABASE_URL이 Streamlit secrets나 환경변수에 없어 코드 기본값을 사용 중입니다.")
    if supabase_key_source == "missing":
        notices.append("SUPABASE_KEY가 없어 Supabase 저장소를 활성화할 수 없습니다.")

    return {
        "name": _current_backend(),
        "reason": state["reason"],
        "override": _normalized_backend_override(),
        "has_supabase_config": _has_supabase_config(),
        "supabase_url_present": bool(supabase_url),
        "supabase_key_present": bool(supabase_key),
        "supabase_url_source": _config_source_label(supabase_url_source),
        "supabase_key_source": _config_source_label(supabase_key_source),
        "supabase_project_host": _masked_supabase_project(),
        "missing_config": missing_items,
        "notices": notices,
    }


def _demo_account_totals(account_id: int) -> tuple[float, float, float]:
    """데모 계좌의 현재 현금, 평가금액, 총원가를 계산한다."""

    holdings = list_holdings(account_id)
    total_cost = sum(float(item.get("avg_cost") or 0) * float(item.get("quantity") or 0) for item in holdings)
    market_value = sum(float(item.get("current_price") or 0) * float(item.get("quantity") or 0) for item in holdings)
    account = get_account(account_id) or {}
    cash_balance = float(account.get("cash_balance") or 0)
    return cash_balance, market_value, total_cost


def seed_demo_workspace() -> dict[str, Any]:
    """현재 로그인 사용자 계정에 데모용 샘플 계좌와 거래 데이터를 생성한다."""

    blueprint = _demo_workspace_blueprint()
    existing_accounts = list_accounts()
    existing_by_name = {str(account.get("name") or ""): account for account in existing_accounts}
    demo_names = [str(item["name"]) for item in blueprint["accounts"]]
    existing_demo_accounts = [existing_by_name[name] for name in demo_names if name in existing_by_name]

    if existing_demo_accounts:
        return {
            "created": False,
            "selected_account_id": int(existing_demo_accounts[0]["id"]),
            "account_ids": [int(account["id"]) for account in existing_demo_accounts],
            "message": "이미 데모 계좌가 있어 기존 데이터를 그대로 사용합니다.",
        }

    created_account_ids: dict[str, int] = {}
    for account_spec in blueprint["accounts"]:
        account_id = create_account(
            name=str(account_spec["name"]),
            account_type=str(account_spec["account_type"]),
            opening_cash=float(account_spec.get("opening_cash") or 0),
        )
        created_account_ids[str(account_spec["name"])] = account_id

        for cash_flow in account_spec["cash_flows"]:
            record_cash_flow(
                account_id,
                flow_type=str(cash_flow["flow_type"]),
                amount=float(cash_flow["amount"]),
                trade_date=str(cash_flow["trade_date"]),
                notes=str(cash_flow.get("notes") or ""),
            )

        for trade in account_spec["trades"]:
            record_trade(
                account_id,
                symbol=str(trade["symbol"]),
                product_name=str(trade["product_name"]),
                trade_type=str(trade["trade_type"]),
                asset_type=str(trade["asset_type"]),
                quantity=float(trade["quantity"]),
                price=float(trade["price"]),
                trade_date=str(trade["trade_date"]),
                notes=str(trade.get("notes") or ""),
            )

    for transfer in blueprint["transfers"]:
        record_account_transfer(
            created_account_ids[str(transfer["from_account"])],
            to_account_id=created_account_ids[str(transfer["to_account"])],
            amount=float(transfer["amount"]),
            trade_date=str(transfer["trade_date"]),
            notes=str(transfer.get("notes") or ""),
        )

    for account_spec in blueprint["accounts"]:
        account_id = created_account_ids[str(account_spec["name"])]
        for entry in account_spec["interest"]:
            record_daily_interest(
                account_id,
                interest_date=str(entry["interest_date"]),
                amount=float(entry["amount"]),
            )

        holdings = list_holdings(account_id, include_closed=True)
        holdings_by_symbol = {str(item.get("symbol") or "").upper(): item for item in holdings}
        for symbol, current_price in account_spec["price_updates"].items():
            holding = holdings_by_symbol.get(str(symbol).upper())
            if not holding:
                continue
            set_holding_price(int(holding["id"]), float(current_price), str(account_spec["snapshot_date"]))

        cash_balance, market_value, total_cost = _demo_account_totals(account_id)
        record_account_snapshot(
            account_id,
            snapshot_date=str(account_spec["snapshot_date"]),
            cash_balance=cash_balance,
            market_value=market_value,
            total_value=cash_balance + market_value,
            total_cost=total_cost,
        )

    selected_account_id = created_account_ids[demo_names[0]]
    return {
        "created": True,
        "selected_account_id": selected_account_id,
        "account_ids": list(created_account_ids.values()),
        "message": "데모 계좌와 샘플 거래 데이터를 만들었습니다.",
    }


def _activate_sqlite(reason: str) -> None:
    sqlite_db.initialize_database()
    _set_backend(BACKEND_SQLITE, reason)


def _build_headers(prefer_return: str | None = None) -> dict[str, str]:
    if not _has_supabase_config():
        raise RuntimeError("SUPABASE_URL 또는 SUPABASE_KEY 설정이 없습니다.")

    supabase_key = _supabase_key()
    access_token = None
    if app_auth.is_authenticated():
        app_auth.refresh_session_state()
        access_token = app_auth.get_access_token()
        if not access_token:
            raise RuntimeError("로그인 세션 토큰을 확인하지 못했습니다. 다시 로그인한 뒤 시도해 주세요.")
    else:
        access_token = supabase_key
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    if prefer_return:
        headers["Prefer"] = f"return={prefer_return}"
    return headers


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


def _today_iso_date() -> str:
    """오늘 날짜를 ISO 형식으로 반환한다."""

    return datetime.utcnow().date().isoformat()


def _demo_workspace_blueprint() -> dict[str, Any]:
    """데모 모드에서 생성할 샘플 계좌와 거래 구성을 반환한다."""

    snapshot_date = _today_iso_date()
    return {
        "accounts": (
            {
                "name": "데모 IRP",
                "account_type": "retirement",
                "opening_cash": 0.0,
                "cash_flows": (
                    {"flow_type": "personal_deposit", "amount": 6_000_000, "trade_date": "2026-01-10", "notes": "데모 개인 납입"},
                    {"flow_type": "employer_deposit", "amount": 3_000_000, "trade_date": "2026-01-25", "notes": "데모 회사 납입"},
                ),
                "trades": (
                    {
                        "symbol": "360750",
                        "product_name": "TIGER 미국S&P500",
                        "trade_type": "buy",
                        "asset_type": "risk",
                        "quantity": 15,
                        "price": 130_000,
                        "trade_date": "2026-02-03",
                        "notes": "데모 장기 적립",
                    },
                    {
                        "symbol": "148070",
                        "product_name": "KOSEF 국고채10년",
                        "trade_type": "buy",
                        "asset_type": "safe",
                        "quantity": 25,
                        "price": 110_000,
                        "trade_date": "2026-02-14",
                        "notes": "데모 채권 비중",
                    },
                ),
                "interest": (
                    {"interest_date": "2026-03-31", "amount": 18_500},
                ),
                "price_updates": {
                    "360750": 142_000,
                    "148070": 108_000,
                },
                "snapshot_date": snapshot_date,
            },
            {
                "name": "데모 일반계좌",
                "account_type": "brokerage",
                "opening_cash": 0.0,
                "cash_flows": (
                    {"flow_type": "personal_deposit", "amount": 7_000_000, "trade_date": "2026-02-03", "notes": "데모 투자금 입금"},
                    {"flow_type": "withdraw", "amount": 250_000, "trade_date": "2026-03-04", "notes": "데모 생활비 출금"},
                ),
                "trades": (
                    {
                        "symbol": "005930",
                        "product_name": "삼성전자",
                        "trade_type": "buy",
                        "asset_type": "risk",
                        "quantity": 20,
                        "price": 82_000,
                        "trade_date": "2026-02-11",
                        "notes": "데모 국내 대형주",
                    },
                    {
                        "symbol": "000660",
                        "product_name": "SK하이닉스",
                        "trade_type": "buy",
                        "asset_type": "risk",
                        "quantity": 10,
                        "price": 210_000,
                        "trade_date": "2026-02-18",
                        "notes": "데모 반도체 비중",
                    },
                ),
                "interest": (),
                "price_updates": {
                    "005930": 86_000,
                    "000660": 198_000,
                },
                "snapshot_date": snapshot_date,
            },
        ),
        "transfers": (
            {
                "from_account": "데모 일반계좌",
                "to_account": "데모 IRP",
                "amount": 400_000,
                "trade_date": "2026-03-15",
                "notes": "데모 자금 재배치",
            },
        ),
    }


def _normalize_cash_flow_type(flow_type: str) -> str:
    normalized = str(flow_type or "").strip().lower()
    return LEGACY_CASH_FLOW_TYPE_MAP.get(normalized, normalized)


def _cash_event_label(trade_type: str) -> str:
    normalized = _normalize_cash_flow_type(trade_type)
    return CASH_EVENT_LABELS.get(normalized, normalized)


def _metadata_payload(metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return dict(metadata or {})


def _supabase_request(
    method: str,
    table: str,
    data: dict[str, Any] | None = None,
    filters: dict[str, str | int] | None = None,
    prefer_return: str | None = None,
) -> list[dict[str, Any]] | dict[str, Any] | None:
    request_headers = _build_headers(prefer_return=prefer_return)
    response = requests.request(
        method=method,
        url=f"{_supabase_url()}/rest/v1/{table}",
        json=data,
        params={key: str(value) for key, value in (filters or {}).items()},
        headers=request_headers,
        timeout=10,
    )

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = response.text.strip().replace("\n", " ")
        detail_lower = detail.lower()
        if (
            response.status_code == 403
            and method == "POST"
            and table == "accounts"
            and "row-level security policy" in detail_lower
        ):
            detail = (
                "운영 Supabase의 accounts INSERT RLS 정책이 오래된 상태입니다. "
                "setup_supabase.sql의 owner_user_id 핫픽스를 적용한 뒤 다시 시도해 주세요."
            )
        raise requests.HTTPError(
            f"Supabase {method} {table} 요청에 실패했습니다 ({response.status_code}): {detail}",
            response=response,
            request=response.request,
        ) from exc

    if method == "DELETE":
        return None

    if method in {"POST", "PATCH"}:
        if response.status_code == 204 or not response.content:
            return None
    payload = response.json()
    if method in {"POST", "PATCH"}:
        return payload[0] if isinstance(payload, list) and payload else payload
    return payload


def _supabase_insert_trade_log(
    *,
    account_id: int,
    symbol: str,
    product_name: str,
    trade_type: str,
    asset_type: str,
    quantity: float,
    price: float,
    total_amount: float,
    cash_delta: float,
    trade_date: str,
    notes: str,
    created_at: str,
    event_group_id: str | None = None,
    counterparty_account_id: int | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> None:
    _supabase_request(
        "POST",
        "trade_logs",
        data={
            "account_id": account_id,
            "symbol": symbol,
            "product_name": product_name,
            "trade_type": trade_type,
            "asset_type": asset_type,
            "quantity": quantity,
            "price": price,
            "total_amount": total_amount,
            "cash_delta": cash_delta,
            "event_group_id": event_group_id,
            "counterparty_account_id": counterparty_account_id,
            "metadata_json": _metadata_payload(metadata_json),
            "trade_date": trade_date,
            "notes": str(notes or "").strip(),
            "created_at": created_at,
        },
        prefer_return="minimal",
    )


def _fallback_reason(exc: Exception) -> str:
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        response = exc.response
        detail = response.text.strip().replace("\n", " ")
        detail = detail[:180] if detail else "Supabase 요청이 거부되었습니다."
        return f"Supabase 요청 오류({response.status_code}): {detail}"

    message = str(exc).strip() or exc.__class__.__name__
    return message[:180]


def _should_fallback(exc: Exception) -> bool:
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        if exc.response.status_code in {401, 403}:
            return False

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


def _require_user_id() -> str:
    token_user_id = _token_user_id()
    if token_user_id:
        return token_user_id

    user_id = app_auth.get_user_id()
    if not user_id:
        raise ValueError("포트폴리오를 관리하려면 로그인해 주세요.")
    return user_id


def _token_user_id() -> str | None:
    """액세스 토큰의 sub 클레임에서 사용자 ID를 추출한다."""

    access_token = app_auth.get_access_token()
    if not access_token or access_token.count(".") < 2:
        return None

    try:
        payload_segment = access_token.split(".")[1]
        padding = "=" * (-len(payload_segment) % 4)
        decoded = base64.urlsafe_b64decode(f"{payload_segment}{padding}")
        payload = json.loads(decoded.decode("utf-8"))
    except Exception:
        return None

    subject = str(payload.get("sub") or "").strip()
    return subject or None


def _account_prefix() -> str:
    return f"{_require_user_id()}{ACCOUNT_NAMESPACE_SEPARATOR}"


def _is_owned_name(stored_name: Any) -> bool:
    try:
        return str(stored_name or "").startswith(_account_prefix())
    except ValueError:
        return False


def _visible_account_name(stored_name: Any) -> str:
    text = str(stored_name or "")
    if ACCOUNT_NAMESPACE_SEPARATOR not in text:
        return text
    return text.split(ACCOUNT_NAMESPACE_SEPARATOR, 1)[1]


def _storage_account_name(display_name: str) -> str:
    cleaned_name = str(display_name or "").strip()
    if not cleaned_name:
        raise ValueError("계좌 이름을 입력해 주세요.")
    return f"{_account_prefix()}{cleaned_name}"


def _present_account(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row or not _is_owned_name(row.get("name")):
        return None
    account = dict(row)
    account["name"] = _visible_account_name(account.get("name"))
    return account


def _owned_account_ids(accounts: list[dict[str, Any]]) -> set[int]:
    return {int(account["id"]) for account in accounts if account.get("id") is not None}


def _supabase_initialize_database() -> None:
    if not app_auth.is_authenticated():
        return
    _supabase_request("GET", "accounts")


def _supabase_list_accounts() -> list[dict[str, Any]]:
    if not app_auth.is_authenticated():
        return []
    result = _supabase_request("GET", "accounts")
    accounts = [_present_account(row) for row in (result or [])]
    visible = [account for account in accounts if account]
    return sorted(visible, key=lambda row: str(row.get("name", "")).lower())


def _supabase_get_account(account_id: int) -> dict[str, Any] | None:
    if not app_auth.is_authenticated():
        return None
    result = _supabase_request("GET", "accounts", filters={"id": f"eq.{account_id}"})
    row = result[0] if isinstance(result, list) and result else result
    return _present_account(row if isinstance(row, dict) else None)


def _supabase_create_account(name: str, account_type: str = "retirement", opening_cash: float = 0) -> int:
    cleaned_name = str(name or "").strip()
    if not cleaned_name:
        raise ValueError("계좌 이름을 입력해 주세요.")

    cleaned_type = str(account_type or "retirement").strip().lower()
    if cleaned_type not in {"retirement", "brokerage"}:
        raise ValueError("계좌 유형 값이 올바르지 않습니다.")

    existing_names = {str(account.get("name", "")).lower() for account in _supabase_list_accounts()}
    if cleaned_name.lower() in existing_names:
        raise ValueError("같은 이름의 계좌가 이미 있습니다.")

    timestamp = now_iso()
    stored_name = _storage_account_name(cleaned_name)
    result = _supabase_request(
        "POST",
        "accounts",
        data={
            "name": stored_name,
            "account_type": cleaned_type,
            "cash_balance": float(opening_cash or 0),
            "created_at": timestamp,
            "updated_at": timestamp,
        },
        prefer_return="minimal",
    )
    if isinstance(result, dict) and result.get("id") is not None:
        return int(result["id"])
    if isinstance(result, list) and result and result[0].get("id") is not None:
        return int(result[0]["id"])

    created_account = _supabase_request("GET", "accounts", filters={"name": f"eq.{stored_name}"})
    created_row = created_account[0] if isinstance(created_account, list) and created_account else created_account
    if isinstance(created_row, dict) and created_row.get("id") is not None:
        return int(created_row["id"])
    raise RuntimeError("Supabase account insert succeeded but the new account id could not be resolved.")


def _supabase_update_cash_balance(account_id: int, amount: float) -> None:
    if float(amount) < 0:
        raise ValueError("현금은 0 이상이어야 합니다.")

    if not _supabase_get_account(account_id):
        raise ValueError("계좌를 찾을 수 없습니다.")

    _supabase_request(
        "PATCH",
        "accounts",
        data={"cash_balance": float(amount), "updated_at": now_iso()},
        filters={"id": f"eq.{account_id}"},
        prefer_return="minimal",
    )


def _supabase_list_holdings(account_id: int, include_closed: bool = False) -> list[dict[str, Any]]:
    if not _supabase_get_account(account_id):
        return []

    result = _supabase_request("GET", "holdings", filters={"account_id": f"eq.{account_id}"})
    holdings = result or []
    if not include_closed:
        holdings = [row for row in holdings if float(row.get("quantity", 0) or 0) > 0]
    return sorted(
        holdings,
        key=lambda row: float(row.get("current_price", 0) or 0) * float(row.get("quantity", 0) or 0),
        reverse=True,
    )


def _supabase_set_holding_price(holding_id: int, current_price: float, as_of: str | None = None) -> None:
    _require_user_id()
    _supabase_request(
        "PATCH",
        "holdings",
        data={
            "current_price": float(current_price or 0),
            "price_updated_at": as_of or now_iso(),
            "updated_at": now_iso(),
        },
        filters={"id": f"eq.{holding_id}"},
        prefer_return="minimal",
    )


def _supabase_list_trade_logs(account_id: int) -> list[dict[str, Any]]:
    if not _supabase_get_account(account_id):
        return []
    result = _supabase_request("GET", "trade_logs", filters={"account_id": f"eq.{account_id}"})
    logs = result or []
    return sorted(logs, key=lambda row: (row.get("trade_date", ""), row.get("id", 0)), reverse=True)


def _supabase_list_daily_interest(account_id: int) -> list[dict[str, Any]]:
    if not _supabase_get_account(account_id):
        return []
    result = _supabase_request("GET", "daily_interest", filters={"account_id": f"eq.{account_id}"})
    rows = result or []
    return sorted(rows, key=lambda row: (row.get("date", ""), row.get("id", 0)))


def _supabase_list_account_snapshots(account_id: int, start_date: str | None = None) -> list[dict[str, Any]]:
    if not _supabase_get_account(account_id):
        return []
    filters: dict[str, str | int] = {"account_id": f"eq.{account_id}"}
    if start_date:
        filters["snapshot_date"] = f"gte.{start_date}"
    result = _supabase_request("GET", "daily_account_snapshot", filters=filters)
    rows = result or []
    return sorted(rows, key=lambda row: (row.get("snapshot_date", ""), row.get("id", 0)))


def _supabase_export_dataframe_rows(table_name: str) -> list[dict[str, Any]]:
    if table_name not in EXPORTABLE_TABLES:
        raise ValueError("지원하지 않는 테이블입니다.")

    accounts = _supabase_list_accounts()
    account_ids = _owned_account_ids(accounts)
    if table_name == "accounts":
        return accounts

    result = _supabase_request("GET", table_name) or []
    rows = [row for row in result if int(row.get("account_id", 0) or 0) in account_ids]
    return sorted(rows, key=lambda row: row.get("id", 0))


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

    if cleaned_type not in BUY_SELL_TRADE_TYPES:
        raise ValueError("매수 또는 매도만 기록할 수 있습니다.")
    if cleaned_asset_type not in {"risk", "safe"}:
        raise ValueError("자산군 값이 올바르지 않습니다.")
    if not cleaned_symbol:
        raise ValueError("종목 코드 또는 심볼을 입력해 주세요.")
    if not cleaned_name:
        raise ValueError("종목명을 입력해 주세요.")

    share_count = float(quantity or 0)
    trade_price = float(price or 0)
    if share_count <= 0 or trade_price <= 0:
        raise ValueError("수량과 단가는 모두 0보다 커야 합니다.")

    account = _supabase_get_account(account_id)
    if not account:
        raise ValueError("계좌를 찾을 수 없습니다.")

    total_amount = share_count * trade_price
    cash_delta = -total_amount if cleaned_type == "buy" else total_amount
    timestamp = now_iso()
    holdings = _supabase_request("GET", "holdings", filters={"account_id": f"eq.{account_id}"}) or []
    holdings = [row for row in holdings if row.get("symbol") == cleaned_symbol]
    holding_row = holdings[0] if holdings else None
    cash_balance = float(account.get("cash_balance", 0) or 0)
    next_cash = cash_balance + cash_delta

    if next_cash < -0.000001:
        raise ValueError("매수하기에 현금이 부족합니다." if cleaned_type == "buy" else "현금 잔액 계산에 실패했습니다.")

    if cleaned_type == "buy":
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
                filters={"id": f"eq.{holding_row['id']}"},
                prefer_return="minimal",
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
                prefer_return="minimal",
            )
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
            filters={"id": f"eq.{holding_row['id']}"},
            prefer_return="minimal",
        )

    _supabase_update_cash_balance(account_id, next_cash)
    _supabase_insert_trade_log(
        account_id=account_id,
        symbol=cleaned_symbol,
        product_name=cleaned_name,
        trade_type=cleaned_type,
        asset_type=cleaned_asset_type,
        quantity=share_count,
        price=trade_price,
        total_amount=total_amount,
        cash_delta=cash_delta,
        trade_date=trade_date,
        notes=notes,
        created_at=timestamp,
        metadata_json={},
    )


def _supabase_record_cash_flow(
    account_id: int,
    *,
    flow_type: str,
    amount: float,
    trade_date: str,
    notes: str = "",
) -> None:
    cleaned_type = _normalize_cash_flow_type(flow_type)
    if cleaned_type not in {"personal_deposit", "employer_deposit", "withdraw"}:
        raise ValueError("개인 입금, 회사 납입금, 일반 출금만 기록할 수 있습니다.")

    flow_amount = float(amount or 0)
    if flow_amount <= 0:
        raise ValueError("금액은 0보다 커야 합니다.")

    account = _supabase_get_account(account_id)
    if not account:
        raise ValueError("계좌를 찾을 수 없습니다.")

    cash_balance = float(account.get("cash_balance", 0) or 0)
    cash_delta = flow_amount if cleaned_type in {"personal_deposit", "employer_deposit"} else -flow_amount
    new_balance = cash_balance + cash_delta
    if new_balance < -0.000001:
        raise ValueError("출금 금액이 현재 현금 잔액을 초과합니다.")

    timestamp = now_iso()
    _supabase_update_cash_balance(account_id, new_balance)
    _supabase_insert_trade_log(
        account_id=account_id,
        symbol="",
        product_name=_cash_event_label(cleaned_type),
        trade_type=cleaned_type,
        asset_type="cash",
        quantity=0,
        price=0,
        total_amount=flow_amount,
        cash_delta=cash_delta,
        trade_date=trade_date,
        notes=notes,
        created_at=timestamp,
        metadata_json={},
    )


def _supabase_adjust_cash_balance(
    account_id: int,
    *,
    target_amount: float,
    trade_date: str,
    notes: str,
) -> None:
    next_cash = float(target_amount or 0)
    if next_cash < 0:
        raise ValueError("현금 잔액은 0 이상이어야 합니다.")

    cleaned_notes = str(notes or "").strip()
    if not cleaned_notes:
        raise ValueError("현금 조정 사유를 입력해 주세요.")

    account = _supabase_get_account(account_id)
    if not account:
        raise ValueError("계좌를 찾을 수 없습니다.")

    current_cash = float(account.get("cash_balance", 0) or 0)
    cash_delta = next_cash - current_cash
    if abs(cash_delta) <= 0.000001:
        raise ValueError("현재 현금과 동일해 조정할 내용이 없습니다.")

    timestamp = now_iso()
    _supabase_update_cash_balance(account_id, next_cash)
    _supabase_insert_trade_log(
        account_id=account_id,
        symbol="",
        product_name=_cash_event_label("cash_adjustment"),
        trade_type="cash_adjustment",
        asset_type="cash",
        quantity=0,
        price=0,
        total_amount=abs(cash_delta),
        cash_delta=cash_delta,
        trade_date=trade_date,
        notes=cleaned_notes,
        created_at=timestamp,
        metadata_json={"target_amount": round(next_cash, 4)},
    )


def _supabase_record_daily_interest(account_id: int, *, interest_date: str, amount: float) -> None:
    interest_amount = float(amount or 0)
    if interest_amount <= 0:
        raise ValueError("이자 금액은 0보다 커야 합니다.")

    account = _supabase_get_account(account_id)
    if not account:
        raise ValueError("계좌를 찾을 수 없습니다.")

    existing = _supabase_request(
        "GET",
        "daily_interest",
        filters={
            "account_id": f"eq.{account_id}",
            "date": f"eq.{interest_date}",
        },
    ) or []
    if existing:
        raise ValueError("해당 일자의 이자가 이미 기록되어 있습니다.")

    current_cash = float(account.get("cash_balance", 0) or 0)
    next_cash = current_cash + interest_amount
    timestamp = now_iso()
    _supabase_request(
        "POST",
        "daily_interest",
        data={
            "account_id": account_id,
            "date": interest_date,
            "interest_amount": interest_amount,
            "created_at": timestamp,
        },
        prefer_return="minimal",
    )
    _supabase_update_cash_balance(account_id, next_cash)
    _supabase_insert_trade_log(
        account_id=account_id,
        symbol="",
        product_name=_cash_event_label("interest"),
        trade_type="interest",
        asset_type="cash",
        quantity=0,
        price=0,
        total_amount=interest_amount,
        cash_delta=interest_amount,
        trade_date=interest_date,
        notes="일별 이자 적립",
        created_at=timestamp,
        metadata_json={},
    )


def _supabase_record_account_transfer(
    from_account_id: int,
    *,
    to_account_id: int,
    amount: float,
    trade_date: str,
    notes: str = "",
) -> None:
    if int(from_account_id) == int(to_account_id):
        raise ValueError("같은 계좌로는 이체할 수 없습니다.")

    transfer_amount = float(amount or 0)
    if transfer_amount <= 0:
        raise ValueError("이체 금액은 0보다 커야 합니다.")

    from_account = _supabase_get_account(from_account_id)
    to_account = _supabase_get_account(to_account_id)
    if not from_account or not to_account:
        raise ValueError("이체 대상 계좌를 찾을 수 없습니다.")

    from_cash = float(from_account.get("cash_balance", 0) or 0)
    to_cash = float(to_account.get("cash_balance", 0) or 0)
    next_from_cash = from_cash - transfer_amount
    next_to_cash = to_cash + transfer_amount
    if next_from_cash < -0.000001:
        raise ValueError("이체할 현금이 부족합니다.")

    timestamp = now_iso()
    event_group_id = str(uuid4())
    _supabase_update_cash_balance(from_account_id, next_from_cash)
    _supabase_update_cash_balance(to_account_id, next_to_cash)
    _supabase_insert_trade_log(
        account_id=from_account_id,
        symbol="",
        product_name=_cash_event_label("transfer_out"),
        trade_type="transfer_out",
        asset_type="cash",
        quantity=0,
        price=0,
        total_amount=transfer_amount,
        cash_delta=-transfer_amount,
        trade_date=trade_date,
        notes=notes,
        created_at=timestamp,
        event_group_id=event_group_id,
        counterparty_account_id=to_account_id,
        metadata_json={},
    )
    _supabase_insert_trade_log(
        account_id=to_account_id,
        symbol="",
        product_name=_cash_event_label("transfer_in"),
        trade_type="transfer_in",
        asset_type="cash",
        quantity=0,
        price=0,
        total_amount=transfer_amount,
        cash_delta=transfer_amount,
        trade_date=trade_date,
        notes=notes,
        created_at=timestamp,
        event_group_id=event_group_id,
        counterparty_account_id=from_account_id,
        metadata_json={},
    )


def _supabase_record_account_snapshot(
    account_id: int,
    *,
    snapshot_date: str,
    cash_balance: float,
    market_value: float,
    total_value: float,
    total_cost: float,
) -> None:
    if not _supabase_get_account(account_id):
        raise ValueError("계좌를 찾을 수 없습니다.")

    timestamp = now_iso()
    existing = _supabase_request(
        "GET",
        "daily_account_snapshot",
        filters={
            "account_id": f"eq.{account_id}",
            "snapshot_date": f"eq.{snapshot_date}",
        },
    ) or []
    payload = {
        "account_id": account_id,
        "snapshot_date": snapshot_date,
        "cash_balance": float(cash_balance or 0),
        "market_value": float(market_value or 0),
        "total_value": float(total_value or 0),
        "total_cost": float(total_cost or 0),
        "updated_at": timestamp,
    }
    if existing:
        snapshot_id = int(existing[0]["id"])
        _supabase_request(
            "PATCH",
            "daily_account_snapshot",
            data=payload,
            filters={"id": f"eq.{snapshot_id}"},
            prefer_return="minimal",
        )
        return

    payload["created_at"] = timestamp
    _supabase_request("POST", "daily_account_snapshot", data=payload, prefer_return="minimal")


def _sqlite_list_accounts() -> list[dict[str, Any]]:
    accounts = [_present_account(row) for row in sqlite_db.list_accounts()]
    visible = [account for account in accounts if account]
    return sorted(visible, key=lambda row: str(row.get("name", "")).lower())


def _sqlite_get_account(account_id: int) -> dict[str, Any] | None:
    return _present_account(sqlite_db.get_account(account_id))


def _sqlite_create_account(name: str, account_type: str = "retirement", opening_cash: float = 0) -> int:
    cleaned_name = str(name or "").strip()
    if not cleaned_name:
        raise ValueError("계좌 이름을 입력해 주세요.")

    cleaned_type = str(account_type or "retirement").strip().lower()
    if cleaned_type not in {"retirement", "brokerage"}:
        raise ValueError("계좌 유형 값이 올바르지 않습니다.")

    existing_names = {str(account.get("name", "")).lower() for account in _sqlite_list_accounts()}
    if cleaned_name.lower() in existing_names:
        raise ValueError("같은 이름의 계좌가 이미 있습니다.")

    return sqlite_db.create_account(_storage_account_name(cleaned_name), cleaned_type, opening_cash)


def _sqlite_update_cash_balance(account_id: int, amount: float) -> None:
    if not _sqlite_get_account(account_id):
        raise ValueError("계좌를 찾을 수 없습니다.")
    sqlite_db.update_cash_balance(account_id, amount)


def _sqlite_list_holdings(account_id: int, include_closed: bool = False) -> list[dict[str, Any]]:
    if not _sqlite_get_account(account_id):
        return []
    return sqlite_db.list_holdings(account_id, include_closed)


def _sqlite_set_holding_price(holding_id: int, current_price: float, as_of: str | None = None) -> None:
    _require_user_id()
    sqlite_db.set_holding_price(holding_id, current_price, as_of)


def _sqlite_list_trade_logs(account_id: int) -> list[dict[str, Any]]:
    if not _sqlite_get_account(account_id):
        return []
    return sqlite_db.list_trade_logs(account_id)


def _sqlite_list_daily_interest(account_id: int) -> list[dict[str, Any]]:
    if not _sqlite_get_account(account_id):
        return []
    return sqlite_db.list_daily_interest(account_id)


def _sqlite_list_account_snapshots(account_id: int, start_date: str | None = None) -> list[dict[str, Any]]:
    if not _sqlite_get_account(account_id):
        return []
    return sqlite_db.list_account_snapshots(account_id, start_date=start_date)


def _sqlite_export_dataframe_rows(table_name: str) -> list[dict[str, Any]]:
    if table_name == "accounts":
        return _sqlite_list_accounts()

    accounts = _sqlite_list_accounts()
    account_ids = _owned_account_ids(accounts)
    rows = sqlite_db.export_dataframe_rows(table_name)
    filtered = [row for row in rows if int(row.get("account_id", 0) or 0) in account_ids]
    return sorted(filtered, key=lambda row: row.get("id", 0))


def _sqlite_record_trade(
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
    if not _sqlite_get_account(account_id):
        raise ValueError("계좌를 찾을 수 없습니다.")
    sqlite_db.record_trade(
        account_id,
        symbol=symbol,
        product_name=product_name,
        trade_type=trade_type,
        asset_type=asset_type,
        quantity=quantity,
        price=price,
        trade_date=trade_date,
        notes=notes,
    )


def _sqlite_record_cash_flow(
    account_id: int,
    *,
    flow_type: str,
    amount: float,
    trade_date: str,
    notes: str = "",
) -> None:
    if not _sqlite_get_account(account_id):
        raise ValueError("계좌를 찾을 수 없습니다.")
    sqlite_db.record_cash_flow(
        account_id,
        flow_type=flow_type,
        amount=amount,
        trade_date=trade_date,
        notes=notes,
    )


def _sqlite_adjust_cash_balance(
    account_id: int,
    *,
    target_amount: float,
    trade_date: str,
    notes: str,
) -> None:
    if not _sqlite_get_account(account_id):
        raise ValueError("계좌를 찾을 수 없습니다.")
    sqlite_db.adjust_cash_balance(
        account_id,
        target_amount=target_amount,
        trade_date=trade_date,
        notes=notes,
    )


def _sqlite_record_daily_interest(account_id: int, *, interest_date: str, amount: float) -> None:
    if not _sqlite_get_account(account_id):
        raise ValueError("계좌를 찾을 수 없습니다.")
    sqlite_db.record_daily_interest(
        account_id,
        interest_date=interest_date,
        amount=amount,
    )


def _sqlite_record_account_transfer(
    from_account_id: int,
    *,
    to_account_id: int,
    amount: float,
    trade_date: str,
    notes: str = "",
) -> None:
    if not _sqlite_get_account(from_account_id) or not _sqlite_get_account(to_account_id):
        raise ValueError("이체 대상 계좌를 찾을 수 없습니다.")
    sqlite_db.record_account_transfer(
        from_account_id,
        to_account_id=to_account_id,
        amount=amount,
        trade_date=trade_date,
        notes=notes,
    )


def _sqlite_record_account_snapshot(
    account_id: int,
    *,
    snapshot_date: str,
    cash_balance: float,
    market_value: float,
    total_value: float,
    total_cost: float,
) -> None:
    if not _sqlite_get_account(account_id):
        raise ValueError("계좌를 찾을 수 없습니다.")
    sqlite_db.record_account_snapshot(
        account_id,
        snapshot_date=snapshot_date,
        cash_balance=cash_balance,
        market_value=market_value,
        total_value=total_value,
        total_cost=total_cost,
    )


def initialize_database() -> None:
    sqlite_db.initialize_database()
    if _current_backend() == BACKEND_SQLITE:
        return
    if not app_auth.is_authenticated():
        return
    _run_with_fallback(
        supabase_call=_supabase_initialize_database,
        sqlite_call=sqlite_db.initialize_database,
    )


def list_accounts() -> list[dict[str, Any]]:
    return _run_with_fallback(
        supabase_call=_supabase_list_accounts,
        sqlite_call=_sqlite_list_accounts,
    )


def get_account(account_id: int) -> dict[str, Any] | None:
    return _run_with_fallback(
        supabase_call=lambda: _supabase_get_account(account_id),
        sqlite_call=lambda: _sqlite_get_account(account_id),
    )


def create_account(name: str, account_type: str = "retirement", opening_cash: float = 0) -> int:
    return _run_with_fallback(
        supabase_call=lambda: _supabase_create_account(name, account_type, opening_cash),
        sqlite_call=lambda: _sqlite_create_account(name, account_type, opening_cash),
    )


def update_cash_balance(account_id: int, amount: float) -> None:
    _run_with_fallback(
        supabase_call=lambda: _supabase_update_cash_balance(account_id, amount),
        sqlite_call=lambda: _sqlite_update_cash_balance(account_id, amount),
    )


def list_holdings(account_id: int, include_closed: bool = False) -> list[dict[str, Any]]:
    return _run_with_fallback(
        supabase_call=lambda: _supabase_list_holdings(account_id, include_closed),
        sqlite_call=lambda: _sqlite_list_holdings(account_id, include_closed),
    )


def set_holding_price(holding_id: int, current_price: float, as_of: str | None = None) -> None:
    _run_with_fallback(
        supabase_call=lambda: _supabase_set_holding_price(holding_id, current_price, as_of),
        sqlite_call=lambda: _sqlite_set_holding_price(holding_id, current_price, as_of),
    )


def list_trade_logs(account_id: int) -> list[dict[str, Any]]:
    return _run_with_fallback(
        supabase_call=lambda: _supabase_list_trade_logs(account_id),
        sqlite_call=lambda: _sqlite_list_trade_logs(account_id),
    )


def list_daily_interest(account_id: int) -> list[dict[str, Any]]:
    """계좌의 일별 이자 기록을 조회한다."""

    if _current_backend() == BACKEND_SQLITE:
        return _sqlite_list_daily_interest(account_id)

    try:
        return _supabase_list_daily_interest(account_id)
    except Exception as exc:
        if _should_fallback(exc):
            return []
        raise


def list_account_snapshots(account_id: int, start_date: str | None = None) -> list[dict[str, Any]]:
    """계좌의 일별 스냅샷을 조회한다."""

    if _current_backend() == BACKEND_SQLITE:
        return _sqlite_list_account_snapshots(account_id, start_date)

    try:
        return _supabase_list_account_snapshots(account_id, start_date)
    except Exception as exc:
        if _should_fallback(exc):
            return []
        raise


def export_dataframe_rows(table_name: str) -> list[dict[str, Any]]:
    return _run_with_fallback(
        supabase_call=lambda: _supabase_export_dataframe_rows(table_name),
        sqlite_call=lambda: _sqlite_export_dataframe_rows(table_name),
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
        sqlite_call=lambda: _sqlite_record_trade(
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
        sqlite_call=lambda: _sqlite_record_cash_flow(
            account_id,
            flow_type=flow_type,
            amount=amount,
            trade_date=trade_date,
            notes=notes,
        ),
    )


def adjust_cash_balance(
    account_id: int,
    *,
    target_amount: float,
    trade_date: str,
    notes: str,
) -> None:
    """목표 현금 잔액에 맞는 조정 이벤트를 기록한다."""

    _run_with_fallback(
        supabase_call=lambda: _supabase_adjust_cash_balance(
            account_id,
            target_amount=target_amount,
            trade_date=trade_date,
            notes=notes,
        ),
        sqlite_call=lambda: _sqlite_adjust_cash_balance(
            account_id,
            target_amount=target_amount,
            trade_date=trade_date,
            notes=notes,
        ),
    )


def record_daily_interest(account_id: int, *, interest_date: str, amount: float) -> None:
    """일별 이자를 상세 테이블과 거래 원장에 함께 기록한다."""

    _run_with_fallback(
        supabase_call=lambda: _supabase_record_daily_interest(
            account_id,
            interest_date=interest_date,
            amount=amount,
        ),
        sqlite_call=lambda: _sqlite_record_daily_interest(
            account_id,
            interest_date=interest_date,
            amount=amount,
        ),
    )


def record_account_snapshot(
    account_id: int,
    *,
    snapshot_date: str,
    cash_balance: float,
    market_value: float,
    total_value: float,
    total_cost: float,
) -> None:
    """계좌의 일별 총자산 스냅샷을 저장한다."""

    _run_with_fallback(
        supabase_call=lambda: _supabase_record_account_snapshot(
            account_id,
            snapshot_date=snapshot_date,
            cash_balance=cash_balance,
            market_value=market_value,
            total_value=total_value,
            total_cost=total_cost,
        ),
        sqlite_call=lambda: _sqlite_record_account_snapshot(
            account_id,
            snapshot_date=snapshot_date,
            cash_balance=cash_balance,
            market_value=market_value,
            total_value=total_value,
            total_cost=total_cost,
        ),
    )


def record_account_transfer(
    from_account_id: int,
    *,
    to_account_id: int,
    amount: float,
    trade_date: str,
    notes: str = "",
) -> None:
    """두 계좌 사이의 현금 이체를 출금/입금 2건으로 기록한다."""

    _run_with_fallback(
        supabase_call=lambda: _supabase_record_account_transfer(
            from_account_id,
            to_account_id=to_account_id,
            amount=amount,
            trade_date=trade_date,
            notes=notes,
        ),
        sqlite_call=lambda: _sqlite_record_account_transfer(
            from_account_id,
            to_account_id=to_account_id,
            amount=amount,
            trade_date=trade_date,
            notes=notes,
        ),
    )

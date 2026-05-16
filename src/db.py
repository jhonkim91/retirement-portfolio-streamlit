from __future__ import annotations

import base64
import os
from typing import Any, Callable, TypeVar
from datetime import date, datetime, timedelta
from urllib.parse import urlparse
from uuid import uuid4
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta

import pandas as pd
import requests
import streamlit as st

from . import auth as app_auth
from . import sqlite_db
from .trade_log_filters import normalized_trade_notional


T = TypeVar("T")

DEFAULT_SUPABASE_URL = ""
BACKEND_AUTO = "auto"
DEFAULT_BACKEND = BACKEND_AUTO
BACKEND_SQLITE = "sqlite"
BACKEND_SUPABASE = "supabase"
BACKEND_STATE_KEY = "db_backend_state"
DATA_REFRESH_TOKEN_KEY = "data_refresh_token"
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
EDITABLE_TRADE_LOG_TYPES = {"buy", "sell", "personal_deposit", "employer_deposit", "withdraw"}
EDITABLE_CASH_FLOW_LOG_TYPES = {"personal_deposit", "employer_deposit", "withdraw"}
EXPORTABLE_TRADE_LOG_TYPES = {"buy", "sell", "personal_deposit", "employer_deposit"}
EXPORTABLE_TABLES = {"accounts", "holdings", "trade_logs", "daily_account_snapshot", "daily_valuation_snapshot"}
DEFAULT_ANNUAL_INTEREST_RATE = 0.05
DEFAULT_ROLLUP_TIMEZONE = "Asia/Seoul"
AUTO_DAILY_INTEREST_NOTE = "일별 이자 적립"
INTEREST_AMOUNT_TOLERANCE = 0.0001
ACCOUNTS_CACHE_TTL_SECONDS = 30
ACCOUNT_CACHE_TTL_SECONDS = 10
HOLDINGS_CACHE_TTL_SECONDS = 5
TRADE_LOGS_CACHE_TTL_SECONDS = 30
SNAPSHOTS_CACHE_TTL_SECONDS = 30
VALUATION_SNAPSHOTS_CACHE_TTL_SECONDS = 30
LEGACY_DEMO_ACCOUNT_NAMES = {"데모 일반계좌"}


def _state_store() -> dict[str, Any]:
    try:
        return st.session_state
    except Exception:
        return _FALLBACK_STATE


def _current_data_refresh_token() -> int:
    """현재 세션의 데이터 조회 캐시 무효화 토큰을 반환한다."""

    return int(_state_store().get(DATA_REFRESH_TOKEN_KEY, 0) or 0)


def _data_cache_scope_key(backend_name: str | None = None) -> str:
    """전역 캐시에 사용자별 조회 범위를 분리할 키를 만든다."""

    normalized_backend = str(backend_name or _current_backend() or BACKEND_SQLITE).strip().lower() or BACKEND_SQLITE
    user_id = str(app_auth.get_user_id() or "anonymous").strip() or "anonymous"
    session_mode = "demo" if app_auth.is_demo_user() else "user"
    return f"{session_mode}:{user_id}:{normalized_backend}"


def mark_data_dirty() -> None:
    """다음 조회에서 데이터 캐시를 다시 읽도록 세션 토큰을 증가시킨다."""

    store = _state_store()
    store[DATA_REFRESH_TOKEN_KEY] = _current_data_refresh_token() + 1


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


def _is_valid_supabase_url(url: str) -> bool:
    """Supabase hosted 프로젝트 URL 형식인지 확인한다."""

    parsed = urlparse(str(url or "").strip())
    return parsed.scheme == "https" and parsed.netloc.endswith(".supabase.co")


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
    if not _is_valid_supabase_url(url):
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
    return _is_valid_supabase_url(_supabase_url()) and bool(_supabase_key())


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

    if app_auth.is_demo_user():
        return BACKEND_SQLITE, "데모 접속 세션이라 로컬 SQLite 데모 저장소를 우선 사용합니다."

    override = _normalized_backend_override()
    if override == BACKEND_SUPABASE:
        if _has_supabase_config():
            return BACKEND_SUPABASE, "PORTFOLIO_BACKEND=supabase 설정으로 Supabase 저장소를 강제 사용 중입니다."
        return BACKEND_SQLITE, "PORTFOLIO_BACKEND=supabase 설정이 있지만 Supabase URL 또는 키가 없어 로컬 SQLite 저장소를 사용합니다."
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
    supabase_url_valid = _is_valid_supabase_url(supabase_url)
    missing_items: list[str] = []
    notices: list[str] = []

    if not supabase_url_valid:
        missing_items.append("SUPABASE_URL")
    if not supabase_key:
        missing_items.append("SUPABASE_KEY")
    if not supabase_url_valid:
        notices.append("SUPABASE_URL이 없거나 형식이 올바르지 않아 Supabase 저장소를 비활성화합니다.")
    if supabase_key_source == "missing":
        notices.append("SUPABASE_KEY가 없어 Supabase 저장소를 활성화할 수 없습니다.")

    return {
        "name": _current_backend(),
        "reason": state["reason"],
        "override": _normalized_backend_override(),
        "has_supabase_config": _has_supabase_config(),
        "supabase_url_present": bool(supabase_url),
        "supabase_url_valid": supabase_url_valid,
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
    total_cost = sum(
        _normalized_trade_notional(item.get("symbol"), item.get("quantity"), item.get("avg_cost"))
        for item in holdings
    )
    market_value = sum(
        _normalized_trade_notional(item.get("symbol"), item.get("quantity"), item.get("current_price"))
        for item in holdings
    )
    account = get_account(account_id) or {}
    cash_balance = float(account.get("cash_balance") or 0)
    return cash_balance, market_value, total_cost


def _demo_cash_flow_delta(flow_type: Any, amount: Any) -> float:
    """데모 현금흐름 정의에서 계좌 현금 증감을 계산한다."""

    normalized_type = _normalize_cash_flow_type(str(flow_type or ""))
    flow_amount = float(amount or 0)
    return flow_amount if normalized_type in {"personal_deposit", "employer_deposit"} else -flow_amount


def _demo_trade_cash_delta(trade: dict[str, Any]) -> float:
    """데모 매수/매도 정의에서 계좌 현금 증감을 계산한다."""

    trade_type = str(trade.get("trade_type") or "").strip().lower()
    amount = _normalized_trade_notional(trade.get("symbol"), trade.get("quantity"), trade.get("price"))
    if trade_type == "buy":
        return -amount
    if trade_type == "sell":
        return amount
    return 0.0


def _demo_cash_balance_from_spec(account_spec: dict[str, Any]) -> float:
    """데모 계좌 정의의 현금흐름과 거래를 반영한 현재 현금을 계산한다."""

    cash_balance = float(account_spec.get("opening_cash") or 0)
    cash_balance += sum(
        _demo_cash_flow_delta(flow.get("flow_type"), flow.get("amount"))
        for flow in account_spec.get("cash_flows", ())
    )
    cash_balance += sum(_demo_trade_cash_delta(trade) for trade in account_spec.get("trades", ()))
    return round(cash_balance, 4)


def _rollup_today(timezone_name: str = DEFAULT_ROLLUP_TIMEZONE) -> date:
    """롤업 기준 오늘 날짜를 반환한다."""

    return datetime.now(ZoneInfo(timezone_name)).date()


def _parse_iso_date(value: Any) -> date | None:
    """문자열/타임스탬프 값을 날짜로 해석한다."""

    if value in (None, ""):
        return None
    timestamp = pd.to_datetime(str(value).strip(), errors="coerce")
    if pd.isna(timestamp):
        return None
    return timestamp.date()


def _is_auto_daily_interest_trade(log: dict[str, Any]) -> bool:
    """자동 적립된 일별 이자 trade log인지 판별한다."""

    trade_type = str(log.get("trade_type") or "").strip().lower()
    if trade_type != "interest":
        return False
    if str(log.get("notes") or "").strip() == AUTO_DAILY_INTEREST_NOTE:
        return True
    return str(log.get("product_name") or "").strip() == _cash_event_label("interest")


def _interest_amount_matches(left: float, right: float) -> bool:
    """일별 이자 금액을 허용 오차 내에서 비교한다."""

    return abs(float(left or 0) - float(right or 0)) <= INTEREST_AMOUNT_TOLERANCE


def _daily_interest_row_amount_by_date(
    interest_rows: list[dict[str, Any]],
    *,
    target_date: date | None,
) -> dict[str, float]:
    """daily_interest 테이블 값을 날짜별로 정리한다."""

    target_iso = target_date.isoformat() if target_date is not None else ""
    existing: dict[str, float] = {}

    for row in interest_rows:
        interest_date = str(row.get("date") or row.get("interest_date") or "").strip()
        if not interest_date or (target_iso and interest_date > target_iso):
            continue
        existing[interest_date] = float(row.get("interest_amount") or 0)

    return existing


def _trade_interest_amount_by_date(
    trade_logs: list[dict[str, Any]],
    *,
    target_date: date | None,
) -> dict[str, float]:
    """자동 적립된 interest trade log 금액을 날짜별로 정리한다."""

    target_iso = target_date.isoformat() if target_date is not None else ""
    existing: dict[str, float] = {}

    for log in trade_logs:
        if not _is_auto_daily_interest_trade(log):
            continue
        trade_date = str(log.get("trade_date") or "").strip()
        if not trade_date or (target_iso and trade_date > target_iso):
            continue
        amount = abs(float(log.get("cash_delta") or 0)) or abs(float(log.get("total_amount") or 0))
        if amount > 0:
            existing[trade_date] = amount

    return existing


def _actual_interest_amount_by_date(
    trade_logs: list[dict[str, Any]],
    interest_rows: list[dict[str, Any]],
    *,
    target_date: date,
) -> dict[str, float]:
    """현재 원장/상세 테이블 기준 일별 이자 금액을 날짜별로 정리한다."""

    row_by_date = _daily_interest_row_amount_by_date(interest_rows, target_date=target_date)
    trade_by_date = _trade_interest_amount_by_date(trade_logs, target_date=target_date)
    existing = dict(row_by_date)
    existing.update(trade_by_date)
    return existing


def _existing_interest_total_to_remove(
    trade_logs: list[dict[str, Any]],
    interest_rows: list[dict[str, Any]],
    *,
    target_date: date,
) -> float:
    """현재 계좌 현금에 반영된 자동 일별 이자 총액을 계산한다."""

    row_by_date = _daily_interest_row_amount_by_date(interest_rows, target_date=target_date)
    trade_by_date = _trade_interest_amount_by_date(trade_logs, target_date=target_date)
    orphaned_row_total = sum(amount for interest_date, amount in row_by_date.items() if interest_date not in trade_by_date)
    return round(sum(trade_by_date.values()) + orphaned_row_total, 4)


def _build_interest_schedule(
    account: dict[str, Any],
    trade_logs: list[dict[str, Any]],
    interest_rows: list[dict[str, Any]],
    *,
    target_date: date,
    annual_rate: float,
) -> list[tuple[str, float]]:
    """원장 기준으로 기대되는 일별 이자 적립 일정을 계산한다."""

    if annual_rate <= 0:
        return []

    non_interest_delta_by_date: dict[str, float] = {}
    earliest_trade_date: date | None = None
    ledger_cash_delta_total = 0.0
    trade_interest_by_date = _trade_interest_amount_by_date(trade_logs, target_date=target_date)
    row_interest_by_date = _daily_interest_row_amount_by_date(interest_rows, target_date=target_date)

    for log in trade_logs:
        cash_delta = float(log.get("cash_delta") or 0)
        ledger_cash_delta_total += cash_delta

        trade_date_text = str(log.get("trade_date") or "").strip()
        trade_date = _parse_iso_date(trade_date_text)
        if trade_date is None or trade_date > target_date:
            continue

        if earliest_trade_date is None or trade_date < earliest_trade_date:
            earliest_trade_date = trade_date

        if _is_auto_daily_interest_trade(log):
            continue
        non_interest_delta_by_date[trade_date.isoformat()] = non_interest_delta_by_date.get(trade_date.isoformat(), 0.0) + cash_delta

    current_cash = float(account.get("cash_balance") or 0)
    orphaned_interest_total = sum(
        amount
        for interest_date, amount in row_interest_by_date.items()
        if interest_date not in trade_interest_by_date
    )
    opening_cash = current_cash - ledger_cash_delta_total - orphaned_interest_total
    account_created_date = _parse_iso_date(account.get("created_at"))

    start_date = earliest_trade_date or account_created_date
    if start_date is None or start_date > target_date:
        return []

    running_cash = opening_cash
    current_date = start_date
    plan: list[tuple[str, float]] = []

    while current_date <= target_date:
        current_iso = current_date.isoformat()
        running_cash += non_interest_delta_by_date.get(current_iso, 0.0)

        if running_cash > 0:
            interest_amount = round(running_cash * annual_rate / 365, 4)
            if interest_amount > 0:
                plan.append((current_iso, interest_amount))
                running_cash += interest_amount

        current_date += timedelta(days=1)

    return plan


def _interest_sync_diff(
    desired_entries: list[tuple[str, float]],
    trade_logs: list[dict[str, Any]],
    interest_rows: list[dict[str, Any]],
    *,
    target_date: date,
) -> dict[str, Any]:
    """기대 이자 일정과 실제 저장 상태의 차이를 집계한다."""

    desired_by_date = {interest_date: amount for interest_date, amount in desired_entries}
    row_by_date = _daily_interest_row_amount_by_date(interest_rows, target_date=target_date)
    trade_by_date = _trade_interest_amount_by_date(trade_logs, target_date=target_date)
    actual_by_date = _actual_interest_amount_by_date(trade_logs, interest_rows, target_date=target_date)

    added_dates = [interest_date for interest_date in desired_by_date if interest_date not in actual_by_date]
    updated_dates = [
        interest_date
        for interest_date, amount in desired_by_date.items()
        if interest_date in actual_by_date and not _interest_amount_matches(amount, actual_by_date[interest_date])
    ]
    removed_dates = [interest_date for interest_date in actual_by_date if interest_date not in desired_by_date]
    inconsistent_dates = sorted(
        interest_date
        for interest_date in set(row_by_date) | set(trade_by_date)
        if interest_date not in row_by_date
        or interest_date not in trade_by_date
        or not _interest_amount_matches(row_by_date.get(interest_date, 0.0), trade_by_date.get(interest_date, 0.0))
    )

    return {
        "desired_entries": desired_entries,
        "desired_by_date": desired_by_date,
        "actual_by_date": actual_by_date,
        "added_dates": added_dates,
        "updated_dates": updated_dates,
        "removed_dates": removed_dates,
        "inconsistent_dates": inconsistent_dates,
        "net_amount_delta": round(sum(desired_by_date.values()) - sum(actual_by_date.values()), 4),
        "requires_rebuild": bool(updated_dates or removed_dates or inconsistent_dates),
    }


def _replace_interest_history_counts(diff: dict[str, Any]) -> dict[str, int]:
    """재구성 결과를 추가/수정/삭제 건수로 정리한다."""

    added_dates = set(diff.get("added_dates") or [])
    updated_dates = set(diff.get("updated_dates") or [])
    removed_dates = set(diff.get("removed_dates") or [])
    inconsistent_dates = set(diff.get("inconsistent_dates") or [])
    desired_dates = set((diff.get("desired_by_date") or {}).keys())

    updated_dates |= (inconsistent_dates & desired_dates) - added_dates
    removed_dates |= inconsistent_dates - desired_dates
    return {
        "interest_rows_added": len(added_dates),
        "interest_rows_updated": len(updated_dates),
        "interest_rows_removed": len(removed_dates),
    }


def _snapshot_matches_current(
    snapshot: dict[str, Any],
    *,
    cash_balance: float,
    market_value: float,
    total_value: float,
    total_cost: float,
) -> bool:
    """기존 스냅샷이 현재 값과 사실상 같은지 확인한다."""

    comparisons = (
        (snapshot.get("cash_balance"), cash_balance),
        (snapshot.get("market_value"), market_value),
        (snapshot.get("total_value"), total_value),
        (snapshot.get("total_cost"), total_cost),
    )
    return all(abs(float(left or 0) - float(right or 0)) <= 0.0001 for left, right in comparisons)


def _cash_delta_by_date(
    trade_logs: list[dict[str, Any]],
    interest_rows: list[dict[str, Any]],
    *,
    target_date: date | None,
) -> dict[str, float]:
    """거래 원장과 orphan 이자 행을 합쳐 날짜별 현금 증감을 계산한다."""

    target_iso = target_date.isoformat() if target_date is not None else ""
    delta_by_date: dict[str, float] = {}

    for log in trade_logs:
        trade_date = str(log.get("trade_date") or "").strip()
        if not trade_date or (target_iso and trade_date > target_iso):
            continue
        delta_by_date[trade_date] = delta_by_date.get(trade_date, 0.0) + float(log.get("cash_delta") or 0)

    row_by_date = _daily_interest_row_amount_by_date(interest_rows, target_date=target_date)
    trade_by_date = _trade_interest_amount_by_date(trade_logs, target_date=target_date)
    for interest_date, amount in row_by_date.items():
        if interest_date in trade_by_date:
            continue
        delta_by_date[interest_date] = delta_by_date.get(interest_date, 0.0) + amount

    return delta_by_date


def _historical_cash_balance_by_date(
    account: dict[str, Any],
    trade_logs: list[dict[str, Any]],
    interest_rows: list[dict[str, Any]],
    *,
    target_date: date,
    snapshot_dates: list[str],
) -> dict[str, float]:
    """지정한 스냅샷 날짜별 종가 기준 현금 잔액을 계산한다."""

    if not snapshot_dates:
        return {}

    trade_interest_by_date = _trade_interest_amount_by_date(trade_logs, target_date=None)
    row_interest_by_date = _daily_interest_row_amount_by_date(interest_rows, target_date=None)
    orphaned_interest_total = sum(
        amount
        for interest_date, amount in row_interest_by_date.items()
        if interest_date not in trade_interest_by_date
    )
    current_cash = float(account.get("cash_balance") or 0)
    ledger_cash_delta_total = sum(
        float(log.get("cash_delta") or 0)
        for log in trade_logs
        if _parse_iso_date(log.get("trade_date")) is not None
    )
    opening_cash = current_cash - ledger_cash_delta_total - orphaned_interest_total
    delta_by_date = _cash_delta_by_date(trade_logs, interest_rows, target_date=None)

    snapshot_date_values = [date.fromisoformat(item) for item in snapshot_dates]
    account_created_date = _parse_iso_date(account.get("created_at"))
    earliest_cash_event_date: date | None = None
    for log in trade_logs:
        trade_date = _parse_iso_date(log.get("trade_date"))
        if trade_date is None:
            continue
        if earliest_cash_event_date is None or trade_date < earliest_cash_event_date:
            earliest_cash_event_date = trade_date
    for row in interest_rows:
        interest_date = _parse_iso_date(row.get("date") or row.get("interest_date"))
        if interest_date is None:
            continue
        if earliest_cash_event_date is None or interest_date < earliest_cash_event_date:
            earliest_cash_event_date = interest_date

    iter_start = min(snapshot_date_values)
    if account_created_date and account_created_date < iter_start:
        iter_start = account_created_date
    if earliest_cash_event_date and earliest_cash_event_date < iter_start:
        iter_start = earliest_cash_event_date

    running_cash = opening_cash
    result: dict[str, float] = {}
    current_date = iter_start
    target_snapshot_dates = set(snapshot_dates)
    while current_date <= target_date:
        current_iso = current_date.isoformat()
        running_cash += delta_by_date.get(current_iso, 0.0)
        if current_iso in target_snapshot_dates:
            result[current_iso] = round(running_cash, 4)
        current_date += timedelta(days=1)

    return result


def _historical_total_cost_by_date(
    trade_logs: list[dict[str, Any]],
    *,
    target_date: date,
    snapshot_dates: list[str],
) -> dict[str, float]:
    """지정한 스냅샷 날짜별 종가 기준 총원가를 계산한다."""

    if not snapshot_dates:
        return {}

    trade_logs_sorted = sorted(
        trade_logs,
        key=lambda row: (str(row.get("trade_date") or ""), int(row.get("id") or 0)),
    )
    trade_events_by_date: dict[str, list[dict[str, Any]]] = {}
    earliest_trade_date: date | None = None
    for log in trade_logs_sorted:
        trade_type = str(log.get("trade_type") or "").strip().lower()
        if trade_type not in BUY_SELL_TRADE_TYPES:
            continue
        trade_date = _parse_iso_date(log.get("trade_date"))
        if trade_date is None or trade_date > target_date:
            continue
        trade_events_by_date.setdefault(trade_date.isoformat(), []).append(log)
        if earliest_trade_date is None or trade_date < earliest_trade_date:
            earliest_trade_date = trade_date

    snapshot_date_values = [date.fromisoformat(item) for item in snapshot_dates]
    iter_start = min(snapshot_date_values)
    if earliest_trade_date and earliest_trade_date < iter_start:
        iter_start = earliest_trade_date

    positions: dict[str, tuple[float, float]] = {}
    result: dict[str, float] = {}
    current_date = iter_start
    target_snapshot_dates = set(snapshot_dates)
    while current_date <= target_date:
        current_iso = current_date.isoformat()
        for log in trade_events_by_date.get(current_iso, []):
            symbol = str(log.get("symbol") or "").strip().upper()
            quantity = float(log.get("quantity") or 0)
            price = float(log.get("price") or 0)
            trade_type = str(log.get("trade_type") or "").strip().lower()
            current_quantity, avg_cost = positions.get(symbol, (0.0, 0.0))

            if trade_type == "buy":
                next_quantity = current_quantity + quantity
                if next_quantity > 0:
                    avg_cost = ((current_quantity * avg_cost) + (quantity * price)) / next_quantity
                positions[symbol] = (next_quantity, avg_cost)
            else:
                next_quantity = max(current_quantity - quantity, 0.0)
                if next_quantity <= 0:
                    positions.pop(symbol, None)
                else:
                    positions[symbol] = (next_quantity, avg_cost)

        if current_iso in target_snapshot_dates:
            result[current_iso] = round(
                sum(quantity * avg_cost for quantity, avg_cost in positions.values() if quantity > 0),
                4,
            )
        current_date += timedelta(days=1)

    return result


def _sync_historical_snapshots(
    account_id: int,
    *,
    account: dict[str, Any],
    trade_logs: list[dict[str, Any]],
    interest_rows: list[dict[str, Any]],
    snapshot_rows: list[dict[str, Any]],
    start_date: date,
    target_date: date,
) -> int:
    """기존 historical snapshot의 현금/원가/총액을 원장 기준으로 다시 맞춘다."""

    relevant_rows_by_date: dict[str, dict[str, Any]] = {}
    for row in snapshot_rows:
        snapshot_date = _parse_iso_date(row.get("snapshot_date"))
        if snapshot_date is None or snapshot_date < start_date or snapshot_date > target_date:
            continue
        relevant_rows_by_date[snapshot_date.isoformat()] = row

    snapshot_dates = sorted(relevant_rows_by_date)
    if not snapshot_dates:
        return 0

    cash_balance_by_date = _historical_cash_balance_by_date(
        account,
        trade_logs,
        interest_rows,
        target_date=target_date,
        snapshot_dates=snapshot_dates,
    )
    total_cost_by_date = _historical_total_cost_by_date(
        trade_logs,
        target_date=target_date,
        snapshot_dates=snapshot_dates,
    )

    updated_count = 0
    for snapshot_date in snapshot_dates:
        snapshot_row = relevant_rows_by_date[snapshot_date]
        market_value = float(snapshot_row.get("market_value") or 0)
        cash_balance = float(cash_balance_by_date.get(snapshot_date, snapshot_row.get("cash_balance") or 0))
        total_cost = float(total_cost_by_date.get(snapshot_date, snapshot_row.get("total_cost") or 0))
        total_value = round(cash_balance + market_value, 4)
        if _snapshot_matches_current(
            snapshot_row,
            cash_balance=cash_balance,
            market_value=market_value,
            total_value=total_value,
            total_cost=total_cost,
        ):
            continue
        record_account_snapshot(
            account_id,
            snapshot_date=snapshot_date,
            cash_balance=cash_balance,
            market_value=market_value,
            total_value=total_value,
            total_cost=total_cost,
        )
        updated_count += 1

    return updated_count


def _demo_account_is_complete(account_id: int, account_spec: dict[str, Any]) -> bool:
    """데모 계좌가 기대하는 샘플 구성까지 모두 채워졌는지 확인한다."""

    expected_symbols = {str(trade["symbol"]).upper() for trade in account_spec["trades"]}
    if expected_symbols:
        holdings = list_holdings(account_id, include_closed=True)
        holding_symbols = {str(item.get("symbol") or "").upper() for item in holdings}
        if not expected_symbols.issubset(holding_symbols):
            return False

    expected_interest_dates = {str(entry["interest_date"]) for entry in account_spec["interest"]}
    if expected_interest_dates:
        interest_rows = list_daily_interest(account_id)
        interest_dates = {
            str(row.get("date") or row.get("interest_date") or "").strip()
            for row in interest_rows
            if str(row.get("date") or row.get("interest_date") or "").strip()
        }
        if not expected_interest_dates.issubset(interest_dates):
            return False

    snapshot_date = str(account_spec["snapshot_date"])
    snapshots = list_account_snapshots(account_id, start_date=snapshot_date)
    snapshot_dates = {
        str(row.get("snapshot_date") or "").strip()
        for row in snapshots
        if str(row.get("snapshot_date") or "").strip()
    }
    return snapshot_date in snapshot_dates


def _existing_demo_workspace_is_complete(
    existing_demo_accounts: list[dict[str, Any]],
    blueprint: dict[str, Any],
) -> bool:
    """기존 데모 계좌가 전부 존재하고 필요한 샘플 데이터까지 갖췄는지 확인한다."""

    demo_account_ids = {str(account.get("name") or ""): int(account["id"]) for account in existing_demo_accounts}
    expected_names = [str(item["name"]) for item in blueprint["accounts"]]
    if len(demo_account_ids) != len(expected_names):
        return False

    for account_spec in blueprint["accounts"]:
        account_name = str(account_spec["name"])
        account_id = demo_account_ids.get(account_name)
        if not account_id:
            return False
        if not _demo_account_is_complete(account_id, account_spec):
            return False
    return True


def _supabase_delete_account(account_id: int) -> None:
    """Supabase 계좌를 삭제하고 연관 데이터는 CASCADE 규칙에 맡긴다."""

    if not _supabase_get_account(account_id):
        return
    _supabase_request("DELETE", "accounts", filters={"id": f"eq.{account_id}"})


def _sqlite_delete_account(account_id: int) -> None:
    """SQLite 계좌를 삭제하고 연관 데이터는 CASCADE 규칙에 맡긴다."""

    with sqlite_db.connect() as connection:
        connection.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        connection.commit()


def _delete_account(account_id: int) -> None:
    """현재 저장소에서 계좌를 삭제한다."""

    _run_with_fallback(
        supabase_call=lambda: _supabase_delete_account(account_id),
        sqlite_call=lambda: _sqlite_delete_account(account_id),
    )


def seed_demo_workspace(snapshot_base_date: date | str | None = None) -> dict[str, Any]:
    """현재 로그인 사용자 계정에 데모용 샘플 계좌와 거래 데이터를 생성한다."""

    blueprint = _demo_workspace_blueprint(snapshot_base_date=snapshot_base_date)
    existing_accounts = list_accounts()
    demo_names = [str(item["name"]) for item in blueprint["accounts"]]
    demo_reset_names = set(demo_names) | LEGACY_DEMO_ACCOUNT_NAMES
    existing_demo_accounts = [
        account
        for account in existing_accounts
        if str(account.get("name") or "") in demo_reset_names
    ]
    reset_existing_workspace = bool(existing_demo_accounts)
    for account in sorted(existing_demo_accounts, key=lambda row: int(row["id"]), reverse=True):
        _delete_account(int(account["id"]))

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

        update_cash_balance(account_id, _demo_cash_balance_from_spec(account_spec))

    for account_spec in blueprint["accounts"]:
        account_id = created_account_ids[str(account_spec["name"])]
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
    message = "데모 계좌와 샘플 거래 데이터를 만들었습니다."
    if reset_existing_workspace:
        message = "기존 데모 계좌를 초기화하고 샘플 거래 데이터를 다시 만들었습니다."
    return {
        "created": True,
        "selected_account_id": selected_account_id,
        "account_ids": list(created_account_ids.values()),
        "message": message,
    }


def _activate_sqlite(reason: str) -> None:
    sqlite_db.initialize_database()
    _set_backend(BACKEND_SQLITE, reason)


def _build_headers(prefer_return: str | None = None, prefer_resolution: str | None = None) -> dict[str, str]:
    if not _has_supabase_config():
        raise RuntimeError("SUPABASE_URL이 없거나 형식이 올바르지 않거나 SUPABASE_KEY 설정이 없습니다.")
    if app_auth.is_demo_user():
        raise RuntimeError("로컬 데모 세션은 Supabase 요청을 사용하지 않습니다.")

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
    prefer_values: list[str] = []
    if prefer_resolution:
        prefer_values.append(f"resolution={prefer_resolution}")
    if prefer_return:
        prefer_values.append(f"return={prefer_return}")
    if prefer_values:
        headers["Prefer"] = ",".join(prefer_values)
    return headers


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


def _today_iso_date() -> str:
    """오늘 날짜를 ISO 형식으로 반환한다."""

    return datetime.utcnow().date().isoformat()


def _demo_history_date(
    snapshot_base_date: date,
    *,
    years: int = 0,
    months: int = 0,
    days: int = 0,
) -> str:
    """데모 시드용 과거 날짜를 기준 스냅샷 날짜에서 상대 이동해 반환한다."""

    return (snapshot_base_date - relativedelta(years=years, months=months, days=days)).isoformat()


def _coerce_demo_snapshot_base_date(value: date | str | None) -> date:
    """데모 seed 기준일 값을 date로 정규화한다."""

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw_value = str(value or "").strip()
    if raw_value:
        try:
            return date.fromisoformat(raw_value[:10])
        except ValueError:
            pass
    return datetime.utcnow().date()


def _demo_workspace_blueprint(snapshot_base_date: date | str | None = None) -> dict[str, Any]:
    """데모 모드에서 생성할 샘플 계좌와 거래 구성을 반환한다."""

    snapshot_base_date = _coerce_demo_snapshot_base_date(snapshot_base_date)
    snapshot_date = snapshot_base_date.isoformat()
    demo_date = lambda **kwargs: _demo_history_date(snapshot_base_date, **kwargs)
    return {
        "accounts": (
            {
                "name": "데모 IRP",
                "account_type": "retirement",
                "opening_cash": 0.0,
                "cash_flows": (
                    {"flow_type": "personal_deposit", "amount": 2_000_000, "trade_date": demo_date(years=5, days=10), "notes": "초기 IRP 납입"},
                    {"flow_type": "employer_deposit", "amount": 1_500_000, "trade_date": demo_date(years=4, months=9), "notes": "연초 회사 납입"},
                    {"flow_type": "employer_deposit", "amount": 1_500_000, "trade_date": demo_date(years=4, months=4), "notes": "반기 회사 납입"},
                    {"flow_type": "personal_deposit", "amount": 1_200_000, "trade_date": demo_date(years=4, months=1), "notes": "추가 개인 납입"},
                    {"flow_type": "employer_deposit", "amount": 1_800_000, "trade_date": demo_date(years=3, months=7), "notes": "성과급 반영 회사 납입"},
                    {"flow_type": "personal_deposit", "amount": 1_000_000, "trade_date": demo_date(years=3, months=2), "notes": "연말 세액공제 맞춤 납입"},
                    {"flow_type": "employer_deposit", "amount": 1_900_000, "trade_date": demo_date(years=2, months=8), "notes": "정기 회사 납입"},
                    {"flow_type": "withdraw", "amount": 350_000, "trade_date": demo_date(years=2, months=6), "notes": "긴급 생활비 일부 출금"},
                    {"flow_type": "personal_deposit", "amount": 1_100_000, "trade_date": demo_date(years=2, months=3), "notes": "추가 납입"},
                    {"flow_type": "employer_deposit", "amount": 2_000_000, "trade_date": demo_date(years=1, months=9), "notes": "연봉 인상 후 회사 납입"},
                    {"flow_type": "personal_deposit", "amount": 1_300_000, "trade_date": demo_date(years=1, months=4), "notes": "연말정산 전 추가 납입"},
                    {"flow_type": "employer_deposit", "amount": 2_100_000, "trade_date": demo_date(months=9), "notes": "최근 회사 납입"},
                ),
                "trades": (
                    {
                        "symbol": "360750",
                        "product_name": "TIGER 미국S&P500",
                        "trade_type": "buy",
                        "asset_type": "risk",
                        "quantity": 20,
                        "price": 121_000,
                        "trade_date": demo_date(years=4, months=11),
                        "notes": "미국 대표지수 장기 적립 시작",
                    },
                    {
                        "symbol": "381170",
                        "product_name": "TIGER 미국테크TOP10 INDXX",
                        "trade_type": "buy",
                        "asset_type": "risk",
                        "quantity": 18,
                        "price": 78_000,
                        "trade_date": demo_date(years=4, months=5),
                        "notes": "AI·빅테크 비중 확대",
                    },
                    {
                        "symbol": "434730",
                        "product_name": "HANARO 원자력 iSelect",
                        "trade_type": "buy",
                        "asset_type": "risk",
                        "quantity": 16,
                        "price": 24_000,
                        "trade_date": demo_date(years=3, months=10),
                        "notes": "원자력 밸류체인 테마 첫 편입",
                    },
                    {
                        "symbol": "148070",
                        "product_name": "KOSEF 국고채10년",
                        "trade_type": "buy",
                        "asset_type": "safe",
                        "quantity": 25,
                        "price": 112_000,
                        "trade_date": demo_date(years=3, months=8),
                        "notes": "채권 방어 자산 편입",
                    },
                    {
                        "symbol": "411060",
                        "product_name": "ACE KRX금현물",
                        "trade_type": "buy",
                        "asset_type": "safe",
                        "quantity": 14,
                        "price": 49_800,
                        "trade_date": demo_date(years=2, months=11),
                        "notes": "지정학 리스크 대응용 금 비중 추가",
                    },
                    {
                        "symbol": "381170",
                        "product_name": "TIGER 미국테크TOP10 INDXX",
                        "trade_type": "sell",
                        "asset_type": "risk",
                        "quantity": 6,
                        "price": 95_000,
                        "trade_date": demo_date(years=2, months=1),
                        "notes": "기술주 급등 구간 일부 차익 실현",
                    },
                    {
                        "symbol": "434730",
                        "product_name": "HANARO 원자력 iSelect",
                        "trade_type": "buy",
                        "asset_type": "risk",
                        "quantity": 10,
                        "price": 28_000,
                        "trade_date": demo_date(years=1, months=9),
                        "notes": "원자력 수주 뉴스 이후 추가 매수",
                    },
                    {
                        "symbol": "360750",
                        "product_name": "TIGER 미국S&P500",
                        "trade_type": "buy",
                        "asset_type": "risk",
                        "quantity": 7,
                        "price": 149_000,
                        "trade_date": demo_date(years=1, months=4),
                        "notes": "조정 구간 추가 적립",
                    },
                    {
                        "symbol": "148070",
                        "product_name": "KOSEF 국고채10년",
                        "trade_type": "sell",
                        "asset_type": "safe",
                        "quantity": 8,
                        "price": 109_000,
                        "trade_date": demo_date(years=1, months=1),
                        "notes": "채권 비중 일부 축소로 소폭 손실 확정",
                    },
                    {
                        "symbol": "475080",
                        "product_name": "TIGER AI반도체핵심공정",
                        "trade_type": "buy",
                        "asset_type": "risk",
                        "quantity": 22,
                        "price": 15_000,
                        "trade_date": demo_date(months=10),
                        "notes": "AI 반도체 테마 테스트 편입",
                    },
                    {
                        "symbol": "329200",
                        "product_name": "TIGER 리츠부동산인프라",
                        "trade_type": "buy",
                        "asset_type": "safe",
                        "quantity": 30,
                        "price": 5_000,
                        "trade_date": demo_date(months=6),
                        "notes": "현금흐름형 자산 다변화",
                    },
                    {
                        "symbol": "411060",
                        "product_name": "ACE KRX금현물",
                        "trade_type": "sell",
                        "asset_type": "safe",
                        "quantity": 5,
                        "price": 62_000,
                        "trade_date": demo_date(months=2),
                        "notes": "금 가격 상승분 일부 수익 실현",
                    },
                ),
                "interest": (),
                "price_updates": {
                    "360750": 177_500,
                    "381170": 104_000,
                    "434730": 31_500,
                    "148070": 107_000,
                    "411060": 61_200,
                    "475080": 18_600,
                    "329200": 4_650,
                },
                "snapshot_date": snapshot_date,
            },
            {
                "name": "데모 주식",
                "account_type": "brokerage",
                "opening_cash": 0.0,
                "cash_flows": (
                    {"flow_type": "personal_deposit", "amount": 3_000_000, "trade_date": demo_date(years=4, months=10), "notes": "초기 투자금"},
                    {"flow_type": "personal_deposit", "amount": 2_500_000, "trade_date": demo_date(years=4, months=3), "notes": "보너스 일부 투자"},
                    {"flow_type": "personal_deposit", "amount": 2_000_000, "trade_date": demo_date(years=3, months=9), "notes": "추가 적립"},
                    {"flow_type": "withdraw", "amount": 300_000, "trade_date": demo_date(years=3, months=6), "notes": "생활비 인출"},
                    {"flow_type": "personal_deposit", "amount": 1_800_000, "trade_date": demo_date(years=2, months=10), "notes": "ISA 만기 자금 재투자"},
                    {"flow_type": "personal_deposit", "amount": 1_500_000, "trade_date": demo_date(years=2, months=4), "notes": "월급 일부 적립"},
                    {"flow_type": "personal_deposit", "amount": 2_200_000, "trade_date": demo_date(years=1, months=10), "notes": "성과급 재투자"},
                    {"flow_type": "withdraw", "amount": 450_000, "trade_date": demo_date(years=1, months=1), "notes": "여행 경비 인출"},
                    {"flow_type": "personal_deposit", "amount": 1_200_000, "trade_date": demo_date(months=6), "notes": "최근 추가 자금"},
                ),
                "trades": (
                    {
                        "symbol": "005930",
                        "product_name": "삼성전자",
                        "trade_type": "buy",
                        "asset_type": "risk",
                        "quantity": 25,
                        "price": 81_000,
                        "trade_date": demo_date(years=4, months=9),
                        "notes": "반도체 대표주 장기 적립",
                    },
                    {
                        "symbol": "000660",
                        "product_name": "SK하이닉스",
                        "trade_type": "buy",
                        "asset_type": "risk",
                        "quantity": 8,
                        "price": 124_000,
                        "trade_date": demo_date(years=4, months=4),
                        "notes": "HBM 수요 기대 반도체 추가",
                    },
                    {
                        "symbol": "034020",
                        "product_name": "두산에너빌리티",
                        "trade_type": "buy",
                        "asset_type": "risk",
                        "quantity": 40,
                        "price": 17_000,
                        "trade_date": demo_date(years=3, months=11),
                        "notes": "원자력 주기기 테마 선매수",
                    },
                    {
                        "symbol": "035720",
                        "product_name": "카카오",
                        "trade_type": "buy",
                        "asset_type": "risk",
                        "quantity": 18,
                        "price": 121_000,
                        "trade_date": demo_date(years=3, months=5),
                        "notes": "플랫폼 반등 기대 매수",
                    },
                    {
                        "symbol": "035720",
                        "product_name": "카카오",
                        "trade_type": "sell",
                        "asset_type": "risk",
                        "quantity": 18,
                        "price": 58_000,
                        "trade_date": demo_date(years=2, months=7),
                        "notes": "플랫폼 업황 둔화로 손절",
                    },
                    {
                        "symbol": "133690",
                        "product_name": "TIGER 미국나스닥100",
                        "trade_type": "buy",
                        "asset_type": "risk",
                        "quantity": 20,
                        "price": 58_000,
                        "trade_date": demo_date(years=2, months=10),
                        "notes": "미국 성장주 지수 비중 확대",
                    },
                    {
                        "symbol": "035420",
                        "product_name": "NAVER",
                        "trade_type": "buy",
                        "asset_type": "risk",
                        "quantity": 6,
                        "price": 220_000,
                        "trade_date": demo_date(years=2, months=8),
                        "notes": "국내 AI 검색 기대감 반영",
                    },
                    {
                        "symbol": "005930",
                        "product_name": "삼성전자",
                        "trade_type": "sell",
                        "asset_type": "risk",
                        "quantity": 5,
                        "price": 76_000,
                        "trade_date": demo_date(years=2, months=2),
                        "notes": "실적 둔화 구간 비중 조절로 소폭 손실 확정",
                    },
                    {
                        "symbol": "012450",
                        "product_name": "한화에어로스페이스",
                        "trade_type": "buy",
                        "asset_type": "risk",
                        "quantity": 4,
                        "price": 81_000,
                        "trade_date": demo_date(years=1, months=11),
                        "notes": "방산 수출 모멘텀 대응",
                    },
                    {
                        "symbol": "247540",
                        "product_name": "에코프로비엠",
                        "trade_type": "buy",
                        "asset_type": "risk",
                        "quantity": 3,
                        "price": 435_000,
                        "trade_date": demo_date(years=1, months=8),
                        "notes": "2차전지 테마 추세 추종",
                    },
                    {
                        "symbol": "247540",
                        "product_name": "에코프로비엠",
                        "trade_type": "sell",
                        "asset_type": "risk",
                        "quantity": 1,
                        "price": 252_000,
                        "trade_date": demo_date(months=11),
                        "notes": "변동성 확대 구간 손실 축소 매도",
                    },
                    {
                        "symbol": "161510",
                        "product_name": "PLUS 고배당주",
                        "trade_type": "buy",
                        "asset_type": "risk",
                        "quantity": 40,
                        "price": 15_500,
                        "trade_date": demo_date(months=9),
                        "notes": "배당 테마 현금흐름 방어용 편입",
                    },
                    {
                        "symbol": "AAPL",
                        "product_name": "Apple",
                        "trade_type": "buy",
                        "asset_type": "risk",
                        "quantity": 4,
                        "price": 185_000,
                        "trade_date": demo_date(months=8),
                        "notes": "미국 빅테크 분산 편입",
                    },
                    {
                        "symbol": "003670",
                        "product_name": "포스코퓨처엠",
                        "trade_type": "buy",
                        "asset_type": "risk",
                        "quantity": 3,
                        "price": 381_000,
                        "trade_date": demo_date(months=6),
                        "notes": "양극재 테마 반등 기대",
                    },
                    {
                        "symbol": "000660",
                        "product_name": "SK하이닉스",
                        "trade_type": "sell",
                        "asset_type": "risk",
                        "quantity": 3,
                        "price": 240_000,
                        "trade_date": demo_date(months=4),
                        "notes": "반도체 급등 구간 일부 차익 실현",
                    },
                    {
                        "symbol": "148070",
                        "product_name": "KOSEF 국고채10년",
                        "trade_type": "buy",
                        "asset_type": "safe",
                        "quantity": 10,
                        "price": 108_000,
                        "trade_date": demo_date(months=3),
                        "notes": "변동성 완충용 채권 버퍼 확보",
                    },
                ),
                "interest": (),
                "price_updates": {
                    "005930": 78_400,
                    "000660": 216_000,
                    "034020": 28_500,
                    "133690": 90_800,
                    "035420": 224_000,
                    "012450": 296_000,
                    "247540": 212_000,
                    "161510": 16_850,
                    "AAPL": 296_000,
                    "003670": 276_000,
                    "148070": 108_500,
                },
                "snapshot_date": snapshot_date,
            },
        ),
        "transfers": (),
    }


def _normalize_cash_flow_type(flow_type: str) -> str:
    normalized = str(flow_type or "").strip().lower()
    return LEGACY_CASH_FLOW_TYPE_MAP.get(normalized, normalized)


def _cash_event_label(trade_type: str) -> str:
    normalized = _normalize_cash_flow_type(trade_type)
    return CASH_EVENT_LABELS.get(normalized, normalized)


def _metadata_payload(metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return dict(metadata or {})


def _normalize_trade_log_type(trade_type: Any) -> str:
    """거래 로그 유형을 현재 앱 기준 값으로 정규화한다."""

    return _normalize_cash_flow_type(str(trade_type or "").strip().lower())


def _editable_trade_log_type(log: dict[str, Any]) -> str:
    """수정/삭제 가능한 거래 로그 유형을 반환하고, 아니면 예외를 던진다."""

    normalized_type = _normalize_trade_log_type(log.get("trade_type"))
    if normalized_type not in EDITABLE_TRADE_LOG_TYPES:
        raise ValueError("이 거래 기록은 현재 수정/삭제를 지원하지 않습니다.")
    return normalized_type


def _is_exportable_trade_log(log: dict[str, Any]) -> bool:
    """데이터 화면과 CSV에 남길 핵심 거래 로그인지 반환한다."""

    return _normalize_trade_log_type(log.get("trade_type")) in EXPORTABLE_TRADE_LOG_TYPES


def _filter_exportable_trade_logs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """거래 기록 내보내기에서 입금/매수/매도 외 행을 제외한다."""

    return [row for row in rows if _is_exportable_trade_log(row)]


def _cash_delta_for_cash_flow(flow_type: str, amount: float) -> float:
    """현금 흐름 유형과 금액으로 계좌 현금 증감값을 계산한다."""

    normalized_type = _normalize_cash_flow_type(flow_type)
    flow_amount = float(amount or 0)
    return flow_amount if normalized_type in {"personal_deposit", "employer_deposit"} else -flow_amount


def _normalized_trade_notional(symbol: Any, quantity: Any, price: Any) -> float:
    """매수/매도 저장용 거래 총액을 펀드 기준가 단위까지 반영해 계산한다."""

    return normalized_trade_notional(symbol, quantity, price)


def _sorted_trade_logs_for_replay(trade_logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """보유 종목 재계산용으로 거래 로그를 오래된 순서대로 정렬한다."""

    return sorted(
        trade_logs,
        key=lambda row: (
            str(row.get("trade_date") or ""),
            str(row.get("created_at") or ""),
            int(row.get("id") or 0),
        ),
    )


def _desired_holdings_by_symbol(trade_logs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """매수/매도 원장만 기준으로 심볼별 최종 보유 상태를 계산한다."""

    desired_rows: dict[str, dict[str, Any]] = {}
    for log in _sorted_trade_logs_for_replay(trade_logs):
        trade_type = _normalize_trade_log_type(log.get("trade_type"))
        if trade_type not in BUY_SELL_TRADE_TYPES:
            continue

        symbol = str(log.get("symbol") or "").strip().upper()
        if not symbol:
            raise ValueError("종목 코드가 비어 있는 거래 기록은 수정/삭제할 수 없습니다.")

        quantity = float(log.get("quantity") or 0)
        price = float(log.get("price") or 0)
        if quantity <= 0 or price <= 0:
            raise ValueError("수량 또는 단가가 올바르지 않은 거래 기록은 수정/삭제할 수 없습니다.")

        product_name = str(log.get("product_name") or "").strip() or symbol
        asset_type = str(log.get("asset_type") or "risk").strip().lower() or "risk"
        if asset_type not in {"risk", "safe"}:
            raise ValueError("자산군 값이 올바르지 않은 거래 기록은 수정/삭제할 수 없습니다.")

        current_row = desired_rows.get(
            symbol,
            {
                "symbol": symbol,
                "product_name": product_name,
                "asset_type": asset_type,
                "quantity": 0.0,
                "avg_cost": 0.0,
            },
        )
        current_quantity = float(current_row.get("quantity") or 0)
        current_avg_cost = float(current_row.get("avg_cost") or 0)

        if trade_type == "buy":
            next_quantity = current_quantity + quantity
            next_avg_cost = ((current_quantity * current_avg_cost) + (quantity * price)) / next_quantity
        else:
            if current_quantity + 0.000001 < quantity:
                raise ValueError("거래 기록 수정 결과 보유 수량이 음수가 됩니다.")
            next_quantity = max(current_quantity - quantity, 0.0)
            next_avg_cost = current_avg_cost if next_quantity > 0 else 0.0

        desired_rows[symbol] = {
            "symbol": symbol,
            "product_name": product_name if trade_type == "buy" else str(current_row.get("product_name") or product_name),
            "asset_type": asset_type if trade_type == "buy" else str(current_row.get("asset_type") or asset_type),
            "quantity": float(next_quantity),
            "avg_cost": float(next_avg_cost),
        }

    return desired_rows


def _supabase_request(
    method: str,
    table: str,
    data: dict[str, Any] | list[dict[str, Any]] | None = None,
    filters: dict[str, str | int] | None = None,
    prefer_return: str | None = None,
    prefer_resolution: str | None = None,
) -> list[dict[str, Any]] | dict[str, Any] | None:
    request_headers = _build_headers(prefer_return=prefer_return, prefer_resolution=prefer_resolution)
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
        if _is_accounts_rls_hotfix_response(method, table, response.status_code, detail_lower):
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


def _is_accounts_rls_hotfix_response(method: str, table: str, status_code: int, detail_lower: str) -> bool:
    """accounts INSERT가 owner_user_id 핫픽스로 막힌 응답인지 판별한다."""

    return (
        status_code == 403
        and method == "POST"
        and table == "accounts"
        and "row-level security policy" in detail_lower
    )


def _is_missing_owner_user_id_schema_error(exc: Exception) -> bool:
    """구형 스키마에서 owner_user_id 컬럼이 없어 재시도가 필요한지 판별한다."""

    if not isinstance(exc, requests.HTTPError) or exc.response is None:
        return False

    if exc.response.status_code != 400:
        return False

    detail_lower = exc.response.text.strip().replace("\n", " ").lower()
    if "owner_user_id" not in detail_lower:
        return False

    markers = (
        "schema cache",
        "could not find the 'owner_user_id' column",
        "column owner_user_id does not exist",
        "unknown column",
    )
    return any(marker in detail_lower for marker in markers)


def is_accounts_hotfix_error(error: Any) -> bool:
    """accounts RLS 핫픽스가 필요한 오류인지 사용자용으로 판별한다."""

    message = str(error or "").strip().lower()
    return (
        "accounts insert rls" in message
        or ("row-level security" in message and "accounts" in message)
        or ("owner_user_id" in message and ("핫픽스" in message or "hotfix" in message))
    )


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
    insert_payload = {
        "name": stored_name,
        "account_type": cleaned_type,
        "cash_balance": float(opening_cash or 0),
        "owner_user_id": _require_user_id(),
        "created_at": timestamp,
        "updated_at": timestamp,
    }

    try:
        result = _supabase_request(
            "POST",
            "accounts",
            data=insert_payload,
            prefer_return="minimal",
        )
    except requests.HTTPError as exc:
        if not _is_missing_owner_user_id_schema_error(exc):
            raise

        # 운영 스키마가 아직 구버전이면 owner_user_id 없이 한 번만 재시도한다.
        legacy_payload = dict(insert_payload)
        legacy_payload.pop("owner_user_id", None)
        result = _supabase_request(
            "POST",
            "accounts",
            data=legacy_payload,
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


def _supabase_update_cash_balance(account_id: int, amount: float, *, allow_negative: bool = False) -> None:
    """Supabase 계좌의 현금 잔액을 갱신한다."""

    if not allow_negative and float(amount) < 0:
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


def _supabase_record_realtime_price_tick(
    *,
    account_id: int,
    holding_id: int | None,
    symbol: str,
    price: float,
    previous_close: float | None = None,
    day_change_rate: float | None = None,
    currency: str = "KRW",
    quote_time: str | None = None,
    source: str = "KIS WebSocket",
    metadata_json: dict[str, Any] | None = None,
) -> None:
    _require_user_id()
    timestamp = str(quote_time or now_iso())
    if holding_id is not None:
        _supabase_set_holding_price(holding_id, float(price), timestamp)
    _supabase_request(
        "POST",
        "realtime_price_ticks",
        data={
            "account_id": account_id,
            "holding_id": holding_id,
            "symbol": str(symbol or "").strip().upper(),
            "price": float(price),
            "previous_close": float(previous_close) if previous_close is not None else None,
            "day_change_rate": float(day_change_rate) if day_change_rate is not None else None,
            "currency": str(currency or "KRW").strip().upper() or "KRW",
            "quote_time": timestamp,
            "ingested_at": now_iso(),
            "source": str(source or "KIS WebSocket").strip() or "KIS WebSocket",
            "metadata_json": _metadata_payload(metadata_json),
        },
        prefer_return="minimal",
    )


def _supabase_list_realtime_price_ticks(account_id: int, limit: int = 200) -> list[dict[str, Any]]:
    result = _supabase_request(
        "GET",
        "realtime_price_ticks",
        filters={
            "account_id": f"eq.{account_id}",
            "order": "quote_time.desc,id.desc",
            "limit": int(limit),
        },
    )
    return list(result or [])


def _supabase_upsert_realtime_worker_status(
    *,
    account_id: int,
    worker_name: str,
    connection_state: str,
    last_seen_at: str | None = None,
    last_quote_at: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> None:
    _require_user_id()
    payload = {
        "worker_name": str(worker_name or "").strip() or "kis-quote-worker",
        "connection_state": str(connection_state or "").strip() or "unknown",
        "last_seen_at": str(last_seen_at or "").strip() or None,
        "updated_at": now_iso(),
        "metadata_json": _metadata_payload(metadata_json),
    }
    normalized_last_quote_at = str(last_quote_at or "").strip() or None
    if normalized_last_quote_at is not None:
        payload["last_quote_at"] = normalized_last_quote_at
    existing = _supabase_request("GET", "realtime_worker_status", filters={"account_id": f"eq.{account_id}"}) or []
    if existing:
        _supabase_request(
            "PATCH",
            "realtime_worker_status",
            data=payload,
            filters={"account_id": f"eq.{account_id}"},
            prefer_return="minimal",
        )
        return
    if normalized_last_quote_at is None:
        payload.pop("last_quote_at", None)
    _supabase_request(
        "POST",
        "realtime_worker_status",
        data={"account_id": account_id, **payload},
        prefer_return="minimal",
    )


def _supabase_get_realtime_worker_status(account_id: int) -> dict[str, Any] | None:
    rows = _supabase_request("GET", "realtime_worker_status", filters={"account_id": f"eq.{account_id}"}) or []
    return rows[0] if rows else None


def _supabase_latest_realtime_quote_time(account_id: int) -> str:
    rows = _supabase_request(
        "GET",
        "realtime_price_ticks",
        filters={
            "account_id": f"eq.{account_id}",
            "select": "quote_time",
            "order": "quote_time.desc,id.desc",
            "limit": 1,
        },
    ) or []
    if rows and rows[0].get("quote_time"):
        return str(rows[0]["quote_time"])
    holdings = _supabase_request(
        "GET",
        "holdings",
        filters={
            "account_id": f"eq.{account_id}",
            "select": "price_updated_at",
            "order": "price_updated_at.desc",
            "limit": 1,
        },
    ) or []
    return str(holdings[0].get("price_updated_at") or "") if holdings else ""


def _supabase_list_trade_logs(account_id: int) -> list[dict[str, Any]]:
    result = _supabase_request("GET", "trade_logs", filters={"account_id": f"eq.{account_id}"})
    logs = result or []
    return sorted(logs, key=lambda row: (row.get("trade_date", ""), row.get("id", 0)), reverse=True)


def _supabase_get_trade_log(account_id: int, log_id: int) -> dict[str, Any] | None:
    """Supabase에서 계좌 소유 거래 로그 1건을 조회한다."""

    result = _supabase_request(
        "GET",
        "trade_logs",
        filters={
            "account_id": f"eq.{account_id}",
            "id": f"eq.{int(log_id)}",
        },
    ) or []
    row = result[0] if isinstance(result, list) and result else result
    return dict(row) if isinstance(row, dict) else None


def _supabase_apply_holding_state(
    account_id: int,
    *,
    trade_logs: list[dict[str, Any]],
    timestamp: str,
) -> None:
    """Supabase 보유 종목 테이블을 현재 매수/매도 원장 기준으로 다시 맞춘다."""

    desired_rows = _desired_holdings_by_symbol(trade_logs)
    existing_rows = _supabase_request("GET", "holdings", filters={"account_id": f"eq.{account_id}"}) or []
    existing_by_symbol = {
        str(row.get("symbol") or "").strip().upper(): row
        for row in existing_rows
        if str(row.get("symbol") or "").strip()
    }

    for symbol, desired in desired_rows.items():
        existing_row = existing_by_symbol.pop(symbol, None)
        if existing_row:
            _supabase_request(
                "PATCH",
                "holdings",
                data={
                    "product_name": desired["product_name"],
                    "asset_type": desired["asset_type"],
                    "quantity": float(desired["quantity"] or 0),
                    "avg_cost": float(desired["avg_cost"] or 0),
                    "updated_at": timestamp,
                },
                filters={"id": f"eq.{int(existing_row['id'])}"},
                prefer_return="minimal",
            )
            continue

        current_price = float(desired["avg_cost"] or 0)
        _supabase_request(
            "POST",
            "holdings",
            data={
                "account_id": account_id,
                "symbol": symbol,
                "product_name": desired["product_name"],
                "asset_type": desired["asset_type"],
                "quantity": float(desired["quantity"] or 0),
                "avg_cost": float(desired["avg_cost"] or 0),
                "current_price": current_price,
                "price_updated_at": timestamp,
                "created_at": timestamp,
                "updated_at": timestamp,
            },
            prefer_return="minimal",
        )

    for stale_row in existing_by_symbol.values():
        _supabase_request(
            "PATCH",
            "holdings",
            data={
                "quantity": 0.0,
                "avg_cost": 0.0,
                "updated_at": timestamp,
            },
            filters={"id": f"eq.{int(stale_row['id'])}"},
            prefer_return="minimal",
        )


def _supabase_list_daily_interest(account_id: int) -> list[dict[str, Any]]:
    result = _supabase_request("GET", "daily_interest", filters={"account_id": f"eq.{account_id}"})
    rows = result or []
    return sorted(rows, key=lambda row: (row.get("date", ""), row.get("id", 0)))


def _supabase_list_account_snapshots(account_id: int, start_date: str | None = None) -> list[dict[str, Any]]:
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
    if table_name == "trade_logs":
        rows = _filter_exportable_trade_logs(rows)
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

    total_amount = _normalized_trade_notional(cleaned_symbol, share_count, trade_price)
    cash_delta = -total_amount if cleaned_type == "buy" else total_amount
    timestamp = now_iso()
    holdings = _supabase_request("GET", "holdings", filters={"account_id": f"eq.{account_id}"}) or []
    holdings = [row for row in holdings if row.get("symbol") == cleaned_symbol]
    holding_row = holdings[0] if holdings else None

    if cleaned_type == "buy":
        if holding_row:
            previous_quantity = float(holding_row.get("quantity", 0) or 0)
            previous_cost = float(holding_row.get("avg_cost", 0) or 0)
            next_quantity = previous_quantity + share_count
            weighted_avg_cost = ((previous_quantity * previous_cost) + (share_count * trade_price)) / next_quantity
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
        metadata_json={},
    )


def _supabase_update_trade_log(
    account_id: int,
    log_id: int,
    *,
    trade_type: str,
    trade_date: str,
    notes: str = "",
    symbol: str = "",
    product_name: str = "",
    asset_type: str = "risk",
    quantity: float = 0.0,
    price: float = 0.0,
    amount: float = 0.0,
) -> None:
    """Supabase 거래 로그 1건을 수정한다."""

    existing_log = _supabase_get_trade_log(account_id, log_id)
    if not existing_log:
        raise ValueError("거래 기록을 찾을 수 없습니다.")

    existing_type = _editable_trade_log_type(existing_log)
    next_type = _normalize_trade_log_type(trade_type)
    if existing_type in BUY_SELL_TRADE_TYPES and next_type not in BUY_SELL_TRADE_TYPES:
        raise ValueError("매수/매도 기록은 매수/매도 안에서만 수정할 수 있습니다.")
    if existing_type in EDITABLE_CASH_FLOW_LOG_TYPES and next_type not in EDITABLE_CASH_FLOW_LOG_TYPES:
        raise ValueError("현금 흐름 기록은 현금 흐름 안에서만 수정할 수 있습니다.")

    timestamp = now_iso()
    account = _supabase_get_account(account_id)
    if not account:
        raise ValueError("계좌를 찾을 수 없습니다.")

    all_logs = _supabase_list_trade_logs(account_id)
    candidate_logs: list[dict[str, Any]] = []

    if existing_type in BUY_SELL_TRADE_TYPES:
        cleaned_symbol = str(symbol or "").strip().upper()
        cleaned_name = str(product_name or "").strip()
        cleaned_asset_type = str(asset_type or "risk").strip().lower()
        share_count = float(quantity or 0)
        trade_price = float(price or 0)
        if next_type not in BUY_SELL_TRADE_TYPES:
            raise ValueError("매수/매도 기록만 수정할 수 있습니다.")
        if cleaned_asset_type not in {"risk", "safe"}:
            raise ValueError("자산군 값이 올바르지 않습니다.")
        if not cleaned_symbol:
            raise ValueError("종목 코드 또는 심볼을 입력해 주세요.")
        if not cleaned_name:
            raise ValueError("종목명을 입력해 주세요.")
        if share_count <= 0 or trade_price <= 0:
            raise ValueError("수량과 단가는 모두 0보다 커야 합니다.")

        total_amount = _normalized_trade_notional(cleaned_symbol, share_count, trade_price)
        cash_delta = -total_amount if next_type == "buy" else total_amount
        updated_log = dict(existing_log)
        updated_log.update(
            {
                "symbol": cleaned_symbol,
                "product_name": cleaned_name,
                "trade_type": next_type,
                "asset_type": cleaned_asset_type,
                "quantity": share_count,
                "price": trade_price,
                "total_amount": total_amount,
                "cash_delta": cash_delta,
                "trade_date": str(trade_date),
                "notes": str(notes or "").strip(),
            }
        )
        for log in all_logs:
            candidate_logs.append(updated_log if int(log.get("id") or 0) == int(log_id) else log)
        _desired_holdings_by_symbol(candidate_logs)
        _supabase_request(
            "PATCH",
            "trade_logs",
            data={
                "symbol": cleaned_symbol,
                "product_name": cleaned_name,
                "trade_type": next_type,
                "asset_type": cleaned_asset_type,
                "quantity": share_count,
                "price": trade_price,
                "total_amount": total_amount,
                "cash_delta": cash_delta,
                "trade_date": str(trade_date),
                "notes": str(notes or "").strip(),
            },
            filters={"id": f"eq.{int(log_id)}"},
            prefer_return="minimal",
        )
        _supabase_apply_holding_state(account_id, trade_logs=candidate_logs, timestamp=timestamp)
        return

    normalized_flow_type = _normalize_cash_flow_type(next_type)
    flow_amount = float(amount or 0)
    if normalized_flow_type not in EDITABLE_CASH_FLOW_LOG_TYPES:
        raise ValueError("지원하지 않는 현금 흐름 유형입니다.")
    if flow_amount <= 0:
        raise ValueError("금액은 0보다 커야 합니다.")

    old_cash_delta = float(existing_log.get("cash_delta") or 0)
    new_cash_delta = _cash_delta_for_cash_flow(normalized_flow_type, flow_amount)
    next_cash = float(account.get("cash_balance") or 0) - old_cash_delta + new_cash_delta
    if next_cash < -0.000001:
        raise ValueError("수정 결과 현금이 부족합니다.")

    _supabase_request(
        "PATCH",
        "trade_logs",
        data={
            "symbol": "",
            "product_name": _cash_event_label(normalized_flow_type),
            "trade_type": normalized_flow_type,
            "asset_type": "cash",
            "quantity": 0,
            "price": 0,
            "total_amount": flow_amount,
            "cash_delta": new_cash_delta,
            "trade_date": str(trade_date),
            "notes": str(notes or "").strip(),
        },
        filters={"id": f"eq.{int(log_id)}"},
        prefer_return="minimal",
    )
    _supabase_update_cash_balance(account_id, next_cash)


def _supabase_delete_trade_log(account_id: int, log_id: int) -> None:
    """Supabase 거래 로그 1건을 삭제한다."""

    existing_log = _supabase_get_trade_log(account_id, log_id)
    if not existing_log:
        raise ValueError("거래 기록을 찾을 수 없습니다.")

    existing_type = _editable_trade_log_type(existing_log)
    timestamp = now_iso()

    if existing_type in BUY_SELL_TRADE_TYPES:
        remaining_logs = [
            log
            for log in _supabase_list_trade_logs(account_id)
            if int(log.get("id") or 0) != int(log_id)
        ]
        _desired_holdings_by_symbol(remaining_logs)
        _supabase_request("DELETE", "trade_logs", filters={"id": f"eq.{int(log_id)}"})
        _supabase_apply_holding_state(account_id, trade_logs=remaining_logs, timestamp=timestamp)
        return

    account = _supabase_get_account(account_id)
    if not account:
        raise ValueError("계좌를 찾을 수 없습니다.")

    old_cash_delta = float(existing_log.get("cash_delta") or 0)
    next_cash = float(account.get("cash_balance") or 0) - old_cash_delta
    if next_cash < -0.000001:
        raise ValueError("삭제 결과 현금이 부족합니다.")

    _supabase_request("DELETE", "trade_logs", filters={"id": f"eq.{int(log_id)}"})
    _supabase_update_cash_balance(account_id, next_cash)


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


def _supabase_delete_rows_by_ids(table_name: str, row_ids: list[int]) -> None:
    """Supabase 테이블에서 지정한 ID 행들을 삭제한다."""

    cleaned_ids = [str(int(row_id)) for row_id in row_ids if int(row_id) > 0]
    if not cleaned_ids:
        return
    _supabase_request("DELETE", table_name, filters={"id": f"in.({','.join(cleaned_ids)})"})


def _supabase_replace_interest_history(
    account_id: int,
    *,
    target_date: str,
    desired_entries: list[tuple[str, float]],
) -> None:
    """Supabase 계좌의 자동 일별 이자 이력을 목표 일정으로 다시 만든다."""

    account = _supabase_get_account(account_id)
    if not account:
        raise ValueError("계좌를 찾을 수 없습니다.")

    target_date_value = date.fromisoformat(target_date)
    trade_logs = _supabase_list_trade_logs(account_id)
    interest_rows = _supabase_list_daily_interest(account_id)
    removed_interest_total = _existing_interest_total_to_remove(
        trade_logs,
        interest_rows,
        target_date=target_date_value,
    )
    base_cash = round(float(account.get("cash_balance") or 0) - removed_interest_total, 4)
    daily_interest_ids = [
        int(row["id"])
        for row in interest_rows
        if row.get("id") is not None
        and (_parse_iso_date(row.get("date") or row.get("interest_date")) or date.max) <= target_date_value
    ]
    auto_trade_log_ids = [
        int(log["id"])
        for log in trade_logs
        if log.get("id") is not None
        and _is_auto_daily_interest_trade(log)
        and (_parse_iso_date(log.get("trade_date")) or date.max) <= target_date_value
    ]

    _supabase_delete_rows_by_ids("daily_interest", daily_interest_ids)
    _supabase_delete_rows_by_ids("trade_logs", auto_trade_log_ids)
    _supabase_update_cash_balance(account_id, base_cash, allow_negative=True)
    for interest_date, amount in desired_entries:
        _supabase_record_daily_interest(account_id, interest_date=interest_date, amount=amount)


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


def _supabase_list_valuation_snapshots(
    account_id: int,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    filters: dict[str, str | int] = {"account_id": f"eq.{account_id}"}
    if start_date:
        filters["valuation_date"] = f"gte.{start_date}"
    if end_date:
        filters["valuation_date"] = f"lte.{end_date}"
    result = _supabase_request("GET", "daily_valuation_snapshot", filters=filters)
    rows = result or []
    return sorted(rows, key=lambda row: (row.get("valuation_date", ""), row.get("id", 0)), reverse=True)


def _supabase_record_valuation_snapshots(account_id: int, snapshots: list[dict[str, Any]]) -> None:
    """Supabase daily_valuation_snapshot를 batch upsert한다."""

    if not snapshots:
        return

    timestamp = now_iso()
    rows: list[dict[str, Any]] = []
    for snapshot in snapshots:
        row = dict(snapshot)
        row["account_id"] = account_id
        row["updated_at"] = timestamp
        row.setdefault("created_at", timestamp)
        rows.append(row)

    _supabase_request(
        "POST",
        "daily_valuation_snapshot",
        data=rows,
        filters={"on_conflict": "account_id,valuation_date"},
        prefer_return="minimal",
        prefer_resolution="merge-duplicates",
    )


def _supabase_delete_valuation_snapshots(account_id: int, start_date: str | None = None) -> None:
    """Supabase 계좌의 입금 기준 평가 스냅샷을 전체 또는 시작일 이후로 삭제한다."""

    filters: dict[str, str | int] = {"account_id": f"eq.{account_id}"}
    if start_date:
        filters["valuation_date"] = f"gte.{start_date}"
    _supabase_request(
        "DELETE",
        "daily_valuation_snapshot",
        filters=filters,
    )


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


def _sqlite_record_realtime_price_tick(
    *,
    account_id: int,
    holding_id: int | None,
    symbol: str,
    price: float,
    previous_close: float | None = None,
    day_change_rate: float | None = None,
    currency: str = "KRW",
    quote_time: str | None = None,
    source: str = "KIS WebSocket",
    metadata_json: dict[str, Any] | None = None,
) -> None:
    _require_user_id()
    sqlite_db.record_realtime_price_tick(
        account_id=account_id,
        holding_id=holding_id,
        symbol=symbol,
        price=price,
        previous_close=previous_close,
        day_change_rate=day_change_rate,
        currency=currency,
        quote_time=quote_time,
        source=source,
        metadata_json=metadata_json,
    )


def _sqlite_list_realtime_price_ticks(account_id: int, limit: int = 200) -> list[dict[str, Any]]:
    if not _sqlite_get_account(account_id):
        return []
    return sqlite_db.list_realtime_price_ticks(account_id, limit=limit)


def _sqlite_upsert_realtime_worker_status(
    *,
    account_id: int,
    worker_name: str,
    connection_state: str,
    last_seen_at: str | None = None,
    last_quote_at: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> None:
    _require_user_id()
    sqlite_db.upsert_realtime_worker_status(
        account_id=account_id,
        worker_name=worker_name,
        connection_state=connection_state,
        last_seen_at=last_seen_at,
        last_quote_at=last_quote_at,
        metadata_json=metadata_json,
    )


def _sqlite_get_realtime_worker_status(account_id: int) -> dict[str, Any] | None:
    if not _sqlite_get_account(account_id):
        return None
    return sqlite_db.get_realtime_worker_status(account_id)


def _sqlite_latest_realtime_quote_time(account_id: int) -> str:
    if not _sqlite_get_account(account_id):
        return ""
    return sqlite_db.latest_realtime_quote_time(account_id)


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


def _sqlite_list_valuation_snapshots(
    account_id: int,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    if not _sqlite_get_account(account_id):
        return []
    return sqlite_db.list_valuation_snapshots(account_id, start_date=start_date, end_date=end_date)


def _sqlite_export_dataframe_rows(table_name: str) -> list[dict[str, Any]]:
    if table_name == "accounts":
        return _sqlite_list_accounts()

    accounts = _sqlite_list_accounts()
    account_ids = _owned_account_ids(accounts)
    rows = sqlite_db.export_dataframe_rows(table_name)
    filtered = [row for row in rows if int(row.get("account_id", 0) or 0) in account_ids]
    if table_name == "trade_logs":
        filtered = _filter_exportable_trade_logs(filtered)
    return sorted(filtered, key=lambda row: row.get("id", 0))


def _read_accounts_once(backend_name: str) -> list[dict[str, Any]]:
    """현재 백엔드 기준 계좌 목록을 한 번 조회한다."""

    if backend_name == BACKEND_SQLITE:
        return _sqlite_list_accounts()

    try:
        return _supabase_list_accounts()
    except Exception as exc:
        if _should_fallback(exc):
            return _sqlite_list_accounts()
        raise


def _read_account_once(backend_name: str, account_id: int) -> dict[str, Any] | None:
    """현재 백엔드 기준 단일 계좌를 한 번 조회한다."""

    if backend_name == BACKEND_SQLITE:
        return _sqlite_get_account(account_id)

    try:
        return _supabase_get_account(account_id)
    except Exception as exc:
        if _should_fallback(exc):
            return _sqlite_get_account(account_id)
        raise


def _read_holdings_once(backend_name: str, account_id: int, include_closed: bool) -> list[dict[str, Any]]:
    """현재 백엔드 기준 보유 종목 목록을 한 번 조회한다."""

    if backend_name == BACKEND_SQLITE:
        return _sqlite_list_holdings(account_id, include_closed)

    try:
        return _supabase_list_holdings(account_id, include_closed)
    except Exception as exc:
        if _should_fallback(exc):
            return _sqlite_list_holdings(account_id, include_closed)
        raise


def _read_trade_logs_once(backend_name: str, account_id: int) -> list[dict[str, Any]]:
    """현재 백엔드 기준 거래 원장을 한 번 조회한다."""

    if backend_name == BACKEND_SQLITE:
        return _sqlite_list_trade_logs(account_id)

    try:
        return _supabase_list_trade_logs(account_id)
    except Exception as exc:
        if _should_fallback(exc):
            return _sqlite_list_trade_logs(account_id)
        raise


def _read_account_snapshots_once(backend_name: str, account_id: int, start_date: str | None) -> list[dict[str, Any]]:
    """현재 백엔드 기준 일별 스냅샷을 한 번 조회한다."""

    if backend_name == BACKEND_SQLITE:
        return _sqlite_list_account_snapshots(account_id, start_date)

    try:
        return _supabase_list_account_snapshots(account_id, start_date)
    except Exception as exc:
        if _should_fallback(exc):
            return _sqlite_list_account_snapshots(account_id, start_date)
        raise


def _read_valuation_snapshots_once(
    backend_name: str,
    account_id: int,
    start_date: str | None,
    end_date: str | None,
) -> list[dict[str, Any]]:
    """현재 백엔드 기준 입금 평가 스냅샷을 한 번 조회한다."""

    if backend_name == BACKEND_SQLITE:
        return _sqlite_list_valuation_snapshots(account_id, start_date=start_date, end_date=end_date)

    try:
        return _supabase_list_valuation_snapshots(account_id, start_date=start_date, end_date=end_date)
    except Exception as exc:
        if _should_fallback(exc):
            return _sqlite_list_valuation_snapshots(account_id, start_date=start_date, end_date=end_date)
        raise


@st.cache_data(ttl=ACCOUNTS_CACHE_TTL_SECONDS, max_entries=200, show_spinner=False)
def _cached_list_accounts(scope_key: str, backend_name: str, refresh_token: int) -> list[dict[str, Any]]:
    """사용자/세션 범위의 계좌 목록 조회를 캐시한다."""

    return _read_accounts_once(backend_name)


@st.cache_data(ttl=ACCOUNT_CACHE_TTL_SECONDS, max_entries=300, show_spinner=False)
def _cached_get_account(
    scope_key: str,
    backend_name: str,
    account_id: int,
    refresh_token: int,
) -> dict[str, Any] | None:
    """사용자/세션 범위의 단일 계좌 조회를 캐시한다."""

    return _read_account_once(backend_name, account_id)


@st.cache_data(ttl=HOLDINGS_CACHE_TTL_SECONDS, max_entries=400, show_spinner=False)
def _cached_list_holdings(
    scope_key: str,
    backend_name: str,
    account_id: int,
    include_closed: bool,
    refresh_token: int,
) -> list[dict[str, Any]]:
    """사용자/세션 범위의 보유 종목 조회를 짧게 캐시한다."""

    return _read_holdings_once(backend_name, account_id, include_closed)


@st.cache_data(ttl=TRADE_LOGS_CACHE_TTL_SECONDS, max_entries=400, show_spinner=False)
def _cached_list_trade_logs(
    scope_key: str,
    backend_name: str,
    account_id: int,
    refresh_token: int,
) -> list[dict[str, Any]]:
    """사용자/세션 범위의 거래 원장 조회를 캐시한다."""

    return _read_trade_logs_once(backend_name, account_id)


@st.cache_data(ttl=SNAPSHOTS_CACHE_TTL_SECONDS, max_entries=400, show_spinner=False)
def _cached_list_account_snapshots(
    scope_key: str,
    backend_name: str,
    account_id: int,
    start_date: str | None,
    refresh_token: int,
) -> list[dict[str, Any]]:
    """사용자/세션 범위의 일별 스냅샷 조회를 캐시한다."""

    return _read_account_snapshots_once(backend_name, account_id, start_date)


@st.cache_data(ttl=VALUATION_SNAPSHOTS_CACHE_TTL_SECONDS, max_entries=400, show_spinner=False)
def _cached_list_valuation_snapshots(
    scope_key: str,
    backend_name: str,
    account_id: int,
    start_date: str | None,
    end_date: str | None,
    refresh_token: int,
) -> list[dict[str, Any]]:
    """사용자/세션 범위의 입금 평가 스냅샷 조회를 캐시한다."""

    return _read_valuation_snapshots_once(backend_name, account_id, start_date, end_date)


def clear_data_cache() -> None:
    """DB 조회 캐시를 모두 비운다."""

    for cache_function in (
        _cached_list_accounts,
        _cached_get_account,
        _cached_list_holdings,
        _cached_list_trade_logs,
        _cached_list_account_snapshots,
        _cached_list_valuation_snapshots,
    ):
        getattr(cache_function, "clear", lambda: None)()


def _invalidate_data_cache_after_write() -> None:
    """쓰기 성공 후 세션 토큰과 Streamlit DB 조회 캐시를 함께 무효화한다."""

    mark_data_dirty()
    clear_data_cache()


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


def _sqlite_get_trade_log(account_id: int, log_id: int) -> dict[str, Any] | None:
    """SQLite에서 계좌 소유 거래 로그 1건을 조회한다."""

    if not sqlite_db.get_account(account_id):
        return None

    with sqlite_db.connect() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM trade_logs
            WHERE account_id = ?
              AND id = ?
            LIMIT 1
            """,
            (account_id, int(log_id)),
        ).fetchone()
    return dict(row) if row else None


def _sqlite_apply_holding_state(
    connection: Any,
    account_id: int,
    *,
    trade_logs: list[dict[str, Any]],
    timestamp: str,
) -> None:
    """SQLite 보유 종목 테이블을 현재 매수/매도 원장 기준으로 다시 맞춘다."""

    desired_rows = _desired_holdings_by_symbol(trade_logs)
    existing_rows = connection.execute(
        """
        SELECT *
        FROM holdings
        WHERE account_id = ?
        """,
        (account_id,),
    ).fetchall()
    existing_by_symbol = {
        str(row["symbol"] or "").strip().upper(): row
        for row in existing_rows
        if str(row["symbol"] or "").strip()
    }

    for symbol, desired in desired_rows.items():
        existing_row = existing_by_symbol.pop(symbol, None)
        if existing_row:
            connection.execute(
                """
                UPDATE holdings
                SET product_name = ?, asset_type = ?, quantity = ?, avg_cost = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    str(desired["product_name"]),
                    str(desired["asset_type"]),
                    float(desired["quantity"] or 0),
                    float(desired["avg_cost"] or 0),
                    timestamp,
                    int(existing_row["id"]),
                ),
            )
            continue

        current_price = float(desired["avg_cost"] or 0)
        connection.execute(
            """
            INSERT INTO holdings (
                account_id, symbol, product_name, asset_type, quantity, avg_cost, current_price,
                price_updated_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                symbol,
                str(desired["product_name"]),
                str(desired["asset_type"]),
                float(desired["quantity"] or 0),
                float(desired["avg_cost"] or 0),
                current_price,
                timestamp,
                timestamp,
                timestamp,
            ),
        )

    for stale_row in existing_by_symbol.values():
        connection.execute(
            """
            UPDATE holdings
            SET quantity = 0, avg_cost = 0, updated_at = ?
            WHERE id = ?
            """,
            (timestamp, int(stale_row["id"])),
        )


def _sqlite_update_trade_log(
    account_id: int,
    log_id: int,
    *,
    trade_type: str,
    trade_date: str,
    notes: str = "",
    symbol: str = "",
    product_name: str = "",
    asset_type: str = "risk",
    quantity: float = 0.0,
    price: float = 0.0,
    amount: float = 0.0,
) -> None:
    """SQLite 거래 로그 1건을 수정한다."""

    existing_log = _sqlite_get_trade_log(account_id, log_id)
    if not existing_log:
        raise ValueError("거래 기록을 찾을 수 없습니다.")

    existing_type = _editable_trade_log_type(existing_log)
    next_type = _normalize_trade_log_type(trade_type)
    if existing_type in BUY_SELL_TRADE_TYPES and next_type not in BUY_SELL_TRADE_TYPES:
        raise ValueError("매수/매도 기록은 매수/매도 안에서만 수정할 수 있습니다.")
    if existing_type in EDITABLE_CASH_FLOW_LOG_TYPES and next_type not in EDITABLE_CASH_FLOW_LOG_TYPES:
        raise ValueError("현금 흐름 기록은 현금 흐름 안에서만 수정할 수 있습니다.")

    timestamp = sqlite_db.now_iso()
    with sqlite_db.connect() as connection:
        account_row = sqlite_db._require_account(connection, account_id)

        if existing_type in BUY_SELL_TRADE_TYPES:
            cleaned_symbol = str(symbol or "").strip().upper()
            cleaned_name = str(product_name or "").strip()
            cleaned_asset_type = str(asset_type or "risk").strip().lower()
            share_count = float(quantity or 0)
            trade_price = float(price or 0)
            if next_type not in BUY_SELL_TRADE_TYPES:
                raise ValueError("매수/매도 기록만 수정할 수 있습니다.")
            if cleaned_asset_type not in {"risk", "safe"}:
                raise ValueError("자산군 값이 올바르지 않습니다.")
            if not cleaned_symbol:
                raise ValueError("종목 코드를 입력해 주세요.")
            if not cleaned_name:
                raise ValueError("종목명을 입력해 주세요.")
            if share_count <= 0 or trade_price <= 0:
                raise ValueError("수량과 단가는 모두 0보다 커야 합니다.")

            total_amount = _normalized_trade_notional(cleaned_symbol, share_count, trade_price)
            cash_delta = -total_amount if next_type == "buy" else total_amount
            connection.execute(
                """
                UPDATE trade_logs
                SET symbol = ?, product_name = ?, trade_type = ?, asset_type = ?, quantity = ?, price = ?,
                    total_amount = ?, cash_delta = ?, trade_date = ?, notes = ?
                WHERE id = ?
                """,
                (
                    cleaned_symbol,
                    cleaned_name,
                    next_type,
                    cleaned_asset_type,
                    share_count,
                    trade_price,
                    total_amount,
                    cash_delta,
                    str(trade_date),
                    str(notes or "").strip(),
                    int(log_id),
                ),
            )
            trade_logs = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT *
                    FROM trade_logs
                    WHERE account_id = ?
                    ORDER BY trade_date DESC, id DESC
                    """,
                    (account_id,),
                ).fetchall()
            ]
            _sqlite_apply_holding_state(connection, account_id, trade_logs=trade_logs, timestamp=timestamp)
            connection.commit()
            return

        normalized_flow_type = _normalize_cash_flow_type(next_type)
        flow_amount = float(amount or 0)
        if normalized_flow_type not in EDITABLE_CASH_FLOW_LOG_TYPES:
            raise ValueError("지원하지 않는 현금 흐름 유형입니다.")
        if flow_amount <= 0:
            raise ValueError("금액은 0보다 커야 합니다.")

        old_cash_delta = float(existing_log.get("cash_delta") or 0)
        new_cash_delta = _cash_delta_for_cash_flow(normalized_flow_type, flow_amount)
        next_cash = float(account_row["cash_balance"] or 0) - old_cash_delta + new_cash_delta
        if next_cash < -0.000001:
            raise ValueError("수정 결과 현금이 부족합니다.")

        sqlite_db._update_account_cash_balance(connection, account_id, next_cash, timestamp)
        connection.execute(
            """
            UPDATE trade_logs
            SET symbol = ?, product_name = ?, trade_type = ?, asset_type = ?, quantity = ?, price = ?,
                total_amount = ?, cash_delta = ?, trade_date = ?, notes = ?
            WHERE id = ?
            """,
            (
                "",
                _cash_event_label(normalized_flow_type),
                normalized_flow_type,
                "cash",
                0,
                0,
                flow_amount,
                new_cash_delta,
                str(trade_date),
                str(notes or "").strip(),
                int(log_id),
            ),
        )
        connection.commit()


def _sqlite_delete_trade_log(account_id: int, log_id: int) -> None:
    """SQLite 거래 로그 1건을 삭제한다."""

    existing_log = _sqlite_get_trade_log(account_id, log_id)
    if not existing_log:
        raise ValueError("거래 기록을 찾을 수 없습니다.")

    existing_type = _editable_trade_log_type(existing_log)
    timestamp = sqlite_db.now_iso()
    with sqlite_db.connect() as connection:
        account_row = sqlite_db._require_account(connection, account_id)

        if existing_type in BUY_SELL_TRADE_TYPES:
            connection.execute("DELETE FROM trade_logs WHERE id = ?", (int(log_id),))
            trade_logs = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT *
                    FROM trade_logs
                    WHERE account_id = ?
                    ORDER BY trade_date DESC, id DESC
                    """,
                    (account_id,),
                ).fetchall()
            ]
            _sqlite_apply_holding_state(connection, account_id, trade_logs=trade_logs, timestamp=timestamp)
            connection.commit()
            return

        old_cash_delta = float(existing_log.get("cash_delta") or 0)
        next_cash = float(account_row["cash_balance"] or 0) - old_cash_delta
        if next_cash < -0.000001:
            raise ValueError("삭제 결과 현금이 부족합니다.")

        sqlite_db._update_account_cash_balance(connection, account_id, next_cash, timestamp)
        connection.execute("DELETE FROM trade_logs WHERE id = ?", (int(log_id),))
        connection.commit()


def _sqlite_record_daily_interest(account_id: int, *, interest_date: str, amount: float) -> None:
    if not _sqlite_get_account(account_id):
        raise ValueError("계좌를 찾을 수 없습니다.")
    sqlite_db.record_daily_interest(
        account_id,
        interest_date=interest_date,
        amount=amount,
    )


def _sqlite_replace_interest_history(
    account_id: int,
    *,
    target_date: str,
    desired_entries: list[tuple[str, float]],
) -> None:
    """SQLite 계좌의 자동 일별 이자 이력을 목표 일정으로 다시 만든다."""

    account = _sqlite_get_account(account_id)
    if not account:
        raise ValueError("계좌를 찾을 수 없습니다.")

    target_date_value = date.fromisoformat(target_date)
    trade_logs = sqlite_db.list_trade_logs(account_id)
    interest_rows = sqlite_db.list_daily_interest(account_id)
    removed_interest_total = _existing_interest_total_to_remove(
        trade_logs,
        interest_rows,
        target_date=target_date_value,
    )
    next_cash = round(float(account.get("cash_balance") or 0) - removed_interest_total, 4)

    timestamp = sqlite_db.now_iso()
    with sqlite_db.connect() as connection:
        sqlite_db._require_account(connection, account_id)
        connection.execute(
            """
            DELETE FROM daily_interest
            WHERE account_id = ?
              AND date <= ?
            """,
            (account_id, target_date),
        )
        connection.execute(
            """
            DELETE FROM trade_logs
            WHERE account_id = ?
              AND trade_type = 'interest'
              AND trade_date <= ?
              AND (
                    TRIM(COALESCE(notes, '')) = ?
                 OR TRIM(COALESCE(product_name, '')) = ?
              )
            """,
            (account_id, target_date, AUTO_DAILY_INTEREST_NOTE, _cash_event_label("interest")),
        )
        for interest_date, amount in desired_entries:
            interest_amount = float(amount or 0)
            connection.execute(
                """
                INSERT INTO daily_interest (account_id, date, interest_amount, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (account_id, interest_date, interest_amount, timestamp),
            )
            sqlite_db._insert_trade_log(
                connection,
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
                notes=AUTO_DAILY_INTEREST_NOTE,
                created_at=timestamp,
                metadata_json=sqlite_db._metadata_json(),
            )
            next_cash += interest_amount

        sqlite_db._update_account_cash_balance(connection, account_id, round(next_cash, 4), timestamp)
        connection.commit()


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
    backend_name = _current_backend()
    return _cached_list_accounts(
        _data_cache_scope_key(backend_name),
        backend_name,
        _current_data_refresh_token(),
    )


def get_account(account_id: int) -> dict[str, Any] | None:
    backend_name = _current_backend()
    return _cached_get_account(
        _data_cache_scope_key(backend_name),
        backend_name,
        int(account_id),
        _current_data_refresh_token(),
    )


def create_account(name: str, account_type: str = "retirement", opening_cash: float = 0) -> int:
    account_id = _run_with_fallback(
        supabase_call=lambda: _supabase_create_account(name, account_type, opening_cash),
        sqlite_call=lambda: _sqlite_create_account(name, account_type, opening_cash),
    )
    mark_data_dirty()
    return int(account_id)


def delete_account(account_id: int) -> None:
    """현재 저장소에서 계좌와 연관 데이터를 삭제한다."""

    _run_with_fallback(
        supabase_call=lambda: _supabase_delete_account(account_id),
        sqlite_call=lambda: _sqlite_delete_account(account_id),
    )
    mark_data_dirty()


def update_cash_balance(account_id: int, amount: float) -> None:
    _run_with_fallback(
        supabase_call=lambda: _supabase_update_cash_balance(account_id, amount),
        sqlite_call=lambda: _sqlite_update_cash_balance(account_id, amount),
    )
    mark_data_dirty()


def list_holdings(account_id: int, include_closed: bool = False) -> list[dict[str, Any]]:
    backend_name = _current_backend()
    return _cached_list_holdings(
        _data_cache_scope_key(backend_name),
        backend_name,
        int(account_id),
        bool(include_closed),
        _current_data_refresh_token(),
    )


def set_holding_price(holding_id: int, current_price: float, as_of: str | None = None) -> None:
    _run_with_fallback(
        supabase_call=lambda: _supabase_set_holding_price(holding_id, current_price, as_of),
        sqlite_call=lambda: _sqlite_set_holding_price(holding_id, current_price, as_of),
    )
    mark_data_dirty()


def record_realtime_price_tick(
    *,
    account_id: int,
    holding_id: int | None,
    symbol: str,
    price: float,
    previous_close: float | None = None,
    day_change_rate: float | None = None,
    currency: str = "KRW",
    quote_time: str | None = None,
    source: str = "KIS WebSocket",
    metadata_json: dict[str, Any] | None = None,
) -> None:
    """최신가 overwrite와 실시간 tick 적재를 동시에 처리한다."""

    _run_with_fallback(
        supabase_call=lambda: _supabase_record_realtime_price_tick(
            account_id=account_id,
            holding_id=holding_id,
            symbol=symbol,
            price=price,
            previous_close=previous_close,
            day_change_rate=day_change_rate,
            currency=currency,
            quote_time=quote_time,
            source=source,
            metadata_json=metadata_json,
        ),
        sqlite_call=lambda: _sqlite_record_realtime_price_tick(
            account_id=account_id,
            holding_id=holding_id,
            symbol=symbol,
            price=price,
            previous_close=previous_close,
            day_change_rate=day_change_rate,
            currency=currency,
            quote_time=quote_time,
            source=source,
            metadata_json=metadata_json,
        ),
    )
    mark_data_dirty()


def list_realtime_price_ticks(account_id: int, *, limit: int = 200) -> list[dict[str, Any]]:
    """계좌의 실시간 quote 이력을 최신순으로 반환한다."""

    if _current_backend() == BACKEND_SQLITE:
        return _sqlite_list_realtime_price_ticks(account_id, limit=limit)

    try:
        return _supabase_list_realtime_price_ticks(account_id, limit=limit)
    except Exception as exc:
        if _should_fallback(exc):
            return []
        raise


def upsert_realtime_worker_status(
    *,
    account_id: int,
    worker_name: str,
    connection_state: str,
    last_seen_at: str | None = None,
    last_quote_at: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> None:
    """계좌별 실시간 worker 연결 상태를 저장한다."""

    _run_with_fallback(
        supabase_call=lambda: _supabase_upsert_realtime_worker_status(
            account_id=account_id,
            worker_name=worker_name,
            connection_state=connection_state,
            last_seen_at=last_seen_at,
            last_quote_at=last_quote_at,
            metadata_json=metadata_json,
        ),
        sqlite_call=lambda: _sqlite_upsert_realtime_worker_status(
            account_id=account_id,
            worker_name=worker_name,
            connection_state=connection_state,
            last_seen_at=last_seen_at,
            last_quote_at=last_quote_at,
            metadata_json=metadata_json,
        ),
    )
    mark_data_dirty()


def get_realtime_worker_status(account_id: int) -> dict[str, Any] | None:
    """계좌별 실시간 worker 상태를 반환한다."""

    if _current_backend() == BACKEND_SQLITE:
        return _sqlite_get_realtime_worker_status(account_id)

    try:
        return _supabase_get_realtime_worker_status(account_id)
    except Exception as exc:
        if _should_fallback(exc):
            return None
        raise


def latest_realtime_quote_time(account_id: int) -> str:
    """계좌별 가장 최근 quote 반영 시각을 반환한다."""

    if _current_backend() == BACKEND_SQLITE:
        return _sqlite_latest_realtime_quote_time(account_id)

    try:
        return _supabase_latest_realtime_quote_time(account_id)
    except Exception as exc:
        if _should_fallback(exc):
            return ""
        raise


def list_trade_logs(account_id: int) -> list[dict[str, Any]]:
    backend_name = _current_backend()
    return _cached_list_trade_logs(
        _data_cache_scope_key(backend_name),
        backend_name,
        int(account_id),
        _current_data_refresh_token(),
    )


def list_daily_interest(account_id: int) -> list[dict[str, Any]]:
    """기존 저장소에 남아 있는 일별 이자 기록을 조회한다."""

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

    backend_name = _current_backend()
    return _cached_list_account_snapshots(
        _data_cache_scope_key(backend_name),
        backend_name,
        int(account_id),
        str(start_date).strip() if start_date not in (None, "") else None,
        _current_data_refresh_token(),
    )


def list_valuation_snapshots(
    account_id: int,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """계좌의 입금 기준 일별 평가 스냅샷을 조회한다."""

    backend_name = _current_backend()
    return _cached_list_valuation_snapshots(
        _data_cache_scope_key(backend_name),
        backend_name,
        int(account_id),
        str(start_date).strip() if start_date not in (None, "") else None,
        str(end_date).strip() if end_date not in (None, "") else None,
        _current_data_refresh_token(),
    )


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
    mark_data_dirty()


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
    mark_data_dirty()


def update_trade_log(
    account_id: int,
    log_id: int,
    *,
    trade_type: str,
    trade_date: str,
    notes: str = "",
    symbol: str = "",
    product_name: str = "",
    asset_type: str = "risk",
    quantity: float = 0.0,
    price: float = 0.0,
    amount: float = 0.0,
) -> None:
    """거래 기록 1건을 수정하고 필요한 보유 종목/현금 상태를 다시 맞춘다."""

    _run_with_fallback(
        supabase_call=lambda: _supabase_update_trade_log(
            account_id,
            log_id,
            trade_type=trade_type,
            trade_date=trade_date,
            notes=notes,
            symbol=symbol,
            product_name=product_name,
            asset_type=asset_type,
            quantity=quantity,
            price=price,
            amount=amount,
        ),
        sqlite_call=lambda: _sqlite_update_trade_log(
            account_id,
            log_id,
            trade_type=trade_type,
            trade_date=trade_date,
            notes=notes,
            symbol=symbol,
            product_name=product_name,
            asset_type=asset_type,
            quantity=quantity,
            price=price,
            amount=amount,
        ),
    )
    mark_data_dirty()


def _delete_trade_log_original(account_id: int, log_id: int) -> None:
    """거래 기록 1건을 삭제하고 필요한 보유 종목/현금 상태를 다시 맞춘다."""

    _run_with_fallback(
        supabase_call=lambda: _supabase_delete_trade_log(account_id, log_id),
        sqlite_call=lambda: _sqlite_delete_trade_log(account_id, log_id),
    )


def delete_trade_log(*args: Any, **kwargs: Any) -> None:
    """거래기록 삭제 후 데이터 캐시를 무효화한다."""

    result = _delete_trade_log_original(*args, **kwargs)
    _invalidate_data_cache_after_write()
    return result


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
    mark_data_dirty()


def record_daily_interest(account_id: int, *, interest_date: str, amount: float) -> None:
    """이자 기능 제거 이후 호출을 차단한다."""

    raise RuntimeError("현금 이자 적립 기능은 제거되었습니다.")


def _replace_interest_history(
    account_id: int,
    *,
    target_date: str,
    desired_entries: list[tuple[str, float]],
) -> None:
    """현재 저장소에서 자동 일별 이자 이력을 목표 일정으로 재구성한다."""

    _run_with_fallback(
        supabase_call=lambda: _supabase_replace_interest_history(
            account_id,
            target_date=target_date,
            desired_entries=desired_entries,
        ),
        sqlite_call=lambda: _sqlite_replace_interest_history(
            account_id,
            target_date=target_date,
            desired_entries=desired_entries,
        ),
    )


def _sync_legacy_interest_history_for_buy(account_id: int, *, trade_type: str) -> None:
    """기존 이자 원장을 쓰던 계좌는 매수 전에 현재 기준 이자 이력을 재동기화한다."""

    normalized_trade_type = str(trade_type or "").strip().lower()
    if normalized_trade_type != "buy":
        return

    account = get_account(account_id)
    if not account:
        return

    trade_logs = list_trade_logs(account_id)
    interest_rows = list_daily_interest(account_id)
    has_legacy_interest_state = bool(interest_rows) or any(_is_auto_daily_interest_trade(log) for log in trade_logs)
    if not has_legacy_interest_state:
        return

    target_date = _rollup_today()
    desired_entries = _build_interest_schedule(
        account,
        trade_logs,
        interest_rows,
        target_date=target_date,
        annual_rate=DEFAULT_ANNUAL_INTEREST_RATE,
    )
    diff = _interest_sync_diff(
        desired_entries,
        trade_logs,
        interest_rows,
        target_date=target_date,
    )
    if not (diff["added_dates"] or diff["requires_rebuild"] or abs(float(diff["net_amount_delta"] or 0)) > 0.000001):
        return

    _replace_interest_history(
        account_id,
        target_date=target_date.isoformat(),
        desired_entries=desired_entries,
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
    mark_data_dirty()


def record_valuation_snapshots(account_id: int, snapshots: list[dict[str, Any]]) -> None:
    """계좌의 입금 기준 일별 평가 스냅샷을 저장한다."""

    _run_with_fallback(
        supabase_call=lambda: _supabase_record_valuation_snapshots(account_id, snapshots),
        sqlite_call=lambda: sqlite_db.record_valuation_snapshots(account_id, snapshots),
    )
    mark_data_dirty()


def delete_valuation_snapshots(account_id: int, start_date: str | None = None) -> None:
    """계좌의 입금 기준 평가 스냅샷을 전체 또는 시작일 이후로 삭제한다."""

    _run_with_fallback(
        supabase_call=lambda: _supabase_delete_valuation_snapshots(account_id, start_date=start_date),
        sqlite_call=lambda: sqlite_db.delete_valuation_snapshots(account_id, start_date=start_date),
    )
    mark_data_dirty()


def current_backend_name() -> str:
    """현재 선택된 저장소 이름을 반환한다."""

    return _current_backend()


def sync_account_rollup(
    account_id: int,
    *,
    annual_rate: float = DEFAULT_ANNUAL_INTEREST_RATE,
    today_date: str | None = None,
    timezone_name: str = DEFAULT_ROLLUP_TIMEZONE,
) -> dict[str, Any]:
    """자동 이자 적립 없이 오늘 스냅샷만 최신 값으로 맞춘다."""

    account = get_account(account_id)
    if not account:
        raise ValueError("계좌를 찾을 수 없습니다.")

    today = date.fromisoformat(today_date) if today_date else _rollup_today(timezone_name)
    trade_logs = list_trade_logs(account_id)
    interest_rows = list_daily_interest(account_id)
    snapshot_rows = list_account_snapshots(account_id)
    historical_snapshots_updated = 0

    historical_target_date = today - timedelta(days=1)
    historical_snapshot_dates = sorted(
        {
            str(row.get("snapshot_date") or "").strip()
            for row in snapshot_rows
            if _parse_iso_date(row.get("snapshot_date")) is not None
            and date.fromisoformat(str(row.get("snapshot_date"))) <= historical_target_date
        }
    )
    if historical_snapshot_dates:
        historical_snapshots_updated = _sync_historical_snapshots(
            account_id,
            account=account,
            trade_logs=trade_logs,
            interest_rows=interest_rows,
            snapshot_rows=snapshot_rows,
            start_date=date.fromisoformat(historical_snapshot_dates[0]),
            target_date=historical_target_date,
        )

    cash_balance, market_value, total_cost = _demo_account_totals(account_id)
    total_value = cash_balance + market_value
    snapshot_date = today.isoformat()
    existing_snapshots = [
        row
        for row in snapshot_rows
        if str(row.get("snapshot_date") or "").strip() >= snapshot_date
    ]
    existing_snapshot = next(
        (
            row
            for row in existing_snapshots
            if str(row.get("snapshot_date") or "").strip() == snapshot_date
        ),
        None,
    )
    snapshot_updated = not (
        existing_snapshot
        and _snapshot_matches_current(
            existing_snapshot,
            cash_balance=cash_balance,
            market_value=market_value,
            total_value=total_value,
            total_cost=total_cost,
        )
    )
    if snapshot_updated:
        record_account_snapshot(
            account_id,
            snapshot_date=snapshot_date,
            cash_balance=cash_balance,
            market_value=market_value,
            total_value=total_value,
            total_cost=total_cost,
        )

    valuation_snapshot_count = 0
    valuation_error = ""
    try:
        from src.valuation import (
            build_price_lookup_for_trade_logs,
            first_principal_deposit_date,
            rebuild_and_save_daily_valuation_snapshots,
        )

        price_lookup = build_price_lookup_for_trade_logs(
            trade_logs,
            start_date=first_principal_deposit_date(trade_logs),
            end_date=today,
        )
        valuation_snapshots = rebuild_and_save_daily_valuation_snapshots(
            account=account,
            trade_logs=trade_logs,
            price_lookup=price_lookup,
            account_snapshots=snapshot_rows,
            end_date=today,
            today_date=today,
            calculation_reason="daily_rollup",
        )
        valuation_snapshot_count = len(valuation_snapshots)
    except Exception as exc:  # noqa: BLE001
        valuation_snapshot_count = 0
        valuation_error = str(exc)

    return {
        "interest_rows_added": 0,
        "interest_rows_updated": 0,
        "interest_rows_removed": 0,
        "historical_snapshots_updated": historical_snapshots_updated,
        "interest_amount_added": 0.0,
        "snapshot_date": snapshot_date,
        "snapshot_updated": snapshot_updated,
        "valuation_snapshot_count": valuation_snapshot_count,
        "valuation_error": valuation_error,
    }


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
    mark_data_dirty()

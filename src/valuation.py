from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from .trade_log_filters import (
    filter_scaled_duplicate_trade_logs,
    is_fund_symbol,
    normalize_trade_symbol,
    normalized_trade_amount,
)


COMPANY_DEPOSIT_TYPE = "employer_deposit"
PRINCIPAL_DEPOSIT_TYPES = {"employer_deposit", "personal_deposit", "deposit", "opening_cash"}
PRINCIPAL_WITHDRAW_TYPES = {"withdraw"}
BUY_SELL_TYPES = {"buy", "sell"}
CASH_DELTA_IN_TYPES = PRINCIPAL_DEPOSIT_TYPES | {"interest", "transfer_in", "dividend", "dividend_income"}
CASH_DELTA_OUT_TYPES = {"withdraw", "transfer_out", "fee", "commission", "tax"}


@dataclass
class Lot:
    """FIFO 잔여 보유 수량과 매입원가를 추적한다."""

    symbol: str
    product_name: str
    quantity: float
    cost: float

    @property
    def unit_cost(self) -> float:
        """잔여 수량 기준 평균 매입가를 반환한다."""

        if self.quantity <= 0:
            return 0.0
        return self.cost / self.quantity


def parse_iso_date(value: Any) -> date | None:
    """YYYY-MM-DD 또는 ISO datetime 문자열을 date로 변환한다."""

    text = str(value or "").strip()
    if not text:
        return None

    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def date_range(start_date: date, end_date: date):
    """시작일부터 종료일까지 날짜를 순회한다."""

    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def safe_float(value: Any, default: float = 0.0) -> float:
    """숫자 변환 실패 시 기본값을 반환한다."""

    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def round_won(value: Any) -> int:
    """금액을 원 단위로 일반 반올림한다."""

    try:
        if value in (None, ""):
            return 0
        return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, TypeError, ValueError):
        return 0


def normalize_symbol(value: Any) -> str:
    """심볼을 비교용으로 정규화한다."""

    return normalize_trade_symbol(value)


def trade_amount(log: dict[str, Any]) -> float:
    """거래 로그의 금액을 계산한다."""

    return normalized_trade_amount(log)


def trade_cash_delta(log: dict[str, Any]) -> float:
    """거래 로그가 현금 잔액에 미치는 영향을 반환한다."""

    raw_cash_delta = log.get("cash_delta")
    trade_type = str(log.get("trade_type") or "").strip().lower()
    amount = trade_amount(log)
    if raw_cash_delta not in (None, "") and trade_type not in BUY_SELL_TYPES:
        cash_delta = safe_float(raw_cash_delta)
        if abs(cash_delta) > 0.000001 or amount <= 0:
            return cash_delta

    if trade_type == "buy":
        return -amount
    if trade_type == "sell":
        return amount
    if trade_type in CASH_DELTA_IN_TYPES:
        return amount
    if trade_type in CASH_DELTA_OUT_TYPES:
        return -amount
    return 0.0


def principal_withdraw_amount(log: dict[str, Any]) -> float:
    """원금 차감용 출금액을 반환한다."""

    amount = trade_amount(log)
    if amount > 0:
        return amount
    return abs(trade_cash_delta(log))


def is_principal_deposit_log(log: dict[str, Any]) -> bool:
    """평가 원금에 포함할 입금성 거래인지 반환한다."""

    return str(log.get("trade_type") or "").strip().lower() in PRINCIPAL_DEPOSIT_TYPES


def first_principal_deposit_date(trade_logs: list[dict[str, Any]]) -> date | None:
    """최초 입금성 거래일을 찾는다."""

    deposit_dates = [
        parsed_date
        for log in trade_logs
        if is_principal_deposit_log(log)
        for parsed_date in [parse_iso_date(log.get("trade_date"))]
        if parsed_date is not None
    ]
    return min(deposit_dates) if deposit_dates else None


def first_company_deposit_date(trade_logs: list[dict[str, Any]]) -> date | None:
    """이전 호출부 호환을 위해 최초 입금성 거래일을 반환한다."""

    return first_principal_deposit_date(trade_logs)


def _canonical_price_lookup(price_lookup: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    """해시 입력용 가격 lookup을 안정적인 형태로 정규화한다."""

    canonical: dict[str, dict[str, float]] = {}
    for symbol, series in sorted((price_lookup or {}).items(), key=lambda item: normalize_symbol(item[0])):
        symbol_key = normalize_symbol(symbol)
        canonical[symbol_key] = {
            str(raw_date): round(safe_float(raw_price), 6)
            for raw_date, raw_price in sorted((series or {}).items(), key=lambda item: str(item[0]))
        }
    return canonical


def source_hash_for_inputs(
    *,
    account: dict[str, Any],
    trade_logs: list[dict[str, Any]],
    price_lookup: dict[str, dict[str, float]],
    end_date: date,
    today_date: date,
    account_snapshots: list[dict[str, Any]] | None = None,
) -> str:
    """재계산 기준 입력값 해시를 생성한다."""

    source_rows = [
        {
            "id": log.get("id"),
            "trade_date": str(log.get("trade_date") or ""),
            "created_at": str(log.get("created_at") or ""),
            "trade_type": str(log.get("trade_type") or ""),
            "symbol": str(log.get("symbol") or ""),
            "product_name": str(log.get("product_name") or ""),
            "quantity": safe_float(log.get("quantity")),
            "price": safe_float(log.get("price")),
            "total_amount": safe_float(log.get("total_amount")),
            "cash_delta": trade_cash_delta(log),
        }
        for log in sorted(
            trade_logs,
            key=lambda row: (
                str(row.get("trade_date") or ""),
                str(row.get("created_at") or ""),
                int(row.get("id") or 0),
            ),
        )
    ]
    snapshot_rows = [
        {
            "snapshot_date": str(row.get("snapshot_date") or ""),
            "cash_balance": safe_float(row.get("cash_balance")),
            "market_value": safe_float(row.get("market_value")),
            "total_value": safe_float(row.get("total_value")),
            "total_cost": safe_float(row.get("total_cost")),
        }
        for row in sorted(
            account_snapshots or [],
            key=lambda row: (
                str(row.get("snapshot_date") or ""),
                int(row.get("id") or 0),
            ),
        )
    ]

    payload = {
        "account_id": account.get("id"),
        "cash_balance": safe_float(account.get("cash_balance")),
        "end_date": end_date.isoformat(),
        "today_date": today_date.isoformat(),
        "trade_logs": source_rows,
        "account_snapshots": snapshot_rows,
        "price_lookup": _canonical_price_lookup(price_lookup),
    }
    payload_text = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload_text.encode("utf-8")).hexdigest()


def price_at_date(
    symbol: str,
    target_date: date,
    price_lookup: dict[str, dict[str, float]],
    *,
    fallback_price: float,
) -> tuple[float, bool]:
    """target_date 기준 가격과 매입가 fallback 사용 여부를 반환한다."""

    symbol_key = normalize_symbol(symbol)
    series = price_lookup.get(symbol_key) or {}
    if not series:
        return fallback_price, True

    target_key = target_date.isoformat()
    if target_key in series:
        return safe_float(series[target_key], fallback_price), False

    previous_candidates: list[tuple[date, float]] = []
    for raw_date, raw_price in series.items():
        parsed_date = parse_iso_date(raw_date)
        if parsed_date is None or parsed_date > target_date:
            continue
        previous_candidates.append((parsed_date, safe_float(raw_price, fallback_price)))

    if not previous_candidates:
        return fallback_price, True

    previous_candidates.sort(key=lambda item: item[0])
    return previous_candidates[-1][1], False


def apply_buy(lots_by_symbol: dict[str, list[Lot]], log: dict[str, Any]) -> None:
    """매수 로그를 FIFO lot에 추가한다."""

    symbol = normalize_symbol(log.get("symbol"))
    if not symbol:
        return

    quantity = safe_float(log.get("quantity"))
    amount = trade_amount(log)
    if quantity <= 0 or amount <= 0:
        return

    lots_by_symbol.setdefault(symbol, []).append(
        Lot(
            symbol=symbol,
            product_name=str(log.get("product_name") or symbol),
            quantity=quantity,
            cost=amount,
        )
    )


def apply_sell(lots_by_symbol: dict[str, list[Lot]], log: dict[str, Any]) -> float:
    """매도 로그를 FIFO 기준으로 잔여 lot에서 차감하고 실제 매칭 수량을 반환한다."""

    symbol = normalize_symbol(log.get("symbol"))
    if not symbol:
        return 0.0

    remaining_quantity = safe_float(log.get("quantity"))
    if remaining_quantity <= 0:
        return 0.0

    updated_lots: list[Lot] = []
    matched_total = 0.0
    for lot in lots_by_symbol.get(symbol) or []:
        if remaining_quantity <= 0:
            updated_lots.append(lot)
            continue
        if lot.quantity <= 0:
            continue

        matched_quantity = min(lot.quantity, remaining_quantity)
        ratio = matched_quantity / lot.quantity
        lot.quantity -= matched_quantity
        lot.cost -= lot.cost * ratio
        remaining_quantity -= matched_quantity
        matched_total += matched_quantity

        if lot.quantity > 0.000001:
            updated_lots.append(lot)

    lots_by_symbol[symbol] = updated_lots
    return matched_total


def account_snapshot_cash_by_date(account_snapshots: list[dict[str, Any]] | None) -> dict[date, float]:
    """일별 계좌 스냅샷에 저장된 실제 현금을 날짜별로 반환한다."""

    cash_by_date: dict[date, float] = {}
    for snapshot in account_snapshots or []:
        snapshot_date = parse_iso_date(snapshot.get("snapshot_date"))
        if snapshot_date is None:
            continue
        cash_by_date[snapshot_date] = safe_float(snapshot.get("cash_balance"))
    return cash_by_date


def current_invested_cost(lots_by_symbol: dict[str, list[Lot]]) -> float:
    """현재 잔여 보유상품 매입원가를 반환한다."""

    return sum(max(lot.cost, 0.0) for lots in lots_by_symbol.values() for lot in lots)


def current_holdings_market_value(
    lots_by_symbol: dict[str, list[Lot]],
    target_date: date,
    price_lookup: dict[str, dict[str, float]],
) -> tuple[float, list[str]]:
    """현재 잔여 보유상품의 날짜별 평가액을 계산한다."""

    market_value = 0.0
    missing_price_symbols: set[str] = set()

    for symbol, lots in lots_by_symbol.items():
        for lot in lots:
            if lot.quantity <= 0:
                continue

            fallback_price = lot.unit_cost * 1000 if is_fund_symbol(symbol) else lot.unit_cost
            price, used_fallback = price_at_date(
                symbol,
                target_date,
                price_lookup,
                fallback_price=fallback_price,
            )
            unit_divisor = 1000 if is_fund_symbol(symbol) else 1
            market_value += lot.quantity * price / unit_divisor
            if used_fallback:
                missing_price_symbols.add(symbol)

    return market_value, sorted(missing_price_symbols)


def build_company_principal_valuation_snapshots(
    *,
    account: dict[str, Any],
    trade_logs: list[dict[str, Any]],
    price_lookup: dict[str, dict[str, float]],
    account_snapshots: list[dict[str, Any]] | None = None,
    end_date: date | None = None,
    today_date: date | None = None,
    output_start_date: date | None = None,
    calculation_reason: str = "auto",
) -> list[dict[str, Any]]:
    """입금액 기준 일별 평가 스냅샷을 생성한다."""

    effective_trade_logs = filter_scaled_duplicate_trade_logs(trade_logs)
    start_date = first_principal_deposit_date(effective_trade_logs)
    if start_date is None:
        return []

    normalized_today = today_date or date.today()
    target_end_date = end_date or normalized_today
    if target_end_date < start_date:
        return []

    normalized_output_start_date = output_start_date or start_date
    if normalized_output_start_date < start_date:
        normalized_output_start_date = start_date
    if normalized_output_start_date > target_end_date:
        return []

    ordered_logs = sorted(
        [
            log
            for log in effective_trade_logs
            if start_date <= (parse_iso_date(log.get("trade_date")) or date.min) <= target_end_date
        ],
        key=lambda row: (
            str(row.get("trade_date") or ""),
            str(row.get("created_at") or ""),
            int(row.get("id") or 0),
        ),
    )

    logs_by_date: dict[date, list[dict[str, Any]]] = {}
    for log in ordered_logs:
        trade_date = parse_iso_date(log.get("trade_date"))
        if trade_date is None:
            continue
        logs_by_date.setdefault(trade_date, []).append(log)

    source_hash = source_hash_for_inputs(
        account=account,
        trade_logs=ordered_logs,
        price_lookup=price_lookup,
        end_date=target_end_date,
        today_date=normalized_today,
        account_snapshots=account_snapshots,
    )
    lots_by_symbol: dict[str, list[Lot]] = {}
    company_principal = 0.0
    ledger_cash = 0.0
    snapshot_cash_by_date = account_snapshot_cash_by_date(account_snapshots)
    snapshots: list[dict[str, Any]] = []

    for valuation_date in date_range(start_date, target_end_date):
        for log in logs_by_date.get(valuation_date, []):
            trade_type = str(log.get("trade_type") or "").strip().lower()

            if trade_type in PRINCIPAL_DEPOSIT_TYPES:
                ledger_cash += trade_cash_delta(log)
                company_principal += trade_amount(log)
            elif trade_type in PRINCIPAL_WITHDRAW_TYPES:
                ledger_cash += trade_cash_delta(log)
                company_principal = max(company_principal - principal_withdraw_amount(log), 0.0)
            elif trade_type == "buy":
                ledger_cash += trade_cash_delta(log)
                apply_buy(lots_by_symbol, log)
            elif trade_type == "sell":
                sell_quantity = safe_float(log.get("quantity"))
                matched_quantity = apply_sell(lots_by_symbol, log)
                matched_ratio = min(matched_quantity / sell_quantity, 1.0) if sell_quantity > 0 else 0.0
                ledger_cash += trade_cash_delta(log) * matched_ratio
            else:
                ledger_cash += trade_cash_delta(log)

        if company_principal <= 0 or valuation_date < normalized_output_start_date:
            continue

        invested_cost = current_invested_cost(lots_by_symbol)
        holdings_market_value, missing_price_symbols = current_holdings_market_value(
            lots_by_symbol,
            valuation_date,
            price_lookup,
        )
        implied_cash = max(ledger_cash, 0.0)
        over_invested_amount = max(-ledger_cash, 0.0)

        if valuation_date == normalized_today:
            cash_value = safe_float(account.get("cash_balance"))
            actual_cash_balance: float | None = cash_value
            cash_source = "actual"
        elif valuation_date in snapshot_cash_by_date:
            cash_value = snapshot_cash_by_date[valuation_date]
            actual_cash_balance = cash_value
            cash_source = "actual"
        else:
            cash_value = implied_cash
            actual_cash_balance = None
            cash_source = "implied"

        rounded_company_principal = round_won(company_principal)
        rounded_invested_cost = round_won(invested_cost)
        rounded_implied_cash = round_won(implied_cash)
        rounded_actual_cash_balance = round_won(actual_cash_balance) if actual_cash_balance is not None else None
        rounded_cash_value = round_won(cash_value)
        rounded_holdings_market_value = round_won(holdings_market_value)
        rounded_valuation_amount = rounded_holdings_market_value + rounded_cash_value
        rounded_profit_loss = rounded_valuation_amount - rounded_company_principal
        rounded_over_invested_amount = round_won(over_invested_amount)
        profit_rate = (
            rounded_profit_loss / rounded_company_principal * 100
            if rounded_company_principal
            else 0.0
        )

        snapshots.append(
            {
                "account_id": int(account["id"]),
                "valuation_date": valuation_date.isoformat(),
                "company_principal": rounded_company_principal,
                "invested_cost": rounded_invested_cost,
                "implied_cash": rounded_implied_cash,
                "actual_cash_balance": rounded_actual_cash_balance,
                "cash_value": rounded_cash_value,
                "cash_source": cash_source,
                "holdings_market_value": rounded_holdings_market_value,
                "valuation_amount": rounded_valuation_amount,
                "profit_loss": rounded_profit_loss,
                "profit_rate": round(profit_rate, 4),
                "over_invested_amount": rounded_over_invested_amount,
                "missing_price_symbols": missing_price_symbols,
                "source_hash": source_hash,
                "calculation_reason": calculation_reason,
            }
        )

    return snapshots


def build_price_lookup_for_trade_logs(
    trade_logs: list[dict[str, Any]],
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, dict[str, float]]:
    """거래 로그에 포함된 종목들의 가격 히스토리를 조회해 lookup으로 만든다."""

    from src.market import fetch_price_history_range, normalize_symbol as market_normalize_symbol

    range_start = start_date or first_principal_deposit_date(trade_logs)
    range_end = end_date or date.today()
    symbols = sorted(
        {
            normalize_symbol(log.get("symbol"))
            for log in trade_logs
            if str(log.get("trade_type") or "").strip().lower() in BUY_SELL_TYPES
            and normalize_symbol(log.get("symbol"))
        }
    )
    if range_start is None or not symbols:
        return {symbol: {} for symbol in symbols}

    price_lookup: dict[str, dict[str, float]] = {}
    for raw_symbol in symbols:
        fetched_symbol = str(market_normalize_symbol(raw_symbol) or raw_symbol).strip().upper()
        try:
            history = fetch_price_history_range(fetched_symbol, start_date=range_start, end_date=range_end)
        except Exception:
            history = None

        symbol_prices: dict[str, float] = {}
        if history is not None and not history.empty:
            for row in history.to_dict("records"):
                parsed_date = parse_iso_date(row.get("date") or row.get("datetime") or row.get("Date"))
                if parsed_date is None:
                    continue
                close_price = row.get("close") or row.get("Close") or row.get("price") or row.get("current_price")
                symbol_prices[parsed_date.isoformat()] = safe_float(close_price)

        price_lookup[raw_symbol] = symbol_prices
        price_lookup[normalize_symbol(fetched_symbol)] = symbol_prices

    return price_lookup


def rebuild_daily_valuation_snapshots(
    *,
    account: dict[str, Any],
    trade_logs: list[dict[str, Any]],
    price_lookup: dict[str, dict[str, float]],
    account_snapshots: list[dict[str, Any]] | None = None,
    end_date: date | None = None,
    today_date: date | None = None,
    output_start_date: date | None = None,
    calculation_reason: str,
) -> list[dict[str, Any]]:
    """계좌의 입금 기준 평가액 기록을 전체 또는 출력 시작일 이후로 재계산한다."""

    return build_company_principal_valuation_snapshots(
        account=account,
        trade_logs=trade_logs,
        price_lookup=price_lookup,
        account_snapshots=account_snapshots,
        end_date=end_date,
        today_date=today_date,
        output_start_date=output_start_date,
        calculation_reason=calculation_reason,
    )


def rebuild_and_save_daily_valuation_snapshots(
    *,
    account: dict[str, Any],
    trade_logs: list[dict[str, Any]],
    price_lookup: dict[str, dict[str, float]],
    account_snapshots: list[dict[str, Any]] | None = None,
    end_date: date | None = None,
    today_date: date | None = None,
    output_start_date: date | None = None,
    calculation_reason: str,
) -> list[dict[str, Any]]:
    """평가액 기록을 재계산하고 DB에 저장한다."""

    from src.db import delete_valuation_snapshots, record_valuation_snapshots

    account_id = int(account["id"])
    snapshots = rebuild_daily_valuation_snapshots(
        account=account,
        trade_logs=trade_logs,
        price_lookup=price_lookup,
        account_snapshots=account_snapshots,
        end_date=end_date,
        today_date=today_date,
        output_start_date=output_start_date,
        calculation_reason=calculation_reason,
    )

    delete_valuation_snapshots(account_id, start_date=output_start_date.isoformat() if output_start_date else None)
    if snapshots:
        record_valuation_snapshots(account_id, snapshots)
    return snapshots

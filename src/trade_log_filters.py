from __future__ import annotations

from collections import defaultdict
from typing import Any


def _safe_float(value: Any) -> float:
    """숫자 변환 실패 시 0을 반환한다."""

    try:
        if value in (None, ""):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _trade_amount(log: dict[str, Any]) -> float:
    """거래 총액을 반환한다."""

    total_amount = abs(_safe_float(log.get("total_amount")))
    if total_amount > 0:
        return total_amount
    return abs(_safe_float(log.get("quantity")) * _safe_float(log.get("price")))


def normalize_trade_symbol(value: Any) -> str:
    """국내 종목 접미사와 앞자리 0 차이를 제거한 비교용 심볼을 반환한다."""

    symbol = str(value or "").strip().upper()
    for suffix in (".KS", ".KQ"):
        if symbol.endswith(suffix):
            symbol = symbol[: -len(suffix)]
            break
    if symbol.isdigit():
        return symbol.zfill(6)
    return symbol


def is_fund_symbol(value: Any) -> bool:
    """좌 단위 기준가를 쓰는 펀드성 심볼인지 반환한다."""

    symbol = normalize_trade_symbol(value)
    return symbol.startswith("K") and any(character.isdigit() for character in symbol)


def is_fund_trade_log(log: dict[str, Any]) -> bool:
    """좌 단위 기준가를 쓰는 펀드성 거래인지 반환한다."""

    return is_fund_symbol(log.get("symbol"))


def normalized_trade_amount(log: dict[str, Any]) -> float:
    """펀드 좌수/기준가 단위 차이를 반영한 거래 총액을 반환한다."""

    total_amount = abs(_safe_float(log.get("total_amount")))
    quantity = abs(_safe_float(log.get("quantity")))
    price = abs(_safe_float(log.get("price")))
    if is_fund_trade_log(log) and quantity > 0 and price > 0:
        expected_amount = quantity * price / 1000.0
        if total_amount <= 0:
            return expected_amount
        if expected_amount > 0 and total_amount >= expected_amount * 100:
            return total_amount / 1000.0
        return total_amount

    if total_amount > 0:
        return total_amount
    return quantity * price


def normalized_trade_notional(symbol: Any, quantity: Any, price: Any) -> float:
    """심볼/수량/단가로 펀드 단위 차이를 반영한 예상 거래 총액을 계산한다."""

    share_count = abs(_safe_float(quantity))
    trade_price = abs(_safe_float(price))
    return normalized_trade_amount(
        {
            "symbol": symbol,
            "quantity": share_count,
            "price": trade_price,
            "total_amount": share_count * trade_price,
        }
    )


def _duplicate_key(log: dict[str, Any]) -> tuple[str, str, str, float, float] | None:
    """총액 스케일 중복 감지를 위한 거래 키를 만든다."""

    trade_type = str(log.get("trade_type") or "").strip().lower()
    if trade_type not in {"buy", "sell"}:
        return None

    trade_date = str(log.get("trade_date") or "").strip()
    symbol = normalize_trade_symbol(log.get("symbol"))
    if not symbol:
        symbol = str(log.get("product_name") or "").strip().casefold()
    quantity = _safe_float(log.get("quantity"))
    price = _safe_float(log.get("price"))
    if not trade_date or not symbol or quantity <= 0 or price <= 0:
        return None
    return (trade_date, trade_type, symbol, round(quantity, 8), round(price, 8))


def scaled_duplicate_trade_log_ids(trade_logs: list[dict[str, Any]]) -> set[int]:
    """같은 거래가 원 단위와 1,000배 단위로 중복 저장된 경우 큰 총액 행 id를 반환한다."""

    grouped_rows: dict[tuple[str, str, str, float, float], list[dict[str, Any]]] = defaultdict(list)
    for log in trade_logs:
        key = _duplicate_key(log)
        if key is not None:
            grouped_rows[key].append(log)

    ignored_ids: set[int] = set()
    for rows in grouped_rows.values():
        if len(rows) < 2:
            continue
        amounts = [amount for amount in (_trade_amount(row) for row in rows) if amount > 0]
        if not amounts:
            continue
        baseline = min(amounts)
        if baseline <= 0:
            continue
        for row in rows:
            amount = _trade_amount(row)
            if amount >= baseline * 100:
                try:
                    ignored_ids.add(int(row.get("id")))
                except (TypeError, ValueError):
                    continue
    return ignored_ids


def filter_scaled_duplicate_trade_logs(trade_logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """총액만 비정상적으로 큰 중복 매수/매도 행을 계산 입력에서 제외한다."""

    ignored_ids = scaled_duplicate_trade_log_ids(trade_logs)
    if not ignored_ids:
        return list(trade_logs)
    filtered_rows: list[dict[str, Any]] = []
    for log in trade_logs:
        try:
            log_id = int(log.get("id"))
        except (TypeError, ValueError):
            log_id = 0
        if log_id not in ignored_ids:
            filtered_rows.append(log)
    return filtered_rows

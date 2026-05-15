from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

import pandas as pd

from .market import fetch_price_history, resolve_kis_sector_label
from .trade_log_filters import (
    filter_scaled_duplicate_trade_logs,
    is_fund_symbol,
    normalize_trade_symbol,
    normalized_trade_amount,
)


CAPITAL_INFLOW_TYPES = {"personal_deposit", "employer_deposit"}
CAPITAL_OUTFLOW_TYPES = {"withdraw"}
TRANSFER_IN_TYPES = {"transfer_in"}
TRANSFER_OUT_TYPES = {"transfer_out"}
INTEREST_TYPES = {"interest"}
DEFAULT_ANNUAL_INTEREST_RATE = 0.05
LEGACY_EMPLOYER_DEPOSIT_NAMES = {"회사 현금입금", "회사 납입금"}
SECTOR_KEYWORD_RULES = (
    ("미국테크", ("미국테크", "BIG TECH", "BIGTECH", "QQQ", "AI반도체", "AI 반도체")),
    ("미국지수", ("S&P500", "S&P 500", "나스닥100", "NASDAQ100", "NASDAQ 100", "미국S&P", "미국나스닥")),
    ("반도체/전자", ("반도체", "하이닉스", "삼성전자", "DB하이텍", "전자")),
    ("플랫폼/인터넷", ("NAVER", "카카오", "인터넷", "플랫폼")),
    ("원자력/에너지", ("원자력", "에너지", "태양광", "2차전지", "배터리")),
    ("채권", ("국고채", "채권", "BOND", "회사채")),
    ("금/원자재", ("금현물", "금 ", "GOLD", "원자재", "은", "구리")),
    ("배당/리츠", ("고배당", "배당", "리츠", "REIT", "부동산", "인프라")),
    ("자동차", ("현대차", "기아", "모비스", "자동차")),
    ("바이오/헬스케어", ("바이오", "제약", "헬스", "의료", "셀트리온")),
    ("방산/산업재", ("한화에어로", "방산", "우주", "항공", "두산", "산업재")),
)


def _trade_match_key(log: dict[str, Any]) -> str:
    symbol = normalize_trade_symbol(log.get("symbol"))
    if symbol:
        return f"symbol:{symbol}"

    product_name = str(log.get("product_name") or "").strip().casefold()
    if product_name:
        return f"name:{product_name}"

    return ""


def holdings_frame(holdings: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(holdings)
    if frame.empty:
        return frame
    symbols = frame["symbol"] if "symbol" in frame.columns else pd.Series([""] * len(frame), index=frame.index)
    unit_divisors = symbols.map(lambda value: 1000.0 if is_fund_symbol(value) else 1.0)
    quantities = pd.to_numeric(frame["quantity"], errors="coerce").fillna(0.0)
    avg_costs = pd.to_numeric(frame["avg_cost"], errors="coerce").fillna(0.0)
    current_prices = pd.to_numeric(frame["current_price"], errors="coerce").fillna(0.0)
    frame["cost_basis"] = quantities * avg_costs / unit_divisors
    frame["current_value"] = quantities * current_prices / unit_divisors
    frame["profit_loss"] = frame["current_value"] - frame["cost_basis"]
    frame["profit_rate"] = frame.apply(
        lambda row: (row["profit_loss"] / row["cost_basis"] * 100) if row["cost_basis"] else 0,
        axis=1,
    )
    return frame.sort_values("current_value", ascending=False)


def holdings_overview_frame(
    holdings: list[dict[str, Any]],
    *,
    selected_symbol: str | None = None,
    limit: int = 10,
) -> pd.DataFrame:
    """상단 개요 차트에 표시할 보유 종목 프레임을 선택 상태와 함께 만든다."""

    frame = holdings_frame(holdings)
    if frame.empty:
        return frame

    selected_key = str(selected_symbol or "").strip().upper()
    working = frame.copy()
    working["selection_symbol"] = working["symbol"].astype(str).str.strip().str.upper()
    working = working.sort_values(["profit_rate", "current_value"], ascending=[False, False])

    if selected_key and selected_key in set(working["selection_symbol"]):
        selected_rows = working.loc[working["selection_symbol"] == selected_key].head(1)
        other_rows = working.loc[working["selection_symbol"] != selected_key]
        working = pd.concat([other_rows.head(max(limit - 1, 0)), selected_rows], ignore_index=True)
    else:
        working = working.head(limit).copy()

    working["is_selected"] = working["selection_symbol"] == selected_key
    return working


def infer_holding_sector_label(product_name: Any, symbol: Any, asset_type: Any) -> str:
    """보유 종목명과 자산군을 기반으로 표시용 섹터 라벨을 추론한다."""

    normalized_asset_type = str(asset_type or "").strip().lower()
    if normalized_asset_type == "cash":
        return "현금"

    kis_sector_label = resolve_kis_sector_label(symbol)
    if kis_sector_label:
        return kis_sector_label

    raw_name = str(product_name or symbol or "").strip()
    name_upper = raw_name.upper().replace("_", " ")
    if normalized_asset_type == "safe":
        if any(keyword in name_upper for keyword in ("국고채", "채권", "BOND", "회사채")):
            return "채권"
        if any(keyword in name_upper for keyword in ("금현물", "GOLD", "원자재", "은", "구리")):
            return "금/원자재"
        if any(keyword in name_upper for keyword in ("리츠", "REIT", "부동산", "인프라")):
            return "배당/리츠"

    for sector_label, keywords in SECTOR_KEYWORD_RULES:
        if any(keyword.upper() in name_upper for keyword in keywords):
            return sector_label

    if normalized_asset_type == "safe":
        return "안전자산"
    if normalized_asset_type == "risk":
        return "주식/ETF"
    return "기타"


def _amount_from_log(log: dict[str, Any]) -> float:
    total_amount = abs(float(log.get("total_amount") or 0))
    if total_amount > 0:
        return total_amount
    return abs(float(log.get("cash_delta") or 0))


def _normalized_trade_type(log: dict[str, Any]) -> str:
    """레거시 라벨을 반영해 거래 유형을 정규화한다."""

    trade_type = str(log.get("trade_type") or "").strip().lower()
    product_name = str(log.get("product_name") or "").strip()
    if trade_type == "personal_deposit" and product_name in LEGACY_EMPLOYER_DEPOSIT_NAMES:
        return "employer_deposit"
    return trade_type


def _cash_flow_summary(
    trade_logs: list[dict[str, Any]] | None = None,
    interest_rows: list[dict[str, Any]] | None = None,
) -> dict[str, float | bool]:
    ordered_logs = sorted(
        trade_logs or [],
        key=lambda row: (row.get("trade_date", ""), row.get("created_at", ""), row.get("id", 0)),
    )
    summary: dict[str, float | bool] = {
        "personal_deposit": 0.0,
        "employer_deposit": 0.0,
        "withdraw": 0.0,
        "transfer_in": 0.0,
        "transfer_out": 0.0,
        "cash_adjustment_in": 0.0,
        "cash_adjustment_out": 0.0,
        "total_interest": 0.0,
        "has_capital_events": False,
    }

    if interest_rows:
        summary["total_interest"] = sum(float(row.get("interest_amount") or 0) for row in interest_rows)

    for log in ordered_logs:
        trade_type = _normalized_trade_type(log)
        amount = _amount_from_log(log)
        if trade_type in CAPITAL_INFLOW_TYPES:
            summary[trade_type] += amount
            summary["has_capital_events"] = True
        elif trade_type in CAPITAL_OUTFLOW_TYPES:
            summary["withdraw"] += amount
            summary["has_capital_events"] = True
        elif trade_type in TRANSFER_IN_TYPES:
            summary["transfer_in"] += amount
            summary["has_capital_events"] = True
        elif trade_type in TRANSFER_OUT_TYPES:
            summary["transfer_out"] += amount
            summary["has_capital_events"] = True
        elif trade_type in INTEREST_TYPES and not interest_rows:
            summary["total_interest"] += amount

    summary["net_principal"] = summary["personal_deposit"] + summary["employer_deposit"] - summary["withdraw"]
    summary["net_transfer"] = summary["transfer_in"] - summary["transfer_out"]
    summary["net_adjustment"] = summary["cash_adjustment_in"] - summary["cash_adjustment_out"]
    summary["net_flow"] = summary["net_principal"] + summary["net_transfer"] + summary["net_adjustment"]
    return summary


def account_summary(
    account: dict[str, Any],
    holdings: list[dict[str, Any]],
    trade_logs: list[dict[str, Any]] | None = None,
    interest_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """계좌 요약을 원금/순유입 기준으로 계산한다."""

    frame = holdings_frame(holdings)
    total_cost = float(frame["cost_basis"].sum()) if not frame.empty else 0.0
    market_value = float(frame["current_value"].sum()) if not frame.empty else 0.0
    cash = float(account.get("cash_balance") or 0)
    total_value = market_value + cash
    market_profit_loss = market_value - total_cost
    market_profit_rate = (market_profit_loss / total_cost * 100) if total_cost else 0.0

    flow_summary = _cash_flow_summary(trade_logs, interest_rows)
    inferred_capital_base = total_cost + cash
    company_principal = float(flow_summary["employer_deposit"] or 0)
    contribution_principal = float(flow_summary["personal_deposit"] or 0) + company_principal
    net_flow = float(flow_summary["net_flow"] or 0)
    total_principal = float(flow_summary["net_principal"] or 0)
    if not bool(flow_summary["has_capital_events"]) and inferred_capital_base > 0:
        net_flow = inferred_capital_base
        total_principal = inferred_capital_base
        contribution_principal = inferred_capital_base
        company_principal = 0.0
    principal_profit_loss = total_value - total_principal
    principal_profit_rate = (principal_profit_loss / total_principal * 100) if total_principal else 0.0
    actual_profit_loss = total_value - net_flow
    actual_profit_rate = (actual_profit_loss / net_flow * 100) if net_flow else 0.0

    risk_value = float(frame.loc[frame["asset_type"] == "risk", "current_value"].sum()) if not frame.empty else 0.0
    safe_value = float(frame.loc[frame["asset_type"] == "safe", "current_value"].sum()) if not frame.empty else 0.0

    return {
        "total_cost": total_cost,
        "company_principal": company_principal,
        "contribution_principal": contribution_principal,
        "total_principal": total_principal,
        "net_flow": net_flow,
        "total_interest": float(flow_summary["total_interest"] or 0),
        "market_value": market_value,
        "cash": cash,
        "total_value": total_value,
        "profit_loss": market_profit_loss,
        "profit_rate": market_profit_rate,
        "principal_profit_loss": principal_profit_loss,
        "principal_profit_rate": principal_profit_rate,
        "actual_profit_loss": actual_profit_loss,
        "actual_profit_rate": actual_profit_rate,
        "allocation": {
            "risk": risk_value,
            "safe": safe_value,
            "cash": cash,
        },
        "cash_flow": flow_summary,
    }


def allocation_treemap_nodes(
    summary: dict[str, Any],
    holdings: list[dict[str, Any]],
    *,
    selected_symbol: str | None = None,
) -> list[dict[str, Any]]:
    """ECharts 트리맵용 자산 배분 계층 데이터를 만든다."""

    frame = holdings_frame(holdings)
    allocation = summary.get("allocation") or {}
    selected_key = str(selected_symbol or "").strip().upper()
    bucket_specs = (
        ("risk", "위험자산", "#E7D36F"),
        ("safe", "안전자산", "#BFD26A"),
        ("cash", "현금", "#8FD17B"),
    )
    nodes: list[dict[str, Any]] = []

    for asset_type, bucket_label, bucket_color in bucket_specs:
        if asset_type == "cash":
            cash_value = float(allocation.get("cash") or summary.get("cash") or 0)
            if cash_value <= 0:
                continue
            rounded_cash_value = round(cash_value)
            nodes.append(
                {
                    "name": bucket_label,
                    "value": rounded_cash_value,
                    "itemStyle": {"color": bucket_color},
                    "children": [
                        {
                            "name": "예수금",
                            "value": rounded_cash_value,
                            "bucket": bucket_label,
                            "selection_symbol": "CASH",
                            "is_selected": selected_key == "CASH",
                            "profit_rate": None,
                        }
                    ],
                }
            )
            continue

        bucket_frame = frame.loc[frame["asset_type"] == asset_type].copy() if not frame.empty else pd.DataFrame()
        if bucket_frame.empty:
            continue

        sector_children_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for _, row in bucket_frame.iterrows():
            current_value = float(row.get("current_value") or 0)
            if current_value <= 0:
                continue
            symbol = str(row.get("symbol") or "").strip().upper()
            sector_label = infer_holding_sector_label(row.get("product_name"), symbol, row.get("asset_type"))
            sector_children_map[sector_label].append(
                {
                    "name": str(row.get("product_name") or row.get("symbol") or "종목"),
                    "value": round(current_value, 4),
                    "bucket": bucket_label,
                    "sector_name": sector_label,
                    "symbol": symbol,
                    "selection_symbol": symbol,
                    "is_selected": bool(symbol and symbol == selected_key),
                    "profit_rate": round(float(row.get("profit_rate") or 0), 4),
                    "current_price": round(float(row.get("current_price") or 0), 4),
                }
            )

        bucket_children: list[dict[str, Any]] = []
        for sector_label, sector_rows in sorted(
            sector_children_map.items(),
            key=lambda item: sum(float(child.get("value") or 0) for child in item[1]),
            reverse=True,
        ):
            sorted_sector_rows = sorted(
                sector_rows,
                key=lambda child: float(child.get("value") or 0),
                reverse=True,
            )
            bucket_children.append(
                {
                    "name": sector_label,
                    "value": round(sum(float(child.get("value") or 0) for child in sorted_sector_rows), 4),
                    "bucket": bucket_label,
                    "sector_name": sector_label,
                    "children": sorted_sector_rows,
                }
            )

        if not bucket_children:
            continue

        nodes.append(
            {
                "name": bucket_label,
                "value": round(sum(float(child["value"]) for child in bucket_children), 4),
                "itemStyle": {"color": bucket_color},
                "children": bucket_children,
            }
        )

    return nodes


def projected_today_interest(
    account: dict[str, Any],
    interest_rows: list[dict[str, Any]] | None = None,
    *,
    annual_rate: float = DEFAULT_ANNUAL_INTEREST_RATE,
    as_of: date | None = None,
) -> float:
    """이자 자동 적립 기능 제거 이후 항상 0을 반환한다."""

    return 0.0


def realized_summary(trade_logs: list[dict[str, Any]]) -> dict[str, Any]:
    lots_by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    realized: list[dict[str, Any]] = []

    ordered_logs = sorted(
        filter_scaled_duplicate_trade_logs(trade_logs),
        key=lambda row: (row.get("trade_date", ""), row.get("created_at", ""), row.get("id", 0)),
    )
    for log in ordered_logs:
        trade_type = str(log.get("trade_type") or "").lower()
        if trade_type not in {"buy", "sell"}:
            continue

        symbol = _trade_match_key(log)
        display_symbol = str(log.get("symbol") or "").strip().upper()
        quantity = float(log.get("quantity") or 0)
        total_amount = normalized_trade_amount(log)
        if quantity <= 0 or total_amount <= 0:
            continue

        if trade_type == "buy":
            lots_by_symbol[symbol].append(
                {
                    "remaining_quantity": quantity,
                    "remaining_amount": total_amount,
                    "product_name": log.get("product_name"),
                    "asset_type": log.get("asset_type"),
                }
            )
            continue

        remaining_quantity = quantity
        matched_cost = 0.0
        lots = lots_by_symbol[symbol]
        while remaining_quantity > 0 and lots:
            lot = lots[0]
            lot_quantity = float(lot["remaining_quantity"] or 0)
            lot_amount = float(lot["remaining_amount"] or 0)
            if lot_quantity <= 0:
                lots.pop(0)
                continue

            matched_quantity = min(remaining_quantity, lot_quantity)
            ratio = matched_quantity / lot_quantity
            consumed_amount = lot_amount * ratio
            matched_cost += consumed_amount
            lot["remaining_quantity"] = lot_quantity - matched_quantity
            lot["remaining_amount"] = lot_amount - consumed_amount
            remaining_quantity -= matched_quantity

            if lot["remaining_quantity"] <= 0.000001:
                lots.pop(0)

        if matched_cost <= 0:
            continue

        profit_loss = total_amount - matched_cost
        realized.append(
            {
                "sell_log_id": log.get("id"),
                "symbol": display_symbol,
                "product_name": log.get("product_name"),
                "asset_type": log.get("asset_type"),
                "buy_amount": matched_cost,
                "sell_amount": total_amount,
                "profit_loss": profit_loss,
                "profit_rate": (profit_loss / matched_cost * 100) if matched_cost else 0,
                "sell_date": log.get("trade_date"),
            }
        )

    frame = pd.DataFrame(realized)
    if frame.empty:
        return {
            "sold_count": 0,
            "total_buy_amount": 0.0,
            "total_sell_amount": 0.0,
            "total_profit_loss": 0.0,
            "total_profit_rate": 0.0,
            "positions": [],
        }

    total_buy = float(frame["buy_amount"].sum())
    total_sell = float(frame["sell_amount"].sum())
    total_profit = total_sell - total_buy
    total_rate = (total_profit / total_buy * 100) if total_buy else 0.0

    frame = frame.sort_values(["sell_date", "product_name"], ascending=[False, True]).copy()
    for column in ("buy_amount", "sell_amount", "profit_loss", "profit_rate"):
        frame[column] = frame[column].astype(float).round(2)

    return {
        "sold_count": int(len(frame)),
        "total_buy_amount": round(total_buy, 2),
        "total_sell_amount": round(total_sell, 2),
        "total_profit_loss": round(total_profit, 2),
        "total_profit_rate": round(total_rate, 2),
        "positions": frame.to_dict(orient="records"),
    }


def _cash_flow_event_frame(
    trade_logs: list[dict[str, Any]] | None = None,
    interest_rows: list[dict[str, Any]] | None = None,
) -> pd.DataFrame:
    event_rows: list[dict[str, Any]] = []

    for log in trade_logs or []:
        trade_type = _normalized_trade_type(log)
        trade_date = str(log.get("trade_date") or "").strip()
        if not trade_date:
            continue

        event = {
            "date": pd.to_datetime(trade_date),
            "personal_deposit_delta": 0.0,
            "employer_deposit_delta": 0.0,
            "withdraw_delta": 0.0,
            "principal_delta": 0.0,
            "flow_delta": 0.0,
            "interest_delta": 0.0,
            "capital_event_flag": 0,
        }
        amount = _amount_from_log(log)
        if trade_type == "personal_deposit":
            event["personal_deposit_delta"] = amount
            event["principal_delta"] = amount
            event["flow_delta"] = amount
            event["capital_event_flag"] = 1
        elif trade_type == "employer_deposit":
            event["employer_deposit_delta"] = amount
            event["principal_delta"] = amount
            event["flow_delta"] = amount
            event["capital_event_flag"] = 1
        elif trade_type in CAPITAL_OUTFLOW_TYPES:
            event["withdraw_delta"] = amount
            event["principal_delta"] = -amount
            event["flow_delta"] = -amount
            event["capital_event_flag"] = 1
        elif trade_type in TRANSFER_IN_TYPES:
            event["flow_delta"] = amount
            event["capital_event_flag"] = 1
        elif trade_type in TRANSFER_OUT_TYPES:
            event["flow_delta"] = -amount
            event["capital_event_flag"] = 1
        elif trade_type in INTEREST_TYPES and not interest_rows:
            event["interest_delta"] = amount
        else:
            continue
        event_rows.append(event)

    for row in interest_rows or []:
        interest_date = str(row.get("date") or "").strip()
        if not interest_date:
            continue
        event_rows.append(
            {
                "date": pd.to_datetime(interest_date),
                "personal_deposit_delta": 0.0,
                "employer_deposit_delta": 0.0,
                "withdraw_delta": 0.0,
                "principal_delta": 0.0,
                "flow_delta": 0.0,
                "interest_delta": float(row.get("interest_amount") or 0),
                "capital_event_flag": 0,
            }
        )

    if not event_rows:
        return pd.DataFrame()

    frame = pd.DataFrame(event_rows)
    grouped = (
        frame.groupby("date", as_index=False)
        .agg(
            personal_deposit_delta=("personal_deposit_delta", "sum"),
            employer_deposit_delta=("employer_deposit_delta", "sum"),
            withdraw_delta=("withdraw_delta", "sum"),
            principal_delta=("principal_delta", "sum"),
            flow_delta=("flow_delta", "sum"),
            interest_delta=("interest_delta", "sum"),
            capital_event_flag=("capital_event_flag", "max"),
        )
        .sort_values("date")
        .reset_index(drop=True)
    )
    grouped["capital_event_seen"] = grouped["capital_event_flag"].astype(int).cumsum().gt(0)
    return grouped


def cumulative_contribution_frame(
    trade_logs: list[dict[str, Any]] | None = None,
    interest_rows: list[dict[str, Any]] | None = None,
    snapshots: list[dict[str, Any]] | None = None,
    *,
    current_total_value: float | None = None,
    current_market_value: float | None = None,
    current_cash_balance: float | None = None,
    current_total_cost: float | None = None,
    current_date: str | date | None = None,
) -> pd.DataFrame:
    """최초 입금일부터 현재까지 누적 원금 흐름과 평가 요약을 만든다."""

    event_frame = _cash_flow_event_frame(trade_logs, interest_rows)
    if event_frame.empty:
        return pd.DataFrame()

    result = event_frame[
        [
            "date",
            "personal_deposit_delta",
            "employer_deposit_delta",
            "withdraw_delta",
            "principal_delta",
            "flow_delta",
            "interest_delta",
        ]
    ].copy()
    result = result.sort_values("date").reset_index(drop=True)
    result["personal_principal"] = result["personal_deposit_delta"].cumsum()
    result["company_principal"] = result["employer_deposit_delta"].cumsum()
    result["total_principal"] = result["principal_delta"].cumsum()
    result["net_flow"] = result["flow_delta"].cumsum()
    result["total_interest"] = result["interest_delta"].cumsum()

    snapshot_frame = pd.DataFrame(snapshots or [])
    if snapshot_frame.empty:
        result["cash_balance"] = float("nan")
        result["market_value"] = float("nan")
        result["total_value"] = float("nan")
        result["total_cost"] = float("nan")
    else:
        snapshot_frame = snapshot_frame.copy()
        snapshot_frame["date"] = pd.to_datetime(snapshot_frame["snapshot_date"])
        for column in ("cash_balance", "market_value", "total_value", "total_cost"):
            snapshot_frame[column] = snapshot_frame[column].astype(float)
        snapshot_frame = snapshot_frame.sort_values("date").drop_duplicates(subset=["date"], keep="last")
        result = result.merge(
            snapshot_frame[["date", "cash_balance", "market_value", "total_value", "total_cost"]],
            on="date",
            how="left",
        )

    if any(
        value is not None
        for value in (current_total_value, current_market_value, current_cash_balance, current_total_cost, current_date)
    ):
        normalized_current_date = pd.to_datetime(current_date or date.today().isoformat())
        current_mask = result["date"].eq(normalized_current_date)
        if current_mask.any():
            current_index = result.index[current_mask][-1]
            if current_cash_balance is not None:
                result.at[current_index, "cash_balance"] = float(current_cash_balance)
            if current_market_value is not None:
                result.at[current_index, "market_value"] = float(current_market_value)
            if current_total_value is not None:
                result.at[current_index, "total_value"] = float(current_total_value)
            if current_total_cost is not None:
                result.at[current_index, "total_cost"] = float(current_total_cost)
        else:
            latest = result.iloc[-1].copy()
            latest["date"] = normalized_current_date
            latest["personal_deposit_delta"] = 0.0
            latest["employer_deposit_delta"] = 0.0
            latest["withdraw_delta"] = 0.0
            latest["principal_delta"] = 0.0
            latest["flow_delta"] = 0.0
            latest["interest_delta"] = 0.0
            latest["cash_balance"] = float(current_cash_balance) if current_cash_balance is not None else float("nan")
            latest["market_value"] = float(current_market_value) if current_market_value is not None else float("nan")
            latest["total_value"] = float(current_total_value) if current_total_value is not None else float("nan")
            latest["total_cost"] = float(current_total_cost) if current_total_cost is not None else float("nan")
            result.loc[len(result)] = latest

    result["principal_profit_loss"] = result["total_value"] - result["total_principal"]
    result["principal_profit_rate"] = result.apply(
        lambda row: (row["principal_profit_loss"] / row["total_principal"] * 100)
        if pd.notna(row["total_value"]) and row["total_principal"]
        else pd.NA,
        axis=1,
    )
    result["date"] = result["date"].dt.strftime("%Y-%m-%d")
    return result.sort_values("date").reset_index(drop=True)


def snapshot_trend_frame(
    snapshots: list[dict[str, Any]],
    trade_logs: list[dict[str, Any]] | None = None,
    interest_rows: list[dict[str, Any]] | None = None,
) -> pd.DataFrame:
    """일별 계좌 스냅샷 목록을 대시보드 추이용 데이터프레임으로 변환한다."""

    frame = pd.DataFrame(snapshots)
    if frame.empty:
        return frame

    result = frame.copy()
    result["date"] = pd.to_datetime(result["snapshot_date"])
    result["cash_balance"] = result["cash_balance"].astype(float)
    result["market_value"] = result["market_value"].astype(float)
    result["total_value"] = result["total_value"].astype(float)
    result["total_cost"] = result["total_cost"].astype(float)
    result["profit_loss"] = result["total_value"] - result["total_cost"]
    result["profit_rate"] = result.apply(
        lambda row: (row["profit_loss"] / row["total_cost"] * 100) if row["total_cost"] else 0,
        axis=1,
    )
    event_frame = _cash_flow_event_frame(trade_logs, interest_rows)
    if event_frame.empty:
        fallback_base = result["total_cost"] + result["cash_balance"]
        result["total_principal"] = fallback_base
        result["net_flow"] = fallback_base
        result["total_interest"] = 0.0
    else:
        cumulative_events = event_frame.copy().sort_values("date")
        cumulative_events["total_principal"] = cumulative_events["principal_delta"].cumsum()
        cumulative_events["net_flow"] = cumulative_events["flow_delta"].cumsum()
        cumulative_events["total_interest"] = cumulative_events["interest_delta"].cumsum()

        result = pd.merge_asof(
            result.sort_values("date"),
            cumulative_events[["date", "total_principal", "net_flow", "total_interest", "capital_event_seen"]],
            on="date",
            direction="backward",
        )
        result["total_principal"] = result["total_principal"].fillna(0.0)
        result["net_flow"] = result["net_flow"].fillna(0.0)
        result["total_interest"] = result["total_interest"].fillna(0.0)
        result["capital_event_seen"] = result["capital_event_seen"].fillna(False).astype(bool)
        fallback_base = result["total_cost"] + result["cash_balance"]
        no_capital_history = ~result["capital_event_seen"].fillna(False).astype(bool)
        result.loc[no_capital_history, "total_principal"] = fallback_base.loc[no_capital_history]
        result.loc[no_capital_history, "net_flow"] = fallback_base.loc[no_capital_history]
        result = result.drop(columns=["capital_event_seen"])

    result["actual_profit_loss"] = result["total_value"] - result["net_flow"]
    result["actual_profit_rate"] = result.apply(
        lambda row: (row["actual_profit_loss"] / row["net_flow"] * 100) if row["net_flow"] else 0,
        axis=1,
    )
    result["principal_profit_loss"] = result["total_value"] - result["total_principal"]
    result["principal_profit_rate"] = result.apply(
        lambda row: (row["principal_profit_loss"] / row["total_principal"] * 100) if row["total_principal"] else 0,
        axis=1,
    )
    return result.sort_values("date").reset_index(drop=True)


def build_portfolio_trend(holdings: list[dict[str, Any]], period: str = "6mo") -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = holdings_frame(holdings)
    if frame.empty:
        return pd.DataFrame(), pd.DataFrame()

    detail_rows: list[pd.DataFrame] = []
    merged_values: list[pd.DataFrame] = []

    for row in frame.to_dict(orient="records"):
        try:
            history = fetch_price_history(str(row["symbol"]), period=period)
        except Exception:  # noqa: BLE001
            continue
        if history.empty:
            continue

        quantity = float(row["quantity"] or 0)
        cost_basis = float(row["avg_cost"] or 0) * quantity
        history = history.copy()
        history["product_name"] = row["product_name"]
        history["market_value"] = history["close"].astype(float) * quantity
        history["cost_basis"] = cost_basis
        history["profit_loss"] = history["market_value"] - history["cost_basis"]
        history["profit_rate"] = history["profit_loss"].apply(lambda value: (value / cost_basis * 100) if cost_basis else 0)
        detail_rows.append(history)

        value_series = history[["date", "market_value"]].copy().rename(columns={"market_value": row["product_name"]})
        merged_values.append(value_series)

    if not detail_rows or not merged_values:
        return pd.DataFrame(), pd.DataFrame()

    portfolio_map = merged_values[0]
    for item in merged_values[1:]:
        portfolio_map = portfolio_map.merge(item, on="date", how="outer")

    portfolio_map = portfolio_map.sort_values("date").ffill().fillna(0)
    portfolio_long = pd.concat(detail_rows, ignore_index=True)
    portfolio_totals = pd.DataFrame(
        {
            "date": portfolio_map["date"],
            "market_value": portfolio_map.drop(columns=["date"]).sum(axis=1),
        }
    )
    total_cost_basis = float(frame["cost_basis"].sum())
    portfolio_totals["cost_basis"] = total_cost_basis
    portfolio_totals["profit_loss"] = portfolio_totals["market_value"] - total_cost_basis
    portfolio_totals["profit_rate"] = portfolio_totals["profit_loss"].apply(
        lambda value: (value / total_cost_basis * 100) if total_cost_basis else 0
    )
    return portfolio_totals, portfolio_long

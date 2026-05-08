from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd

from .market import fetch_price_history


CAPITAL_INFLOW_TYPES = {"personal_deposit", "employer_deposit"}
CAPITAL_OUTFLOW_TYPES = {"withdraw"}
TRANSFER_IN_TYPES = {"transfer_in"}
TRANSFER_OUT_TYPES = {"transfer_out"}
MANUAL_ADJUSTMENT_TYPES = {"cash_adjustment"}
INTEREST_TYPES = {"interest"}


def _trade_match_key(log: dict[str, Any]) -> str:
    symbol = str(log.get("symbol") or "").strip().upper()
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
    frame["cost_basis"] = frame["quantity"].astype(float) * frame["avg_cost"].astype(float)
    frame["current_value"] = frame["quantity"].astype(float) * frame["current_price"].astype(float)
    frame["profit_loss"] = frame["current_value"] - frame["cost_basis"]
    frame["profit_rate"] = frame.apply(
        lambda row: (row["profit_loss"] / row["cost_basis"] * 100) if row["cost_basis"] else 0,
        axis=1,
    )
    return frame.sort_values("current_value", ascending=False)


def _amount_from_log(log: dict[str, Any]) -> float:
    total_amount = abs(float(log.get("total_amount") or 0))
    if total_amount > 0:
        return total_amount
    return abs(float(log.get("cash_delta") or 0))


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
        trade_type = str(log.get("trade_type") or "").strip().lower()
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
        elif trade_type in MANUAL_ADJUSTMENT_TYPES:
            delta = float(log.get("cash_delta") or 0)
            if delta >= 0:
                summary["cash_adjustment_in"] += abs(delta)
            else:
                summary["cash_adjustment_out"] += abs(delta)
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
    """계좌 요약을 원금/순유입/누적 이자 기준까지 포함해 계산한다."""

    frame = holdings_frame(holdings)
    total_cost = float(frame["cost_basis"].sum()) if not frame.empty else 0.0
    market_value = float(frame["current_value"].sum()) if not frame.empty else 0.0
    cash = float(account.get("cash_balance") or 0)
    total_value = market_value + cash
    market_profit_loss = market_value - total_cost
    market_profit_rate = (market_profit_loss / total_cost * 100) if total_cost else 0.0

    flow_summary = _cash_flow_summary(trade_logs, interest_rows)
    inferred_capital_base = total_cost + cash
    net_flow = float(flow_summary["net_flow"] or 0)
    total_principal = float(flow_summary["net_principal"] or 0)
    if not bool(flow_summary["has_capital_events"]) and inferred_capital_base > 0:
        net_flow = inferred_capital_base
        total_principal = inferred_capital_base
    actual_profit_loss = total_value - net_flow
    actual_profit_rate = (actual_profit_loss / net_flow * 100) if net_flow else 0.0

    risk_value = float(frame.loc[frame["asset_type"] == "risk", "current_value"].sum()) if not frame.empty else 0.0
    safe_value = float(frame.loc[frame["asset_type"] == "safe", "current_value"].sum()) if not frame.empty else 0.0

    return {
        "total_cost": total_cost,
        "total_principal": total_principal,
        "net_flow": net_flow,
        "total_interest": float(flow_summary["total_interest"] or 0),
        "market_value": market_value,
        "cash": cash,
        "total_value": total_value,
        "profit_loss": market_profit_loss,
        "profit_rate": market_profit_rate,
        "actual_profit_loss": actual_profit_loss,
        "actual_profit_rate": actual_profit_rate,
        "allocation": {
            "risk": risk_value,
            "safe": safe_value,
            "cash": cash,
        },
        "cash_flow": flow_summary,
    }


def realized_summary(trade_logs: list[dict[str, Any]]) -> dict[str, Any]:
    lots_by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    realized: list[dict[str, Any]] = []

    ordered_logs = sorted(
        trade_logs,
        key=lambda row: (row.get("trade_date", ""), row.get("created_at", ""), row.get("id", 0)),
    )
    for log in ordered_logs:
        trade_type = str(log.get("trade_type") or "").lower()
        if trade_type not in {"buy", "sell"}:
            continue

        symbol = _trade_match_key(log)
        display_symbol = str(log.get("symbol") or "").strip().upper()
        quantity = float(log.get("quantity") or 0)
        total_amount = float(log.get("total_amount") or 0)
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
        trade_type = str(log.get("trade_type") or "").strip().lower()
        trade_date = str(log.get("trade_date") or "").strip()
        if not trade_date:
            continue

        event = {
            "date": pd.to_datetime(trade_date),
            "principal_delta": 0.0,
            "flow_delta": 0.0,
            "interest_delta": 0.0,
            "capital_event_flag": 0,
        }
        amount = _amount_from_log(log)
        if trade_type in CAPITAL_INFLOW_TYPES:
            event["principal_delta"] = amount
            event["flow_delta"] = amount
            event["capital_event_flag"] = 1
        elif trade_type in CAPITAL_OUTFLOW_TYPES:
            event["principal_delta"] = -amount
            event["flow_delta"] = -amount
            event["capital_event_flag"] = 1
        elif trade_type in TRANSFER_IN_TYPES:
            event["flow_delta"] = amount
            event["capital_event_flag"] = 1
        elif trade_type in TRANSFER_OUT_TYPES:
            event["flow_delta"] = -amount
            event["capital_event_flag"] = 1
        elif trade_type in MANUAL_ADJUSTMENT_TYPES:
            event["flow_delta"] = float(log.get("cash_delta") or 0)
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

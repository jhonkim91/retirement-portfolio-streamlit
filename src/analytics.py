from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd

from .market import fetch_price_history


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


def account_summary(account: dict[str, Any], holdings: list[dict[str, Any]]) -> dict[str, Any]:
    frame = holdings_frame(holdings)
    total_cost = float(frame["cost_basis"].sum()) if not frame.empty else 0.0
    market_value = float(frame["current_value"].sum()) if not frame.empty else 0.0
    cash = float(account.get("cash_balance") or 0)
    total_value = market_value + cash
    profit_loss = market_value - total_cost
    profit_rate = (profit_loss / total_cost * 100) if total_cost else 0.0

    risk_value = float(frame.loc[frame["asset_type"] == "risk", "current_value"].sum()) if not frame.empty else 0.0
    safe_value = float(frame.loc[frame["asset_type"] == "safe", "current_value"].sum()) if not frame.empty else 0.0

    return {
        "total_cost": total_cost,
        "market_value": market_value,
        "cash": cash,
        "total_value": total_value,
        "profit_loss": profit_loss,
        "profit_rate": profit_rate,
        "allocation": {
            "risk": risk_value,
            "safe": safe_value,
            "cash": cash,
        },
    }


def realized_summary(trade_logs: list[dict[str, Any]]) -> dict[str, Any]:
    lots_by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    realized: list[dict[str, Any]] = []

    ordered_logs = sorted(trade_logs, key=lambda row: (row["trade_date"], row["id"]))
    for log in ordered_logs:
        trade_type = str(log.get("trade_type") or "").lower()
        if trade_type not in {"buy", "sell"}:
            continue

        symbol = str(log.get("symbol") or "").strip().upper()
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
                "symbol": symbol,
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


def build_portfolio_trend(holdings: list[dict[str, Any]], period: str = "6mo") -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = holdings_frame(holdings)
    if frame.empty:
        return pd.DataFrame(), pd.DataFrame()

    detail_rows: list[pd.DataFrame] = []
    merged_values: list[pd.DataFrame] = []

    for row in frame.to_dict(orient="records"):
        history = fetch_price_history(str(row["symbol"]), period=period)
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

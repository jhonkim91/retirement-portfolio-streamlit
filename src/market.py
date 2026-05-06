from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st
import yfinance as yf


def normalize_symbol(symbol: str) -> str:
    cleaned = str(symbol or "").strip().upper()
    if cleaned.isdigit() and len(cleaned) == 6:
        return f"{cleaned}.KS"
    return cleaned


@st.cache_data(ttl=900, show_spinner=False)
def fetch_latest_price(symbol: str) -> dict[str, Any]:
    normalized = normalize_symbol(symbol)
    if not normalized:
        raise ValueError("종목 코드를 입력해 주세요.")

    history = yf.Ticker(normalized).history(period="5d", auto_adjust=False)
    closes = history.get("Close")
    if closes is None or closes.dropna().empty:
        raise ValueError(f"{normalized} 가격을 가져오지 못했습니다.")

    last_value = closes.dropna().iloc[-1]
    last_date = closes.dropna().index[-1]
    return {
        "symbol": normalized,
        "price": float(last_value),
        "as_of": pd.Timestamp(last_date).date().isoformat(),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_price_history(symbol: str, period: str = "6mo") -> pd.DataFrame:
    normalized = normalize_symbol(symbol)
    if not normalized:
        return pd.DataFrame(columns=["date", "close", "symbol"])

    history = yf.Ticker(normalized).history(period=period, auto_adjust=False)
    closes = history.get("Close")
    if closes is None or closes.dropna().empty:
        return pd.DataFrame(columns=["date", "close", "symbol"])

    frame = closes.dropna().reset_index()
    frame.columns = ["date", "close"]
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame["symbol"] = normalized
    return frame

from __future__ import annotations

import html
import re
import urllib.parse
from typing import Any

import pandas as pd
import requests
import streamlit as st
import yfinance as yf


NAVER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

US_YAHOO_EXCHANGE_CODES = {"ASE", "BTS", "NCM", "NGM", "NMS", "NYQ", "PCX"}
US_YAHOO_EXCHANGE_NAMES = {"AMEX", "BATS TRADING", "NASDAQ", "NYSE", "NYSEARCA"}
US_YAHOO_QUOTE_TYPES = {"EQUITY", "ETF", "MUTUALFUND"}
PREFERRED_DOMESTIC_BRANDS = {
    "ACE",
    "ARIRANG",
    "HANARO",
    "KBSTAR",
    "KODEX",
    "KOSEF",
    "PLUS",
    "RISE",
    "SOL",
    "TIGER",
    "TIMEFOLIO",
    "TREX",
}


def clean_code(code: str) -> str:
    cleaned = str(code or "").strip().upper()
    if re.fullmatch(r"[0-9A-Z]{6}\.(KS|KQ)", cleaned):
        return cleaned.split(".")[0]
    if len(cleaned) % 2 == 0:
        half = cleaned[: len(cleaned) // 2]
        if half == cleaned[len(cleaned) // 2 :] and (
            re.fullmatch(r"[0-9A-Z]{6}", half)
            or re.fullmatch(r"(?:K[0-9A-Z]{11}|KR[0-9A-Z]{10})", half)
        ):
            return half
    return cleaned


def normalize_symbol(symbol: str) -> str:
    raw = str(symbol or "").strip().upper()
    if re.fullmatch(r"[0-9]{6}\.(KS|KQ)", raw):
        return raw
    cleaned = clean_code(raw)
    if cleaned.isdigit() and len(cleaned) < 6:
        cleaned = cleaned.zfill(6)
    if is_krx_code(cleaned):
        return f"{cleaned}.KS"
    return cleaned


def normalize_search_text(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "")).lower()


def contains_hangul(value: str) -> bool:
    return re.search(r"[\uac00-\ud7a3]", str(value or "")) is not None


def is_krx_code(code: str) -> bool:
    return bool(re.fullmatch(r"[0-9]{6}", clean_code(code)))


def is_fund_code(code: str) -> bool:
    return bool(re.fullmatch(r"(?:K[0-9A-Z]{11}|KR[0-9A-Z]{10})", clean_code(code)))


def is_global_symbol_query(query: str) -> bool:
    cleaned = clean_code(query)
    return bool(re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", cleaned)) and not is_krx_code(cleaned) and not is_fund_code(cleaned)


def matches_search_query(query: str, *, code: str, name: str) -> bool:
    normalized_query = normalize_search_text(query)
    normalized_name = normalize_search_text(name)
    normalized_code = clean_code(code)
    query_code = clean_code(query)
    return bool(normalized_query and normalized_query in normalized_name) or bool(query_code and query_code in normalized_code)


def has_exact_search_match(items: list[dict[str, Any]], query: str) -> bool:
    normalized_query = normalize_search_text(query)
    normalized_code = clean_code(query)
    return any(
        item.get("code") == normalized_code or normalize_search_text(item.get("name")) == normalized_query
        for item in items
    )


def encode_naver_search_query(query: str) -> str:
    try:
        return urllib.parse.quote_from_bytes(str(query or "").encode("cp949"))
    except UnicodeEncodeError:
        return urllib.parse.quote(str(query or ""))


def search_products_from_yfinance(query: str, limit: int, *, include_global: bool = False) -> list[dict[str, Any]]:
    try:
        if not hasattr(yf, "Search"):
            return []

        search = yf.Search(query, max_results=max(limit * 2, 10))
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for quote in search.quotes:
            symbol = str(quote.get("symbol") or "").strip().upper()
            name = quote.get("shortname") or quote.get("longname")
            if not name:
                continue
            match = re.match(r"^([0-9]{6})\.(KS|KQ)$", symbol)
            if match:
                code = match.group(1)
                if code in seen:
                    continue
                seen.add(code)
                rows.append(
                    {
                        "name": str(name).strip(),
                        "code": code,
                        "symbol": symbol,
                        "exchange": quote.get("exchDisp") or quote.get("exchange") or "Korea",
                        "type": quote.get("quoteType") or quote.get("typeDisp") or "stock",
                        "source": "Yahoo",
                    }
                )
                continue

            if not include_global:
                continue

            quote_type = str(quote.get("quoteType") or quote.get("typeDisp") or "").strip().upper()
            exchange_code = str(quote.get("exchange") or "").strip().upper()
            exchange_name = str(quote.get("exchDisp") or "").strip().upper()
            if quote_type not in US_YAHOO_QUOTE_TYPES:
                continue
            if exchange_code not in US_YAHOO_EXCHANGE_CODES and exchange_name not in US_YAHOO_EXCHANGE_NAMES:
                continue
            if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", symbol):
                continue
            if symbol.startswith("^") or symbol.endswith("-USD") or symbol.endswith("=F"):
                continue
            if not matches_search_query(query, code=symbol, name=str(name)):
                continue
            if symbol in seen:
                continue
            seen.add(symbol)
            rows.append(
                {
                    "name": str(name).strip(),
                    "code": symbol,
                    "symbol": symbol,
                    "exchange": "US",
                    "type": quote_type.lower(),
                    "source": "Yahoo",
                }
            )
            if len(rows) >= limit:
                break
        return rows
    except Exception:
        return []


def search_products_from_naver_search(query: str, limit: int) -> list[dict[str, Any]]:
    try:
        response = requests.get(
            f"https://finance.naver.com/search/search.naver?query={encode_naver_search_query(query)}",
            headers=NAVER_HEADERS,
            timeout=6,
        )
        if response.status_code != 200:
            return []
        response.encoding = "EUC-KR"
        text = response.text

        redirect = re.search(r"code=([0-9A-Z]{6})", text)
        if redirect and len(text) < 500:
            item = get_naver_product_by_code(redirect.group(1))
            return [item] if item else []

        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        pattern = r'href="/item/main\.naver\?code=([0-9A-Z]{6})"[^>]*>(.*?)</a>'
        for code, raw_name in re.findall(pattern, text, flags=re.IGNORECASE | re.DOTALL):
            name = html.unescape(re.sub(r"<[^>]+>", "", raw_name)).strip()
            code = code.upper()
            if not name or code in seen:
                continue
            seen.add(code)
            is_listed = is_krx_code(code)
            rows.append(
                {
                    "name": name,
                    "code": code,
                    "symbol": f"{code}.KS" if is_listed else code,
                    "exchange": "KRX" if is_listed else "Fund",
                    "type": "stock/ETF" if is_listed else "fund",
                    "source": "Naver",
                }
            )
            if len(rows) >= limit:
                break
        return rows
    except Exception:
        return []


def search_products_from_naver_etf_list(query: str, limit: int) -> list[dict[str, Any]]:
    normalized_query = normalize_search_text(query)
    query_code = str(query or "").strip().upper()
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    sources = [
        ("https://finance.naver.com/api/sise/etfItemList.nhn", "etfItemList", "ETF"),
        ("https://finance.naver.com/api/sise/etnItemList.nhn", "etnItemList", "ETN"),
    ]

    for url, list_key, product_type in sources:
        try:
            response = requests.get(url, headers=NAVER_HEADERS, timeout=8)
            if response.status_code != 200:
                continue
            data = response.json()
            items = ((data.get("result") or {}).get(list_key) or [])
            for item in items:
                code = str(item.get("itemcode") or "").strip().upper()
                name = str(item.get("itemname") or "").strip()
                if not code or not name or code in seen:
                    continue
                if normalized_query not in normalize_search_text(name) and query_code not in code:
                    continue
                seen.add(code)
                rows.append(
                    {
                        "name": name,
                        "code": code,
                        "symbol": f"{code}.KS",
                        "exchange": "KRX",
                        "type": product_type,
                        "source": "Naver",
                    }
                )
                if len(rows) >= limit:
                    return rows
        except Exception:
            continue
    return rows


def search_funds_from_funetf(query: str, limit: int) -> list[dict[str, Any]]:
    cleaned_query = str(query or "").strip()
    if len(cleaned_query) < 2:
        return []
    try:
        response = requests.get(
            "https://www.funetf.co.kr/api/public/main/search/all",
            params={
                "schVal": cleaned_query,
                "reSchVal": "",
                "reSchChk": "",
                "schKeyword": "",
            },
            headers=NAVER_HEADERS,
            timeout=8,
        )
        if response.status_code != 200:
            return []
        response.encoding = "utf-8"
        data = response.json()
        groups = [
            (((data.get("fundList") or {}).get("content") or []), "fund"),
            (((data.get("etfList") or {}).get("content") or []), "ETF"),
        ]
        rows: list[dict[str, Any]] = []
        for items, product_type in groups:
            for item in items:
                if product_type == "ETF":
                    code = str(item.get("sotCd") or item.get("shortCd") or item.get("fundCd") or "").strip().upper()
                else:
                    code = str(item.get("fundCd") or item.get("repFundCd") or "").strip().upper()
                name = str(item.get("itemNm") or item.get("fundFnm") or item.get("repFundNm") or "").strip()
                if not code or not name:
                    continue
                if not matches_search_query(cleaned_query, code=code, name=name):
                    continue
                rows.append(
                    {
                        "name": name,
                        "code": code,
                        "symbol": f"{code}.KS" if product_type == "ETF" and is_krx_code(code) else code,
                        "exchange": "KRX" if product_type == "ETF" else "Fund",
                        "type": product_type,
                        "source": "FunETF",
                    }
                )
                if len(rows) >= limit:
                    return rows
        return rows
    except Exception:
        return []


def get_naver_product_by_code(code: str) -> dict[str, Any] | None:
    try:
        cleaned = clean_code(code)
        if not is_krx_code(cleaned):
            return None
        response = requests.get(
            "https://finance.naver.com/item/main.naver",
            params={"code": cleaned},
            headers=NAVER_HEADERS,
            timeout=6,
        )
        if response.status_code != 200:
            return None
        response.encoding = "utf-8"
        text = response.text
        title_match = re.search(r"<title>\s*(.*?)\s*[:|-]\s*Npay", text, flags=re.DOTALL)
        name = html.unescape(re.sub(r"<[^>]+>", "", title_match.group(1))).strip() if title_match else ""
        if not name:
            name_match = re.search(
                r"item\.naver\?code=" + re.escape(cleaned) + r'.*?>([^<]+)</a>',
                text,
                flags=re.DOTALL,
            )
            name = html.unescape(name_match.group(1)).strip() if name_match else ""
        if not name:
            return None
        return {
            "name": name,
            "code": cleaned,
            "symbol": f"{cleaned}.KS",
            "exchange": "KRX",
            "type": "stock/ETF",
            "source": "Naver",
        }
    except Exception:
        return None


def get_funetf_product_by_code(code: str) -> dict[str, Any] | None:
    cleaned = clean_code(code)
    if not is_fund_code(cleaned):
        return None
    try:
        response = requests.get(
            f"https://www.funetf.co.kr/product/fund/view/{cleaned}",
            headers=NAVER_HEADERS,
            timeout=8,
        )
        if response.status_code != 200:
            return None
        response.encoding = "utf-8"
        title_match = re.search(r"<title>\s*(.*?)\s*\|\s*FunETF", response.text, flags=re.DOTALL)
        name = html.unescape(re.sub(r"<[^>]+>", "", title_match.group(1))).strip() if title_match else ""
        if not name:
            og_match = re.search(r'<meta property="og:title" content="([^"]+)"', response.text)
            name = html.unescape(og_match.group(1).split("|")[0]).strip() if og_match else ""
        if not name:
            return None
        return {
            "name": name,
            "code": cleaned,
            "symbol": cleaned,
            "exchange": "Fund",
            "type": "fund",
            "source": "FunETF",
        }
    except Exception:
        return None


@st.cache_data(ttl=600, show_spinner=False)
def search_products(query: str, limit: int = 8) -> list[dict[str, Any]]:
    cleaned_query = clean_code(query)
    if len(cleaned_query) < 2:
        return []

    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    normalized_query = normalize_search_text(cleaned_query)

    def add_result(item: dict[str, Any] | None) -> None:
        if not item:
            return
        code = clean_code(item.get("code"))
        name = str(item.get("name") or "").strip()
        if not code or not name or code in seen:
            return
        seen.add(code)
        results.append(
            {
                "name": name,
                "code": code,
                "symbol": item.get("symbol") or (f"{code}.KS" if is_krx_code(code) else code),
                "exchange": item.get("exchange") or "KRX",
                "type": item.get("type") or "stock",
                "source": item.get("source") or "market",
            }
        )

    def rank(item: dict[str, Any]) -> tuple[int, str]:
        code = str(item.get("code") or "").upper()
        name = normalize_search_text(item.get("name"))
        if code == cleaned_query.upper():
            return (0, name)
        if code.startswith(cleaned_query.upper()):
            return (1, name)
        if name == normalized_query:
            return (2, name)
        if name.startswith(normalized_query):
            return (3, name)
        return (4, name)

    if is_krx_code(cleaned_query):
        add_result(get_naver_product_by_code(cleaned_query))
        if results:
            return sorted(results, key=rank)[:limit]

    if is_fund_code(cleaned_query):
        add_result(get_funetf_product_by_code(cleaned_query))
        if results:
            return sorted(results, key=rank)[:limit]

    if is_global_symbol_query(cleaned_query) and cleaned_query not in PREFERRED_DOMESTIC_BRANDS:
        for item in search_products_from_yfinance(cleaned_query, limit, include_global=True):
            add_result(item)
        if has_exact_search_match(results, cleaned_query):
            return sorted(results, key=rank)[:limit]

    if cleaned_query.isdigit():
        for item in search_products_from_yfinance(cleaned_query, limit):
            add_result(item)
        if has_exact_search_match(results, cleaned_query):
            return sorted(results, key=rank)[:limit]

    source_functions = [
        search_products_from_naver_search,
        search_products_from_naver_etf_list,
        search_funds_from_funetf,
    ]
    if not contains_hangul(cleaned_query) and not cleaned_query.isdigit():
        source_functions = [
            search_products_from_naver_etf_list,
            search_funds_from_funetf,
            search_products_from_naver_search,
        ]

    for source_function in source_functions:
        for item in source_function(cleaned_query, limit):
            add_result(item)
        if has_exact_search_match(results, cleaned_query) or len(results) >= limit:
            return sorted(results, key=rank)[:limit]

    if not contains_hangul(cleaned_query):
        for item in search_products_from_yfinance(cleaned_query, limit, include_global=True):
            add_result(item)

    return sorted(results, key=rank)[:limit]


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

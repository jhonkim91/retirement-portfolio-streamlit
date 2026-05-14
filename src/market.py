from __future__ import annotations

import ast
from datetime import date, timedelta
import html
import re
import urllib.parse
from typing import Any

import pandas as pd
import requests
import streamlit as st

try:
    import yfinance as yf
except ImportError:
    yf = None

from .kis import (
    KisApiClient,
    get_master_record,
    is_kis_domestic_symbol,
    is_kis_enabled,
    kis_runtime_status,
    normalize_domestic_code,
    resolve_sector_name as resolve_kis_sector_name,
    search_master_products,
)


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
KRX_LISTED_CODE_PATTERN = r"(?:[0-9]{6}|[0-9]{4}[A-Z][0-9])"


def quote_provider_status() -> dict[str, Any]:
    """운영 상태 패널에 표시할 시세 provider 정보를 반환한다."""

    return kis_runtime_status()


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
    if re.fullmatch(rf"{KRX_LISTED_CODE_PATTERN}\.(KS|KQ)", raw):
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
    return bool(re.fullmatch(KRX_LISTED_CODE_PATTERN, clean_code(code)))


def is_krx_symbol(symbol: str) -> bool:
    """거래소 suffix 포함 여부와 무관하게 KRX 상장 코드인지 확인한다."""

    return is_krx_code(clean_code(symbol))


def is_fund_code(code: str) -> bool:
    return bool(re.fullmatch(r"(?:K[0-9A-Z]{11}|KR[0-9A-Z]{10})", clean_code(code)))


def is_global_symbol_query(query: str) -> bool:
    cleaned = clean_code(query)
    return bool(re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", cleaned)) and not is_krx_code(cleaned) and not is_fund_code(cleaned)


def prefers_kis_quote(symbol: str) -> bool:
    """현재 심볼이 KIS REST 우선 조회 대상인지 판별한다."""

    return is_kis_enabled() and is_kis_domestic_symbol(symbol)


def supports_kis_history(symbol: str, period: str) -> bool:
    """기간 제한을 고려해 KIS 일봉을 우선 적용할지 판별한다."""

    return prefers_kis_quote(symbol) and period in {"1mo", "3mo"}


def resolve_kis_sector_label(symbol: Any) -> str | None:
    """국내 종목이면 KIS 마스터 기준 섹터명을 반환한다."""

    try:
        return resolve_kis_sector_name(symbol)
    except Exception:
        return None


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
        if yf is None or not hasattr(yf, "Search"):
            return []

        search = yf.Search(query, max_results=max(limit * 2, 10))
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for quote in search.quotes:
            symbol = str(quote.get("symbol") or "").strip().upper()
            name = quote.get("shortname") or quote.get("longname")
            if not name:
                continue
            match = re.match(rf"^({KRX_LISTED_CODE_PATTERN})\.(KS|KQ)$", symbol)
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


@st.cache_data(ttl=3600, max_entries=300, show_spinner=False)
def _search_products_cached(cleaned_query: str, limit: int = 8) -> list[dict[str, Any]]:
    """정규화된 검색어 기준으로 외부 상품 검색 결과를 캐시한다."""

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

    try:
        for item in search_master_products(cleaned_query, limit=limit):
            add_result(item)
        if has_exact_search_match(results, cleaned_query):
            return sorted(results, key=rank)[:limit]
    except Exception:
        pass

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


@st.cache_data(ttl=3600, max_entries=300, show_spinner=False)
def search_products(query: str, limit: int = 8) -> list[dict[str, Any]]:
    """여러 외부 경로를 순차 조회해 검색 후보를 반환한다."""

    cleaned_query = clean_code(query)
    if len(cleaned_query) < 2:
        return []

    try:
        normalized_limit = max(1, int(limit))
    except (TypeError, ValueError):
        normalized_limit = 8

    return _search_products_cached(cleaned_query, normalized_limit)


def _empty_intraday_snapshot(normalized: str) -> dict[str, Any]:
    """비어 있는 intraday 스냅샷 기본값을 반환한다."""

    return {
        "symbol": normalized,
        "series": [],
        "timeline": [],
        "current_price": None,
        "previous_close": None,
        "day_change_rate": None,
        "as_of": "",
        "currency": "KRW" if re.fullmatch(rf"{KRX_LISTED_CODE_PATTERN}\.(KS|KQ)", normalized) else "USD",
        "source": "",
    }


def _to_float_or_none(value: Any) -> float | None:
    """외부 시세 응답 값을 float로 변환하고 실패하면 None을 반환한다."""

    try:
        if value in (None, ""):
            return None
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _parse_naver_sise_json(text: str) -> list[list[Any]]:
    """Naver siseJson 응답의 JS 배열 문자열을 행 목록으로 변환한다."""

    raw_text = str(text or "").strip()
    if not raw_text:
        return []

    try:
        payload = ast.literal_eval(re.sub(r"\bnull\b", "None", raw_text))
    except (SyntaxError, ValueError):
        return []

    if not isinstance(payload, list):
        return []

    rows: list[list[Any]] = []
    for row in payload[1:]:
        if isinstance(row, list) and len(row) >= 5:
            rows.append(row)
    return rows


def _fetch_naver_sise_frame(symbol: str, *, timeframe: str, start_date: date, end_date: date) -> pd.DataFrame:
    """Naver 차트 JSON에서 국내 종목의 일봉/분봉 프레임을 가져온다."""

    code = clean_code(symbol)
    if not is_krx_code(code):
        return pd.DataFrame(columns=["datetime", "close", "symbol"])

    try:
        response = requests.get(
            "https://api.finance.naver.com/siseJson.naver",
            params={
                "symbol": code,
                "requestType": "1",
                "startTime": start_date.strftime("%Y%m%d"),
                "endTime": end_date.strftime("%Y%m%d"),
                "timeframe": timeframe,
            },
            headers=NAVER_HEADERS,
            timeout=8,
        )
    except Exception:
        return pd.DataFrame(columns=["datetime", "close", "symbol"])

    if response.status_code != 200:
        return pd.DataFrame(columns=["datetime", "close", "symbol"])

    parsed_rows = _parse_naver_sise_json(response.text)
    normalized_symbol = normalize_symbol(symbol)
    rows: list[dict[str, Any]] = []
    for row in parsed_rows:
        raw_datetime = str(row[0] or "").strip()
        close_value = _to_float_or_none(row[4])
        if close_value is None:
            continue

        is_minute_row = len(raw_datetime) >= 12
        date_format = "%Y%m%d%H%M" if is_minute_row else "%Y%m%d"
        parsed_datetime = pd.to_datetime(
            raw_datetime[:12 if is_minute_row else 8],
            format=date_format,
            errors="coerce",
        )
        if pd.isna(parsed_datetime):
            continue
        rows.append(
            {
                "datetime": parsed_datetime,
                "close": float(close_value),
                "symbol": normalized_symbol,
            }
        )

    if not rows:
        return pd.DataFrame(columns=["datetime", "close", "symbol"])

    frame = pd.DataFrame(rows)
    return frame.sort_values("datetime").drop_duplicates(subset=["datetime"], keep="last").reset_index(drop=True)


def _fetch_latest_price_from_naver(symbol: str) -> dict[str, Any]:
    """Naver 일봉 JSON으로 국내 종목의 최신 종가를 조회한다."""

    normalized = normalize_symbol(symbol)
    today = date.today()
    frame = _fetch_naver_sise_frame(
        normalized,
        timeframe="day",
        start_date=today - timedelta(days=10),
        end_date=today,
    )
    if frame.empty:
        raise ValueError(f"{normalized} Naver 가격 데이터가 비어 있습니다.")

    last_row = frame.iloc[-1]
    return {
        "symbol": normalized,
        "price": float(last_row["close"]),
        "as_of": pd.Timestamp(last_row["datetime"]).date().isoformat(),
        "source": "Naver",
    }


def _fetch_latest_price_from_yfinance(symbol: str) -> dict[str, Any]:
    """기존 yfinance 경로로 최신 종가를 조회한다. timeout을 강제한다."""

    normalized = normalize_symbol(symbol)
    if not normalized:
        raise ValueError("종목 코드를 입력해 주세요.")
    if yf is None:
        raise ValueError("가격 조회 모듈을 불러오지 못했습니다.")

    try:
        data = yf.download(
            normalized,
            period="5d",
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False,
            timeout=6,
        )
        if data.empty or "Close" not in data:
            raise ValueError(f"{normalized} 가격 데이터가 비어 있습니다.")

        closes = data["Close"].dropna().astype(float)
        if closes.empty:
            raise ValueError(f"{normalized} 가격을 가져오지 못했습니다.")

        last_price = float(closes.iloc[-1])
        last_index = closes.dropna().index[-1]
        return {
            "symbol": normalized,
            "price": last_price,
            "as_of": pd.Timestamp(last_index).date().isoformat(),
            "source": "Yahoo",
        }
    except Exception as exc:
        raise ValueError(f"{normalized} 가격 조회 실패: {exc}") from exc


def _fetch_intraday_price_snapshot_from_yfinance(symbol: str, interval: str = "5m") -> dict[str, Any]:
    """기존 yfinance 경로로 intraday 스냅샷을 조회한다."""

    normalized = normalize_symbol(symbol)
    if not normalized or yf is None:
        return _empty_intraday_snapshot(normalized)

    try:
        history = yf.Ticker(normalized).history(period="2d", interval=interval, auto_adjust=False)
    except Exception:
        return _empty_intraday_snapshot(normalized)

    closes = history.get("Close")
    if closes is None or closes.dropna().empty:
        return _empty_intraday_snapshot(normalized)

    frame = closes.dropna().reset_index()
    frame.columns = ["datetime", "close"]
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    frame["session_date"] = frame["datetime"].apply(lambda value: pd.Timestamp(value).date())
    latest_session_date = frame["session_date"].max()

    latest_session = frame.loc[frame["session_date"] == latest_session_date].copy()
    previous_session = frame.loc[frame["session_date"] < latest_session_date].copy()
    if latest_session.empty:
        return _empty_intraday_snapshot(normalized)

    latest_prices = latest_session["close"].astype(float)
    current_price = float(latest_prices.iloc[-1])
    previous_close = float(previous_session["close"].astype(float).iloc[-1]) if not previous_session.empty else None
    if previous_close and previous_close != 0:
        day_change_rate = ((current_price - previous_close) / previous_close) * 100
    else:
        first_price = float(latest_prices.iloc[0]) if not latest_prices.empty else 0.0
        day_change_rate = ((current_price - first_price) / first_price * 100) if first_price else 0.0

    as_of = pd.Timestamp(latest_session["datetime"].iloc[-1]).isoformat()
    timeline = [
        {
            "datetime": pd.Timestamp(row.datetime).isoformat(),
            "close": round(float(row.close), 4),
        }
        for row in latest_session.itertuples(index=False)
    ]
    return {
        "symbol": normalized,
        "series": [round(float(value), 4) for value in latest_prices.tolist()],
        "timeline": timeline,
        "current_price": round(current_price, 4),
        "previous_close": round(previous_close, 4) if previous_close is not None else None,
        "day_change_rate": round(float(day_change_rate), 4) if day_change_rate is not None else None,
        "as_of": as_of,
        "currency": "KRW" if re.fullmatch(rf"{KRX_LISTED_CODE_PATTERN}\.(KS|KQ)", normalized) else "USD",
        "source": "Yahoo",
    }


def _fetch_intraday_price_snapshot_from_naver(symbol: str) -> dict[str, Any]:
    """Naver 차트 JSON으로 국내 종목의 당일 분봉 스냅샷을 조회한다."""

    normalized = normalize_symbol(symbol)
    today = date.today()
    minute_frame = _fetch_naver_sise_frame(
        normalized,
        timeframe="minute",
        start_date=today - timedelta(days=7),
        end_date=today,
    )
    if minute_frame.empty:
        return _empty_intraday_snapshot(normalized)

    minute_frame["session_date"] = pd.to_datetime(minute_frame["datetime"]).dt.date
    latest_session_date = minute_frame["session_date"].max()
    latest_session = minute_frame.loc[minute_frame["session_date"] == latest_session_date].copy()
    if latest_session.empty:
        return _empty_intraday_snapshot(normalized)

    latest_prices = latest_session["close"].astype(float)
    current_price = float(latest_prices.iloc[-1])

    daily_frame = _fetch_naver_sise_frame(
        normalized,
        timeframe="day",
        start_date=today - timedelta(days=14),
        end_date=today,
    )
    previous_close: float | None = None
    if not daily_frame.empty:
        daily_frame["session_date"] = pd.to_datetime(daily_frame["datetime"]).dt.date
        previous_rows = daily_frame.loc[daily_frame["session_date"] < latest_session_date]
        if not previous_rows.empty:
            previous_close = float(previous_rows.iloc[-1]["close"])

    if previous_close and previous_close != 0:
        day_change_rate = ((current_price - previous_close) / previous_close) * 100
    else:
        first_price = float(latest_prices.iloc[0]) if not latest_prices.empty else 0.0
        day_change_rate = ((current_price - first_price) / first_price * 100) if first_price else 0.0

    timeline = [
        {
            "datetime": pd.Timestamp(row.datetime).isoformat(),
            "close": round(float(row.close), 4),
        }
        for row in latest_session.itertuples(index=False)
    ]
    return {
        "symbol": normalized,
        "series": [round(float(value), 4) for value in latest_prices.tolist()],
        "timeline": timeline,
        "current_price": round(current_price, 4),
        "previous_close": round(previous_close, 4) if previous_close is not None else None,
        "day_change_rate": round(float(day_change_rate), 4),
        "as_of": pd.Timestamp(latest_session["datetime"].iloc[-1]).isoformat(),
        "currency": "KRW",
        "source": "Naver",
    }


def _fetch_price_history_from_yfinance(symbol: str, period: str = "6mo") -> pd.DataFrame:
    """기존 yfinance 경로로 기간별 종가를 조회한다."""

    normalized = normalize_symbol(symbol)
    if not normalized or yf is None:
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


def _fetch_price_history_range_from_yfinance(symbol: str, *, start_date: date, end_date: date) -> pd.DataFrame:
    """yfinance에서 지정 날짜 범위의 종가 이력을 조회한다."""

    normalized = normalize_symbol(symbol)
    if not normalized or yf is None:
        return pd.DataFrame(columns=["date", "close", "symbol"])

    history = yf.Ticker(normalized).history(
        start=start_date.isoformat(),
        end=(end_date + timedelta(days=1)).isoformat(),
        auto_adjust=False,
    )
    closes = history.get("Close")
    if closes is None or closes.dropna().empty:
        return pd.DataFrame(columns=["date", "close", "symbol"])

    frame = closes.dropna().reset_index()
    frame.columns = ["date", "close"]
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame["symbol"] = normalized
    return frame


def _fetch_price_history_from_naver(symbol: str, period: str = "6mo") -> pd.DataFrame:
    """Naver 차트 JSON으로 국내 종목의 일봉 종가 이력을 조회한다."""

    normalized = normalize_symbol(symbol)
    start_date, end_date = _history_period_range(period)
    frame = _fetch_naver_sise_frame(
        normalized,
        timeframe="day",
        start_date=start_date,
        end_date=end_date,
    )
    if frame.empty:
        return pd.DataFrame(columns=["date", "close", "symbol"])

    result = frame.copy()
    result["date"] = pd.to_datetime(result["datetime"]).dt.date
    result["symbol"] = normalized
    return result[["date", "close", "symbol"]].sort_values("date").reset_index(drop=True)


def _fetch_price_history_range_from_naver(symbol: str, *, start_date: date, end_date: date) -> pd.DataFrame:
    """Naver 차트 JSON으로 지정 날짜 범위의 국내 종가 이력을 조회한다."""

    normalized = normalize_symbol(symbol)
    frame = _fetch_naver_sise_frame(
        normalized,
        timeframe="day",
        start_date=start_date,
        end_date=end_date,
    )
    if frame.empty:
        return pd.DataFrame(columns=["date", "close", "symbol"])

    result = frame.copy()
    result["date"] = pd.to_datetime(result["datetime"]).dt.date
    result["symbol"] = normalized
    return result[["date", "close", "symbol"]].sort_values("date").reset_index(drop=True)


def _fetch_latest_price_from_kis(symbol: str) -> dict[str, Any]:
    """KIS REST로 국내 현재가를 조회한다."""

    client = KisApiClient()
    payload = client.get_domestic_latest_price(symbol)
    return {
        "symbol": normalize_symbol(symbol),
        "price": float(payload["price"]),
        "as_of": str(payload["as_of"]),
        "source": "KIS REST",
    }


def _fetch_intraday_price_snapshot_from_kis(symbol: str) -> dict[str, Any]:
    """KIS REST로 국내 intraday 스냅샷을 조회한다."""

    client = KisApiClient()
    payload = client.get_domestic_intraday_snapshot(symbol)
    return {
        "symbol": normalize_symbol(symbol),
        "series": payload.get("series") or [],
        "timeline": payload.get("timeline") or [],
        "current_price": payload.get("current_price"),
        "previous_close": payload.get("previous_close"),
        "day_change_rate": payload.get("day_change_rate"),
        "as_of": payload.get("as_of") or "",
        "currency": payload.get("currency") or "KRW",
        "source": "KIS REST",
    }


def _history_period_range(period: str) -> tuple[date, date]:
    """yfinance 스타일 기간 문자열을 시작/종료 날짜로 바꾼다."""

    end_date = date.today()
    days_by_period = {
        "1mo": 31,
        "3mo": 93,
        "6mo": 186,
        "1y": 366,
        "2y": 732,
        "5d": 7,
    }
    days = days_by_period.get(str(period or "").strip().lower(), 186)
    return end_date - timedelta(days=days), end_date


def _fetch_price_history_from_kis(symbol: str, period: str = "6mo") -> pd.DataFrame:
    """KIS REST로 국내 일봉 종가를 조회한다."""

    start_date, end_date = _history_period_range(period)
    client = KisApiClient()
    frame = client.get_domestic_daily_history(
        symbol,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )
    if frame.empty:
        return frame
    frame["symbol"] = normalize_symbol(symbol)
    return frame


def _fetch_price_history_range_from_kis(symbol: str, *, start_date: date, end_date: date) -> pd.DataFrame:
    """KIS REST로 지정 날짜 범위의 국내 일봉 종가를 조회한다."""

    client = KisApiClient()
    frame = client.get_domestic_daily_history(
        symbol,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )
    if frame.empty:
        return pd.DataFrame(columns=["date", "close", "symbol"])
    frame["symbol"] = normalize_symbol(symbol)
    return frame


@st.cache_data(ttl=900, show_spinner=False)
def fetch_latest_price(symbol: str) -> dict[str, Any]:
    """최신 가격을 KIS 우선 provider 구조로 조회한다."""

    normalized = normalize_symbol(symbol)
    if not normalized:
        raise ValueError("종목 코드를 입력해 주세요.")

    if prefers_kis_quote(normalized):
        try:
            return _fetch_latest_price_from_kis(normalized)
        except Exception:
            pass
    if is_krx_symbol(normalized):
        try:
            return _fetch_latest_price_from_naver(normalized)
        except Exception:
            pass
    return _fetch_latest_price_from_yfinance(normalized)


@st.cache_data(ttl=120, show_spinner=False)
def fetch_intraday_price_snapshot(symbol: str, interval: str = "5m") -> dict[str, Any]:
    """가장 최근 거래일 intraday 가격 흐름과 요약 정보를 반환한다."""

    normalized = normalize_symbol(symbol)
    if not normalized:
        return _empty_intraday_snapshot(normalized)

    if is_krx_symbol(normalized):
        try:
            naver_snapshot = _fetch_intraday_price_snapshot_from_naver(normalized)
        except Exception:
            naver_snapshot = _empty_intraday_snapshot(normalized)
        if naver_snapshot.get("timeline") or naver_snapshot.get("series"):
            return naver_snapshot

    if prefers_kis_quote(normalized):
        try:
            return _fetch_intraday_price_snapshot_from_kis(normalized)
        except Exception:
            pass
    return _fetch_intraday_price_snapshot_from_yfinance(normalized, interval=interval)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_price_history(symbol: str, period: str = "6mo") -> pd.DataFrame:
    """기간별 종가 이력을 KIS 우선 provider 구조로 조회한다."""

    normalized = normalize_symbol(symbol)
    if not normalized:
        return pd.DataFrame(columns=["date", "close", "symbol"])

    if supports_kis_history(normalized, period):
        try:
            frame = _fetch_price_history_from_kis(normalized, period=period)
        except Exception:
            frame = pd.DataFrame(columns=["date", "close", "symbol"])
        if not frame.empty:
            return frame
    if is_krx_symbol(normalized):
        frame = _fetch_price_history_from_naver(normalized, period=period)
        if not frame.empty:
            return frame
    return _fetch_price_history_from_yfinance(normalized, period=period)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_price_history_range(symbol: str, *, start_date: date, end_date: date) -> pd.DataFrame:
    """지정 날짜 범위의 종가 이력을 KIS/Naver/yfinance 순서로 조회한다."""

    normalized = normalize_symbol(symbol)
    if not normalized or end_date < start_date:
        return pd.DataFrame(columns=["date", "close", "symbol"])

    if prefers_kis_quote(normalized):
        try:
            frame = _fetch_price_history_range_from_kis(normalized, start_date=start_date, end_date=end_date)
        except Exception:
            frame = pd.DataFrame(columns=["date", "close", "symbol"])
        if not frame.empty:
            return frame

    if is_krx_symbol(normalized):
        try:
            frame = _fetch_price_history_range_from_naver(normalized, start_date=start_date, end_date=end_date)
        except Exception:
            frame = pd.DataFrame(columns=["date", "close", "symbol"])
        if not frame.empty:
            return frame

    return _fetch_price_history_range_from_yfinance(normalized, start_date=start_date, end_date=end_date)

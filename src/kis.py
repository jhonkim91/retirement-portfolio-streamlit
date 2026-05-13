from __future__ import annotations

import json
import os
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
import requests

try:
    import streamlit as st
except ImportError:  # pragma: no cover - worker/script 환경 fallback
    st = None


DEFAULT_KIS_ENV = "prod"
KIS_ENV_ALIASES = {
    "prod": "prod",
    "production": "prod",
    "real": "prod",
    "paper": "paper",
    "demo": "paper",
    "mock": "paper",
    "test": "paper",
}
KIS_REST_BASE_URLS = {
    "prod": "https://openapi.koreainvestment.com:9443",
    "paper": "https://openapivts.koreainvestment.com:29443",
}
KIS_WS_URLS = {
    "prod": "ws://ops.koreainvestment.com:21000/tryitout",
    "paper": "ws://ops.koreainvestment.com:21000/tryitout",
}
KST_TIMEZONE = timezone(timedelta(hours=9))
KIS_REGULAR_SESSION_OPEN = "090000"
KIS_REGULAR_SESSION_CLOSE = "153000"
KIS_MASTER_CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "kis_cache"
KIS_MASTER_CACHE_TTL_SECONDS = 24 * 60 * 60
KIS_MASTER_URLS = {
    "kospi": "https://new.real.download.dws.co.kr/common/master/kospi_code.mst.zip",
    "kosdaq": "https://new.real.download.dws.co.kr/common/master/kosdaq_code.mst.zip",
    "idxcode": "https://new.real.download.dws.co.kr/common/master/idxcode.mst.zip",
}
KIS_DOMESTIC_PRICE_TR_ID = "FHKST01010100"
KIS_DOMESTIC_DAILY_TR_ID = "FHKST03010100"
KIS_DOMESTIC_INTRADAY_TR_ID = "FHKST03010200"
KIS_WS_APPROVAL_PATH = "/oauth2/Approval"
KIS_ACCESS_TOKEN_PATH = "/oauth2/tokenP"
KIS_DOMESTIC_PRICE_PATH = "/uapi/domestic-stock/v1/quotations/inquire-price"
KIS_DOMESTIC_DAILY_PRICE_PATH = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
KIS_DOMESTIC_INTRADAY_PRICE_PATH = "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
KIS_WS_QUOTE_TR_ID = "H0STCNT0"
KIS_WS_QUOTE_COLUMNS = [
    "mksc_shrn_iscd",
    "stck_cntg_hour",
    "stck_prpr",
    "prdy_vrss_sign",
    "prdy_vrss",
    "prdy_ctrt",
    "wghn_avrg_stck_prc",
    "stck_oprc",
    "stck_hgpr",
    "stck_lwpr",
    "askp1",
    "bidp1",
    "cntg_vol",
    "acml_vol",
    "acml_tr_pbmn",
    "seln_cntg_csnu",
    "shnu_cntg_csnu",
    "ntby_cntg_csnu",
    "cttr",
    "seln_cntg_smtn",
    "shnu_cntg_smtn",
    "ccld_dvsn",
    "shnu_rate",
    "prdy_vol_vrss_acml_vol_rate",
    "oprc_hour",
    "oprc_vrss_prpr_sign",
    "oprc_vrss_prpr",
    "hgpr_hour",
    "hgpr_vrss_prpr_sign",
    "hgpr_vrss_prpr",
    "lwpr_hour",
    "lwpr_vrss_prpr_sign",
    "lwpr_vrss_prpr",
    "bsop_date",
    "new_mkop_cls_code",
    "trht_yn",
    "askp_rsqn1",
    "bidp_rsqn1",
    "total_askp_rsqn",
    "total_bidp_rsqn",
    "vol_tnrt",
    "prdy_smns_hour_acml_vol",
    "prdy_smns_hour_acml_vol_rate",
    "hour_cls_code",
    "mrkt_trtm_cls_code",
    "vi_stnd_prc",
]
KOSPI_MASTER_WIDTHS = [
    2,
    1,
    4,
    4,
    4,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    9,
    5,
    5,
    1,
    1,
    1,
    2,
    1,
    1,
    1,
    2,
    2,
    2,
    3,
    1,
    3,
    12,
    12,
    8,
    15,
    21,
    2,
    7,
    1,
    1,
    1,
    1,
    1,
    9,
    9,
    9,
    5,
    9,
    8,
    9,
    3,
    1,
    1,
    1,
]
KOSPI_MASTER_FIELDS = [
    "group_code",
    "market_cap_scale",
    "sector_large_code",
    "sector_middle_code",
    "sector_small_code",
    "manufacturing_flag",
    "low_liquidity_flag",
    "governance_index_flag",
    "kospi200_sector_flag",
    "kospi100_flag",
    "kospi50_flag",
    "krx_flag",
    "etp_flag",
    "elw_issue_flag",
    "krx100_flag",
    "krx_auto_flag",
    "krx_semiconductor_flag",
    "krx_bio_flag",
    "krx_bank_flag",
    "spac_flag",
    "krx_energy_chem_flag",
    "krx_steel_flag",
    "overheat_flag",
    "krx_media_flag",
    "krx_construction_flag",
    "reserved_flag",
    "krx_securities_flag",
    "krx_ship_flag",
    "krx_insurance_flag",
    "krx_transport_flag",
    "sri_flag",
    "base_price",
    "regular_lot_size",
    "after_hours_lot_size",
    "trade_stop_flag",
    "cleanup_trade_flag",
    "managed_flag",
    "market_warning_code",
    "warning_notice_flag",
    "disclosure_issue_flag",
    "backdoor_listing_flag",
    "lock_code",
    "par_value_change_code",
    "capital_increase_code",
    "margin_rate",
    "credit_order_flag",
    "credit_period",
    "previous_volume",
    "par_value",
    "listed_date",
    "listed_shares",
    "capital",
    "settlement_month",
    "ipo_price",
    "preferred_stock_flag",
    "short_sale_overheat_flag",
    "abnormal_surge_flag",
    "krx300_flag",
    "kospi_flag",
    "revenue",
    "operating_income",
    "ordinary_income",
    "net_income",
    "roe",
    "financial_base_ym",
    "market_cap",
    "group_company_code",
    "credit_limit_exceeded_flag",
    "collateral_loan_flag",
    "short_available_flag",
]
KOSDAQ_MASTER_WIDTHS = [
    2,
    1,
    4,
    4,
    4,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    9,
    5,
    5,
    1,
    1,
    1,
    2,
    1,
    1,
    1,
    2,
    2,
    2,
    3,
    1,
    3,
    12,
    12,
    8,
    15,
    21,
    2,
    7,
    1,
    1,
    1,
    1,
    9,
    9,
    9,
    5,
    9,
    8,
    9,
    3,
    1,
    1,
    1,
]
KOSDAQ_MASTER_FIELDS = [
    "group_code",
    "market_cap_scale",
    "sector_large_code",
    "sector_middle_code",
    "sector_small_code",
    "venture_flag",
    "low_liquidity_flag",
    "krx_flag",
    "etp_flag",
    "krx100_flag",
    "krx_auto_flag",
    "krx_semiconductor_flag",
    "krx_bio_flag",
    "krx_bank_flag",
    "spac_flag",
    "krx_energy_chem_flag",
    "krx_steel_flag",
    "overheat_flag",
    "krx_media_flag",
    "krx_construction_flag",
    "investment_caution_flag",
    "krx_securities_flag",
    "krx_ship_flag",
    "krx_insurance_flag",
    "krx_transport_flag",
    "kosdaq150_flag",
    "base_price",
    "regular_lot_size",
    "after_hours_lot_size",
    "trade_stop_flag",
    "cleanup_trade_flag",
    "managed_flag",
    "market_warning_code",
    "warning_notice_flag",
    "disclosure_issue_flag",
    "backdoor_listing_flag",
    "lock_code",
    "par_value_change_code",
    "capital_increase_code",
    "margin_rate",
    "credit_order_flag",
    "credit_period",
    "previous_volume",
    "par_value",
    "listed_date",
    "listed_shares",
    "capital",
    "settlement_month",
    "ipo_price",
    "preferred_stock_flag",
    "short_sale_overheat_flag",
    "abnormal_surge_flag",
    "krx300_flag",
    "revenue",
    "operating_income",
    "ordinary_income",
    "net_income",
    "roe",
    "financial_base_ym",
    "market_cap",
    "group_company_code",
    "credit_limit_exceeded_flag",
    "collateral_loan_flag",
    "short_available_flag",
]
SECTOR_FLAG_LABELS = (
    ("krx_semiconductor_flag", "반도체"),
    ("krx_bio_flag", "바이오"),
    ("krx_bank_flag", "은행"),
    ("krx_energy_chem_flag", "에너지·화학"),
    ("krx_steel_flag", "철강"),
    ("krx_media_flag", "미디어·통신"),
    ("krx_construction_flag", "건설"),
    ("krx_securities_flag", "증권"),
    ("krx_ship_flag", "선박"),
    ("krx_insurance_flag", "보험"),
    ("krx_transport_flag", "운송"),
    ("krx_auto_flag", "자동차"),
)
_ACCESS_TOKEN_CACHE: dict[str, tuple[str, float]] = {}
_APPROVAL_KEY_CACHE: dict[str, tuple[str, float]] = {}
_MASTER_RECORDS_CACHE: tuple[float, dict[str, dict[str, Any]]] | None = None
_SECTOR_LOOKUP_CACHE: tuple[float, dict[str, str]] | None = None


def _read_config_value(name: str, default: str = "") -> str:
    """환경 변수와 Streamlit secrets에서 설정값을 읽는다."""

    value = str(os.getenv(name, "")).strip()
    if value:
        return value
    if st is not None:
        try:
            secret_value = st.secrets.get(name)
        except Exception:
            secret_value = None
        if secret_value not in (None, ""):
            return str(secret_value).strip()
    return str(default).strip()


def normalize_kis_env(value: str | None = None) -> str:
    """KIS 환경 값을 prod 또는 paper로 정규화한다."""

    normalized = str(value or _read_config_value("KIS_ENV", DEFAULT_KIS_ENV)).strip().lower()
    return KIS_ENV_ALIASES.get(normalized, DEFAULT_KIS_ENV)


def kis_settings() -> dict[str, Any]:
    """KIS 연결 가능 여부와 런타임 구성을 반환한다."""

    app_key = _read_config_value("KIS_APP_KEY")
    app_secret = _read_config_value("KIS_APP_SECRET")
    env_name = normalize_kis_env()
    return {
        "enabled": bool(app_key and app_secret),
        "app_key_present": bool(app_key),
        "app_secret_present": bool(app_secret),
        "env": env_name,
        "rest_base_url": KIS_REST_BASE_URLS[env_name],
        "ws_url": KIS_WS_URLS[env_name],
        "missing_config": [name for name, value in (("KIS_APP_KEY", app_key), ("KIS_APP_SECRET", app_secret)) if not value],
    }


def is_kis_enabled() -> bool:
    """KIS REST 시세를 사용할 수 있는지 반환한다."""

    return bool(kis_settings()["enabled"])


def normalize_domestic_code(symbol: Any) -> str:
    """KIS 국내 종목 REST에 전달할 6자리 종목 코드를 반환한다."""

    text = str(symbol or "").strip().upper()
    if text.endswith(".KS") or text.endswith(".KQ"):
        text = text[:-3]
    if text.isdigit() and len(text) < 6:
        text = text.zfill(6)
    return text


def is_kis_domestic_symbol(symbol: Any) -> bool:
    """KIS 국내 시세로 조회 가능한 KRX 코드인지 판별한다."""

    code = normalize_domestic_code(symbol)
    return len(code) == 6 and code.isdigit()


def _domestic_intraday_query_time(now: datetime | None = None) -> str:
    """KIS 국내 분봉 조회 기준 시각을 정규 장 시간 안으로 제한한다."""

    current = now or datetime.now(tz=KST_TIMEZONE)
    if current.tzinfo is None:
        current = current.replace(tzinfo=KST_TIMEZONE)
    else:
        current = current.astimezone(KST_TIMEZONE)

    raw_time = current.strftime("%H%M%S")
    if raw_time < KIS_REGULAR_SESSION_OPEN:
        return KIS_REGULAR_SESSION_OPEN
    if raw_time > KIS_REGULAR_SESSION_CLOSE:
        return KIS_REGULAR_SESSION_CLOSE
    return raw_time


def _cache_path(file_name: str) -> Path:
    """KIS 캐시 파일 경로를 반환한다."""

    KIS_MASTER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return KIS_MASTER_CACHE_DIR / file_name


def _load_json_cache(file_name: str, *, ttl_seconds: int) -> Any | None:
    """TTL 내 JSON 캐시를 읽는다."""

    path = _cache_path(file_name)
    if not path.exists():
        return None
    age = time.time() - path.stat().st_mtime
    if age > ttl_seconds:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_json_cache(file_name: str, payload: Any) -> None:
    """JSON 캐시 파일을 저장한다."""

    path = _cache_path(file_name)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _download_master_text(url: str, member_name: str) -> str:
    """KIS 마스터 ZIP을 내려받아 텍스트로 반환한다."""

    response = requests.get(url, timeout=20)
    response.raise_for_status()
    with zipfile.ZipFile(BytesIO(response.content)) as archive:
        return archive.read(member_name).decode("cp949")


def _parse_fixed_width_tail(raw_tail: str, widths: list[int], fields: list[str]) -> dict[str, str]:
    """고정폭 문자열 꼬리를 필드 딕셔너리로 변환한다."""

    cursor = 0
    parsed: dict[str, str] = {}
    for field_name, width in zip(fields, widths):
        parsed[field_name] = raw_tail[cursor : cursor + width].strip()
        cursor += width
    return parsed


def _parse_master_records(
    *,
    raw_text: str,
    market_name: str,
    tail_size: int,
    widths: list[int],
    fields: list[str],
) -> dict[str, dict[str, Any]]:
    """KOSPI/KOSDAQ 마스터 본문을 코드 기준 딕셔너리로 파싱한다."""

    records: dict[str, dict[str, Any]] = {}
    for line in raw_text.splitlines():
        if not line.strip():
            continue
        head = line[:-tail_size]
        tail = line[-tail_size:]
        code = head[:9].strip()
        standard_code = head[9:21].strip()
        name = head[21:].strip()
        if not code or not name:
            continue
        details = _parse_fixed_width_tail(tail, widths, fields)
        records[code] = {
            "code": code,
            "standard_code": standard_code,
            "name": name,
            "market": market_name,
            "symbol": f"{code}.KS" if market_name == "KOSPI" else f"{code}.KQ",
            **details,
        }
    return records


def load_sector_lookup(*, force_refresh: bool = False) -> dict[str, str]:
    """업종 코드 마스터를 조회해 코드별 업종명을 반환한다."""

    global _SECTOR_LOOKUP_CACHE
    if not force_refresh and _SECTOR_LOOKUP_CACHE is not None:
        cached_at, cached_payload = _SECTOR_LOOKUP_CACHE
        if time.time() - cached_at <= KIS_MASTER_CACHE_TTL_SECONDS:
            return cached_payload

    if not force_refresh:
        cached_payload = _load_json_cache("idxcode.json", ttl_seconds=KIS_MASTER_CACHE_TTL_SECONDS)
        if isinstance(cached_payload, dict):
            _SECTOR_LOOKUP_CACHE = (time.time(), cached_payload)
            return cached_payload

    raw_text = _download_master_text(KIS_MASTER_URLS["idxcode"], "idxcode.mst")
    payload = {line[:5].strip(): line[5:].strip() for line in raw_text.splitlines() if line[:5].strip()}
    _save_json_cache("idxcode.json", payload)
    _SECTOR_LOOKUP_CACHE = (time.time(), payload)
    return payload


def _sector_name_from_codes(record: dict[str, Any], sector_lookup: dict[str, str]) -> str:
    """업종 코드와 보조 플래그를 이용해 표시용 섹터명을 고른다."""

    for code_key in ("sector_small_code", "sector_middle_code", "sector_large_code"):
        raw_code = str(record.get(code_key) or "").strip()
        if not raw_code or set(raw_code) == {"0"}:
            continue
        sector_name = sector_lookup.get(raw_code.zfill(5))
        if sector_name:
            return sector_name

    for field_name, sector_name in SECTOR_FLAG_LABELS:
        if str(record.get(field_name) or "").strip().upper() == "Y":
            return sector_name
    return ""


def load_master_records(*, force_refresh: bool = False) -> dict[str, dict[str, Any]]:
    """KOSPI/KOSDAQ 종목 마스터를 통합해 코드별 레코드를 반환한다."""

    global _MASTER_RECORDS_CACHE
    if not force_refresh and _MASTER_RECORDS_CACHE is not None:
        cached_at, cached_payload = _MASTER_RECORDS_CACHE
        if time.time() - cached_at <= KIS_MASTER_CACHE_TTL_SECONDS:
            return cached_payload

    if not force_refresh:
        cached_payload = _load_json_cache("master_records.json", ttl_seconds=KIS_MASTER_CACHE_TTL_SECONDS)
        if isinstance(cached_payload, dict):
            _MASTER_RECORDS_CACHE = (time.time(), cached_payload)
            return cached_payload

    sector_lookup = load_sector_lookup(force_refresh=force_refresh)
    kospi_text = _download_master_text(KIS_MASTER_URLS["kospi"], "kospi_code.mst")
    kosdaq_text = _download_master_text(KIS_MASTER_URLS["kosdaq"], "kosdaq_code.mst")
    records = {}
    records.update(
        _parse_master_records(
            raw_text=kospi_text,
            market_name="KOSPI",
            tail_size=sum(KOSPI_MASTER_WIDTHS),
            widths=KOSPI_MASTER_WIDTHS,
            fields=KOSPI_MASTER_FIELDS,
        )
    )
    records.update(
        _parse_master_records(
            raw_text=kosdaq_text,
            market_name="KOSDAQ",
            tail_size=sum(KOSDAQ_MASTER_WIDTHS),
            widths=KOSDAQ_MASTER_WIDTHS,
            fields=KOSDAQ_MASTER_FIELDS,
        )
    )
    for record in records.values():
        record["sector_name"] = _sector_name_from_codes(record, sector_lookup)
    _save_json_cache("master_records.json", records)
    _MASTER_RECORDS_CACHE = (time.time(), records)
    return records


def get_master_record(symbol: Any) -> dict[str, Any] | None:
    """국내 종목 코드에 대응하는 KIS 마스터 레코드를 반환한다."""

    code = normalize_domestic_code(symbol)
    if not is_kis_domestic_symbol(code):
        return None
    try:
        return load_master_records().get(code)
    except Exception:
        return None


def resolve_sector_name(symbol: Any) -> str | None:
    """국내 종목의 KIS 기준 섹터명을 반환한다."""

    record = get_master_record(symbol)
    if not record:
        return None
    sector_name = str(record.get("sector_name") or "").strip()
    return sector_name or None


def search_master_products(query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    """KIS 종목 마스터에서 국내 종목/ETF를 검색한다."""

    cleaned_query = str(query or "").strip().upper()
    normalized_query = "".join(cleaned_query.split())
    if len(normalized_query) < 2:
        return []

    try:
        records = load_master_records()
    except Exception:
        return []

    rows: list[dict[str, Any]] = []
    for record in records.values():
        code = str(record.get("code") or "").strip().upper()
        name = str(record.get("name") or "").strip()
        normalized_name = "".join(name.upper().split())
        if normalized_query not in normalized_name and normalized_query not in code:
            continue
        group_code = str(record.get("group_code") or "").strip().upper()
        item_type = "ETF" if group_code == "EF" or str(record.get("etp_flag") or "").strip() else "stock/ETF"
        rows.append(
            {
                "name": name,
                "code": code,
                "symbol": record.get("symbol") or code,
                "exchange": "KRX",
                "type": item_type,
                "source": "KIS Master",
            }
        )
    rows.sort(key=lambda item: (0 if str(item["code"]).upper() == cleaned_query else 1, str(item["name"])))
    return rows[:limit]


@dataclass
class KisCredentials:
    """KIS 인증 정보 묶음."""

    app_key: str
    app_secret: str
    env: str = DEFAULT_KIS_ENV


class KisApiClient:
    """KIS REST 및 WebSocket 승인 키를 다루는 최소 클라이언트."""

    def __init__(self, credentials: KisCredentials | None = None) -> None:
        settings = kis_settings()
        creds = credentials or KisCredentials(
            app_key=_read_config_value("KIS_APP_KEY"),
            app_secret=_read_config_value("KIS_APP_SECRET"),
            env=settings["env"],
        )
        self.credentials = creds
        self.rest_base_url = KIS_REST_BASE_URLS[normalize_kis_env(creds.env)]
        self.ws_url = KIS_WS_URLS[normalize_kis_env(creds.env)]

    def _require_credentials(self) -> None:
        if not self.credentials.app_key or not self.credentials.app_secret:
            raise ValueError("KIS_APP_KEY 와 KIS_APP_SECRET 을 설정해 주세요.")

    def _token_cache_key(self) -> str:
        return f"{self.credentials.env}:{self.credentials.app_key[:8]}"

    def get_access_token(self) -> str:
        """KIS 액세스 토큰을 가져온다."""

        self._require_credentials()
        cache_key = self._token_cache_key()
        cached = _ACCESS_TOKEN_CACHE.get(cache_key)
        if cached and cached[1] > time.time() + 60:
            return cached[0]

        response = requests.post(
            f"{self.rest_base_url}{KIS_ACCESS_TOKEN_PATH}",
            headers={"Content-Type": "application/json"},
            json={
                "grant_type": "client_credentials",
                "appkey": self.credentials.app_key,
                "appsecret": self.credentials.app_secret,
            },
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        access_token = str(payload.get("access_token") or "").strip()
        if not access_token:
            raise ValueError("KIS access token 응답이 비어 있습니다.")
        expires_in = int(float(payload.get("expires_in") or 86400))
        _ACCESS_TOKEN_CACHE[cache_key] = (access_token, time.time() + expires_in)
        return access_token

    def get_approval_key(self) -> str:
        """KIS WebSocket 승인 키를 가져온다."""

        self._require_credentials()
        cache_key = self._token_cache_key()
        cached = _APPROVAL_KEY_CACHE.get(cache_key)
        if cached and cached[1] > time.time() + 60:
            return cached[0]

        response = requests.post(
            f"{self.rest_base_url}{KIS_WS_APPROVAL_PATH}",
            headers={"Content-Type": "application/json"},
            json={
                "grant_type": "client_credentials",
                "appkey": self.credentials.app_key,
                "secretkey": self.credentials.app_secret,
            },
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        approval_key = str(payload.get("approval_key") or "").strip()
        if not approval_key:
            raise ValueError("KIS approval key 응답이 비어 있습니다.")
        _APPROVAL_KEY_CACHE[cache_key] = (approval_key, time.time() + 24 * 60 * 60)
        return approval_key

    def _request(
        self,
        *,
        method: str,
        path: str,
        tr_id: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """KIS REST API를 호출하고 JSON 응답을 반환한다."""

        response = requests.request(
            method=method,
            url=f"{self.rest_base_url}{path}",
            params=params,
            json=json_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.get_access_token()}",
                "appkey": self.credentials.app_key,
                "appsecret": self.credentials.app_secret,
                "custtype": "P",
                "tr_id": tr_id,
            },
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        rt_cd = str(payload.get("rt_cd") or "").strip()
        if rt_cd and rt_cd != "0":
            message = str(payload.get("msg1") or payload.get("msg_cd") or "KIS API 오류").strip()
            raise ValueError(message)
        return payload

    def get_domestic_latest_price(self, symbol: Any) -> dict[str, Any]:
        """국내 종목 현재가와 기준 시각을 반환한다."""

        code = normalize_domestic_code(symbol)
        if not is_kis_domestic_symbol(code):
            raise ValueError("KIS 국내 시세는 6자리 KRX 종목코드만 지원합니다.")
        payload = self._request(
            method="GET",
            path=KIS_DOMESTIC_PRICE_PATH,
            tr_id=KIS_DOMESTIC_PRICE_TR_ID,
            params={
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": code,
            },
        )
        output = payload.get("output") or {}
        price = _safe_float(output.get("stck_prpr"))
        if price is None:
            raise ValueError(f"{code} KIS 현재가를 해석하지 못했습니다.")
        quote_date = str(output.get("stck_bsop_date") or datetime.now().strftime("%Y%m%d")).strip()
        quote_time = str(output.get("stck_cntg_hour") or "").strip()
        return {
            "symbol": code,
            "price": float(price),
            "as_of": _compose_quote_timestamp(quote_date, quote_time),
            "source": "KIS REST",
        }

    def get_domestic_intraday_snapshot(self, symbol: Any) -> dict[str, Any]:
        """국내 종목 장중 스냅샷을 반환한다."""

        code = normalize_domestic_code(symbol)
        if not is_kis_domestic_symbol(code):
            raise ValueError("KIS 국내 분봉은 6자리 KRX 종목코드만 지원합니다.")
        payload = self._request(
            method="GET",
            path=KIS_DOMESTIC_INTRADAY_PRICE_PATH,
            tr_id=KIS_DOMESTIC_INTRADAY_TR_ID,
            params={
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": code,
                "FID_INPUT_HOUR_1": _domestic_intraday_query_time(),
                "FID_PW_DATA_INCU_YN": "Y",
                "FID_ETC_CLS_CODE": "",
            },
        )
        output1 = payload.get("output1") or {}
        output2 = payload.get("output2") or []
        if not isinstance(output2, list) or not output2:
            raise ValueError(f"{code} KIS 분봉 데이터가 없습니다.")

        frame = pd.DataFrame(output2)
        time_column = "stck_cntg_hour" if "stck_cntg_hour" in frame.columns else "stck_bsop_hour"
        price_column = "stck_prpr" if "stck_prpr" in frame.columns else "stck_cntg_pric"
        if time_column not in frame.columns or price_column not in frame.columns:
            raise ValueError(f"{code} KIS 분봉 응답 컬럼이 예상과 다릅니다.")

        frame[price_column] = pd.to_numeric(frame[price_column], errors="coerce")
        frame = frame.dropna(subset=[price_column]).copy()
        if frame.empty:
            raise ValueError(f"{code} KIS 분봉 가격 데이터가 없습니다.")
        frame[time_column] = frame[time_column].astype(str).str.zfill(6)
        frame = frame.sort_values(time_column)
        current_price = float(frame[price_column].iloc[-1])
        previous_close = _safe_float(output1.get("stck_sdpr")) or _derive_previous_close_from_change(
            current_price=current_price,
            day_change_rate=_safe_float(output1.get("prdy_ctrt")),
        )
        day_change_rate = _safe_float(output1.get("prdy_ctrt"))
        if day_change_rate is None and previous_close:
            day_change_rate = (current_price - previous_close) / previous_close * 100
        quote_date = str(output1.get("stck_bsop_date") or datetime.now().strftime("%Y%m%d")).strip()
        timeline = [
            {
                "datetime": _compose_quote_timestamp(quote_date, str(row[time_column])),
                "close": round(float(row[price_column]), 4),
            }
            for _, row in frame.iterrows()
        ]
        return {
            "symbol": code,
            "series": [round(float(value), 4) for value in frame[price_column].tolist()],
            "timeline": timeline,
            "current_price": round(current_price, 4),
            "previous_close": round(previous_close, 4) if previous_close is not None else None,
            "day_change_rate": round(float(day_change_rate), 4) if day_change_rate is not None else None,
            "as_of": _compose_quote_timestamp(quote_date, str(frame[time_column].iloc[-1])),
            "currency": "KRW",
            "source": "KIS REST",
        }

    def get_domestic_daily_history(self, symbol: Any, *, start_date: str, end_date: str) -> pd.DataFrame:
        """국내 종목 일별 종가 이력을 반환한다."""

        code = normalize_domestic_code(symbol)
        if not is_kis_domestic_symbol(code):
            raise ValueError("KIS 국내 일봉은 6자리 KRX 종목코드만 지원합니다.")
        payload = self._request(
            method="GET",
            path=KIS_DOMESTIC_DAILY_PRICE_PATH,
            tr_id=KIS_DOMESTIC_DAILY_TR_ID,
            params={
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": code,
                "FID_INPUT_DATE_1": start_date.replace("-", ""),
                "FID_INPUT_DATE_2": end_date.replace("-", ""),
                "FID_PERIOD_DIV_CODE": "D",
                "FID_ORG_ADJ_PRC": "1",
            },
        )
        output2 = payload.get("output2") or []
        if not isinstance(output2, list) or not output2:
            return pd.DataFrame(columns=["date", "close", "symbol"])
        frame = pd.DataFrame(output2)
        date_column = "stck_bsop_date" if "stck_bsop_date" in frame.columns else "bas_dt"
        close_column = "stck_clpr" if "stck_clpr" in frame.columns else "close"
        if date_column not in frame.columns or close_column not in frame.columns:
            return pd.DataFrame(columns=["date", "close", "symbol"])
        frame["date"] = pd.to_datetime(frame[date_column].astype(str), format="%Y%m%d", errors="coerce").dt.date
        frame["close"] = pd.to_numeric(frame[close_column], errors="coerce")
        frame = frame.dropna(subset=["date", "close"])[["date", "close"]].copy()
        frame["symbol"] = code
        return frame.sort_values("date").reset_index(drop=True)


def _safe_float(value: Any) -> float | None:
    """문자/숫자 값을 float로 변환한다."""

    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except Exception:
        return None


def _compose_quote_timestamp(quote_date: str, quote_time: str) -> str:
    """YYYYMMDD + HHMMSS 값을 ISO 문자열로 바꾼다."""

    date_part = str(quote_date or "").strip()
    time_part = str(quote_time or "").strip()
    if len(date_part) == 8 and len(time_part) == 6 and date_part.isdigit() and time_part.isdigit():
        try:
            timestamp = datetime.strptime(f"{date_part}{time_part}", "%Y%m%d%H%M%S")
            return timestamp.isoformat()
        except Exception:
            pass
    if len(date_part) == 8 and date_part.isdigit():
        try:
            return datetime.strptime(date_part, "%Y%m%d").date().isoformat()
        except Exception:
            pass
    return datetime.utcnow().replace(microsecond=0).isoformat()


def _derive_previous_close_from_change(*, current_price: float, day_change_rate: float | None) -> float | None:
    """등락률에서 전일 종가를 역산한다."""

    if day_change_rate is None or day_change_rate <= -100:
        return None
    try:
        return current_price / (1 + (day_change_rate / 100))
    except Exception:
        return None


def websocket_subscription_message(approval_key: str, symbol: str, *, subscribe: bool = True) -> str:
    """KIS 국내 체결가 구독/해지 메시지를 JSON 문자열로 만든다."""

    return json.dumps(
        {
            "header": {
                "approval_key": approval_key,
                "custtype": "P",
                "tr_type": "1" if subscribe else "2",
                "content-type": "utf-8",
            },
            "body": {
                "input": {
                    "tr_id": KIS_WS_QUOTE_TR_ID,
                    "tr_key": normalize_domestic_code(symbol),
                }
            },
        }
    )


def parse_websocket_message(raw_message: str) -> dict[str, Any] | None:
    """KIS WebSocket 메시지를 quote/control 형태로 해석한다."""

    text = str(raw_message or "").strip()
    if not text:
        return None

    if text.startswith("{"):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return None
        header = payload.get("header") or {}
        body = payload.get("body") or {}
        return {
            "message_type": "control",
            "tr_id": header.get("tr_id"),
            "tr_key": header.get("tr_key"),
            "rt_cd": body.get("rt_cd"),
            "message": body.get("msg1") or body.get("msg_cd") or "",
            "payload": payload,
        }

    chunks = text.split("|")
    if len(chunks) < 4 or chunks[1] != KIS_WS_QUOTE_TR_ID:
        return None

    values = chunks[3].split("^")
    if len(values) < len(KIS_WS_QUOTE_COLUMNS):
        return None
    quote_row = dict(zip(KIS_WS_QUOTE_COLUMNS, values))
    current_price = _safe_float(quote_row.get("stck_prpr"))
    day_change_rate = _safe_float(quote_row.get("prdy_ctrt"))
    if current_price is None:
        return None
    previous_close = _derive_previous_close_from_change(current_price=current_price, day_change_rate=day_change_rate)
    quote_time = _compose_quote_timestamp(quote_row.get("bsop_date", ""), quote_row.get("stck_cntg_hour", ""))
    return {
        "message_type": "quote",
        "tr_id": KIS_WS_QUOTE_TR_ID,
        "symbol": normalize_domestic_code(quote_row.get("mksc_shrn_iscd")),
        "price": float(current_price),
        "previous_close": previous_close,
        "day_change_rate": day_change_rate,
        "quote_time": quote_time,
        "currency": "KRW",
        "source": "KIS WebSocket",
        "metadata": quote_row,
    }


def kis_runtime_status() -> dict[str, Any]:
    """앱 운영 상태 패널용 KIS 런타임 정보를 반환한다."""

    settings = kis_settings()
    master_cache_path = _cache_path("master_records.json")
    master_cache_updated_at = ""
    if master_cache_path.exists():
        master_cache_updated_at = datetime.fromtimestamp(master_cache_path.stat().st_mtime, tz=timezone.utc).isoformat()
    return {
        "kis_rest_enabled": bool(settings["enabled"]),
        "kis_ws_configured": bool(settings["enabled"]),
        "kis_env": settings["env"],
        "kis_missing_config": settings["missing_config"],
        "kis_master_cache_updated_at": master_cache_updated_at,
    }

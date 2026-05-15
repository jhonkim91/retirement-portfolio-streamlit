from __future__ import annotations

import html
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from string import Template
from typing import Any, MutableMapping
import tomllib
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta

JsCode: Any | None = None
st_echarts: Any | None = None
st_keyup: Any | None = None
_ECHARTS_IMPORT_ERROR: Exception | None = None
_KEYUP_IMPORT_ERROR: Exception | None = None


def _discover_streamlit_component_manifests() -> None:
    """v2 컴포넌트 asset_dir 메타데이터를 import 전에 등록한다."""

    try:
        from streamlit.components.v2.get_bidi_component_manager import get_bidi_component_manager

        get_bidi_component_manager().discover_and_register_components(start_file_watching=False)
    except Exception:
        return


def load_echarts_runtime() -> bool:
    """ECharts 컴포넌트를 실제 차트 렌더링 시점에 로드한다."""

    global JsCode, st_echarts, _ECHARTS_IMPORT_ERROR
    if JsCode is not None and st_echarts is not None:
        return True
    if _ECHARTS_IMPORT_ERROR is not None:
        raise RuntimeError("`streamlit-echarts` 패키지를 불러오지 못했습니다. `python -m pip install -r requirements.txt` 후 다시 실행해 주세요.") from _ECHARTS_IMPORT_ERROR

    _discover_streamlit_component_manifests()
    try:
        from streamlit_echarts import JsCode as runtime_js_code
        from streamlit_echarts import st_echarts as runtime_st_echarts
    except Exception as exc:  # pragma: no cover - 런타임 의존성
        _ECHARTS_IMPORT_ERROR = exc
        raise RuntimeError("`streamlit-echarts` 패키지를 불러오지 못했습니다. `python -m pip install -r requirements.txt` 후 다시 실행해 주세요.") from exc

    JsCode = runtime_js_code
    st_echarts = runtime_st_echarts
    return True


def get_jscode_runtime() -> Any | None:
    """ECharts 옵션 생성용 `JsCode` 클래스를 가능한 경우 지연 로드한다."""

    if JsCode is not None:
        return JsCode
    try:
        load_echarts_runtime()
    except RuntimeError:
        return None
    return JsCode


def load_keyup_runtime() -> Any:
    """상품 검색 입력에서 사용할 `st_keyup` 컴포넌트를 지연 로드한다."""

    global st_keyup, _KEYUP_IMPORT_ERROR
    if st_keyup is not None:
        return st_keyup
    if _KEYUP_IMPORT_ERROR is not None:
        raise RuntimeError("`streamlit-keyup` 패키지가 필요합니다. `python -m pip install -r requirements.txt` 후 다시 실행해 주세요.") from _KEYUP_IMPORT_ERROR

    try:
        from st_keyup import st_keyup as runtime_st_keyup
    except Exception as exc:  # pragma: no cover - 런타임 의존성
        _KEYUP_IMPORT_ERROR = exc
        raise RuntimeError("`streamlit-keyup` 패키지가 필요합니다. `python -m pip install -r requirements.txt` 후 다시 실행해 주세요.") from exc

    st_keyup = runtime_st_keyup
    return st_keyup

import src.auth as app_auth

_ANALYTICS_MODULE: Any | None = None
_MARKET_MODULE: Any | None = None
_DB_MODULE: Any | None = None


def get_analytics_module() -> Any:
    """성과 계산 모듈을 실제 계산 시점에 로드한다."""

    global _ANALYTICS_MODULE
    if _ANALYTICS_MODULE is None:
        import src.analytics as analytics_module

        _ANALYTICS_MODULE = analytics_module
    return _ANALYTICS_MODULE


def get_market_module() -> Any:
    """시세 조회 모듈을 실제 조회 시점에 로드한다."""

    global _MARKET_MODULE
    if _MARKET_MODULE is None:
        import src.market as market_module

        _MARKET_MODULE = market_module
    return _MARKET_MODULE


def get_db_module() -> Any:
    """저장소 모듈을 실제 데이터 접근 시점에 로드한다."""

    global _DB_MODULE
    if _DB_MODULE is None:
        import src.db as db_module

        _DB_MODULE = db_module
    return _DB_MODULE


def account_summary(*args: Any, **kwargs: Any) -> Any:
    """지연 로드된 analytics 모듈의 계좌 요약을 반환한다."""

    return get_analytics_module().account_summary(*args, **kwargs)


def allocation_treemap_nodes(*args: Any, **kwargs: Any) -> Any:
    """지연 로드된 analytics 모듈의 자산 배분 노드를 반환한다."""

    return get_analytics_module().allocation_treemap_nodes(*args, **kwargs)


def build_portfolio_trend(*args: Any, **kwargs: Any) -> Any:
    """지연 로드된 analytics 모듈의 포트폴리오 추이를 반환한다."""

    return get_analytics_module().build_portfolio_trend(*args, **kwargs)


def cumulative_contribution_frame(*args: Any, **kwargs: Any) -> Any:
    """지연 로드된 analytics 모듈의 누적 입금 프레임을 반환한다."""

    return get_analytics_module().cumulative_contribution_frame(*args, **kwargs)


def holdings_frame(*args: Any, **kwargs: Any) -> Any:
    """지연 로드된 analytics 모듈의 보유 종목 프레임을 반환한다."""

    return get_analytics_module().holdings_frame(*args, **kwargs)


def realized_summary(*args: Any, **kwargs: Any) -> Any:
    """지연 로드된 analytics 모듈의 실현손익 요약을 반환한다."""

    return get_analytics_module().realized_summary(*args, **kwargs)


def fetch_latest_price(symbol: str) -> dict[str, Any]:
    """지연 로드된 market 모듈에서 최신 가격을 조회한다."""

    return get_market_module().fetch_latest_price(symbol)


def fetch_intraday_price_snapshot(symbol: str, interval: str = "5m") -> dict[str, Any]:
    """지연 로드된 market 모듈에서 당일 가격 스냅샷을 조회한다."""

    helper = getattr(get_market_module(), "fetch_intraday_price_snapshot", None)
    return helper(symbol, interval=interval) if callable(helper) else {}


def search_products(query: str, limit: int = 8) -> list[dict[str, Any]]:
    """지연 로드된 market 모듈에서 상품 후보를 검색한다."""

    helper = getattr(get_market_module(), "search_products", None)
    return helper(query, limit=limit) if callable(helper) else []


def quote_provider_status() -> dict[str, Any]:
    """지연 로드된 market 모듈에서 시세 provider 상태를 반환한다."""

    helper = getattr(get_market_module(), "quote_provider_status", None)
    return helper() if callable(helper) else {}


def is_kis_domestic_symbol(symbol: str) -> bool:
    """지연 로드된 market 모듈에서 국내 KIS 심볼 여부를 판별한다."""

    helper = getattr(get_market_module(), "is_kis_domestic_symbol", None)
    return bool(helper(symbol)) if callable(helper) else False

APP_ROOT = Path(__file__).resolve().parents[2]
STREAMLIT_CONFIG_PATH = APP_ROOT / ".streamlit" / "config.toml"
APP_CSS_PATH = APP_ROOT / ".streamlit" / "app.css"
DEFAULT_THEME_SETTINGS = {
    "primaryColor": "#33658A",
    "backgroundColor": "#F8FAFC",
    "secondaryBackgroundColor": "#F0F4F8",
    "textColor": "#102A43",
}


def _normalize_hex_color(value: Any, fallback: str) -> str:
    """16진수 색상 문자열을 `#RRGGBB` 형식으로 정규화한다."""

    raw_value = str(value or "").strip()
    candidate = raw_value if raw_value.startswith("#") else f"#{raw_value}"
    if len(candidate) == 4:
        candidate = "#" + "".join(channel * 2 for channel in candidate[1:])
    if len(candidate) != 7:
        return fallback
    if any(channel not in "0123456789abcdefABCDEF" for channel in candidate[1:]):
        return fallback
    return candidate.upper()


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    """정규화된 16진수 색상을 RGB 튜플로 변환한다."""

    normalized = _normalize_hex_color(value, "#000000").lstrip("#")
    return tuple(int(normalized[index : index + 2], 16) for index in (0, 2, 4))


def _mix_hex_colors(start_hex: str, end_hex: str, ratio: float) -> str:
    """두 16진수 색상을 비율에 따라 섞어 새 16진수 색상을 만든다."""

    ratio = max(0.0, min(1.0, float(ratio)))
    start_rgb = _hex_to_rgb(start_hex)
    end_rgb = _hex_to_rgb(end_hex)
    mixed_rgb = tuple(
        round(source + (target - source) * ratio)
        for source, target in zip(start_rgb, end_rgb)
    )
    return "#{:02X}{:02X}{:02X}".format(*mixed_rgb)


def _rgba_from_hex(value: str, alpha: float) -> str:
    """16진수 색상과 alpha 값으로 CSS rgba 문자열을 만든다."""

    red, green, blue = _hex_to_rgb(value)
    return f"rgba({red}, {green}, {blue}, {max(0.0, min(1.0, float(alpha))):.2f})"


@st.cache_data(show_spinner=False)
def load_design_tokens() -> dict[str, str | list[str]]:
    """`.streamlit/config.toml`을 기준으로 파생 디자인 토큰을 계산한다."""

    theme_settings = dict(DEFAULT_THEME_SETTINGS)
    try:
        parsed_config = tomllib.loads(STREAMLIT_CONFIG_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, tomllib.TOMLDecodeError):
        parsed_config = {}

    raw_theme_settings = parsed_config.get("theme") if isinstance(parsed_config, dict) else {}
    if isinstance(raw_theme_settings, dict):
        for key, fallback in DEFAULT_THEME_SETTINGS.items():
            theme_settings[key] = _normalize_hex_color(raw_theme_settings.get(key), fallback)
    else:
        for key, fallback in DEFAULT_THEME_SETTINGS.items():
            theme_settings[key] = fallback

    primary_color = str(theme_settings["primaryColor"])
    background_color = str(theme_settings["backgroundColor"])
    secondary_background_color = str(theme_settings["secondaryBackgroundColor"])
    text_color = str(theme_settings["textColor"])

    brand_deep_color = "#17324D"
    brand_accent_color = "#33658A"
    brand_hover_color = "#2B5677"
    brand_soft_color = _rgba_from_hex(brand_accent_color, 0.12)
    border_soft_color = "#D9E2EC"
    border_emphasis_color = "#CBD5E1"
    text_muted_color = "#697586"
    text_mid_color = "#486581"
    text_dim_color = "#829AB1"
    status_good_color = "#256F68"
    status_warn_color = "#D97706"
    auth_background_start_color = "#17324D"
    auth_background_end_color = "#102A43"
    hero_start_color = "#17324D"
    hero_mid_color = "#1F4667"
    hero_end_color = "#102A43"
    hero_glow_color = _rgba_from_hex("#8ECAE6", 0.16)
    card_shadow_color = "rgba(15, 23, 42, 0.05)"
    chart_line_color = "#17324D"
    chart_accent_color = "#33658A"
    chart_accent_strong_color = "#2B5677"
    chart_up_color = "#256F68"
    chart_up_strong_color = "#0F766E"
    chart_down_color = "#D94841"
    chart_down_strong_color = "#B93833"
    chart_band_upper_color = "#D97706"
    chart_band_lower_color = "#0F766E"
    tooltip_background_color = _rgba_from_hex("#17324D", 0.96)
    treemap_palette = [
        chart_down_strong_color,
        chart_down_color,
        _mix_hex_colors(chart_down_color, "#FFFFFF", 0.62),
        _mix_hex_colors("#D9E2EC", "#FFFFFF", 0.5),
        _mix_hex_colors(chart_up_color, "#FFFFFF", 0.62),
        chart_up_color,
        chart_up_strong_color,
    ]

    return {
        "theme_primary_color": primary_color,
        "theme_background_color": background_color,
        "theme_secondary_background_color": secondary_background_color,
        "theme_text_color": text_color,
        "panel_color": "#FFFFFF",
        "panel_alt_color": _mix_hex_colors(background_color, secondary_background_color, 0.52),
        "surface_color": _rgba_from_hex("#FFFFFF", 0.94),
        "surface_strong_color": "#FFFFFF",
        "border_soft_color": border_soft_color,
        "border_emphasis_color": border_emphasis_color,
        "text_muted_color": text_muted_color,
        "text_mid_color": text_mid_color,
        "text_dim_color": text_dim_color,
        "brand_deep_color": brand_deep_color,
        "brand_accent_color": brand_accent_color,
        "brand_hover_color": brand_hover_color,
        "brand_soft_color": brand_soft_color,
        "status_good_color": status_good_color,
        "status_warn_color": status_warn_color,
        "auth_background_start_color": auth_background_start_color,
        "auth_background_end_color": auth_background_end_color,
        "hero_start_color": hero_start_color,
        "hero_mid_color": hero_mid_color,
        "hero_end_color": hero_end_color,
        "hero_glow_color": hero_glow_color,
        "card_shadow_color": card_shadow_color,
        "chart_canvas_bg_color": "#FFFFFF",
        "chart_canvas_border_color": "#D9E2EC",
        "chart_title_text_color": brand_deep_color,
        "chart_title_bg_color": _rgba_from_hex("#F8FAFC", 0.98),
        "chart_title_border_color": _rgba_from_hex("#D9E2EC", 0.92),
        "chart_panel_color": "#FFFFFF",
        "chart_panel_alt_color": "#F8FAFC",
        "chart_border_color": _rgba_from_hex("#D9E2EC", 0.94),
        "chart_dim_text_color": text_dim_color,
        "chart_muted_text_color": text_muted_color,
        "chart_mid_text_color": text_mid_color,
        "chart_text_color": brand_deep_color,
        "chart_inverse_text_color": "#FFFFFF",
        "chart_inverse_muted_text_color": "#D9E2EC",
        "chart_up_color": chart_up_color,
        "chart_up_strong_color": chart_up_strong_color,
        "chart_down_color": chart_down_color,
        "chart_down_strong_color": chart_down_strong_color,
        "chart_flat_color": "#829AB1",
        "chart_accent_color": chart_accent_color,
        "chart_accent_soft_color": _rgba_from_hex(chart_accent_color, 0.18),
        "chart_accent_strong_color": chart_accent_strong_color,
        "chart_band_upper_color": chart_band_upper_color,
        "chart_band_lower_color": chart_band_lower_color,
        "chart_live_dot_color": status_good_color,
        "chart_line_color": chart_line_color,
        "chart_line_soft_color": _rgba_from_hex(chart_line_color, 0.28),
        "chart_line_faint_color": _rgba_from_hex(chart_line_color, 0.08),
        "chart_tooltip_bg_color": tooltip_background_color,
        "chart_tooltip_text_color": "#F8FAFC",
        "chart_tooltip_muted_text_color": "#DCE7EA",
        "treemap_palette": treemap_palette,
    }


@st.cache_data(show_spinner=False)
def render_app_stylesheet() -> str:
    """디자인 토큰을 외부 CSS 템플릿에 주입한 결과를 반환한다."""

    css_template = APP_CSS_PATH.read_text(encoding="utf-8")
    css_variables = {key: str(value) for key, value in DESIGN_TOKENS.items() if isinstance(value, str)}
    return Template(css_template).safe_substitute(css_variables)


KST_TIMEZONE = ZoneInfo("Asia/Seoul")
REALTIME_QUOTE_FRESHNESS = timedelta(minutes=3)


def create_account(*args: Any, **kwargs: Any) -> Any:
    """저장소 모듈의 계좌 생성 함수를 지연 호출한다."""

    return get_db_module().create_account(*args, **kwargs)


def delete_account(*args: Any, **kwargs: Any) -> Any:
    """저장소 모듈의 계좌 삭제 함수를 지연 호출한다."""

    return get_db_module().delete_account(*args, **kwargs)


def adjust_cash_balance(*args: Any, **kwargs: Any) -> Any:
    """저장소 모듈의 현금 조정 함수를 지연 호출한다."""

    return get_db_module().adjust_cash_balance(*args, **kwargs)


def delete_trade_log(*args: Any, **kwargs: Any) -> Any:
    """저장소 모듈의 거래 기록 삭제 함수를 지연 호출한다."""

    return get_db_module().delete_trade_log(*args, **kwargs)


def export_dataframe_rows(*args: Any, **kwargs: Any) -> Any:
    """저장소 모듈의 테이블 내보내기 함수를 지연 호출한다."""

    return get_db_module().export_dataframe_rows(*args, **kwargs)


def get_account(*args: Any, **kwargs: Any) -> Any:
    """저장소 모듈의 계좌 조회 함수를 지연 호출한다."""

    return get_db_module().get_account(*args, **kwargs)


def initialize_database(*args: Any, **kwargs: Any) -> Any:
    """저장소 모듈의 초기화 함수를 지연 호출한다."""

    return get_db_module().initialize_database(*args, **kwargs)


def list_accounts(*args: Any, **kwargs: Any) -> Any:
    """저장소 모듈의 계좌 목록 함수를 지연 호출한다."""

    return get_db_module().list_accounts(*args, **kwargs)


def list_account_snapshots(*args: Any, **kwargs: Any) -> Any:
    """저장소 모듈의 계좌 스냅샷 목록 함수를 지연 호출한다."""

    return get_db_module().list_account_snapshots(*args, **kwargs)


def list_holdings(*args: Any, **kwargs: Any) -> Any:
    """저장소 모듈의 보유 종목 목록 함수를 지연 호출한다."""

    return get_db_module().list_holdings(*args, **kwargs)


def latest_realtime_quote_time(*args: Any, **kwargs: Any) -> Any:
    """저장소 모듈의 최신 실시간 시세 시각 함수를 지연 호출한다."""

    return get_db_module().latest_realtime_quote_time(*args, **kwargs)


def list_trade_logs(*args: Any, **kwargs: Any) -> Any:
    """저장소 모듈의 거래 기록 목록 함수를 지연 호출한다."""

    return get_db_module().list_trade_logs(*args, **kwargs)


def get_realtime_worker_status(*args: Any, **kwargs: Any) -> Any:
    """저장소 모듈의 실시간 worker 상태 함수를 지연 호출한다."""

    return get_db_module().get_realtime_worker_status(*args, **kwargs)


def record_account_snapshot(*args: Any, **kwargs: Any) -> Any:
    """저장소 모듈의 계좌 스냅샷 저장 함수를 지연 호출한다."""

    return get_db_module().record_account_snapshot(*args, **kwargs)


def record_cash_flow(*args: Any, **kwargs: Any) -> Any:
    """저장소 모듈의 현금 흐름 저장 함수를 지연 호출한다."""

    return get_db_module().record_cash_flow(*args, **kwargs)


def record_trade(*args: Any, **kwargs: Any) -> Any:
    """저장소 모듈의 매매 저장 함수를 지연 호출한다."""

    return get_db_module().record_trade(*args, **kwargs)


def update_trade_log(*args: Any, **kwargs: Any) -> Any:
    """저장소 모듈의 거래 기록 수정 함수를 지연 호출한다."""

    return get_db_module().update_trade_log(*args, **kwargs)


def seed_demo_workspace(*args: Any, **kwargs: Any) -> Any:
    """저장소 모듈의 데모 작업공간 생성 함수를 지연 호출한다."""

    return get_db_module().seed_demo_workspace(*args, **kwargs)


def set_holding_price(*args: Any, **kwargs: Any) -> Any:
    """저장소 모듈의 보유 종목 가격 갱신 함수를 지연 호출한다."""

    return get_db_module().set_holding_price(*args, **kwargs)


def backend_status(*args: Any, **kwargs: Any) -> Any:
    """저장소 모듈의 백엔드 상태 함수를 지연 호출한다."""

    return get_db_module().backend_status(*args, **kwargs)


def is_accounts_hotfix_error(*args: Any, **kwargs: Any) -> Any:
    """저장소 모듈의 계좌 hotfix 오류 판별 함수를 지연 호출한다."""

    return get_db_module().is_accounts_hotfix_error(*args, **kwargs)


def sync_account_rollup(*args: Any, **kwargs: Any) -> Any:
    """저장소 모듈의 계좌 롤업 동기화 함수를 지연 호출한다."""

    return get_db_module().sync_account_rollup(*args, **kwargs)


def holdings_overview_frame(
    holdings: list[dict[str, Any]],
    *,
    selected_symbol: str | None = None,
    limit: int = 10,
) -> pd.DataFrame:
    """개요 차트용 보유 종목 프레임을 호환성 있게 반환한다."""

    helper = getattr(get_analytics_module(), "holdings_overview_frame", None)
    if callable(helper):
        return helper(holdings, selected_symbol=selected_symbol, limit=limit)

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


st.set_page_config(
    page_title="은퇴 포트폴리오",
    page_icon="💼",
    layout="wide",
)


DESIGN_TOKENS = load_design_tokens()
PAGES = ("Dashboard", "Trades", "Data")
NAVIGATION_CONTEXT_KEY = "navigation_page_context"
PENDING_CONFIRMATION_EMAIL_KEY = "pending_confirmation_email"
AUTH_FEEDBACK_KEY = "auth_feedback"
AUTH_CALLBACK_RERUN_SIGNATURE_KEY = "auth_callback_rerun_signature"
INVALID_ACCOUNT_RERUN_GUARD_KEY = "invalid_account_rerun_guard"
TRADE_SEARCH_QUERY_KEY = "trade_search_query"
TRADE_SYMBOL_KEY = "trade_symbol"
TRADE_PRODUCT_NAME_KEY = "trade_product_name"
TRADE_ASSET_TYPE_KEY = "trade_asset_type"
TRADE_TYPE_KEY = "trade_type"
TRADE_QUANTITY_KEY = "trade_quantity"
TRADE_PRICE_KEY = "trade_price"
TRADE_DATE_KEY = "trade_date"
TRADE_NOTES_KEY = "trade_notes"
TRADE_PREFILL_MARKER_KEY = "trade_prefill_marker"
CASH_FLOW_TYPE_KEY = "cash_flow_type"
CASH_FLOW_AMOUNT_KEY = "cash_flow_amount"
CASH_FLOW_DATE_KEY = "cash_flow_date"
CASH_FLOW_NOTES_KEY = "cash_flow_notes"
TRADE_FORM_RESET_PENDING_KEY = "trade_form_reset_pending"
CASH_FLOW_FORM_RESET_PENDING_KEY = "cash_flow_form_reset_pending"
TRADE_PAGE_SUCCESS_MESSAGE_KEY = "trade_page_success_message"
PAGE_LABELS = {
    "Dashboard": "대시보드",
    "Trades": "거래",
    "Data": "데이터",
}
ACCOUNT_TYPE_LABELS = {
    "retirement": "연금(IRP/퇴직연금)",
    "brokerage": "일반",
}
TRADE_TYPE_LABELS = {
    "buy": "매수",
    "sell": "매도",
}
TRADE_TYPE_BADGE_STYLES = {
    "buy": {
        "background": "#E6F4F1",
        "border": "#B6D9D4",
        "color": "#256F68",
    },
    "sell": {
        "background": "#FDEDEC",
        "border": "#F3C1BD",
        "color": "#D94841",
    },
}
ASSET_TYPE_LABELS = {
    "risk": "위험자산",
    "safe": "안전자산",
    "cash": "현금",
}
CASH_FLOW_TYPE_LABELS = {
    "deposit": "입금",
    "personal_deposit": "개인 입금",
    "employer_deposit": "회사 납입금",
    "withdraw": "일반 출금",
    "transfer_out": "계좌 이체 출금",
    "transfer_in": "계좌 이체 입금",
    "cash_adjustment": "현금 조정",
}
TABLE_LABELS = {
    "accounts": "계좌",
    "holdings": "보유 종목",
    "trade_logs": "거래 기록",
    "daily_account_snapshot": "일별 자산 스냅샷",
}
VISIBLE_TRADE_LOG_TYPES = {"buy", "sell", "personal_deposit", "employer_deposit"}
TRADE_LOG_TABLE_HEADER_LABELS = ["거래일", "종목명", "코드", "유형", "자산군", "수량", "단가", "총액", "관리"]
TRADE_LOG_TABLE_DISPLAY_FIELDS = [
    "trade_date",
    "product_name",
    "symbol",
    "trade_type",
    "asset_type",
    "quantity",
    "price",
    "total_amount",
]
TRADE_LOG_TABLE_COLUMN_WEIGHT_BY_LABEL = {
    "거래일": 1.05,
    "종목명": 1.45,
    "코드": 1.0,
    "유형": 0.9,
    "자산군": 0.95,
    "수량": 0.9,
    "단가": 0.9,
    "총액": 1.0,
    "관리": 1.3,
}
TRADE_LOG_TABLE_COLUMN_WEIGHTS = [
    TRADE_LOG_TABLE_COLUMN_WEIGHT_BY_LABEL[label]
    for label in TRADE_LOG_TABLE_HEADER_LABELS
]
TRADE_LOG_INLINE_TRADE_EDIT_COLUMN_WEIGHTS = [1.55, 1.0, 1.1, 0.82, 0.95, 0.95, 1.18, 0.74, 0.74]
TRADE_LOG_INLINE_CASH_EDIT_COLUMN_WEIGHTS = [1.05, 1.05, 1.2, 1.7, 0.74, 0.74]
DETAIL_MEASURE_LABELS = {
    "market_value": "평가금액",
    "profit_rate": "수익률",
    "close": "종가",
}
DEFAULT_SELECTED_TREND_MEASURE = "profit_rate"
PERIOD_LABELS = {
    "today": "당일",
    "1mo": "1개월",
    "3mo": "3개월",
    "6mo": "6개월",
    "1y": "1년",
}
SELECTED_TREND_PERIOD_OPTIONS = ("today", "1mo", "3mo", "6mo", "1y")
DASHBOARD_SELECTED_TREND_PERIOD_OPTIONS = tuple(
    period for period in SELECTED_TREND_PERIOD_OPTIONS if period != "today"
)
DASHBOARD_ALLOCATION_CHART_HEIGHT = 560
DASHBOARD_HOLDINGS_CHART_HEIGHT = 360
DASHBOARD_HOLDINGS_COMPARE_CHART_HEIGHT = 430
DASHBOARD_DETAIL_CHART_HEIGHT = DASHBOARD_HOLDINGS_COMPARE_CHART_HEIGHT
DASHBOARD_HOLDINGS_TABLE_HEIGHT = 380


@dataclass(frozen=True)
class ChartColors:
    """대시보드 차트 전용 색상 토큰 묶음."""

    feargreed_bg: str
    feargreed_panel: str
    feargreed_panel_alt: str
    feargreed_border: str
    feargreed_dim_text: str
    feargreed_muted_text: str
    feargreed_mid_text: str
    feargreed_bright_text: str
    feargreed_full_text: str
    feargreed_up: str
    feargreed_down: str
    feargreed_flat: str
    feargreed_accent: str
    feargreed_live_dot: str
    treemap_canvas_bg: str
    treemap_canvas_border: str
    treemap_title_text: str
    treemap_title_bg: str
    treemap_title_border: str
    feargreed_treemap_palette: tuple[str, ...]
    chart_line: str
    chart_line_soft: str
    chart_line_faint: str
    chart_tooltip_bg: str
    chart_tooltip_text: str
    chart_text: str
    chart_accent_soft: str
    chart_accent_strong: str


def build_chart_colors(tokens: dict[str, str | list[str]]) -> ChartColors:
    """디자인 토큰에서 차트 색상 네임스페이스를 생성한다."""

    return ChartColors(
        feargreed_bg=str(tokens["chart_panel_alt_color"]),
        feargreed_panel=str(tokens["chart_panel_color"]),
        feargreed_panel_alt=str(tokens["chart_panel_alt_color"]),
        feargreed_border=str(tokens["chart_border_color"]),
        feargreed_dim_text=str(tokens["chart_dim_text_color"]),
        feargreed_muted_text=str(tokens["chart_muted_text_color"]),
        feargreed_mid_text=str(tokens["chart_mid_text_color"]),
        feargreed_bright_text=str(tokens["chart_inverse_muted_text_color"]),
        feargreed_full_text=str(tokens["chart_inverse_text_color"]),
        feargreed_up=str(tokens["chart_up_color"]),
        feargreed_down=str(tokens["chart_down_color"]),
        feargreed_flat=str(tokens["chart_flat_color"]),
        feargreed_accent=str(tokens["chart_accent_color"]),
        feargreed_live_dot=str(tokens["chart_live_dot_color"]),
        treemap_canvas_bg=str(tokens["chart_canvas_bg_color"]),
        treemap_canvas_border=str(tokens["chart_canvas_border_color"]),
        treemap_title_text=str(tokens["chart_title_text_color"]),
        treemap_title_bg=str(tokens["chart_title_bg_color"]),
        treemap_title_border=str(tokens["chart_title_border_color"]),
        feargreed_treemap_palette=tuple(
            str(color)
            for color in tokens["treemap_palette"]
            if isinstance(color, str)
        ),
        chart_line=str(tokens["chart_line_color"]),
        chart_line_soft=str(tokens["chart_line_soft_color"]),
        chart_line_faint=str(tokens["chart_line_faint_color"]),
        chart_tooltip_bg=str(tokens["chart_tooltip_bg_color"]),
        chart_tooltip_text=str(tokens["chart_tooltip_text_color"]),
        chart_text=str(tokens["chart_text_color"]),
        chart_accent_soft=str(tokens["chart_accent_soft_color"]),
        chart_accent_strong=str(tokens["chart_accent_strong_color"]),
    )


CHART_COLORS = build_chart_colors(DESIGN_TOKENS)
FEARGREED_BG_COLOR = CHART_COLORS.feargreed_bg
FEARGREED_PANEL_COLOR = CHART_COLORS.feargreed_panel
FEARGREED_PANEL_ALT_COLOR = CHART_COLORS.feargreed_panel_alt
FEARGREED_BORDER_COLOR = CHART_COLORS.feargreed_border
FEARGREED_DIM_TEXT_COLOR = CHART_COLORS.feargreed_dim_text
FEARGREED_MUTED_TEXT_COLOR = CHART_COLORS.feargreed_muted_text
FEARGREED_MID_TEXT_COLOR = CHART_COLORS.feargreed_mid_text
FEARGREED_BRIGHT_TEXT_COLOR = CHART_COLORS.feargreed_bright_text
FEARGREED_FULL_TEXT_COLOR = CHART_COLORS.feargreed_full_text
FEARGREED_UP_COLOR = CHART_COLORS.feargreed_up
FEARGREED_DOWN_COLOR = CHART_COLORS.feargreed_down
FEARGREED_FLAT_COLOR = CHART_COLORS.feargreed_flat
FEARGREED_ACCENT_COLOR = CHART_COLORS.feargreed_accent
FEARGREED_LIVE_DOT_COLOR = CHART_COLORS.feargreed_live_dot
TREEMAP_CANVAS_BG_COLOR = CHART_COLORS.treemap_canvas_bg
TREEMAP_CANVAS_BORDER_COLOR = CHART_COLORS.treemap_canvas_border
TREEMAP_TITLE_TEXT_COLOR = CHART_COLORS.treemap_title_text
TREEMAP_TITLE_BG_COLOR = CHART_COLORS.treemap_title_bg
TREEMAP_TITLE_BORDER_COLOR = CHART_COLORS.treemap_title_border
FEARGREED_TREEMAP_PALETTE = list(CHART_COLORS.feargreed_treemap_palette)
CHART_LINE_COLOR = CHART_COLORS.chart_line
CHART_LINE_SOFT_COLOR = CHART_COLORS.chart_line_soft
CHART_LINE_FAINT_COLOR = CHART_COLORS.chart_line_faint
CHART_TOOLTIP_BG_COLOR = CHART_COLORS.chart_tooltip_bg
CHART_TOOLTIP_TEXT_COLOR = CHART_COLORS.chart_tooltip_text
CHART_TEXT_COLOR = CHART_COLORS.chart_text
CHART_ACCENT_SOFT_COLOR = CHART_COLORS.chart_accent_soft
CHART_ACCENT_STRONG_COLOR = CHART_COLORS.chart_accent_strong
PRODUCT_TYPE_LABELS = {
    "stock": "주식",
    "stock/ETF": "주식/ETF",
    "etf": "ETF",
    "ETF": "ETF",
    "equity": "주식",
    "EQUITY": "주식",
    "etn": "ETN",
    "ETN": "ETN",
    "fund": "펀드",
    "mutualfund": "펀드",
    "MUTUALFUND": "펀드",
}
EXCHANGE_LABELS = {
    "KRX": "국내",
    "Korea": "국내",
    "Fund": "펀드",
    "US": "미국",
}


def format_won(value: Any) -> str:
    return f"₩{float(value or 0):,.0f}"


def format_pct(value: Any) -> str:
    return f"{float(value or 0):+.2f}%"


def _quote_currency_for_symbol(symbol: str, fallback: str = "KRW") -> str:
    normalized = str(symbol or "").strip().upper()
    if normalized.endswith(".KS") or normalized.endswith(".KQ") or normalized.isdigit():
        return "KRW"
    return str(fallback or "USD").strip().upper()


def _format_quote_price(value: Any, *, currency: str) -> str:
    numeric = float(value or 0)
    if str(currency or "").strip().upper() == "USD":
        return f"${numeric:,.2f}"
    return f"₩{numeric:,.0f}"


def metric_delta(value: Any) -> str:
    return f"{float(value or 0):+,.0f}"


def label_page(value: Any) -> str:
    return PAGE_LABELS.get(str(value), str(value))


def label_account_type(value: Any) -> str:
    return ACCOUNT_TYPE_LABELS.get(str(value), str(value))


def label_trade_type(value: Any) -> str:
    return TRADE_TYPE_LABELS.get(str(value), str(value))


def label_asset_type(value: Any) -> str:
    return ASSET_TYPE_LABELS.get(str(value), str(value))


def label_cash_flow_type(value: Any) -> str:
    return CASH_FLOW_TYPE_LABELS.get(str(value), str(value))


def label_transaction_type(value: Any) -> str:
    text = str(value)
    return TRADE_TYPE_LABELS.get(text, CASH_FLOW_TYPE_LABELS.get(text, text))


def trade_type_badge_html(value: Any) -> str:
    """거래유형을 매수/매도 컬러 배지 HTML로 반환한다."""

    normalized_type = normalize_trade_log_type(value)
    label = html.escape(label_transaction_type(normalized_type))
    style = TRADE_TYPE_BADGE_STYLES.get(normalized_type)
    if style is None:
        return label
    return (
        f'<span style="display:inline-block; min-width:38px; text-align:center; '
        f'padding:3px 8px; border-radius:999px; font-weight:700; font-size:0.86rem; '
        f'background:{style["background"]}; border:1px solid {style["border"]}; color:{style["color"]};">'
        f'{label}</span>'
    )


def normalize_trade_log_type(value: Any) -> str:
    """거래 로그 유형을 현재 앱 기준 값으로 정규화한다."""

    text = str(value or "").strip().lower()
    return "personal_deposit" if text == "deposit" else text


def is_visible_trade_log(log: dict[str, Any]) -> bool:
    """거래/데이터 화면에 노출할 핵심 거래 로그인지 반환한다."""

    return normalize_trade_log_type(log.get("trade_type")) in VISIBLE_TRADE_LOG_TYPES


def is_trade_log_editable(log: dict[str, Any]) -> bool:
    """거래 기록 수정/삭제 UI에서 지원하는 유형인지 반환한다."""

    return normalize_trade_log_type(log.get("trade_type")) in VISIBLE_TRADE_LOG_TYPES


def trade_log_editor_option_label(log: dict[str, Any]) -> str:
    """거래 기록 선택 UI에 표시할 한 줄 라벨을 만든다."""

    trade_date = str(log.get("trade_date") or "-").strip() or "-"
    trade_type = label_transaction_type(normalize_trade_log_type(log.get("trade_type")))
    product_name = str(log.get("product_name") or "미지정").strip() or "미지정"
    amount = float(log.get("total_amount") or 0)
    return f"{trade_date} | {trade_type} | {product_name} | {amount:,.0f}원"


def trade_submit_button_label(trade_type: str) -> str:
    """거래 저장 버튼 문구를 반환한다."""

    return "상품 추가" if str(trade_type or "").strip().lower() == "buy" else "상품 저장"


def trade_price_label(trade_type: str) -> str:
    """거래 유형에 맞는 단가 필드명을 반환한다."""

    return "매입가/기준가" if str(trade_type or "").strip().lower() == "buy" else "매도가/기준가"


def trade_date_label(trade_type: str) -> str:
    """거래 유형에 맞는 일자 필드명을 반환한다."""

    return "매입일" if str(trade_type or "").strip().lower() == "buy" else "매매일"


def cash_flow_panel_title(flow_type: str) -> str:
    """현금 흐름 패널 제목을 반환한다."""

    normalized = normalize_trade_log_type(flow_type)
    return {
        "personal_deposit": "개인 현금입금",
        "employer_deposit": "회사 현금입금",
        "withdraw": "현금 출금",
    }.get(normalized, "현금 흐름")


def cash_flow_panel_caption(flow_type: str) -> str:
    """현금 흐름 패널 설명 문구를 반환한다."""

    normalized = normalize_trade_log_type(flow_type)
    return {
        "personal_deposit": "입금액을 개인 원금으로 계산하고 매매일지에 기록합니다.",
        "employer_deposit": "입금액을 퇴직금 원금으로 계산하고 매매일지에 기록합니다.",
        "withdraw": "출금액을 원금 차감으로 계산하고 매매일지에 기록합니다.",
    }.get(normalized, "현금 흐름을 원장에 기록합니다.")


def cash_flow_submit_label(flow_type: str) -> str:
    """현금 흐름 저장 버튼 문구를 반환한다."""

    normalized = normalize_trade_log_type(flow_type)
    return "출금 기록" if normalized == "withdraw" else "입금 기록"


def format_trade_log_cell(log: dict[str, Any], field_name: str, account_name_map: dict[int, str]) -> str:
    """거래 기록 행의 표시 문자열을 컬럼별로 반환한다."""

    if field_name == "trade_date":
        return str(log.get("trade_date") or "-").strip() or "-"
    if field_name == "product_name":
        return str(log.get("product_name") or "-").strip() or "-"
    if field_name == "symbol":
        return str(log.get("symbol") or "-").strip() or "-"
    if field_name == "trade_type":
        return trade_type_badge_html(log.get("trade_type"))
    if field_name == "counterparty_account":
        raw_value = log.get("counterparty_account_id")
        if raw_value in (None, ""):
            return "-"
        try:
            return account_name_map.get(int(raw_value), "-")
        except (TypeError, ValueError):
            return "-"
    if field_name == "asset_type":
        return label_asset_type(log.get("asset_type"))
    if field_name == "quantity":
        return f"{float(log.get('quantity') or 0):,.4f}".rstrip("0").rstrip(".") or "0"
    if field_name in {"price", "total_amount", "cash_delta"}:
        return f"{float(log.get(field_name) or 0):,.0f}"
    if field_name == "notes":
        return str(log.get("notes") or "-").strip() or "-"
    return str(log.get(field_name) or "-").strip() or "-"


def _trade_log_date_value(log: dict[str, Any]) -> date:
    """거래 로그의 날짜 값을 입력 폼용 date 객체로 변환한다."""

    raw_value = str(log.get("trade_date") or date.today().isoformat()).strip()
    try:
        return date.fromisoformat(raw_value)
    except ValueError:
        return date.today()


def _optional_int(value: Any) -> int | None:
    """세션 상태의 선택 ID를 정수로 변환하고 실패하면 None을 반환한다."""

    try:
        parsed_value = int(value)
    except (TypeError, ValueError):
        return None
    return parsed_value if parsed_value > 0 else None


def render_trade_log_edit_form(
    account: dict[str, Any],
    selected_log: dict[str, Any],
    *,
    edit_state_key: str,
    editing_log_id: int,
) -> None:
    """선택한 거래 기록 행 바로 아래에 수정 폼을 렌더링한다."""

    selected_type = normalize_trade_log_type(selected_log.get("trade_type"))
    selected_trade_date = _trade_log_date_value(selected_log)
    with st.container(key="trade-log-inline-editor-shell"):
        if not is_trade_log_editable(selected_log):
            st.info("이 기록은 현재 수정/삭제를 지원하지 않습니다.")
            return

        if selected_type in {"buy", "sell"}:
            with st.form(f"trade-log-edit-form:{account['id']}:{editing_log_id}", clear_on_submit=False):
                row_columns = st.columns(TRADE_LOG_INLINE_TRADE_EDIT_COLUMN_WEIGHTS, gap="small")
                with row_columns[0]:
                    edit_product_name = st.text_input(
                        "상품명",
                        value=str(selected_log.get("product_name") or "").strip(),
                        placeholder="상품명",
                        label_visibility="collapsed",
                    )
                with row_columns[1]:
                    edit_symbol = st.text_input(
                        "상품 코드",
                        value=str(selected_log.get("symbol") or "").strip(),
                        placeholder="코드",
                        label_visibility="collapsed",
                    )
                with row_columns[2]:
                    edit_trade_date = st.date_input(
                        trade_date_label(selected_type),
                        value=selected_trade_date,
                        label_visibility="collapsed",
                    )
                with row_columns[3]:
                    edit_quantity = st.number_input(
                        "수량/좌수",
                        min_value=0.0,
                        step=1.0,
                        value=float(selected_log.get("quantity") or 0),
                        label_visibility="collapsed",
                    )
                with row_columns[4]:
                    edit_price = st.number_input(
                        trade_price_label(selected_type),
                        min_value=0.0,
                        step=100.0,
                        value=float(selected_log.get("price") or 0),
                        label_visibility="collapsed",
                    )
                with row_columns[5]:
                    edit_asset_type = st.selectbox(
                        "자산 구분",
                        ["risk", "safe"],
                        index=0 if str(selected_log.get("asset_type") or "risk").strip().lower() == "risk" else 1,
                        format_func=label_asset_type,
                        label_visibility="collapsed",
                    )
                with row_columns[6]:
                    edit_notes = st.text_input(
                        "메모",
                        value=str(selected_log.get("notes") or "").strip(),
                        placeholder="메모",
                        label_visibility="collapsed",
                    )
                with row_columns[7]:
                    submitted = st.form_submit_button("저장", width="stretch", type="primary")
                with row_columns[8]:
                    cancelled = st.form_submit_button("취소", width="stretch")
            if submitted:
                try:
                    update_trade_log(
                        int(account["id"]),
                        int(editing_log_id),
                        trade_type=selected_type,
                        symbol=edit_symbol,
                        product_name=edit_product_name,
                        asset_type=edit_asset_type,
                        quantity=edit_quantity,
                        price=edit_price,
                        trade_date=edit_trade_date.isoformat(),
                        notes=edit_notes,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state.pop(edit_state_key, None)
                    mark_rollup_dirty()
                    st.session_state[TRADE_PAGE_SUCCESS_MESSAGE_KEY] = "거래 기록을 수정했습니다."
                    st.rerun()
            if cancelled:
                st.session_state.pop(edit_state_key, None)
                st.rerun()
            return

        flow_options = ["personal_deposit", "employer_deposit"]
        selected_flow_index = flow_options.index(selected_type) if selected_type in flow_options else 0
        with st.form(f"cash-log-edit-form:{account['id']}:{editing_log_id}", clear_on_submit=False):
            row_columns = st.columns(TRADE_LOG_INLINE_CASH_EDIT_COLUMN_WEIGHTS, gap="small")
            with row_columns[0]:
                edit_flow_type = st.selectbox(
                    "현금 흐름",
                    flow_options,
                    index=selected_flow_index,
                    format_func=label_cash_flow_type,
                    label_visibility="collapsed",
                )
            with row_columns[1]:
                edit_trade_date = st.date_input("처리일", value=selected_trade_date, label_visibility="collapsed")
            with row_columns[2]:
                edit_amount = st.number_input(
                    "금액",
                    min_value=0,
                    step=100000,
                    value=int(round(float(selected_log.get("total_amount") or 0))),
                    label_visibility="collapsed",
                )
            with row_columns[3]:
                edit_notes = st.text_input(
                    "메모",
                    value=str(selected_log.get("notes") or ""),
                    placeholder="메모",
                    label_visibility="collapsed",
                )
            with row_columns[4]:
                submitted = st.form_submit_button("저장", width="stretch", type="primary")
            with row_columns[5]:
                cancelled = st.form_submit_button("취소", width="stretch")
        if submitted:
            try:
                update_trade_log(
                    int(account["id"]),
                    int(editing_log_id),
                    trade_type=edit_flow_type,
                    amount=edit_amount,
                    trade_date=edit_trade_date.isoformat(),
                    notes=edit_notes,
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state.pop(edit_state_key, None)
                mark_rollup_dirty()
                st.session_state[TRADE_PAGE_SUCCESS_MESSAGE_KEY] = "거래 기록을 수정했습니다."
                st.rerun()
        if cancelled:
            st.session_state.pop(edit_state_key, None)
            st.rerun()


@st.dialog("거래 기록 삭제 확인")
def render_trade_log_delete_dialog(
    account_id: int,
    log_id: int,
    selected_log: dict[str, Any],
    *,
    delete_state_key: str,
) -> None:
    """거래 기록 삭제 확인 팝업을 렌더링한다."""

    st.write("다음 거래 기록을 삭제하시겠습니까?")
    st.write(trade_log_editor_option_label(selected_log))
    st.caption("삭제 후 보유 종목과 대시보드 계산 데이터가 다시 갱신됩니다.")
    action_col_1, action_col_2 = st.columns(2, gap="small")
    with action_col_1:
        if st.button("삭제 실행", key=f"trade-log-delete-confirm:{account_id}:{log_id}", width="stretch", type="primary"):
            try:
                delete_trade_log(int(account_id), int(log_id))
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state.pop(delete_state_key, None)
                mark_rollup_dirty()
                st.session_state[TRADE_PAGE_SUCCESS_MESSAGE_KEY] = "거래 기록을 삭제했습니다."
                st.rerun()
    with action_col_2:
        if st.button("취소", key=f"trade-log-delete-cancel:{account_id}:{log_id}", width="stretch"):
            st.session_state.pop(delete_state_key, None)
            st.rerun()


def label_table_name(value: Any) -> str:
    return TABLE_LABELS.get(str(value), str(value))


def render_operation_error(exc: Exception) -> None:
    """사용자 작업 오류와 필요한 운영 후속 조치를 함께 표시한다."""

    st.error(str(exc))
    if not is_accounts_hotfix_error(exc):
        return
    if not is_hotfix_guide_visible():
        st.caption("운영 정책 점검이 필요한 오류입니다. 상세 hotfix 절차는 관리자 모드에서만 표시됩니다.")
        return

    with st.container(border=True):
        st.caption("운영 조치 필요")
        st.write("현재 계좌 생성과 데모 데이터 시드는 앱 코드가 아니라 운영 Supabase RLS 정책 때문에 차단되고 있습니다.")
        st.write("1. 운영 Supabase SQL Editor에서 `docs/supabase-owner-user-id-hotfix.sql` 또는 최신 `setup_supabase.sql`을 적용합니다.")
        st.write("2. 적용 후 앱에서 `첫 계좌 만들기` 또는 `데모 데이터 불러오기`를 다시 실행합니다.")
        st.write("3. 필요하면 `python scripts/verify_streamlit_deployment.py --click-demo --expect-backend supabase`로 재검증합니다.")


def is_hotfix_guide_visible() -> bool:
    """운영 hotfix 상세 안내를 관리자 플래그에서만 노출할지 판별한다."""

    flag = os.getenv("PORTFOLIO_SHOW_HOTFIX_GUIDE", "")
    return str(flag).strip().lower() in {"1", "true", "yes", "on"}


def label_detail_measure(value: Any) -> str:
    return DETAIL_MEASURE_LABELS.get(str(value), str(value))


def label_period(value: Any) -> str:
    return PERIOD_LABELS.get(str(value), str(value))


def latest_date_text(rows: list[dict[str, Any]], field_name: str) -> str:
    """주어진 일자 필드에서 가장 최근 날짜 문자열을 반환한다."""

    dates = [str(row.get(field_name) or "").strip() for row in rows if str(row.get(field_name) or "").strip()]
    return max(dates) if dates else "-"


def period_start_date(period: str) -> date:
    """선택한 기간에 해당하는 시작 날짜를 반환한다."""

    today = date.today()
    normalized = str(period or "6mo")
    if normalized == "today":
        return today
    if normalized == "1mo":
        return today - relativedelta(months=1)
    if normalized == "3mo":
        return today - relativedelta(months=3)
    if normalized == "1y":
        return today - relativedelta(years=1)
    return today - relativedelta(months=6)


def label_product_type(value: Any) -> str:
    return PRODUCT_TYPE_LABELS.get(str(value), str(value))


def label_exchange(value: Any) -> str:
    return EXCHANGE_LABELS.get(str(value), str(value))


def product_search_label(product: dict[str, Any]) -> str:
    name = str(product.get("name") or "").strip()
    code = str(product.get("code") or "").strip()
    product_type = label_product_type(product.get("type"))
    exchange = label_exchange(product.get("exchange"))
    parts: list[str] = []
    for part in (code, product_type, exchange):
        if part and part not in parts:
            parts.append(part)
    return f"{name} | {' | '.join(parts)}" if parts else name


def product_search_option_label(product: dict[str, Any]) -> str:
    """자동완성 후보 버튼에 표시할 2줄 요약 문구를 반환한다."""

    name = str(product.get("name") or "").strip()
    code = str(product.get("code") or "").strip()
    exchange = label_exchange(product.get("exchange"))
    source = str(product.get("source") or "").strip()
    subtitle_parts: list[str] = []
    for part in (code, exchange, source):
        if part and part not in subtitle_parts:
            subtitle_parts.append(part)
    subtitle = " · ".join(subtitle_parts)
    return f"{name}\n{subtitle}" if subtitle else name


def apply_search_product(product: dict[str, Any]) -> None:
    st.session_state[TRADE_SEARCH_QUERY_KEY] = str(product.get("name") or "").strip()
    st.session_state[TRADE_PRODUCT_NAME_KEY] = str(product.get("name") or "").strip()
    st.session_state[TRADE_SYMBOL_KEY] = str(product.get("symbol") or product.get("code") or "").strip()
    selected_type = str(product.get("type") or "").strip().lower()
    selected_exchange = str(product.get("exchange") or "").strip()
    if selected_type in {"fund", "mutualfund"} or selected_exchange == "Fund":
        st.session_state[TRADE_ASSET_TYPE_KEY] = "safe"


def prefill_trade_from_holding(holding: dict[str, Any], marker: str) -> None:
    if st.session_state.get(TRADE_PREFILL_MARKER_KEY) == marker:
        return

    st.session_state[TRADE_SEARCH_QUERY_KEY] = str(holding.get("product_name") or "").strip()
    st.session_state[TRADE_PRODUCT_NAME_KEY] = str(holding.get("product_name") or "").strip()
    st.session_state[TRADE_SYMBOL_KEY] = str(holding.get("symbol") or "").strip()
    st.session_state[TRADE_ASSET_TYPE_KEY] = str(holding.get("asset_type") or "risk")
    st.session_state[TRADE_PREFILL_MARKER_KEY] = marker


def init_state() -> None:
    st.session_state.setdefault("selected_account_id", None)
    st.session_state.setdefault("active_page", PAGES[0])
    st.session_state.setdefault("auth_mode", "sign-in")
    st.session_state.setdefault("rollup_dirty_token", 0)
    st.session_state.setdefault("rollup_sync_signature", "")
    st.session_state.setdefault(PENDING_CONFIRMATION_EMAIL_KEY, "")
    st.session_state.setdefault(AUTH_FEEDBACK_KEY, None)
    st.session_state.setdefault(AUTH_CALLBACK_RERUN_SIGNATURE_KEY, "")
    st.session_state.setdefault(INVALID_ACCOUNT_RERUN_GUARD_KEY, False)
    st.session_state.setdefault(TRADE_SEARCH_QUERY_KEY, "")
    st.session_state.setdefault(TRADE_SYMBOL_KEY, "")
    st.session_state.setdefault(TRADE_PRODUCT_NAME_KEY, "")
    st.session_state.setdefault(TRADE_ASSET_TYPE_KEY, "risk")
    st.session_state.setdefault(TRADE_TYPE_KEY, "buy")
    st.session_state.setdefault(TRADE_QUANTITY_KEY, 1.0)
    st.session_state.setdefault(TRADE_PRICE_KEY, 0.0)
    st.session_state.setdefault(TRADE_DATE_KEY, date.today())
    st.session_state.setdefault(TRADE_NOTES_KEY, "")
    st.session_state.setdefault(TRADE_PREFILL_MARKER_KEY, "")
    st.session_state.setdefault(CASH_FLOW_TYPE_KEY, "personal_deposit")
    st.session_state.setdefault(CASH_FLOW_AMOUNT_KEY, 0)
    st.session_state.setdefault(CASH_FLOW_DATE_KEY, date.today())
    st.session_state.setdefault(CASH_FLOW_NOTES_KEY, "")
    st.session_state.setdefault(TRADE_FORM_RESET_PENDING_KEY, False)
    st.session_state.setdefault(CASH_FLOW_FORM_RESET_PENDING_KEY, False)
    st.session_state.setdefault(TRADE_PAGE_SUCCESS_MESSAGE_KEY, "")


def apply_pending_form_reset(
    session_state: MutableMapping[str, Any],
    *,
    pending_key: str,
    reset_values: dict[str, Any],
) -> None:
    """다음 rerun 시점에만 폼 기본값을 다시 주입한다."""

    if not session_state.pop(pending_key, False):
        return
    for key, value in reset_values.items():
        session_state[key] = value


def consume_session_message(session_state: MutableMapping[str, Any], key: str) -> str:
    """세션 메시지를 한 번만 읽고 비운다."""

    return str(session_state.pop(key, "") or "").strip()


def mark_rollup_dirty() -> None:
    """다음 렌더에서 계좌 롤업 동기화를 다시 실행하도록 세션 토큰을 갱신한다."""

    current = int(st.session_state.get("rollup_dirty_token", 0) or 0)
    st.session_state["rollup_dirty_token"] = current + 1
    st.session_state["rollup_sync_signature"] = ""


def current_rollup_signature(account_id: int) -> str:
    """현재 세션에서 롤업 재실행 여부를 판단할 서명을 반환한다."""

    dirty_token = int(st.session_state.get("rollup_dirty_token", 0) or 0)
    return f"{int(account_id)}:{date.today().isoformat()}:{dirty_token}"


def should_sync_rollup(account_id: int) -> bool:
    """같은 계좌/날짜/세션 상태에서 이미 롤업을 실행했는지 확인한다."""

    return str(st.session_state.get("rollup_sync_signature") or "") != current_rollup_signature(account_id)


def mark_rollup_synced(account_id: int) -> None:
    """현재 계좌 기준 롤업 동기화가 끝났음을 세션에 기록한다."""

    st.session_state["rollup_sync_signature"] = current_rollup_signature(account_id)


def inject_app_styles() -> None:
    """대시보드 중심 UI 정리를 위한 앱 전역 스타일을 주입한다."""

    st.markdown(f"<style>{render_app_stylesheet()}</style>", unsafe_allow_html=True)


def set_auth_feedback(level: str, message: str) -> None:
    st.session_state[AUTH_FEEDBACK_KEY] = {
        "level": str(level or "info"),
        "message": str(message or "").strip(),
    }


def render_auth_feedback() -> None:
    feedback = st.session_state.pop(AUTH_FEEDBACK_KEY, None)
    if not isinstance(feedback, dict):
        return

    message = str(feedback.get("message") or "").strip()
    if not message:
        return

    level = str(feedback.get("level") or "info").strip().lower()
    renderer = getattr(st, level, st.info)
    renderer(message)


def render_auth_landing_header() -> None:
    """초기 인증 카드 상단 브랜드 영역을 렌더링한다."""

    st.markdown(
        """
        <div class="auth-card-brand">
            <h1 class="auth-card-brand__title">자산관리 대장</h1>
            <p class="auth-card-brand__caption">퇴직연금과 주식 통장을 함께 관리하는 개인 자산 기록</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def set_auth_mode(mode: str) -> None:
    """인증 화면 표시 모드를 바꾸고 즉시 다시 그린다."""

    st.session_state["auth_mode"] = str(mode or "sign-in").strip() or "sign-in"
    st.rerun()


def start_demo_workspace_session() -> None:
    """데모 계정 또는 로컬 데모 작업공간으로 진입한다."""

    demo_identity: dict[str, str] | None = None
    try:
        with st.spinner("데모 계정으로 접속하고 테스트 데이터를 준비하는 중입니다..."):
            demo_identity = app_auth.sign_in_demo_user()
            initialize_database()
            result = seed_demo_workspace()
    except Exception as exc:  # noqa: BLE001
        if demo_identity:
            set_auth_feedback("error", f"데모 계정 로그인 후 테스트 데이터 준비에 실패했습니다: {exc}")
            st.rerun()
        st.error(f"데모 접속에 실패했습니다: {exc}")
        return

    st.session_state[PENDING_CONFIRMATION_EMAIL_KEY] = ""
    st.session_state["selected_account_id"] = int(result["selected_account_id"])
    st.session_state["active_page"] = PAGES[0]
    mark_rollup_dirty()
    demo_mode = str(demo_identity.get("mode") or "").strip()
    result_message = str(result.get("message") or "데모 데이터를 준비했습니다.").strip()
    if demo_mode == "supabase":
        demo_email = str(demo_identity.get("email") or "데모 계정").strip()
        set_auth_feedback("success", f"`{demo_email}` 계정으로 접속했습니다. {result_message}")
    else:
        set_auth_feedback("success", f"로컬 데모 작업공간으로 접속했습니다. {result_message}")
    st.rerun()


def render_auth_mode_links(current_mode: str) -> None:
    """카드 하단의 인증 모드 전환 링크를 렌더링한다."""

    current_mode = str(current_mode or "sign-in").strip() or "sign-in"
    with st.container(key="auth-card-links"):
        if current_mode == "sign-in":
            if st.button("새 계정 만들기", key="auth-link-sign-up", width="stretch"):
                set_auth_mode("sign-up")
            if st.button("데모 모드", key="auth-link-demo", width="stretch"):
                set_auth_mode("demo")
            return

        if current_mode == "sign-up":
            if st.button("로그인으로 돌아가기", key="auth-link-sign-in", width="stretch"):
                set_auth_mode("sign-in")
            if st.button("데모 모드", key="auth-link-demo-from-sign-up", width="stretch"):
                set_auth_mode("demo")
            return

        if st.button("로그인으로 돌아가기", key="auth-link-sign-in-from-demo", width="stretch"):
            set_auth_mode("sign-in")
        if st.button("새 계정 만들기", key="auth-link-sign-up-from-demo", width="stretch"):
            set_auth_mode("sign-up")


def render_sign_in_auth_card(auth_enabled: bool) -> None:
    """로그인 카드를 렌더링한다."""

    if not auth_enabled:
        st.info("Supabase 인증 설정이 없어 실제 로그인은 잠시 비활성 상태입니다. 아래 데모 모드는 바로 사용할 수 있습니다.")
        st.markdown('<div class="auth-card-section-label">이메일</div>', unsafe_allow_html=True)
        st.text_input("이메일", key="sign-in-email-disabled", label_visibility="collapsed", placeholder="you@example.com", disabled=True)
        st.markdown('<div class="auth-card-section-label">비밀번호</div>', unsafe_allow_html=True)
        st.text_input("비밀번호", type="password", key="sign-in-password-disabled", label_visibility="collapsed", placeholder="비밀번호 입력", disabled=True)
        st.button("로그인", width="stretch", disabled=True)
        render_auth_mode_links("sign-in")
        return

    with st.form("sign-in-form", clear_on_submit=False):
        st.markdown('<div class="auth-card-section-label">이메일</div>', unsafe_allow_html=True)
        sign_in_email = st.text_input("이메일", key="sign-in-email", label_visibility="collapsed", placeholder="you@example.com")
        st.markdown('<div class="auth-card-section-label">비밀번호</div>', unsafe_allow_html=True)
        sign_in_password = st.text_input("비밀번호", type="password", key="sign-in-password", label_visibility="collapsed", placeholder="비밀번호 입력")
        sign_in_submitted = st.form_submit_button("로그인", width="stretch", disabled=not auth_enabled)

    render_auth_mode_links("sign-in")

    if not sign_in_submitted:
        return

    try:
        app_auth.sign_in(email=sign_in_email, password=sign_in_password)
    except Exception as exc:  # noqa: BLE001
        message = str(exc)
        if "Email not confirmed" in message:
            st.session_state[PENDING_CONFIRMATION_EMAIL_KEY] = str(sign_in_email or "").strip()
            set_auth_feedback("warning", "이 이메일은 아직 확인되지 않았습니다. 위의 버튼으로 확인 메일을 다시 보내고, 가장 최근 메일의 링크를 열어 주세요.")
            st.rerun()
        st.error(message)
    else:
        st.session_state[PENDING_CONFIRMATION_EMAIL_KEY] = ""
        st.success("로그인되었습니다.")
        st.rerun()


def render_sign_up_auth_card(auth_enabled: bool) -> None:
    """회원가입 카드를 렌더링한다."""

    st.markdown('<div class="auth-card-mode">새 계정 만들기</div>', unsafe_allow_html=True)
    st.markdown('<p class="auth-card-helper">확인 메일을 거쳐 개인 작업공간을 만들고, 이후에는 같은 계정으로 계속 이어서 사용합니다.</p>', unsafe_allow_html=True)
    if not auth_enabled:
        st.info("Supabase 인증 설정이 없어 실제 계정 만들기는 잠시 비활성 상태입니다. 설정 전에는 데모 모드만 사용할 수 있습니다.")
        st.text_input("이메일", key="sign-up-email-disabled", placeholder="you@example.com", disabled=True)
        st.text_input("비밀번호", type="password", key="sign-up-password-disabled", placeholder="비밀번호 입력", disabled=True)
        st.text_input("비밀번호 확인", type="password", key="sign-up-password-confirm-disabled", placeholder="비밀번호 다시 입력", disabled=True)
        st.button("계정 만들기", width="stretch", disabled=True)
        render_auth_mode_links("sign-up")
        return

    with st.form("sign-up-form", clear_on_submit=False):
        sign_up_email = st.text_input("이메일", key="sign-up-email", placeholder="you@example.com")
        sign_up_password = st.text_input("비밀번호", type="password", key="sign-up-password", placeholder="비밀번호 입력")
        confirm_password = st.text_input("비밀번호 확인", type="password", key="sign-up-password-confirm", placeholder="비밀번호 다시 입력")
        sign_up_submitted = st.form_submit_button("계정 만들기", width="stretch", disabled=not auth_enabled)

    render_auth_mode_links("sign-up")

    if not sign_up_submitted:
        return

    if sign_up_password != confirm_password:
        st.error("비밀번호가 서로 다릅니다.")
        return

    try:
        response = app_auth.sign_up(email=sign_up_email, password=sign_up_password)
    except Exception as exc:  # noqa: BLE001
        st.error(str(exc))
        return

    if getattr(response, "session", None):
        st.session_state[PENDING_CONFIRMATION_EMAIL_KEY] = ""
        st.success("계정을 만들고 바로 로그인했습니다.")
        st.rerun()

    st.session_state[PENDING_CONFIRMATION_EMAIL_KEY] = str(sign_up_email or "").strip()
    set_auth_feedback(
        "info",
        "계정을 만들었습니다. 확인 메일을 열어 주세요. 예전 링크가 안 되면 위의 버튼으로 새 메일을 다시 보내면 됩니다.",
    )
    st.rerun()


def render_demo_auth_card() -> None:
    """데모 모드 카드를 렌더링한다."""

    st.markdown('<div class="auth-card-mode">데모 모드</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="auth-card-helper">로그인 없이 바로 샘플 작업공간으로 들어가 약 5년치 투자 흐름과 자산 배분 화면을 확인할 수 있습니다.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="auth-demo-mini-list">
            <div class="auth-demo-mini-item">
                <div class="auth-demo-mini-item__title">5년 투자 이력</div>
                <div class="auth-demo-mini-item__desc">입금, 매수, 매도, 스냅샷이 모두 준비된 상태로 시작합니다.</div>
            </div>
            <div class="auth-demo-mini-item">
                <div class="auth-demo-mini-item__title">혼합 포트폴리오 예시</div>
                <div class="auth-demo-mini-item__desc">반도체, 배당, 방산, 채권 등 손익이 섞인 예시 자산 구성을 바로 볼 수 있습니다.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key="auth-demo-primary-action"):
        demo_submitted = st.button("데모 작업공간 시작하기", key="auth-demo-entry-compact", width="stretch")
    if app_auth.has_demo_credentials():
        st.markdown('<p class="auth-card-note">설정된 데모 계정이 우선 사용되며, 없으면 로컬 데모 작업공간으로 연결됩니다.</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="auth-card-note">현재는 로컬 데모 작업공간으로 바로 연결됩니다.</p>', unsafe_allow_html=True)

    render_auth_mode_links("demo")

    if demo_submitted:
        start_demo_workspace_session()


def render_demo_access_entry() -> None:
    """초기 인증 화면의 데모 접속 패널을 렌더링한다."""

    with st.container(border=True, key="auth-demo-panel"):
        st.markdown('<div class="auth-panel-eyebrow">로그인 없이 바로 확인</div>', unsafe_allow_html=True)
        st.markdown('<h3 class="auth-panel-title">데모 작업공간 시작</h3>', unsafe_allow_html=True)
        st.markdown(
            '<p class="auth-panel-caption">약 5년치 예시 투자 이력, 현금 흐름, 스냅샷 데이터가 준비된 작업공간으로 즉시 들어갑니다.</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="auth-demo-points">
                <div class="auth-demo-point">
                    <div class="auth-demo-point__title">5년 투자 일지</div>
                    <div class="auth-demo-point__desc">입금, 매수, 매도까지 약 5년치 흐름이 이미 채워져 있습니다.</div>
                </div>
                <div class="auth-demo-point">
                    <div class="auth-demo-point__title">테마 분산 예시</div>
                    <div class="auth-demo-point__desc">반도체, 원자력, 방산, 배당, 채권 등 손익이 섞인 샘플 포지션을 바로 볼 수 있습니다.</div>
                </div>
                <div class="auth-demo-point">
                    <div class="auth-demo-point__title">계정 없이 테스트</div>
                    <div class="auth-demo-point__desc">데모 계정이 있으면 그 계정으로, 없으면 로컬 작업공간으로 연결됩니다.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        demo_submitted = st.button(
            "데모 작업공간 시작하기",
            key="auth-demo-entry",
            icon=":material/rocket_launch:",
            width="stretch",
            type="primary",
        )
        if app_auth.has_demo_credentials():
            st.caption("설정된 데모 계정이 우선 사용되며, 없으면 로컬 데모 작업공간으로 연결됩니다.")
        else:
            st.caption("현재는 로컬 데모 작업공간으로 바로 연결됩니다.")

    if not demo_submitted:
        return
    start_demo_workspace_session()


def clear_query_params() -> None:
    for key in list(st.query_params.keys()):
        del st.query_params[key]


def auth_callback_signature() -> str:
    """현재 URL의 인증 콜백 파라미터를 1회 처리용 서명으로 반환한다."""

    for key in ("error_description", "code", "token_hash"):
        value = str(st.query_params.get(key) or "").strip()
        if value:
            return f"{key}:{value}"
    return ""


def handle_auth_callback() -> bool:
    callback_signature = auth_callback_signature()
    if callback_signature and st.session_state.get(AUTH_CALLBACK_RERUN_SIGNATURE_KEY) == callback_signature:
        clear_query_params()
        return False

    error_description = str(st.query_params.get("error_description") or "").strip()
    error_code = str(st.query_params.get("error_code") or "").strip()
    if error_description:
        suffix = f" ({error_code})" if error_code else ""
        set_auth_feedback("error", f"이메일 확인에 실패했습니다{suffix}: {error_description}")
        st.session_state[AUTH_CALLBACK_RERUN_SIGNATURE_KEY] = callback_signature
        clear_query_params()
        return True

    auth_code = str(st.query_params.get("code") or "").strip()
    if auth_code:
        try:
            app_auth.exchange_code_for_session(auth_code)
        except Exception as exc:  # noqa: BLE001
            set_auth_feedback("error", f"이메일 확인은 되었지만 로그인 처리에 실패했습니다: {exc}")
        else:
            set_auth_feedback("success", "이메일 확인이 완료되어 바로 로그인했습니다.")
            st.session_state[PENDING_CONFIRMATION_EMAIL_KEY] = ""
        st.session_state[AUTH_CALLBACK_RERUN_SIGNATURE_KEY] = callback_signature
        clear_query_params()
        return True

    token_hash = str(st.query_params.get("token_hash") or "").strip()
    if token_hash:
        otp_type = str(st.query_params.get("type") or "email").strip()
        try:
            app_auth.verify_otp(token_hash=token_hash, otp_type=otp_type)
        except Exception as exc:  # noqa: BLE001
            set_auth_feedback("error", f"이메일 확인에 실패했습니다: {exc}")
        else:
            set_auth_feedback("success", "이메일 확인이 완료되었습니다. 이제 로그인해 주세요.")
            st.session_state[PENDING_CONFIRMATION_EMAIL_KEY] = ""
        st.session_state[AUTH_CALLBACK_RERUN_SIGNATURE_KEY] = callback_signature
        clear_query_params()
        return True

    st.session_state[AUTH_CALLBACK_RERUN_SIGNATURE_KEY] = ""
    return False


def account_label(account: dict[str, Any]) -> str:
    account_type = label_account_type(account.get("account_type") or "retirement")
    return f"{account['name']} | {account_type}"


def render_dashboard_metric_strip(cards: list[dict[str, str]]) -> None:
    """대시보드 상단 핵심 지표를 카드 스트립 형태로 렌더링한다."""

    columns = st.columns(len(cards), gap="small")
    for column, card in zip(columns, cards):
        label = html.escape(str(card.get("label") or ""))
        value = html.escape(str(card.get("value") or ""))
        note = str(card.get("note") or "").strip()
        action = str(card.get("action") or "").strip()
        tone = str(card.get("tone") or "").strip()
        value_class = "dashboard-metric-card__value"
        if tone in {"accent", "positive", "negative"}:
            value_class += f" dashboard-metric-card__value--{tone}"
        note_html = f'<div class="dashboard-metric-card__note">{html.escape(note)}</div>' if note else ""
        action_html = f'<div class="dashboard-metric-card__action">{html.escape(action)}</div>' if action else ""
        card_html = (
            '<div class="dashboard-metric-card">'
            '<div>'
            '<div class="dashboard-metric-card__top">'
            f'<div class="dashboard-metric-card__label">{label}</div>'
            f"{action_html}"
            "</div>"
            f'<div class="{value_class}">{value}</div>'
            "</div>"
            f"{note_html}"
            "</div>"
        )
        with column:
            st.markdown(card_html, unsafe_allow_html=True)


def render_dashboard_summary_card(label: str, value: str, *, tone: str = "", action: str = "", actionable: bool = False) -> None:
    """기본 요약 카드 본문을 렌더링한다."""

    value_class = "dashboard-summary-card__value"
    if tone in {"accent", "positive", "negative"}:
        value_class += f" dashboard-summary-card__value--{tone}"
    field_class = "dashboard-summary-card__field"
    if actionable:
        field_class += " dashboard-summary-card__field--actionable"
    action_caption = html.escape(action) if action else ""
    action_modifier = "" if action else " dashboard-summary-card__action--ghost"
    action_html = (
        '<div class="dashboard-summary-card__header">'
        f'<div class="dashboard-summary-card__label">{html.escape(label)}</div>'
        f'<div class="dashboard-summary-card__action{action_modifier}">{action_caption}</div>'
        "</div>"
    )
    st.markdown(
        (
            f'<div class="{field_class}">'
            f"{action_html}"
            f'<div class="{value_class}">{html.escape(value)}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


@st.fragment
def render_dashboard_cash_card(account_id: int, display_cash: float) -> None:
    """보유 현금 카드 편집 UI를 부분 리런 단위로 렌더링한다."""

    cash_edit_state_key = f"dashboard-cash-editing:{account_id}"
    cash_edit_amount_key = f"dashboard-cash-edit-amount:{account_id}"

    with st.container(border=True, key="dashboard-card-cash"):
        if st.session_state.get(cash_edit_state_key, False):
            if cash_edit_amount_key not in st.session_state:
                st.session_state[cash_edit_amount_key] = int(round(display_cash))
            st.markdown(
                '<div class="dashboard-summary-card__label">보유 현금</div>',
                unsafe_allow_html=True,
            )
            st.number_input(
                "목표 현금 잔액",
                min_value=0,
                step=100000,
                key=cash_edit_amount_key,
                label_visibility="collapsed",
            )
            save_col, cancel_col = st.columns(2, gap="small")
            with save_col:
                if st.button("저장", key=f"dashboard-cash-save:{account_id}", width="stretch"):
                    try:
                        adjust_cash_balance(
                            account_id,
                            target_amount=float(int(st.session_state.get(cash_edit_amount_key, round(display_cash)) or 0)),
                            trade_date=date.today().isoformat(),
                            notes="대시보드 현금 카드 조정",
                        )
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        st.session_state[cash_edit_state_key] = False
                        mark_rollup_dirty()
                        st.rerun()
            with cancel_col:
                if st.button("취소", key=f"dashboard-cash-cancel:{account_id}", width="stretch"):
                    st.session_state[cash_edit_state_key] = False
                    st.rerun(scope="fragment")
        else:
            render_dashboard_summary_card("보유 현금", format_won(display_cash), actionable=True)
            with st.container(key="dashboard-cash-card-overlay"):
                if st.button(
                    "수정",
                    key=f"dashboard-cash-card-trigger-button:{account_id}",
                ):
                    st.session_state[cash_edit_state_key] = True
                    st.session_state[cash_edit_amount_key] = int(round(display_cash))
                    st.rerun(scope="fragment")


def render_dashboard_total_value_card(account_id: int, display_total_value: float, holdings: list[dict[str, Any]]) -> None:
    """현재 평가액 카드와 실시간 가격 갱신 버튼을 함께 렌더링한다."""

    with st.container(border=True, key="dashboard-card-total-value"):
        render_dashboard_summary_card("현재 평가액", format_won(display_total_value), actionable=True)
        with st.container(key="dashboard-total-value-refresh-overlay"):
            refresh_submitted = st.button(
                "실시간",
                key=f"dashboard-live-refresh:{account_id}",
                disabled=not bool(holdings),
            )

    if not refresh_submitted:
        return

    with st.status("현재가 갱신 중...", expanded=True) as refresh_status:
        updated, errors = refresh_prices(holdings)
        if errors:
            refresh_status.update(label="현재가 갱신 일부 실패", state="error")
        else:
            refresh_status.update(label="현재가 갱신 완료", state="complete")
    if updated:
        mark_rollup_dirty()
        st.success(f"{updated}개 종목 가격을 갱신했습니다.")
    if errors:
        st.warning("\n".join(errors))
    st.rerun()


def render_dashboard_section_header(
    title: str,
    description: str,
    *,
    compact: bool = False,
    status_text: str = "",
    status_tone: str = "live",
    status_palette_colors: list[str] | tuple[str, ...] | None = None,
) -> None:
    """대시보드 섹션 헤더를 동일한 타이포 체계로 렌더링한다."""

    wrapper_class = "dashboard-section-header dashboard-section-header--compact" if compact else "dashboard-section-header"
    title_class = "dashboard-section-header__title dashboard-section-header__title--compact" if compact else "dashboard-section-header__title"
    status_items: list[str] = []
    if status_text:
        status_items.append(
            f'<div class="dashboard-load-status dashboard-load-status--{html.escape(status_tone)}">'
            '<span class="dashboard-load-status__dot"></span>'
            f'<span class="dashboard-load-status__text">{html.escape(status_text)}</span>'
            "</div>"
        )
    if status_palette_colors:
        palette_segments = "".join(
            f'<span class="dashboard-load-palette__segment" style="background:{html.escape(color)};"></span>'
            for color in status_palette_colors
        )
        status_items.append(
            '<div class="dashboard-load-palette" title="자산 배분 수익률 색상 팔레트">'
            '<span class="dashboard-load-palette__label">-</span>'
            f'<div class="dashboard-load-palette__bar">{palette_segments}</div>'
            '<span class="dashboard-load-palette__label">+</span>'
            "</div>"
        )
    status_group_html = ""
    if status_items:
        status_group_html = f'<div class="dashboard-section-header__status-group">{"".join(status_items)}</div>'
    st.markdown(
        (
            f'<div class="{wrapper_class}">'
            '<div class="dashboard-section-header__top">'
            f'<div class="{title_class}">{html.escape(title)}</div>'
            f"{status_group_html}"
            "</div>"
            f'<p class="dashboard-section-header__caption">{html.escape(description)}</p>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_dashboard_reference_time(reference_time_text: str) -> None:
    """대시보드 요약 카드 아래에 기준시각을 우측 정렬로 표시한다."""

    st.markdown(
        (
            '<div class="dashboard-reference-time">'
            '<span class="dashboard-reference-time__label">기준시각</span>'
            f'<span class="dashboard-reference-time__value">{html.escape(reference_time_text)}</span>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def normalize_holding_symbol(value: Any) -> str:
    """보유 종목 선택에 쓸 심볼 키를 정규화한다."""

    return str(value or "").strip().upper()


def dashboard_holding_selection_key(account_id: int) -> str:
    """계좌별 대시보드 선택 종목 세션 키를 반환한다."""

    return f"dashboard-selected-holding:{int(account_id)}"


def dashboard_trend_period_key(account_id: int) -> str:
    """계좌별 대시보드 추이 기간 세션 키를 반환한다."""

    return f"trend-period:{int(account_id)}"


def extract_dashboard_chart_symbol(event_payload: Any) -> str:
    """ECharts 클릭/선택 payload에서 원시 선택 값을 추출한다."""

    if not isinstance(event_payload, dict):
        return ""
    selection_payload = event_payload
    nested_selection = event_payload.get("selection")
    if isinstance(nested_selection, dict):
        selection_payload = nested_selection
    elif isinstance(event_payload.get("chart_event"), dict):
        selection_payload = event_payload["chart_event"]

    if isinstance(selection_payload.get("points"), list) and selection_payload["points"]:
        first_point = selection_payload["points"][0]
        if isinstance(first_point, dict):
            return str(first_point.get("name") or "").strip()
    return str(
        selection_payload.get("selection_symbol")
        or selection_payload.get("symbol")
        or selection_payload.get("name")
        or ""
    ).strip()


def resolve_dashboard_selected_symbol(holdings: list[dict[str, Any]], event_payload: Any) -> str:
    """차트에서 선택한 이름/심볼을 현재 보유 종목 심볼로 해석한다."""

    raw_value = extract_dashboard_chart_symbol(event_payload)
    normalized_value = normalize_holding_symbol(raw_value)
    if not normalized_value:
        return ""
    if normalized_value == "CASH" or raw_value == "예수금":
        return "CASH"

    for holding in holdings:
        holding_symbol = normalize_holding_symbol(holding.get("symbol"))
        holding_name = str(holding.get("product_name") or "").strip()
        if holding_symbol == normalized_value or normalize_holding_symbol(holding_name) == normalized_value:
            return holding_symbol
    return ""


def sync_dashboard_selected_holding(
    account_id: int,
    event_payload: Any,
    *,
    holdings: list[dict[str, Any]],
) -> bool:
    """차트 클릭 결과를 계좌별 선택 종목 세션 상태와 동기화한다."""

    selected_symbol = resolve_dashboard_selected_symbol(holdings, event_payload)
    if not selected_symbol:
        return False

    selection_key = dashboard_holding_selection_key(account_id)
    current_symbol = normalize_holding_symbol(st.session_state.get(selection_key))
    if current_symbol == selected_symbol:
        return False

    st.session_state[selection_key] = selected_symbol
    return True


def dashboard_selected_holding_name(holdings: list[dict[str, Any]], selected_symbol: str | None) -> str:
    """현재 선택된 심볼에 대응하는 보유 종목 표시명을 반환한다."""

    normalized_symbol = normalize_holding_symbol(selected_symbol)
    if normalized_symbol == "CASH":
        return "예수금"
    for holding in holdings:
        holding_symbol = normalize_holding_symbol(holding.get("symbol"))
        if holding_symbol == normalized_symbol:
            return str(holding.get("product_name") or holding.get("symbol") or normalized_symbol)
    return normalized_symbol


def dashboard_live_refresh_interval(account_id: int, holdings: list[dict[str, Any]]) -> str | None:
    """실시간 worker 상태와 보유 종목 조건에 맞춰 대시보드 새로고침 간격을 반환한다."""

    status = get_realtime_worker_status(account_id) or {}
    if str(status.get("connection_state") or "").strip().lower() == "connected":
        return "10s"
    if is_recent_realtime_quote(latest_realtime_quote_time(account_id)):
        return "10s"
    if any(is_kis_domestic_symbol(str(holding.get("symbol") or "").strip()) for holding in holdings):
        return "30s"
    return None


def parse_realtime_timestamp(value: str | None) -> datetime | None:
    """실시간 quote 시각 문자열을 KST 기준 aware datetime으로 파싱한다."""

    normalized = str(value or "").strip()
    if not normalized:
        return None

    candidate = normalized.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=KST_TIMEZONE)
    return parsed.astimezone(KST_TIMEZONE)


def format_dashboard_reference_time(value: Any) -> str:
    """대시보드 기준시각을 `YYYY-MM-DD HH:MM:SS` 형식으로 반환한다."""

    parsed = parse_realtime_timestamp(str(value or "").strip())
    if parsed is not None:
        return parsed.strftime("%Y-%m-%d %H:%M:%S")

    raw_value = str(value or "").strip()
    if not raw_value:
        return "-"

    fallback_timestamp = pd.to_datetime(raw_value, errors="coerce")
    if pd.isna(fallback_timestamp):
        return raw_value
    if fallback_timestamp.tzinfo is None:
        fallback_timestamp = fallback_timestamp.tz_localize(KST_TIMEZONE)
    else:
        fallback_timestamp = fallback_timestamp.tz_convert(KST_TIMEZONE)
    return fallback_timestamp.strftime("%Y-%m-%d %H:%M:%S")


def is_recent_realtime_quote(
    quote_time: str | None,
    *,
    now_value: datetime | None = None,
    freshness_window: timedelta = REALTIME_QUOTE_FRESHNESS,
) -> bool:
    """최근 실시간 quote가 freshness window 안에 있으면 True를 반환한다."""

    parsed_quote_time = parse_realtime_timestamp(quote_time)
    if parsed_quote_time is None:
        return False

    current_time = now_value or datetime.now(KST_TIMEZONE)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=KST_TIMEZONE)
    else:
        current_time = current_time.astimezone(KST_TIMEZONE)

    return current_time - parsed_quote_time <= freshness_window


def dashboard_allocation_status(
    account_id: int,
    holdings: list[dict[str, Any]],
    *,
    has_allocation_data: bool,
) -> tuple[str, str]:
    """자산 배분 헤더에 표시할 실시간 상태 문구와 톤을 계산한다."""

    if not has_allocation_data:
        return ("데이터 대기", "idle")
    if not holdings:
        return ("실시간 대상 없음", "idle")

    worker_status = get_realtime_worker_status(account_id) or {}
    connection_state = str(worker_status.get("connection_state") or "").strip().lower()
    quote_time = latest_realtime_quote_time(account_id)
    if connection_state == "connected":
        if str(quote_time or "").strip():
            return ("실시간 연동 중", "live")
        return ("실시간 연결 중", "live")
    if is_recent_realtime_quote(quote_time) and any(
        is_kis_domestic_symbol(str(holding.get("symbol") or "").strip()) for holding in holdings
    ):
        return ("실시간 반영 중", "live")
    return ("지연 데이터 표시 중", "stale")


def interpolate_hex_color(start_hex: str, end_hex: str, ratio: float) -> str:
    """두 색상 사이를 0~1 비율로 보간한다."""

    ratio = max(0.0, min(1.0, float(ratio)))
    start = start_hex.lstrip("#")
    end = end_hex.lstrip("#")
    start_rgb = tuple(int(start[index : index + 2], 16) for index in (0, 2, 4))
    end_rgb = tuple(int(end[index : index + 2], 16) for index in (0, 2, 4))
    mixed = tuple(round(source + (target - source) * ratio) for source, target in zip(start_rgb, end_rgb))
    return "#{:02X}{:02X}{:02X}".format(*mixed)


def profit_rate_color(rate: float, minimum: float, maximum: float) -> str:
    """수익률 구간에 따라 트리맵 타일 색상을 계산한다."""

    rate = float(rate or 0)
    minimum = float(minimum or 0)
    maximum = float(maximum or 0)
    if rate <= 0:
        if minimum >= 0:
            return "#F2D675"
        ratio = (rate - minimum) / (0 - minimum) if minimum != 0 else 1.0
        return interpolate_hex_color("#F1646C", "#F2D675", ratio)
    if maximum <= 0:
        return "#F2D675"
    ratio = rate / maximum if maximum != 0 else 0.0
    return interpolate_hex_color("#F2D675", "#78CB84", ratio)


def holdings_profit_rate_stats(frame: pd.DataFrame, selected_symbol: str | None = None) -> dict[str, Any]:
    """범례와 하이라이트에 필요한 수익률 범위와 선택 종목 정보를 계산한다."""

    if frame.empty:
        return {
            "minimum": 0.0,
            "maximum": 0.0,
            "selected_name": "",
            "selected_symbol": "",
            "selected_rate": None,
            "selected_position": None,
        }

    working = frame.copy()
    working["selection_symbol"] = working["symbol"].astype(str).str.strip().str.upper()
    minimum = float(working["profit_rate"].min() or 0)
    maximum = float(working["profit_rate"].max() or 0)
    selected_key = normalize_holding_symbol(selected_symbol)
    selected_row = working.loc[working["selection_symbol"] == selected_key].head(1) if selected_key else pd.DataFrame()
    if selected_row.empty:
        return {
            "minimum": minimum,
            "maximum": maximum,
            "selected_name": "",
            "selected_symbol": "",
            "selected_rate": None,
            "selected_position": None,
        }

    selected_rate = float(selected_row.iloc[0]["profit_rate"] or 0)
    if maximum == minimum:
        position = 50.0
    else:
        position = (selected_rate - minimum) / (maximum - minimum) * 100
    return {
        "minimum": minimum,
        "maximum": maximum,
        "selected_name": str(selected_row.iloc[0]["product_name"] or selected_row.iloc[0]["symbol"] or "선택 종목"),
        "selected_symbol": selected_key,
        "selected_rate": selected_rate,
        "selected_position": max(0.0, min(100.0, position)),
    }


def render_dashboard_treemap_legend(stats: dict[str, Any]) -> None:
    """트리맵 하단 범례를 수익률 기준 커스텀 HTML로 렌더링한다."""

    minimum = float(stats.get("minimum") or 0)
    maximum = float(stats.get("maximum") or 0)
    selected_name = str(stats.get("selected_name") or "").strip()
    selected_rate = stats.get("selected_rate")
    selected_position = stats.get("selected_position")
    marker_html = ""
    selected_caption = "아래 하이라이트 슬라이더에서 종목을 고르면 같은 종목을 강조하고 수익률 위치를 표시합니다."
    if selected_name and selected_rate is not None and selected_position is not None:
        marker_html = (
            '<div class="dashboard-treemap-legend__marker" '
            f'style="left: calc({float(selected_position):.2f}% - 9px);">'
            f'<div class="dashboard-treemap-legend__marker-label">{html.escape(selected_name)} {html.escape(format_pct(float(selected_rate)))}</div>'
            "</div>"
        )
        selected_caption = f"선택 종목: {selected_name} {format_pct(float(selected_rate))}"
    legend_segments_html = "".join(
        f'<span class="dashboard-treemap-legend__segment" style="background:{color};"></span>'
        for color in FEARGREED_TREEMAP_PALETTE
    )

    st.markdown(
        (
            '<div class="dashboard-treemap-legend">'
            '<div class="dashboard-treemap-legend__range">'
            '<div class="dashboard-treemap-legend__bar">'
            f'<div class="dashboard-treemap-legend__segments">{legend_segments_html}</div>'
            f"{marker_html}"
            "</div>"
            '<div class="dashboard-treemap-legend__labels">'
            f'<span>{html.escape(format_pct(minimum))}</span>'
            '<span>현재 종목 수익률 기준</span>'
            f'<span>{html.escape(format_pct(maximum))}</span>'
            "</div>"
            "</div>"
            f'<div class="dashboard-treemap-legend__hint">{html.escape(selected_caption)}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def holding_highlight_slider_choices(frame: pd.DataFrame) -> list[dict[str, str]]:
    """자산 배분 하이라이트 슬라이더에 쓸 종목 목록을 수익률 순으로 반환한다."""

    if frame.empty:
        return []

    working = frame.copy().sort_values(["profit_rate", "current_value"], ascending=[True, False])
    choices: list[dict[str, str]] = [{"label": "선택 안 함", "symbol": ""}]
    seen: set[str] = set()
    for row in working.to_dict(orient="records"):
        symbol = normalize_holding_symbol(row.get("symbol"))
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        product_name = str(row.get("product_name") or symbol).strip()
        rate = float(row.get("profit_rate") or 0)
        choices.append(
            {
                "label": f"{product_name} {format_pct(rate)}",
                "symbol": symbol,
            }
        )
    return choices


def style_dashboard_altair_chart(chart: alt.Chart, *, height: int) -> alt.Chart:
    """대시보드 Altair 차트에 공통 높이와 축 스타일을 적용한다."""

    return (
        chart.properties(height=height)
        .configure(background="transparent")
        .configure_view(stroke=None)
        .configure_axis(
            gridColor=FEARGREED_BORDER_COLOR,
            domainColor=FEARGREED_BORDER_COLOR,
            tickColor=FEARGREED_BORDER_COLOR,
            labelColor=FEARGREED_MID_TEXT_COLOR,
            titleColor=FEARGREED_MID_TEXT_COLOR,
            titleFontWeight=700,
            labelFontSize=12,
            titleFontSize=12,
        )
    )


def refresh_prices(holdings: list[dict[str, Any]]) -> tuple[int, list[str]]:
    updated = 0
    errors: list[str] = []
    for holding in holdings:
        try:
            result = fetch_latest_price(holding["symbol"])
            set_holding_price(int(holding["id"]), float(result["price"]), str(result["as_of"]))
            updated += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{holding['product_name']} ({holding['symbol']}): {exc}")
    return updated, errors


def _format_intraday_as_of(value: Any) -> str:
    raw_value = str(value or "").strip()
    if not raw_value:
        return "당일 데이터 없음"
    try:
        timestamp = pd.Timestamp(raw_value)
    except Exception:  # noqa: BLE001
        return raw_value
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize(KST_TIMEZONE)
    else:
        timestamp = timestamp.tz_convert(KST_TIMEZONE)
    return f"기준시각 {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


def _build_intraday_sparkline_svg(
    values: list[float],
    *,
    positive: bool,
    width: int = 188,
    height: int = 40,
) -> str:
    if not values:
        return (
            '<div style="height:40px; display:flex; align-items:center; justify-content:center; '
            f'color:{FEARGREED_MUTED_TEXT_COLOR}; font-size:10px;">당일 데이터 없음</div>'
        )

    numeric_values = [float(value) for value in values]
    minimum = min(numeric_values)
    maximum = max(numeric_values)
    stroke_color = FEARGREED_UP_COLOR if positive else FEARGREED_DOWN_COLOR
    fill_color = CHART_ACCENT_SOFT_COLOR if positive else _rgba_from_hex(FEARGREED_DOWN_COLOR, 0.18)
    left_pad = 4
    top_pad = 3
    usable_width = max(width - left_pad * 2, 1)
    usable_height = max(height - top_pad * 2, 1)
    point_count = max(len(numeric_values) - 1, 1)

    points: list[str] = []
    for index, value in enumerate(numeric_values):
        x = left_pad + usable_width * (index / point_count)
        if maximum == minimum:
            y = top_pad + usable_height / 2
        else:
            y = top_pad + usable_height * (1 - ((value - minimum) / (maximum - minimum)))
        points.append(f"{x:.1f},{y:.1f}")

    line_points = " ".join(points)
    baseline = height - top_pad
    area_points = f"{left_pad:.1f},{baseline:.1f} {line_points} {width - left_pad:.1f},{baseline:.1f}"
    last_point = points[-1]
    return (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="당일 가격 추세">'
        f'<polyline points="{area_points}" fill="{fill_color}" stroke="none"></polyline>'
        f'<polyline points="{line_points}" fill="none" stroke="{stroke_color}" stroke-width="2.2" '
        'stroke-linecap="round" stroke-linejoin="round"></polyline>'
        f'<circle cx="{last_point.split(",")[0]}" cy="{last_point.split(",")[1]}" r="2.8" '
        f'fill="{stroke_color}" stroke="#FFFFFF" stroke-width="1"></circle>'
        "</svg>"
    )


def _build_treemap_market_snapshot_lookup(holdings: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """트리맵 tooltip에 사용할 종목별 당일 시세 요약 맵을 만든다."""

    snapshots: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for holding in holdings:
        symbol = normalize_holding_symbol(holding.get("symbol"))
        if not symbol or symbol == "CASH" or symbol in seen:
            continue
        seen.add(symbol)
        try:
            snapshot = fetch_intraday_price_snapshot(symbol)
        except Exception:  # noqa: BLE001
            snapshot = {}
        snapshots[symbol] = snapshot if isinstance(snapshot, dict) else {}
    return snapshots


def _attach_leaf_market_details(
    leaf: dict[str, Any],
    snapshot_lookup: dict[str, dict[str, Any]],
) -> None:
    symbol = normalize_holding_symbol(leaf.get("symbol") or leaf.get("selection_symbol"))
    if symbol == "CASH":
        revenue_value = float(leaf.get("revenue_value") or leaf.get("value") or 0)
        leaf["node_kind"] = "holding"
        leaf["quote_currency"] = "KRW"
        leaf["current_price_value"] = round(revenue_value, 4)
        leaf["current_price_text"] = format_won(revenue_value)
        leaf["day_change_rate"] = None
        leaf["day_change_text"] = "-"
        leaf["holding_profit_text"] = "-"
        leaf["sparkline_svg"] = (
            '<div style="height:40px; display:flex; align-items:center; justify-content:center; '
            f'color:{FEARGREED_MUTED_TEXT_COLOR}; font-size:10px;">현금 자산은 장중 추세가 없습니다</div>'
        )
        leaf["intraday_as_of"] = "현금 잔액"
        return

    raw_snapshot = snapshot_lookup.get(symbol) or {}
    prices = [float(value) for value in (raw_snapshot.get("series") or []) if value is not None]
    quote_currency = _quote_currency_for_symbol(symbol, str(raw_snapshot.get("currency") or "KRW"))
    fallback_current_price = float(leaf.get("current_price") or 0)
    current_price = raw_snapshot.get("current_price")
    current_price_value = float(current_price) if current_price not in (None, "") else fallback_current_price
    day_change_rate = raw_snapshot.get("day_change_rate")
    day_change_numeric = float(day_change_rate) if day_change_rate not in (None, "") else None
    holding_profit_rate = leaf.get("profit_rate")
    holding_profit_numeric = float(holding_profit_rate) if holding_profit_rate not in (None, "") else None
    sparkline_positive = bool(day_change_numeric is None or day_change_numeric >= 0)
    leaf["node_kind"] = "holding"
    leaf["quote_currency"] = quote_currency
    leaf["current_price_value"] = round(current_price_value, 4)
    leaf["current_price_text"] = _format_quote_price(current_price_value, currency=quote_currency)
    leaf["day_change_rate"] = round(day_change_numeric, 4) if day_change_numeric is not None else None
    leaf["day_change_text"] = format_pct(day_change_numeric) if day_change_numeric is not None else "-"
    leaf["holding_profit_text"] = format_pct(holding_profit_numeric) if holding_profit_numeric is not None else "-"
    leaf["sparkline_svg"] = _build_intraday_sparkline_svg(prices, positive=sparkline_positive)
    leaf["intraday_as_of"] = _format_intraday_as_of(raw_snapshot.get("as_of"))


def _rollup_treemap_node_values(
    node: dict[str, Any],
    *,
    snapshot_lookup: dict[str, dict[str, Any]],
) -> tuple[float, float, float]:
    children = node.get("children") or []
    if not children:
        revenue_value = float(node.get("value") or 0)
        profit_rate = node.get("profit_rate")
        node["revenue_value"] = round(revenue_value, 4)
        child_rate = round(float(profit_rate or 0), 4)
        node["value"] = [round(revenue_value, 4), child_rate]
        node["itemStyle"] = {
            "borderColor": "#F8FAFC",
            "borderWidth": 1,
            "gapWidth": 1,
        }
        _attach_leaf_market_details(node, snapshot_lookup)
        if profit_rate is None:
            return revenue_value, 0.0, 0.0
        return revenue_value, revenue_value * float(profit_rate), revenue_value

    node["node_kind"] = "group"
    total_value = 0.0
    weighted_rate_total = 0.0
    weighted_rate_weight = 0.0
    for child in children:
        child_value, child_weighted_total, child_weight = _rollup_treemap_node_values(
            child,
            snapshot_lookup=snapshot_lookup,
        )
        total_value += child_value
        weighted_rate_total += child_weighted_total
        weighted_rate_weight += child_weight

    parent_rate = (weighted_rate_total / weighted_rate_weight) if weighted_rate_weight else 0.0
    node["revenue_value"] = round(total_value, 4)
    node["profit_rate"] = round(parent_rate, 4)
    node["value"] = [
        round(total_value, 4),
        round(parent_rate, 4),
    ]
    return total_value, weighted_rate_total, weighted_rate_weight


def _iter_treemap_leaves(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    leaves: list[dict[str, Any]] = []
    stack = list(nodes)
    while stack:
        current = stack.pop()
        children = current.get("children") or []
        if children:
            stack.extend(children)
            continue
        leaves.append(current)
    return leaves


def allocation_chart(summary: dict[str, Any]) -> alt.Chart | None:
    allocation = summary.get("allocation") or {}
    frame = pd.DataFrame(
        [
            {"bucket": "위험자산", "value": float(allocation.get("risk") or 0)},
            {"bucket": "안전자산", "value": float(allocation.get("safe") or 0)},
            {"bucket": "현금", "value": float(allocation.get("cash") or 0)},
        ]
    )
    frame = frame[frame["value"] > 0]
    if frame.empty:
        return None
    return (
        alt.Chart(frame)
        .mark_arc(innerRadius=70)
        .encode(
            theta=alt.Theta("value:Q"),
            color=alt.Color("bucket:N", scale=alt.Scale(range=["#D97706", "#0F766E", "#33658A"])),
            tooltip=[alt.Tooltip("bucket:N"), alt.Tooltip("value:Q", format=",.0f")],
        )
    )


def allocation_treemap_options(
    summary: dict[str, Any],
    holdings: list[dict[str, Any]],
    *,
    selected_symbol: str | None = None,
) -> dict[str, Any] | None:
    """자산 배분 트리맵용 ECharts 옵션을 만든다."""

    get_jscode_runtime()
    nodes = allocation_treemap_nodes(summary, holdings, selected_symbol=selected_symbol)
    if not nodes:
        return None

    snapshot_lookup = _build_treemap_market_snapshot_lookup(holdings)
    for node in nodes:
        _rollup_treemap_node_values(node, snapshot_lookup=snapshot_lookup)

    leaf_rates = [
        round(float(leaf.get("profit_rate") or 0), 2)
        for leaf in _iter_treemap_leaves(nodes)
        if leaf.get("profit_rate") is not None
    ]
    rate_min = min(leaf_rates) if leaf_rates else 0.0
    rate_max = max(leaf_rates) if leaf_rates else 0.0
    visual_min = float(rate_min)
    visual_max = float(rate_max)
    if visual_min == visual_max:
        visual_min -= 0.01
        visual_max += 0.01

    tooltip_formatter = None
    if JsCode is not None:
        tooltip_formatter = JsCode(
            """
            function(info) {
                function esc(value) {
                    return String(value || '')
                        .replace(/&/g, '&amp;')
                        .replace(/</g, '&lt;')
                        .replace(/>/g, '&gt;')
                        .replace(/"/g, '&quot;')
                        .replace(/'/g, '&#39;');
                }
                var data = info.data || {};
                var rawValue = Array.isArray(info.value) ? info.value[0] : info.value;
                var revenue = '₩' + Math.round(Number(rawValue || 0)).toLocaleString('ko-KR');
                var path = [];
                if (info.treePathInfo) {
                    for (var i = 1; i < info.treePathInfo.length; i += 1) {
                        path.push(info.treePathInfo[i].name);
                    }
                }
                if (data.node_kind !== 'holding') {
                    var summaryLines = [
                        '<div style="font-size:11px; color:#8B93A7; margin-bottom:6px;">' + esc(path.join(' → ')) + '</div>',
                        '<div style="font-size:16px; font-weight:700; color:#FFFFFF; margin-bottom:10px;">' + esc(info.name) + '</div>',
                        '<div style="display:flex; justify-content:space-between; gap:16px; margin-bottom:4px;">'
                            + '<span style="font-size:11px; color:#7F8798;">평가금액</span>'
                            + '<span style="font-family:monospace; font-size:12px; color:#DDE3EE;">' + revenue + '</span>'
                        + '</div>'
                    ];
                    if (data.profit_rate !== null && data.profit_rate !== undefined) {
                        var groupRate = Number(data.profit_rate || 0);
                        var groupColor = groupRate >= 0 ? '#E22B2B' : '#1763B2';
                        summaryLines.push(
                            '<div style="display:flex; justify-content:space-between; gap:16px;">'
                                + '<span style="font-size:11px; color:#7F8798;">가중 수익률</span>'
                                + '<span style="font-family:monospace; font-size:12px; color:' + groupColor + ';">'
                                + (groupRate >= 0 ? '+' : '') + groupRate.toFixed(2) + '%</span>'
                            + '</div>'
                        );
                    }
                    return (
                        '<div style="min-width:220px; max-width:280px; background:rgba(30,34,45,.97); border:1px solid rgba(255,255,255,.10); '
                        + 'border-radius:10px; padding:14px 16px 12px; box-shadow:0 12px 32px rgba(0,0,0,.42);">'
                        + summaryLines.join('')
                        + '</div>'
                    );
                }
                var dayRate = data.day_change_rate;
                var dayText = data.day_change_text || '-';
                var dayPositive = dayRate === null || dayRate === undefined || Number(dayRate || 0) >= 0;
                var dayColor = dayPositive ? '#E22B2B' : '#1763B2';
                var dayBackground = dayPositive ? 'rgba(226,43,43,.13)' : 'rgba(23,99,178,.15)';
                var profitRate = data.profit_rate;
                var holdingPositive = profitRate === null || profitRate === undefined || Number(profitRate || 0) >= 0;
                var holdingColor = holdingPositive ? '#E22B2B' : '#1763B2';
                var pathLabel = path.length > 1 ? path.slice(0, -1).join(' → ') : (data.bucket || '');
                return (
                    '<div style="min-width:230px; max-width:280px; background:rgba(30,34,45,.97); border:1px solid rgba(255,255,255,.10); '
                    + 'border-radius:10px; padding:14px 16px 12px; box-shadow:0 4px 6px rgba(0,0,0,.3),0 12px 32px rgba(0,0,0,.6);">'
                    +   '<div style="display:flex; align-items:flex-start; justify-content:space-between; gap:10px; margin-bottom:10px; '
                    +   'padding-bottom:10px; border-bottom:1px solid rgba(255,255,255,.07);">'
                    +     '<div>'
                    +       '<div style="font-size:16px; font-weight:700; color:#FFFFFF; letter-spacing:-0.02em;">' + esc(info.name) + '</div>'
                    +       '<div style="font-size:10px; color:#868993; margin-top:2px; line-height:1.35;">' + esc(data.symbol || '') + '</div>'
                    +     '</div>'
                    +     '<div style="font-family:monospace; font-size:12px; font-weight:500; padding:3px 8px; border-radius:4px; '
                    +       'white-space:nowrap; color:' + dayColor + '; background:' + dayBackground + ';">' + esc(dayText) + '</div>'
                    +   '</div>'
                    +   '<div style="display:flex; flex-direction:column; gap:5px; margin-bottom:10px;">'
                    +     '<div style="display:flex; justify-content:space-between; align-items:center; gap:12px;"><span style="font-size:10px; color:#555C6E;">현재가</span><span style="font-family:monospace; font-size:11px; color:#D1D4DC;">' + esc(data.current_price_text || revenue) + '</span></div>'
                    +     '<div style="display:flex; justify-content:space-between; align-items:center; gap:12px;"><span style="font-size:10px; color:#555C6E;">당일 등락률</span><span style="font-family:monospace; font-size:11px; color:' + dayColor + ';">' + esc(dayText) + '</span></div>'
                    +     '<div style="display:flex; justify-content:space-between; align-items:center; gap:12px;"><span style="font-size:10px; color:#555C6E;">보유 수익률</span><span style="font-family:monospace; font-size:11px; color:' + holdingColor + ';">' + esc(data.holding_profit_text || '-') + '</span></div>'
                    +     '<div style="display:flex; justify-content:space-between; align-items:center; gap:12px;"><span style="font-size:10px; color:#555C6E;">섹터</span><span style="font-family:monospace; font-size:11px; color:#9BA3B2;">' + esc(data.sector_name || data.bucket || '-') + '</span></div>'
                    +   '</div>'
                    +   '<div style="margin-top:10px; padding-top:9px; border-top:1px solid rgba(255,255,255,.07);">'
                    +     '<div style="font-size:9px; font-weight:500; color:#555C6E; letter-spacing:.08em; text-transform:uppercase; margin-bottom:5px;">당일 추세</div>'
                    +     (data.sparkline_svg || '<div style="height:40px; display:flex; align-items:center; justify-content:center; color:#868993; font-size:10px;">당일 데이터 없음</div>')
                    +     '<div style="display:flex; justify-content:space-between; gap:8px; margin-top:6px;">'
                    +       '<span style="font-size:10px; color:#868993;">' + esc(pathLabel) + '</span>'
                    +       '<span style="font-size:10px; color:#868993;">' + esc(data.intraday_as_of || '') + '</span>'
                    +     '</div>'
                    +   '</div>'
                    + '</div>'
                );
            }
            """
            .replace("#E22B2B", FEARGREED_UP_COLOR)
            .replace("#1763B2", FEARGREED_DOWN_COLOR)
            .replace("rgba(226,43,43,.13)", _rgba_from_hex(FEARGREED_UP_COLOR, 0.14))
            .replace("rgba(23,99,178,.15)", _rgba_from_hex(FEARGREED_DOWN_COLOR, 0.14))
            .replace("#7F8798", FEARGREED_DIM_TEXT_COLOR)
            .replace("#868993", FEARGREED_MUTED_TEXT_COLOR)
            .replace("#555C6E", FEARGREED_MID_TEXT_COLOR)
            .replace("#9BA3B2", FEARGREED_DIM_TEXT_COLOR)
            .replace("#DDE3EE", CHART_TOOLTIP_TEXT_COLOR)
            .replace("#D1D4DC", CHART_TOOLTIP_TEXT_COLOR)
            .replace("rgba(30,34,45,.97)", "rgba(23,50,77,.97)")
        )

    tooltip_config: dict[str, Any] = {
        "backgroundColor": "transparent",
        "borderWidth": 0,
        "padding": 0,
        "confine": True,
        "textStyle": {"color": CHART_TEXT_COLOR, "fontSize": 12},
        "extraCssText": "box-shadow:none;",
    }
    if tooltip_formatter is not None:
        tooltip_config["formatter"] = tooltip_formatter

    label_formatter: Any = "{b}"
    if JsCode is not None:
        label_formatter = JsCode(
            """
            function(info) {
                var name = String(info.name || '');
                return name.length > 14 ? name.slice(0, 13) + '…' : name;
            }
            """
        )

    return {
        "backgroundColor": TREEMAP_CANVAS_BG_COLOR,
        "animationDurationUpdate": 220,
        "title": {
            "text": "자산군 → 섹터 → 보유 종목",
            "left": "center",
            "top": 2,
            "padding": [6, 12],
            "backgroundColor": TREEMAP_TITLE_BG_COLOR,
            "borderColor": TREEMAP_TITLE_BORDER_COLOR,
            "borderWidth": 1,
            "borderRadius": 999,
            "textStyle": {
                "fontSize": 15,
                "fontWeight": 700,
                "color": TREEMAP_TITLE_TEXT_COLOR,
            },
        },
        "tooltip": tooltip_config,
        "visualMap": {
            "type": "continuous",
            "min": visual_min,
            "max": visual_max,
            "dimension": 1,
            "seriesIndex": 0,
            "calculable": True,
            "realtime": True,
            "orient": "horizontal",
            "left": "center",
            "bottom": 6,
            "itemWidth": 14,
            "itemHeight": 200,
            "handleSize": 20,
            "text": ["높은 수익률", "낮은 수익률"],
            "textGap": 6,
            "textStyle": {
                "color": FEARGREED_MUTED_TEXT_COLOR,
                "fontSize": 12,
                "fontWeight": 600,
            },
            "inRange": {
                "color": FEARGREED_TREEMAP_PALETTE,
            },
            "outOfRange": {
                "colorAlpha": 0.0,
            },
            "borderColor": FEARGREED_BORDER_COLOR,
            "padding": 0,
        },
        "series": [
            {
                "name": "자산 배분",
                "type": "treemap",
                "top": 38,
                "left": 0,
                "right": 0,
                "bottom": 52,
                "roam": False,
                "nodeClick": False,
                "sort": "desc",
                "breadcrumb": {"show": False},
                "visibleMin": 1,
                "visualDimension": 1,
                "visualMin": visual_min,
                "visualMax": visual_max,
                "label": {
                    "show": True,
                    "formatter": label_formatter,
                    "color": CHART_TEXT_COLOR,
                    "fontWeight": 700,
                    "fontSize": 14,
                    "lineHeight": 18,
                    "overflow": "truncate",
                    "ellipsis": "…",
                },
                "upperLabel": {
                    "show": True,
                    "formatter": label_formatter,
                    "height": 22,
                    "color": "#F8FAFC",
                    "fontWeight": 700,
                    "overflow": "truncate",
                    "ellipsis": "…",
                },
                "itemStyle": {
                    "borderColor": TREEMAP_CANVAS_BORDER_COLOR,
                    "borderWidth": 1,
                    "gapWidth": 1,
                    "borderRadius": 6,
                },
                "emphasis": {
                    "focus": "self",
                    "itemStyle": {
                        "borderColor": TREEMAP_TITLE_TEXT_COLOR,
                        "borderWidth": 3,
                        "shadowBlur": 16,
                        "shadowColor": "rgba(0, 0, 0, 0.26)",
                    }
                },
                "levels": [
                    {
                        "itemStyle": {
                            "borderColor": TREEMAP_CANVAS_BORDER_COLOR,
                            "borderWidth": 1,
                            "gapWidth": 1,
                            "borderRadius": 6,
                        },
                        "upperLabel": {
                            "show": True,
                            "height": 26,
                            "color": FEARGREED_FULL_TEXT_COLOR,
                            "backgroundColor": FEARGREED_FLAT_COLOR,
                            "padding": [5, 8],
                        },
                    },
                    {
                        "itemStyle": {
                            "borderColor": TREEMAP_CANVAS_BORDER_COLOR,
                            "borderWidth": 1,
                            "gapWidth": 1,
                            "borderRadius": 6,
                        },
                        "upperLabel": {
                            "show": True,
                            "height": 20,
                            "color": FEARGREED_BRIGHT_TEXT_COLOR,
                            "backgroundColor": "rgba(42,46,57,0.88)",
                            "padding": [3, 6],
                        },
                    },
                    {
                        "color": FEARGREED_TREEMAP_PALETTE,
                        "colorMappingBy": "value",
                        "itemStyle": {
                            "borderColor": TREEMAP_CANVAS_BORDER_COLOR,
                            "borderWidth": 1,
                            "gapWidth": 1,
                            "borderRadius": 4,
                        },
                    },
                ],
                "data": nodes,
            }
        ],
    }


def holdings_bar_options(frame: pd.DataFrame, *, selected_symbol: str | None = None) -> dict[str, Any] | None:
    """보유 종목 수익률 ECharts 막대 옵션을 만든다."""

    get_jscode_runtime()
    if frame.empty:
        return None
    chart_frame = frame.copy().sort_values(["profit_rate", "current_value"], ascending=[False, False]).reset_index(drop=True)
    chart_frame["display_name"] = chart_frame["product_name"].astype(str).apply(
        lambda value: value if len(value) <= 14 else f"{value[:13]}…"
    )
    selected_key = normalize_holding_symbol(selected_symbol)
    data: list[dict[str, Any]] = []
    rates: list[float] = []
    for row in chart_frame.to_dict(orient="records"):
        symbol = normalize_holding_symbol(row.get("selection_symbol") or row.get("symbol"))
        rate = float(row.get("profit_rate") or 0)
        rates.append(rate)
        is_selected = bool(symbol and symbol == selected_key)
        data.append(
            {
                "value": round(rate, 2),
                "symbol": symbol,
                "product_name": str(row.get("product_name") or symbol or "종목"),
                "display_name": str(row.get("display_name") or row.get("product_name") or symbol or "종목"),
                "current_value": round(float(row.get("current_value") or 0), 4),
                "profit_rate": round(rate, 2),
                "itemStyle": {
                    "color": FEARGREED_UP_COLOR if rate >= 0 else FEARGREED_DOWN_COLOR,
                    "borderRadius": [10, 10, 0, 0] if rate >= 0 else [0, 0, 10, 10],
                    "borderColor": FEARGREED_ACCENT_COLOR if is_selected else "rgba(255,255,255,0.08)",
                    "borderWidth": 3 if is_selected else 0,
                    "shadowBlur": 18 if is_selected else 0,
                    "shadowColor": CHART_ACCENT_SOFT_COLOR if is_selected else "transparent",
                    "opacity": 1 if is_selected else 0.92,
                },
                "label": {
                    "show": True,
                    "position": "top" if rate >= 0 else "bottom",
                    "distance": 8,
                    "formatter": format_pct(rate),
                    "color": CHART_TEXT_COLOR if is_selected else FEARGREED_MID_TEXT_COLOR,
                    "fontWeight": 700 if is_selected else 600,
                    "opacity": 1 if is_selected or not selected_key else 0.78,
                },
            }
        )

    if not data:
        return None

    minimum = min(rates)
    maximum = max(rates)

    tooltip_formatter = None
    if JsCode is not None:
        tooltip_formatter = JsCode(
            """
            function(params) {
                var currentValue = Math.round(Number(params.data.current_value || 0)).toLocaleString('ko-KR');
                var profitRate = Number(params.data.profit_rate || 0).toFixed(2);
                return [
                    '<strong>' + params.data.product_name + '</strong>',
                    '평가금액: ₩' + currentValue,
                    '수익률: ' + profitRate + '%'
                ].join('<br/>');
            }
            """
        )

    y_axis_config: dict[str, Any] = {
        "type": "value",
        "name": "수익률 (%)",
        "nameTextStyle": {"color": FEARGREED_MID_TEXT_COLOR, "fontWeight": 700},
        "axisLabel": {"color": FEARGREED_MUTED_TEXT_COLOR, "formatter": "{value}%"},
        "axisLine": {"show": False},
        "splitLine": {"lineStyle": {"color": FEARGREED_BORDER_COLOR}},
    }
    if minimum >= 0:
        y_axis_config["min"] = 0.0
    elif maximum <= 0:
        y_axis_config["max"] = 0.0

    return {
        "backgroundColor": "transparent",
        "animationDuration": 260,
        "animationDurationUpdate": 320,
        "grid": {"top": 44, "right": 12, "bottom": 82, "left": 56},
        "tooltip": {
            "trigger": "item",
            "backgroundColor": CHART_TOOLTIP_BG_COLOR,
            "borderWidth": 0,
            "textStyle": {"color": CHART_TOOLTIP_TEXT_COLOR, "fontSize": 12},
            **({"formatter": tooltip_formatter} if tooltip_formatter is not None else {}),
        },
        "xAxis": {
            "type": "category",
            "data": [item["display_name"] for item in data],
            "axisLabel": {
                "interval": 0,
                "rotate": 32,
                "color": FEARGREED_MUTED_TEXT_COLOR,
                "fontSize": 11,
                "margin": 14,
            },
            "axisLine": {"lineStyle": {"color": FEARGREED_BORDER_COLOR}},
            "axisTick": {"show": False},
        },
        "yAxis": y_axis_config,
        "series": [
            {
                "name": "수익률",
                "type": "bar",
                "barWidth": "52%",
                "data": data,
                "emphasis": {
                    "focus": "self",
                    "itemStyle": {
                        "shadowBlur": 22,
                        "shadowColor": "rgba(15, 23, 42, 0.16)",
                    },
                },
            }
        ],
    }


def holdings_bar_fallback_chart(frame: pd.DataFrame, *, selected_symbol: str | None = None) -> alt.Chart | None:
    """ECharts 미사용 환경에서 보유 종목 수익률 막대차트를 Altair로 대체한다."""

    if frame.empty:
        return None
    chart_frame = frame.copy().sort_values(["profit_rate", "current_value"], ascending=[False, False]).reset_index(drop=True)
    chart_frame["tone"] = chart_frame["profit_rate"].apply(lambda value: "수익" if float(value or 0) >= 0 else "손실")
    chart_frame["display_name"] = chart_frame["product_name"].astype(str).apply(
        lambda value: value if len(value) <= 14 else f"{value[:13]}…"
    )
    selected_key = normalize_holding_symbol(selected_symbol)
    chart_frame["selection_symbol"] = chart_frame["selection_symbol"].astype(str).str.strip().str.upper()
    chart_frame["selected_opacity"] = chart_frame["selection_symbol"].apply(
        lambda value: 1.0 if value == selected_key else (0.92 if not selected_key else 0.48)
    )
    chart_frame["profit_rate_label"] = chart_frame["profit_rate"].apply(format_pct)
    display_order = chart_frame["display_name"].tolist()
    bars = (
        alt.Chart(chart_frame)
        .mark_bar(cornerRadiusEnd=8, size=52)
        .encode(
            x=alt.X(
                "display_name:N",
                sort=display_order,
                title="종목",
                axis=alt.Axis(
                    labelAngle=-32,
                    labelLimit=118,
                    labelPadding=10,
                    titlePadding=14,
                    labelColor=FEARGREED_MUTED_TEXT_COLOR,
                    titleColor=FEARGREED_MID_TEXT_COLOR,
                ),
            ),
            y=alt.Y(
                "profit_rate:Q",
                title="수익률 (%)",
                axis=alt.Axis(
                    format=".0f",
                    grid=True,
                    gridColor=FEARGREED_BORDER_COLOR,
                    tickCount=6,
                    labelColor=FEARGREED_MUTED_TEXT_COLOR,
                    titleColor=FEARGREED_MID_TEXT_COLOR,
                ),
            ),
            color=alt.Color("tone:N", legend=None, scale=alt.Scale(domain=["수익", "손실"], range=[FEARGREED_UP_COLOR, FEARGREED_DOWN_COLOR])),
            opacity=alt.Opacity("selected_opacity:Q", legend=None),
            tooltip=[
                alt.Tooltip("product_name:N", title="종목"),
                alt.Tooltip("current_value:Q", title="평가금액", format=",.0f"),
                alt.Tooltip("profit_rate:Q", title="수익률 (%)", format=".2f"),
            ],
        )
    )
    labels = (
        alt.Chart(chart_frame)
        .mark_text(dy=-8, fontSize=11, fontWeight="bold", color=CHART_TEXT_COLOR)
        .encode(
            x=alt.X("display_name:N", sort=display_order),
            y=alt.Y("profit_rate:Q"),
            text=alt.Text("profit_rate_label:N"),
            opacity=alt.Opacity("selected_opacity:Q", legend=None),
        )
    )
    return style_dashboard_altair_chart(bars + labels, height=DASHBOARD_HOLDINGS_COMPARE_CHART_HEIGHT)


def realized_profit_bar_options(frame: pd.DataFrame) -> dict[str, Any] | None:
    """실현 손익 요약을 대시보드 보유 종목 수익률과 같은 톤의 막대 옵션으로 만든다."""

    get_jscode_runtime()
    if frame.empty:
        return None

    chart_frame = frame.copy().sort_values(["profit_loss", "sell_amount"], ascending=[False, False]).reset_index(drop=True)
    chart_frame["display_name"] = chart_frame["product_name"].astype(str).apply(
        lambda value: value if len(value) <= 14 else f"{value[:13]}…"
    )
    data: list[dict[str, Any]] = []
    values: list[float] = []
    for row in chart_frame.to_dict(orient="records"):
        profit_loss = float(row.get("profit_loss") or 0)
        profit_rate = float(row.get("profit_rate") or 0)
        values.append(profit_loss)
        data.append(
            {
                "value": round(profit_loss, 2),
                "product_name": str(row.get("product_name") or "종목"),
                "display_name": str(row.get("display_name") or row.get("product_name") or "종목"),
                "sell_amount": round(float(row.get("sell_amount") or 0), 2),
                "profit_rate": round(profit_rate, 2),
                "itemStyle": {
                    "color": FEARGREED_UP_COLOR if profit_loss >= 0 else FEARGREED_DOWN_COLOR,
                    "borderRadius": [10, 10, 0, 0] if profit_loss >= 0 else [0, 0, 10, 10],
                    "opacity": 0.94,
                },
                "label": {
                    "show": True,
                    "position": "top" if profit_loss >= 0 else "bottom",
                    "distance": 8,
                    "formatter": format_won(profit_loss),
                    "color": FEARGREED_MID_TEXT_COLOR,
                    "fontWeight": 700,
                },
            }
        )

    if not data:
        return None

    minimum = min(values)
    maximum = max(values)
    tooltip_formatter = None
    if JsCode is not None:
        tooltip_formatter = JsCode(
            """
            function(params) {
                var realizedAmount = Math.round(Number(params.data.value || 0)).toLocaleString('ko-KR');
                var soldAmount = Math.round(Number(params.data.sell_amount || 0)).toLocaleString('ko-KR');
                var profitRate = Number(params.data.profit_rate || 0).toFixed(2);
                return [
                    '<strong>' + params.data.product_name + '</strong>',
                    '실현손익: ₩' + realizedAmount,
                    '매도금액: ₩' + soldAmount,
                    '실현수익률: ' + profitRate + '%'
                ].join('<br/>');
            }
            """
        )

    y_axis_label_config: dict[str, Any] = {
        "color": FEARGREED_MUTED_TEXT_COLOR,
    }
    if JsCode is not None:
        y_axis_label_config["formatter"] = JsCode(
            """
            function(value) {
                return '₩' + Math.round(Number(value || 0)).toLocaleString('ko-KR');
            }
            """
        )
    else:
        y_axis_label_config["formatter"] = "₩{value}"

    y_axis_config: dict[str, Any] = {
        "type": "value",
        "name": "실현손익",
        "nameTextStyle": {"color": FEARGREED_MID_TEXT_COLOR, "fontWeight": 700},
        "axisLabel": y_axis_label_config,
        "axisLine": {"show": False},
        "splitLine": {"lineStyle": {"color": FEARGREED_BORDER_COLOR}},
    }
    if minimum >= 0:
        y_axis_config["min"] = 0.0
    elif maximum <= 0:
        y_axis_config["max"] = 0.0

    return {
        "backgroundColor": "transparent",
        "animationDuration": 260,
        "animationDurationUpdate": 320,
        "grid": {"top": 44, "right": 14, "bottom": 82, "left": 74},
        "tooltip": {
            "trigger": "item",
            "backgroundColor": CHART_TOOLTIP_BG_COLOR,
            "borderWidth": 0,
            "textStyle": {"color": CHART_TOOLTIP_TEXT_COLOR, "fontSize": 12},
            **({"formatter": tooltip_formatter} if tooltip_formatter is not None else {}),
        },
        "xAxis": {
            "type": "category",
            "data": [item["display_name"] for item in data],
            "axisLabel": {
                "interval": 0,
                "rotate": 32,
                "color": FEARGREED_MUTED_TEXT_COLOR,
                "fontSize": 11,
                "margin": 14,
            },
            "axisLine": {"lineStyle": {"color": FEARGREED_BORDER_COLOR}},
            "axisTick": {"show": False},
        },
        "yAxis": y_axis_config,
        "series": [
            {
                "name": "실현손익",
                "type": "bar",
                "barWidth": "52%",
                "data": data,
                "emphasis": {
                    "focus": "self",
                    "itemStyle": {
                        "shadowBlur": 22,
                        "shadowColor": "rgba(15, 23, 42, 0.16)",
                    },
                },
            }
        ],
    }


def realized_profit_bar_fallback_chart(frame: pd.DataFrame) -> alt.Chart | None:
    """실현 손익 요약을 Altair 막대차트로 대체한다."""

    if frame.empty:
        return None
    chart_frame = frame.copy().sort_values(["profit_loss", "sell_amount"], ascending=[False, False]).reset_index(drop=True)
    chart_frame["tone"] = chart_frame["profit_loss"].apply(lambda value: "수익" if float(value or 0) >= 0 else "손실")
    chart_frame["display_name"] = chart_frame["product_name"].astype(str).apply(
        lambda value: value if len(value) <= 14 else f"{value[:13]}…"
    )
    chart_frame["profit_loss_label"] = chart_frame["profit_loss"].apply(format_won)
    display_order = chart_frame["display_name"].tolist()
    bars = (
        alt.Chart(chart_frame)
        .mark_bar(cornerRadiusEnd=8, size=52)
        .encode(
            x=alt.X(
                "display_name:N",
                sort=display_order,
                title="종목",
                axis=alt.Axis(
                    labelAngle=-32,
                    labelLimit=118,
                    labelPadding=10,
                    titlePadding=14,
                    labelColor=FEARGREED_MUTED_TEXT_COLOR,
                    titleColor=FEARGREED_MID_TEXT_COLOR,
                ),
            ),
            y=alt.Y(
                "profit_loss:Q",
                title="실현손익",
                axis=alt.Axis(
                    format=",.0f",
                    grid=True,
                    gridColor=FEARGREED_BORDER_COLOR,
                    tickCount=6,
                    labelColor=FEARGREED_MUTED_TEXT_COLOR,
                    titleColor=FEARGREED_MID_TEXT_COLOR,
                ),
            ),
            color=alt.Color("tone:N", legend=None, scale=alt.Scale(domain=["수익", "손실"], range=[FEARGREED_UP_COLOR, FEARGREED_DOWN_COLOR])),
            tooltip=[
                alt.Tooltip("product_name:N", title="종목"),
                alt.Tooltip("profit_loss:Q", title="실현손익", format=",.0f"),
                alt.Tooltip("sell_amount:Q", title="매도금액", format=",.0f"),
                alt.Tooltip("profit_rate:Q", title="실현수익률 (%)", format=".2f"),
            ],
        )
    )
    labels = (
        alt.Chart(chart_frame)
        .mark_text(dy=-8, fontSize=11, fontWeight="bold", color=CHART_TEXT_COLOR)
        .encode(
            x=alt.X("display_name:N", sort=display_order),
            y=alt.Y("profit_loss:Q"),
            text=alt.Text("profit_loss_label:N"),
        )
    )
    return style_dashboard_altair_chart(bars + labels, height=DASHBOARD_HOLDINGS_CHART_HEIGHT)


def build_selected_holding_intraday_trend_frame(holding: dict[str, Any]) -> pd.DataFrame:
    """선택 종목 1건의 intraday 타임라인을 차트용 프레임으로 변환한다."""

    symbol = str(holding.get("symbol") or "").strip()
    if not symbol:
        return pd.DataFrame()

    snapshot = fetch_intraday_price_snapshot(symbol)
    timeline = snapshot.get("timeline") or []
    current_price = snapshot.get("current_price")
    as_of_timestamp = pd.to_datetime(snapshot.get("as_of"), errors="coerce")
    fallback_current_price = holding.get("current_price")
    quantity = float(holding.get("quantity") or 0)
    cost_basis = float(holding.get("avg_cost") or 0) * quantity
    normalized_points: list[dict[str, Any]] = []
    if isinstance(timeline, list):
        for point in timeline:
            point_datetime = pd.to_datetime(point.get("datetime"), errors="coerce")
            if pd.isna(point_datetime):
                continue
            close_price = float(point.get("close") or 0)
            normalized_points.append({"date": point_datetime, "close": close_price})

    if current_price not in (None, "") and not pd.isna(as_of_timestamp):
        normalized_points.append({"date": as_of_timestamp, "close": float(current_price)})

    if not normalized_points:
        fallback_timestamp = as_of_timestamp if not pd.isna(as_of_timestamp) else pd.Timestamp.now(tz=KST_TIMEZONE)
        if fallback_current_price in (None, ""):
            return pd.DataFrame()
        normalized_points.append({"date": fallback_timestamp, "close": float(fallback_current_price)})

    normalized_frame = (
        pd.DataFrame(normalized_points)
        .sort_values("date")
        .drop_duplicates(subset=["date"], keep="last")
        .reset_index(drop=True)
    )
    if normalized_frame.empty:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for point in normalized_frame.itertuples(index=False):
        point_datetime = pd.to_datetime(point.date, errors="coerce")
        close_price = float(point.close or 0)
        market_value = close_price * quantity
        profit_loss = market_value - cost_basis
        rows.append(
            {
                "date": point_datetime,
                "symbol": symbol,
                "product_name": str(holding.get("product_name") or symbol).strip(),
                "close": close_price,
                "market_value": market_value,
                "cost_basis": cost_basis,
                "profit_loss": profit_loss,
                "profit_rate": (profit_loss / cost_basis * 100) if cost_basis else 0.0,
            }
        )

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)


def build_selected_holding_trend_frame(selected_holdings: list[dict[str, Any]], period: str) -> pd.DataFrame:
    """선택 종목 추이를 기간에 맞춰 일봉 또는 intraday 프레임으로 반환한다."""

    normalized_period = str(period or "6mo").strip().lower() or "6mo"
    if normalized_period != "today":
        _, selected_holding_trend = build_portfolio_trend(selected_holdings, period=normalized_period)
        return selected_holding_trend

    detail_rows = [
        build_selected_holding_intraday_trend_frame(holding)
        for holding in selected_holdings
    ]
    detail_rows = [frame for frame in detail_rows if not frame.empty]
    if not detail_rows:
        return pd.DataFrame()

    merged = pd.concat(detail_rows, ignore_index=True)
    aggregated = (
        merged.groupby("date", as_index=False)
        .agg(
            product_name=("product_name", "last"),
            symbol=("symbol", "last"),
            close=("close", "last"),
            market_value=("market_value", "sum"),
            cost_basis=("cost_basis", "sum"),
        )
        .sort_values("date")
        .reset_index(drop=True)
    )
    aggregated["profit_loss"] = aggregated["market_value"] - aggregated["cost_basis"]
    aggregated["profit_rate"] = aggregated.apply(
        lambda row: (row["profit_loss"] / row["cost_basis"] * 100) if row["cost_basis"] else 0.0,
        axis=1,
    )
    return aggregated


def selected_holding_trend_chart(
    frame: pd.DataFrame,
    *,
    measure: str,
    selected_holding_name: str,
    selected_symbol_code: str,
    period_label: str,
) -> alt.Chart:
    """선택 종목 단일 추이 차트를 만든다."""

    measure_key = str(measure or DEFAULT_SELECTED_TREND_MEASURE)
    measure_title = label_detail_measure(measure_key)
    measure_format = ",.2f" if measure_key == "close" else (".2f" if measure_key == "profit_rate" else ",.0f")
    x_axis_title = "시간" if str(period_label) == "당일" else "날짜"
    return (
        alt.Chart(frame)
        .mark_line(point=True, strokeWidth=3, color=CHART_LINE_COLOR)
        .encode(
            x=alt.X("date:T", title=x_axis_title),
            y=alt.Y(f"{measure_key}:Q", title=measure_title),
            tooltip=[
                alt.Tooltip("product_name:N", title="종목"),
                alt.Tooltip("date:T", title="날짜"),
                alt.Tooltip(f"{measure_key}:Q", title=measure_title, format=measure_format),
                alt.Tooltip("market_value:Q", title="평가금액", format=",.0f"),
                alt.Tooltip("profit_rate:Q", title="수익률 (%)", format=".2f"),
                alt.Tooltip("close:Q", title="종가", format=",.2f"),
            ],
        )
        .properties(
            title=alt.TitleParams(
                text=selected_holding_name,
                subtitle=[f"{selected_symbol_code} · {measure_title} · {period_label}"],
            )
        )
    )


def _selected_holding_trend_data_view_option() -> Any | None:
    """선택 종목 트렌드 toolbox의 데이터 보기 HTML 렌더러를 반환한다."""

    js_code = get_jscode_runtime()
    if js_code is None:
        return None

    return js_code(
        """
        function(option) {
            function esc(value) {
                return String(value || '')
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#39;');
            }

            function formatClose(value) {
                return Number(value || 0).toLocaleString('ko-KR', {
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 2
                });
            }

            function formatRate(value) {
                var numeric = Number(value || 0);
                return (numeric >= 0 ? '+' : '') + numeric.toFixed(2) + '%';
            }

            function formatValue(value) {
                return '₩' + Math.round(Number(value || 0)).toLocaleString('ko-KR');
            }

            var rows = (((option || {}).series || [])[0] || {}).data || [];
            var hasTime = rows.some(function(row) {
                return String((row || {}).time || '').trim() !== '';
            });
            var headerStyle = 'padding:8px 10px; border-bottom:1px solid #D7E2E7; background:#F8FAFC; color:#334155; font-weight:700; text-align:center;';
            var cellStyle = 'padding:8px 10px; border-bottom:1px solid #E2E8F0; color:#1E293B;';
            var html = '<div style="padding:8px 2px 2px;">';
            html += '<table style="width:100%; border-collapse:collapse; font-size:12px;">';
            html += '<thead><tr>';
            html += '<th style="' + headerStyle + '">년</th>';
            html += '<th style="' + headerStyle + '">월</th>';
            html += '<th style="' + headerStyle + '">일</th>';
            if (hasTime) {
                html += '<th style="' + headerStyle + '">시간</th>';
            }
            html += '<th style="' + headerStyle + '">기준가(종가)</th>';
            html += '<th style="' + headerStyle + '">수익률</th>';
            html += '<th style="' + headerStyle + '">평가금액</th>';
            html += '</tr></thead><tbody>';

            if (!rows.length) {
                html += '<tr><td colspan="' + (hasTime ? '7' : '6') + '" style="' + cellStyle + ' text-align:center; color:#64748B;">데이터가 없습니다.</td></tr>';
            } else {
                for (var index = 0; index < rows.length; index += 1) {
                    var row = rows[index] || {};
                    html += '<tr>'
                        + '<td style="' + cellStyle + ' text-align:center;">' + esc(row.year || '') + '</td>'
                        + '<td style="' + cellStyle + ' text-align:center;">' + esc(row.month || '') + '</td>'
                        + '<td style="' + cellStyle + ' text-align:center;">' + esc(row.day || '') + '</td>';
                    if (hasTime) {
                        html += '<td style="' + cellStyle + ' text-align:center;">' + esc(row.time || '') + '</td>';
                    }
                    html += ''
                        + '<td style="' + cellStyle + ' text-align:right; font-variant-numeric:tabular-nums;">' + esc(formatClose(row.close)) + '</td>'
                        + '<td style="' + cellStyle + ' text-align:right; font-variant-numeric:tabular-nums;">' + esc(formatRate(row.profit_rate)) + '</td>'
                        + '<td style="' + cellStyle + ' text-align:right; font-variant-numeric:tabular-nums;">' + esc(formatValue(row.market_value)) + '</td>'
                        + '</tr>';
                }
            }

            html += '</tbody></table></div>';
            return html;
        }
        """
        .replace("#D7E2E7", "#D9E2EC")
        .replace("#E2E8F0", "#D9E2EC")
        .replace("#F8FAFC", "#F8FAFC")
        .replace("#334155", CHART_TEXT_COLOR)
        .replace("#1E293B", CHART_TEXT_COLOR)
        .replace("#64748B", FEARGREED_MUTED_TEXT_COLOR)
    )


def selected_holding_trend_options(
    frame: pd.DataFrame,
    *,
    selected_holding_name: str,
    selected_symbol_code: str,
    measure: str,
    period_label: str,
) -> dict[str, Any] | None:
    """선택 종목 트렌드 ECharts 옵션을 만든다."""

    get_jscode_runtime()
    if frame.empty:
        return None

    measure_key = str(measure or DEFAULT_SELECTED_TREND_MEASURE)
    measure_title = label_detail_measure(measure_key)
    working = frame.sort_values("date").copy()
    working["date"] = pd.to_datetime(working["date"])
    intraday_mode = str(period_label) == "당일"
    if intraday_mode:
        date_format = "%H:%M"
        full_date_format = "%Y-%m-%d %H:%M"
    elif str(period_label) in {"1개월", "3개월"}:
        date_format = "%m-%d"
        full_date_format = "%Y-%m-%d"
    else:
        date_format = "%Y-%m"
        full_date_format = "%Y-%m-%d"
    x_labels = working["date"].dt.strftime(date_format).tolist()
    full_dates = working["date"].dt.strftime(full_date_format).tolist()

    series_data: list[dict[str, Any]] = []
    for row, label_date, full_date, row_date in zip(
        working.to_dict(orient="records"),
        x_labels,
        full_dates,
        working["date"],
    ):
        series_data.append(
            {
                "value": round(float(row.get(measure_key) or 0), 4),
                "date": full_date,
                "axis_label": label_date,
                "year": row_date.strftime("%Y"),
                "month": row_date.strftime("%m"),
                "day": row_date.strftime("%d"),
                "time": row_date.strftime("%H:%M") if intraday_mode else "",
                "product_name": selected_holding_name,
                "market_value": round(float(row.get("market_value") or 0), 4),
                "profit_rate": round(float(row.get("profit_rate") or 0), 4),
                "close": round(float(row.get("close") or 0), 4),
            }
        )

    axis_label_formatter: Any = None
    tooltip_formatter: Any = None
    if JsCode is not None:
        if measure_key == "profit_rate":
            axis_label_formatter = JsCode(
                """
                function(value) {
                    return Number(value || 0).toFixed(2) + '%';
                }
                """
            )
        elif measure_key == "close":
            axis_label_formatter = JsCode(
                """
                function(value) {
                    return Number(value || 0).toLocaleString('ko-KR', {
                        minimumFractionDigits: 0,
                        maximumFractionDigits: 2
                    });
                }
                """
            )
        else:
            axis_label_formatter = JsCode(
                """
                function(value) {
                    return Number(value || 0).toLocaleString('ko-KR');
                }
                """
            )

        tooltip_formatter = JsCode(
            f"""
            function(params) {{
                if (!params || !params.length) {{
                    return '';
                }}
                var point = params[0].data || {{}};
                var primaryValue = Number(point.value || 0);
                var primaryText = '';
                if ({measure_key!r} === 'profit_rate') {{
                    primaryText = primaryValue.toFixed(2) + '%';
                }} else if ({measure_key!r} === 'close') {{
                    primaryText = primaryValue.toLocaleString('ko-KR', {{
                        minimumFractionDigits: 0,
                        maximumFractionDigits: 2
                    }});
                }} else {{
                    primaryText = '₩' + Math.round(primaryValue).toLocaleString('ko-KR');
                }}
                return [
                    '<div style="font-weight:700; margin-bottom:6px;">' + String(point.product_name || {selected_holding_name!r}) + '</div>',
                    '날짜: ' + String(point.date || ''),
                    {measure_title!r} + ': ' + primaryText,
                    '평가금액: ₩' + Math.round(Number(point.market_value || 0)).toLocaleString('ko-KR'),
                    '수익률: ' + Number(point.profit_rate || 0).toFixed(2) + '%',
                    '종가: ' + Number(point.close || 0).toLocaleString('ko-KR', {{
                        minimumFractionDigits: 0,
                        maximumFractionDigits: 2
                    }})
                ].join('<br/>');
            }}
            """
        )

    y_axis_config: dict[str, Any] = {
        "type": "value",
        "name": measure_title,
        "nameTextStyle": {"color": FEARGREED_MID_TEXT_COLOR, "fontWeight": 700, "padding": [0, 0, 0, 4]},
        "axisLine": {"show": False},
        "axisTick": {"show": False},
        "splitLine": {"lineStyle": {"color": FEARGREED_BORDER_COLOR}},
        "axisLabel": {"color": FEARGREED_MUTED_TEXT_COLOR},
    }
    if axis_label_formatter is not None:
        y_axis_config["axisLabel"]["formatter"] = axis_label_formatter

    data_view_option = _selected_holding_trend_data_view_option()

    return {
        "backgroundColor": "transparent",
        "animationDuration": 260,
        "animationDurationUpdate": 320,
        "title": {
            "text": selected_holding_name,
            "subtext": f"{selected_symbol_code} · {measure_title} · {period_label}",
            "left": "center",
            "top": 6,
            "textStyle": {
                "fontSize": 16,
                "fontWeight": 700,
                "color": CHART_TEXT_COLOR,
            },
            "subtextStyle": {
                "fontSize": 11,
                "color": FEARGREED_MUTED_TEXT_COLOR,
            },
        },
        "legend": {
            "show": True,
            "bottom": 0,
            "left": "center",
            "itemWidth": 10,
            "itemHeight": 10,
            "icon": "circle",
            "textStyle": {
                "color": FEARGREED_MUTED_TEXT_COLOR,
                "fontSize": 12,
            },
        },
        "grid": {
            "top": 76,
            "right": 16,
            "bottom": 92,
            "left": 58,
            "containLabel": False,
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {
                "type": "line",
                "lineStyle": {
                    "color": FEARGREED_MUTED_TEXT_COLOR,
                    "width": 1,
                    "type": "dashed",
                },
            },
            "backgroundColor": CHART_TOOLTIP_BG_COLOR,
            "borderColor": FEARGREED_BORDER_COLOR,
            "borderWidth": 1,
            "borderRadius": 12,
            "padding": [10, 12],
            "textStyle": {"color": FEARGREED_BRIGHT_TEXT_COLOR, "fontSize": 12},
            "extraCssText": "box-shadow: 0 8px 24px rgba(0, 0, 0, 0.28);",
            **({"formatter": tooltip_formatter} if tooltip_formatter is not None else {}),
        },
        "toolbox": {
            "show": True,
            "top": 8,
            "right": 0,
            "itemSize": 16,
            "iconStyle": {
                "borderColor": FEARGREED_ACCENT_COLOR,
            },
            "emphasis": {
                "iconStyle": {
                    "borderColor": CHART_TEXT_COLOR,
                }
            },
            "feature": {
                "saveAsImage": {
                    "show": True,
                    "title": "이미지 저장",
                    "name": f"{selected_holding_name}-{measure_title}-trend",
                },
                "dataView": {
                    "show": True,
                    "title": "데이터 보기",
                    "readOnly": True,
                    "lang": ["데이터 보기", "닫기", "새로고침"],
                    **({"optionToContent": data_view_option} if data_view_option is not None else {}),
                },
                "dataZoom": {
                    "show": True,
                    "title": {
                        "zoom": "확대",
                        "back": "되돌리기",
                    },
                    "yAxisIndex": "none",
                },
                "restore": {
                    "show": True,
                    "title": "초기화",
                },
                "magicType": {
                    "show": True,
                    "type": ["line", "bar"],
                    "title": {
                        "line": "라인 차트",
                        "bar": "막대 차트",
                    },
                },
            },
        },
        "xAxis": {
            "type": "category",
            "boundaryGap": False,
            "data": x_labels,
            "axisLine": {"lineStyle": {"color": FEARGREED_BORDER_COLOR}},
            "axisTick": {"show": False},
            "axisLabel": {
                "color": FEARGREED_MUTED_TEXT_COLOR,
                "hideOverlap": True,
                "margin": 12,
            },
        },
        "yAxis": y_axis_config,
        "dataZoom": [
            {
                "type": "inside",
                "zoomOnMouseWheel": True,
                "moveOnMouseMove": True,
                "moveOnMouseWheel": True,
            },
            {
                "type": "slider",
                "height": 22,
                "bottom": 30,
                "borderColor": FEARGREED_BORDER_COLOR,
                "backgroundColor": FEARGREED_PANEL_COLOR,
                "fillerColor": CHART_ACCENT_SOFT_COLOR,
                "handleSize": 18,
                "brushSelect": False,
                "dataBackground": {
                    "lineStyle": {"color": CHART_LINE_SOFT_COLOR},
                    "areaStyle": {"color": CHART_LINE_FAINT_COLOR},
                },
                "selectedDataBackground": {
                    "lineStyle": {"color": FEARGREED_ACCENT_COLOR},
                    "areaStyle": {"color": CHART_ACCENT_SOFT_COLOR},
                },
            },
        ],
        "series": [
            {
                "name": measure_title,
                "type": "line",
                "smooth": True,
                "showSymbol": True,
                "symbol": "circle",
                "symbolSize": 7,
                "data": series_data,
                "lineStyle": {
                    "color": CHART_LINE_COLOR,
                    "width": 3,
                },
                "itemStyle": {
                    "color": FEARGREED_FULL_TEXT_COLOR,
                    "borderColor": CHART_LINE_COLOR,
                    "borderWidth": 2,
                },
                "areaStyle": {
                    "color": {
                        "type": "linear",
                        "x": 0,
                        "y": 0,
                        "x2": 0,
                        "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": CHART_LINE_SOFT_COLOR},
                            {"offset": 1, "color": CHART_LINE_FAINT_COLOR},
                        ],
                    }
                },
                "emphasis": {
                    "focus": "series",
                },
                **(
                    {
                        "markLine": {
                            "symbol": "none",
                            "silent": True,
                            "lineStyle": {
                                "color": FEARGREED_MUTED_TEXT_COLOR,
                                "type": "dashed",
                            },
                            "data": [{"yAxis": 0}],
                        }
                    }
                    if measure_key == "profit_rate"
                    else {}
                ),
            }
        ],
        "aria": {
            "enabled": True,
        },
    }


def show_holdings_table(frame: pd.DataFrame, *, height: int = 420) -> None:
    """현재 보유 종목 표를 커스텀 테마 HTML 테이블로 렌더링한다."""

    if frame.empty:
        st.info("보유 종목이 없습니다.")
        return

    display = build_holdings_table_display(frame)
    st.markdown(build_holdings_table_html(display, max_height=height), unsafe_allow_html=True)


def build_holdings_mix_bar_html(summary: dict[str, Any]) -> str:
    """현재 보유 종목 박스 상단에 넣을 위험/안전(현금 포함) 비율 막대 HTML을 만든다."""

    allocation = summary.get("allocation") or {}
    cash_amount = float(allocation.get("cash") or summary.get("cash") or 0)
    segments = [
        ("위험자산", float(allocation.get("risk") or 0), FEARGREED_DOWN_COLOR),
        ("안전자산", float(allocation.get("safe") or 0) + cash_amount, FEARGREED_UP_COLOR),
    ]
    total_value = sum(max(amount, 0.0) for _, amount, _ in segments)
    if total_value <= 0:
        return ""

    bar_segments: list[str] = []
    legend_segments: list[str] = []
    for label, amount, color in segments:
        percentage = (max(amount, 0.0) / total_value) * 100 if total_value else 0.0
        bar_segments.append(
            "".join(
                [
                    f'<div style="width:{percentage:.4f}%; background:{color}; min-width:0; height:100%;',
                    ' display:flex; align-items:center; justify-content:center; overflow:hidden;">',
                    (
                        f'<span style="font-size:11px; font-weight:700; color:{FEARGREED_FULL_TEXT_COLOR}; white-space:nowrap;">{percentage:.0f}%</span>'
                        if percentage >= 10
                        else ""
                    ),
                    "</div>",
                ]
            )
        )
        legend_segments.append(
            "".join(
                [
                    '<div style="display:flex; align-items:center; gap:8px;">',
                    f'<span style="width:10px; height:10px; border-radius:999px; background:{color}; display:inline-block;"></span>',
                    f'<span style="font-size:12px; color:{FEARGREED_MUTED_TEXT_COLOR};">{label}</span>',
                    f'<span style="font-size:12px; font-weight:700; color:{CHART_TEXT_COLOR};">{percentage:.1f}%</span>',
                    f'<span style="font-size:12px; color:{FEARGREED_MUTED_TEXT_COLOR};">{format_won(amount)}</span>',
                    (
                        f'<span style="font-size:11px; color:{FEARGREED_MUTED_TEXT_COLOR};">(보유현금 {format_won(cash_amount)} 포함)</span>'
                        if label == "안전자산" and cash_amount > 0
                        else ""
                    ),
                    "</div>",
                ]
            )
        )

    return "".join(
        [
            '<div class="holdings-mix-bar-shell" style="margin:4px 0 14px;">',
            '<div style="display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:8px;">',
            f'<div style="font-size:12px; font-weight:700; color:{CHART_TEXT_COLOR};">자산 비중</div>',
            f'<div style="font-size:11px; color:{FEARGREED_MUTED_TEXT_COLOR};">총 평가액 {format_won(total_value)}</div>',
            "</div>",
            f'<div style="display:flex; width:100%; height:18px; overflow:hidden; border-radius:999px; background:#FFFFFF; border:1px solid {FEARGREED_BORDER_COLOR};">',
            "".join(bar_segments),
            "</div>",
            '<div style="display:flex; flex-wrap:wrap; gap:10px 16px; margin-top:10px;">',
            "".join(legend_segments),
            "</div>",
            "</div>",
        ]
    )


def render_holdings_mix_bar(summary: dict[str, Any]) -> None:
    """현재 보유 종목 박스 상단에 자산 비중 막대바를 렌더링한다."""

    mix_bar_html = build_holdings_mix_bar_html(summary)
    if not mix_bar_html:
        return
    st.markdown(mix_bar_html, unsafe_allow_html=True)


def dashboard_return_metric_tone(value: float) -> str:
    """평가손익/수익률 요약 카드 값에 맞는 강조 톤을 반환한다."""

    try:
        numeric_value = float(value or 0)
    except (TypeError, ValueError):
        return "accent"
    if numeric_value > 0:
        return "positive"
    if numeric_value < 0:
        return "negative"
    return "accent"


def format_holdings_price_updated_at(value: Any) -> str:
    """보유 종목 현재가 갱신 시각을 초 단위까지 읽기 쉽게 포맷한다."""

    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        raw_value = str(value or "").strip()
        return raw_value or "-"
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def build_holdings_table_display(frame: pd.DataFrame) -> pd.DataFrame:
    """보유 종목 원본 프레임을 표시용 DataFrame으로 변환한다."""

    if frame.empty:
        return pd.DataFrame()

    display = frame[
        [
            "product_name",
            "symbol",
            "asset_type",
            "quantity",
            "avg_cost",
            "current_price",
            "cost_basis",
            "current_value",
            "profit_loss",
            "profit_rate",
            "price_updated_at",
        ]
    ].copy()
    display.columns = [
        "상품명",
        "코드",
        "자산군",
        "수량",
        "평단가",
        "현재가",
        "원금",
        "평가금액",
        "손익",
        "수익률(%)",
        "가격갱신",
    ]
    display["자산군"] = display["자산군"].map(label_asset_type)
    display["수량"] = display["수량"].map(lambda value: f"{float(value or 0):,.4f}".rstrip("0").rstrip("."))
    for column in ("평단가", "현재가", "원금", "평가금액", "손익"):
        display[column] = display[column].map(lambda value: f"{float(value or 0):,.0f}")
    display["수익률(%)"] = display["수익률(%)"].map(lambda value: f"{float(value or 0):+.2f}")
    display["가격갱신"] = display["가격갱신"].map(format_holdings_price_updated_at)
    return display


def _holding_value_tone_style(value: Any) -> str:
    """손익/수익률 숫자 문자열을 색상 스타일로 변환한다."""

    normalized_value = str(value or "").replace(",", "").replace("%", "").strip()
    numeric = pd.to_numeric(normalized_value, errors="coerce")
    if pd.isna(numeric):
        return ""
    if float(numeric) > 0:
        return f"color: {FEARGREED_UP_COLOR}; font-weight: 700;"
    if float(numeric) < 0:
        return f"color: {FEARGREED_DOWN_COLOR}; font-weight: 700;"
    return f"color: {FEARGREED_MUTED_TEXT_COLOR}; font-weight: 600;"


def style_holdings_table(display: pd.DataFrame) -> Any:
    """보유 종목 표시용 DataFrame에 손익/수익률 컬러 스타일을 적용한다."""

    if display.empty:
        return display
    return display.style.map(_holding_value_tone_style, subset=["손익", "수익률(%)"])


def _holding_value_tone_class(value: Any) -> str:
    """손익/수익률 숫자 문자열을 HTML 테이블용 tone class로 변환한다."""

    normalized_value = str(value or "").replace(",", "").replace("%", "").strip()
    numeric = pd.to_numeric(normalized_value, errors="coerce")
    if pd.isna(numeric):
        return ""
    if float(numeric) > 0:
        return " holdings-table__value--positive"
    if float(numeric) < 0:
        return " holdings-table__value--negative"
    return " holdings-table__value--neutral"


def build_holdings_table_html(display: pd.DataFrame, *, max_height: int = 420) -> str:
    """현재 보유 종목 표를 스크린샷 스타일에 맞는 HTML 테이블로 변환한다."""

    if display.empty:
        return ""

    numeric_columns = {"수량", "평단가", "현재가", "원금", "평가금액", "손익", "수익률(%)", "가격갱신"}
    tone_columns = {"손익", "수익률(%)"}

    header_html = "".join(
        f'<th class="holdings-table__head{" holdings-table__head--numeric" if column in numeric_columns else ""}">{html.escape(str(column))}</th>'
        for column in display.columns
    )

    body_rows: list[str] = []
    for row in display.to_dict(orient="records"):
        cells: list[str] = []
        for column in display.columns:
            value = str(row.get(column) or "-")
            tone_class = _holding_value_tone_class(value) if column in tone_columns else ""
            align_class = " holdings-table__cell--numeric" if column in numeric_columns else ""
            cells.append(
                f'<td class="holdings-table__cell{align_class}{tone_class}" title="{html.escape(value)}">{html.escape(value)}</td>'
            )
        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    return "".join(
        [
            f'<div class="holdings-table-shell" style="max-height:{int(max_height)}px;">',
            '<table class="holdings-table">',
            f"<thead><tr>{header_html}</tr></thead>",
            f"<tbody>{''.join(body_rows)}</tbody>",
            "</table>",
            "</div>",
        ]
    )


def auth_page(auth_enabled: bool = True) -> None:
    st.markdown('<div class="auth-page-shell"></div>', unsafe_allow_html=True)
    render_auth_feedback()

    pending_email = str(st.session_state.get(PENDING_CONFIRMATION_EMAIL_KEY) or "").strip()
    if pending_email:
        with st.container(border=True, key="auth-pending-panel"):
            st.write(f"이메일 확인 대기: `{pending_email}`")
            st.caption("예전 확인 링크가 열리지 않았다면 여기서 새 메일을 다시 보내고, 가장 최근 메일의 링크를 열어 주세요.")
            if st.button("확인 메일 다시 보내기", key="resend-confirmation", width="stretch"):
                try:
                    app_auth.resend_signup(pending_email)
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))
                else:
                    st.success(f"{pending_email} 주소로 새 확인 메일을 보냈습니다.")

    current_mode = str(st.session_state.get("auth_mode") or "sign-in").strip() or "sign-in"
    left_col, center_col, right_col = st.columns((1.15, 1.05, 1.15), gap="large")
    del left_col, right_col

    with center_col:
        with st.container(key="auth-card-shell"):
            render_auth_landing_header()
            if current_mode == "sign-up":
                render_sign_up_auth_card(auth_enabled)
            elif current_mode == "demo":
                render_demo_auth_card()
            else:
                render_sign_in_auth_card(auth_enabled)


def empty_state() -> None:
    st.markdown('<div class="empty-state-shell"></div>', unsafe_allow_html=True)
    st.title("은퇴 포트폴리오")
    st.caption("완전히 분리된 별도 Streamlit 앱입니다. 먼저 계좌를 하나 만들면 시작할 수 있습니다.")
    create_col, demo_col = st.columns((1.35, 1), gap="large")

    with create_col:
        with st.form("create-first-account", clear_on_submit=True):
            name = st.text_input("계좌 이름", placeholder="예: IRP, ISA, 미국주식")
            account_type = st.selectbox("계좌 유형", ["retirement", "brokerage"], format_func=label_account_type)
            opening_cash = st.number_input("시작 현금", min_value=0, value=0, step=100000)
            submitted = st.form_submit_button("첫 계좌 만들기", width="stretch")
    if submitted:
        try:
            account_id = create_account(name=name, account_type=account_type, opening_cash=opening_cash)
        except Exception as exc:  # noqa: BLE001
            render_operation_error(exc)
        else:
            st.session_state["selected_account_id"] = account_id
            mark_rollup_dirty()
            st.success("계좌를 만들었습니다.")
            st.rerun()

    with demo_col:
        with st.container(border=True, key="trade-log-table"):
            st.subheader("데모 모드")
            st.caption("실제 계좌 없이 화면 흐름을 빠르게 확인할 수 있도록 샘플 데이터를 불러옵니다.")
            st.write("연금 계좌, 일반 계좌, 입금, 매수, 계좌 이동, 스냅샷 예시가 함께 생성됩니다.")
            demo_submitted = st.button(
                "데모 데이터 불러오기",
                icon=":material/rocket_launch:",
                width="stretch",
                type="secondary",
            )
        if demo_submitted:
            try:
                result = seed_demo_workspace()
            except Exception as exc:  # noqa: BLE001
                render_operation_error(exc)
            else:
                st.session_state["selected_account_id"] = int(result["selected_account_id"])
                st.session_state["active_page"] = PAGES[0]
                mark_rollup_dirty()
                st.success(str(result.get("message") or "데모 데이터를 준비했습니다."))
                st.rerun()


def sidebar(accounts: list[dict[str, Any]], selected_account_id: int | None, user: dict[str, Any]) -> int:
    """공통 사이드바를 렌더링하고 선택 계좌 id를 반환한다."""

    account_ids = [int(account["id"]) for account in accounts]
    if selected_account_id not in account_ids:
        selected_account_id = account_ids[0]
        st.session_state["selected_account_id"] = selected_account_id

    with st.sidebar:
        st.title("내 작업공간")
        user_label = user.get("email") or user.get("id") or "로그인 사용자"
        st.caption("계좌 맥락과 이동 흐름을 한 곳에서 관리합니다.")

        with st.container(border=True):
            st.caption("로그인 계정")
            st.write(f"`{user_label}`")
            st.caption("페이지는 좌측 내비게이션에서 전환합니다.")
            if st.button("로그아웃", width="stretch"):
                app_auth.sign_out()
                st.session_state["selected_account_id"] = None
                st.rerun()

        with st.container(border=True):
            st.caption("보고 있는 계좌")
            selected_account_id = st.selectbox(
                "계좌",
                options=account_ids,
                index=account_ids.index(selected_account_id),
                format_func=lambda account_id: account_label(next(account for account in accounts if int(account["id"]) == account_id)),
            )
            st.session_state["selected_account_id"] = selected_account_id
            selected_account = next(account for account in accounts if int(account["id"]) == int(selected_account_id))
            st.caption(f"선택 계좌: `{selected_account['name']}`")
            st.caption(f"계좌 유형: `{label_account_type(selected_account['account_type'])}`")
            with st.expander("현재 계좌 삭제", expanded=False):
                st.warning("이 계좌를 삭제하면 보유 종목, 거래 기록, 자산 스냅샷도 함께 삭제됩니다.")
                confirm_delete_account = st.checkbox(
                    "삭제 내용을 확인했습니다.",
                    key=f"confirm-delete-account:{selected_account_id}",
                )
                if st.button(
                    "선택 계좌 삭제",
                    key=f"delete-account:{selected_account_id}",
                    width="stretch",
                    disabled=not confirm_delete_account,
                ):
                    try:
                        delete_account(int(selected_account_id))
                    except Exception as exc:  # noqa: BLE001
                        render_operation_error(exc)
                    else:
                        remaining_account_ids = [account_id for account_id in account_ids if account_id != int(selected_account_id)]
                        st.session_state["selected_account_id"] = remaining_account_ids[0] if remaining_account_ids else None
                        mark_rollup_dirty()
                        st.rerun()

        with st.container(border=True):
            st.caption("새 계좌 만들기")
            with st.expander("입력 열기", expanded=False):
                with st.form("new-account-form", clear_on_submit=True):
                    name = st.text_input("계좌 이름")
                    account_type = st.selectbox("유형", ["retirement", "brokerage"], format_func=label_account_type, key="new-account-type")
                    opening_cash = st.number_input("시작 현금", min_value=0, value=0, step=100000, key="new-account-cash")
                    submitted = st.form_submit_button("계좌 추가", width="stretch")
                if submitted:
                    try:
                        create_account(name=name, account_type=account_type, opening_cash=opening_cash)
                    except Exception as exc:  # noqa: BLE001
                        render_operation_error(exc)
                    else:
                        mark_rollup_dirty()
                        st.success("계좌를 추가했습니다.")
                        st.rerun()

    return int(selected_account_id)


def dashboard_page(account: dict[str, Any], holdings: list[dict[str, Any]], rollup_state: dict[str, Any] | None = None) -> None:
    frame = holdings_frame(holdings)
    trade_logs = list_trade_logs(int(account["id"]))
    summary = account_summary(account, holdings, trade_logs=trade_logs)
    display_cash = float(summary["cash"] or 0)
    display_total_value = float(summary["total_value"] or 0)
    display_principal_profit_loss = float(summary["principal_profit_loss"] or 0)
    display_principal_profit_rate = (
        display_principal_profit_loss / float(summary["total_principal"] or 0) * 100
        if float(summary["total_principal"] or 0)
        else 0.0
    )
    profit_tone = dashboard_return_metric_tone(display_principal_profit_loss)
    profit_rate_tone = dashboard_return_metric_tone(display_principal_profit_rate)
    account_id = int(account["id"])
    echarts_error = ""
    try:
        echarts_available = load_echarts_runtime()
    except RuntimeError as exc:
        echarts_available = False
        echarts_error = str(exc)
    selection_key = dashboard_holding_selection_key(account_id)
    trend_period_key = dashboard_trend_period_key(account_id)
    trend_measure_key = f"selected-trend-measure:{account_id}"
    available_symbols = {
        normalize_holding_symbol(holding.get("symbol"))
        for holding in holdings
        if normalize_holding_symbol(holding.get("symbol"))
    }
    selected_symbol = normalize_holding_symbol(st.session_state.get(selection_key))
    if selected_symbol and selected_symbol not in available_symbols and selected_symbol != "CASH":
        st.session_state[selection_key] = ""
        selected_symbol = ""
    period = str(st.session_state.get(trend_period_key, "6mo") or "6mo")
    if period not in DASHBOARD_SELECTED_TREND_PERIOD_OPTIONS:
        period = "6mo"
        st.session_state[trend_period_key] = period
    if str(st.session_state.get(trend_measure_key) or "").strip() not in DETAIL_MEASURE_LABELS:
        st.session_state[trend_measure_key] = DEFAULT_SELECTED_TREND_MEASURE
    overview_frame = holdings_overview_frame(holdings, selected_symbol=selected_symbol or None, limit=10)
    reference_time_text = format_dashboard_reference_time(latest_realtime_quote_time(account_id))

    with st.container(key="dashboard-summary-strip"):
        summary_cols = st.columns(5, gap="small", vertical_alignment="top")

        with summary_cols[0]:
            with st.container(border=True, key="dashboard-card-principal"):
                render_dashboard_summary_card("입금 원금", format_won(summary["total_principal"]))

        with summary_cols[1]:
            render_dashboard_cash_card(int(account["id"]), display_cash)

        with summary_cols[2]:
            render_dashboard_total_value_card(int(account["id"]), display_total_value, holdings)

        with summary_cols[3]:
            with st.container(border=True, key="dashboard-card-profit"):
                render_dashboard_summary_card("원금 대비 평가손익", format_won(display_principal_profit_loss), tone=profit_tone)

        with summary_cols[4]:
            with st.container(border=True, key="dashboard-card-profit-rate"):
                render_dashboard_summary_card("원금 대비 수익률", format_pct(display_principal_profit_rate), tone=profit_rate_tone)

    render_dashboard_reference_time(reference_time_text)

    if not echarts_available:
        st.warning(echarts_error or "현재 환경에서는 ECharts 모듈을 불러오지 못해 대시보드 차트를 표시할 수 없습니다.")

    with st.container(border=True, key="dashboard-panel-allocation"):
        treemap_options = allocation_treemap_options(
            summary,
            holdings,
            selected_symbol=selected_symbol or None,
        )
        allocation_status_text, allocation_status_tone = dashboard_allocation_status(
            account_id,
            holdings,
            has_allocation_data=treemap_options is not None,
        )
        render_dashboard_section_header(
            "자산 배분",
            "자산군에서 보유 종목까지 한 번에 보고, 종목을 누르면 아래에서 개별 트렌드를 바로 확인합니다.",
            status_text=allocation_status_text,
            status_tone=allocation_status_tone,
            status_palette_colors=FEARGREED_TREEMAP_PALETTE if treemap_options is not None else None,
        )
        if treemap_options is None:
            st.info("배분을 그릴 데이터가 아직 없습니다.")
        elif not echarts_available:
            st.info("현재 환경에서는 자산 배분 차트를 표시할 수 없습니다.")
        else:
            treemap_selection = st_echarts(
                options=treemap_options,
                height=f"{DASHBOARD_ALLOCATION_CHART_HEIGHT}px",
                key=f"allocation-treemap:{account_id}",
                on_select="rerun",
                selection_mode="points",
            )
            if sync_dashboard_selected_holding(account_id, treemap_selection, holdings=holdings):
                st.rerun()

    with st.container(key="dashboard-secondary-grid"):
        trend_col, holdings_col = st.columns((1, 1), gap="large", vertical_alignment="top")

        with trend_col:
            with st.container(border=True, key="dashboard-panel-selected-trend"):
                selected_trend_measure = DEFAULT_SELECTED_TREND_MEASURE
                st.markdown("### 선택 종목 트렌드")

                if not selected_symbol:
                    st.info("자산 배분 트리맵에서 종목 타일을 누르면 여기에서 해당 종목 트렌드가 표시됩니다.")
                elif selected_symbol == "CASH":
                    with st.container(key="dashboard-trend-controls"):
                        _, action_col = st.columns((1, 0.36), gap="medium", vertical_alignment="bottom")
                        with action_col:
                            if st.button("선택 해제", key=f"clear-selected-holding:{account_id}", width="stretch"):
                                st.session_state[selection_key] = ""
                                st.rerun()
                    st.info("예수금은 시장 가격 추이가 없어서 개별 트렌드 차트를 표시하지 않습니다.")
                else:
                    selected_holding_name = dashboard_selected_holding_name(holdings, selected_symbol)
                    with st.container(key="dashboard-trend-controls"):
                        period_col, measure_col, action_col = st.columns(
                            (0.98, 0.82, 0.46),
                            gap="small",
                            vertical_alignment="center",
                        )
                        with period_col:
                            period = st.selectbox(
                                "기간",
                                options=list(DASHBOARD_SELECTED_TREND_PERIOD_OPTIONS),
                                format_func=label_period,
                                key=trend_period_key,
                                index=list(DASHBOARD_SELECTED_TREND_PERIOD_OPTIONS).index(period),
                                label_visibility="collapsed",
                            )
                        with measure_col:
                            selected_trend_measure = st.selectbox(
                                "표시 지표",
                                options=["market_value", "profit_rate", "close"],
                                format_func=label_detail_measure,
                                key=trend_measure_key,
                                index=["market_value", "profit_rate", "close"].index(
                                    str(st.session_state.get(trend_measure_key) or DEFAULT_SELECTED_TREND_MEASURE)
                                ),
                                label_visibility="collapsed",
                            )
                        with action_col:
                            if st.button(
                                "선택 해제",
                                key=f"clear-selected-holding:{account_id}",
                                width="stretch",
                                type="secondary",
                            ):
                                st.session_state[selection_key] = ""
                                st.rerun()
                    selected_holdings = [
                        holding for holding in holdings if normalize_holding_symbol(holding.get("symbol")) == selected_symbol
                    ]
                    if not selected_holdings:
                        st.info("선택한 종목을 현재 보유 목록에서 찾지 못했습니다.")
                    else:
                        try:
                            with st.spinner(f"{selected_holding_name} 추이를 불러오는 중입니다..."):
                                selected_holding_trend = build_selected_holding_trend_frame(
                                    selected_holdings,
                                    period=period,
                                )
                        except Exception as exc:  # noqa: BLE001
                            st.warning(f"선택 종목 추이를 불러오지 못했습니다: {exc}")
                        else:
                            if selected_holding_trend.empty:
                                st.info("선택 종목의 시세 이력이 아직 없어 트렌드 차트를 표시할 수 없습니다.")
                            else:
                                selected_frame = selected_holding_trend.sort_values("date").copy()
                                selected_measure = str(selected_trend_measure or DEFAULT_SELECTED_TREND_MEASURE)
                                selected_symbol_code = str(selected_holdings[0].get("symbol") or selected_symbol).strip() or selected_symbol
                                if echarts_available:
                                    trend_options = selected_holding_trend_options(
                                        selected_frame,
                                        selected_holding_name=selected_holding_name,
                                        selected_symbol_code=selected_symbol_code,
                                        measure=selected_measure,
                                        period_label=label_period(period),
                                    )
                                    if trend_options is None:
                                        st.info("선택 종목의 추이 옵션을 만들지 못했습니다.")
                                    else:
                                        st_echarts(
                                            options=trend_options,
                                            height=f"{DASHBOARD_DETAIL_CHART_HEIGHT}px",
                                            key=f"selected-holding-trend:{account_id}:{selected_symbol}:{selected_measure}:{period}",
                                        )
                                else:
                                    trend_chart = selected_holding_trend_chart(
                                        selected_frame,
                                        measure=selected_measure,
                                        selected_holding_name=selected_holding_name,
                                        selected_symbol_code=selected_symbol_code,
                                        period_label=label_period(period),
                                    )
                                    st.altair_chart(
                                        style_dashboard_altair_chart(trend_chart, height=DASHBOARD_DETAIL_CHART_HEIGHT),
                                        width="stretch",
                                    )

        with holdings_col:
            with st.container(border=True, key="dashboard-panel-holdings"):
                render_dashboard_section_header("보유 종목 수익률", "현재 보유 상위 종목의 수익률 흐름을 같은 행에서 함께 비교합니다.")
                if overview_frame.empty:
                    st.info("보유 종목이 없어 수익률 차트를 그릴 수 없습니다.")
                elif not echarts_available:
                    fallback_chart = holdings_bar_fallback_chart(overview_frame, selected_symbol=selected_symbol or None)
                    if fallback_chart is None:
                        st.info("현재 환경에서는 보유 종목 수익률 차트를 표시할 수 없습니다.")
                    else:
                        st.altair_chart(fallback_chart, width="stretch")
                else:
                    bar_options = holdings_bar_options(overview_frame, selected_symbol=selected_symbol or None)
                    st_echarts(
                        options=bar_options,
                        height=f"{DASHBOARD_HOLDINGS_COMPARE_CHART_HEIGHT}px",
                        key=f"holdings-profit-bar:{account_id}",
                    )

    with st.container(border=True, key="dashboard-panel-holdings-table"):
        render_dashboard_section_header("현재 보유 종목", "계좌 전체 포지션을 표로 읽고 현재 선택 종목과 함께 확인합니다.", compact=True)
        render_holdings_mix_bar(summary)
        show_holdings_table(frame, height=DASHBOARD_HOLDINGS_TABLE_HEIGHT)


def trade_entry_page(account: dict[str, Any], holdings: list[dict[str, Any]], accounts: list[dict[str, Any]]) -> None:
    apply_pending_form_reset(
        st.session_state,
        pending_key=TRADE_FORM_RESET_PENDING_KEY,
        reset_values={
            TRADE_SYMBOL_KEY: "",
            TRADE_PRODUCT_NAME_KEY: "",
            TRADE_SEARCH_QUERY_KEY: "",
            TRADE_QUANTITY_KEY: 1.0,
            TRADE_PRICE_KEY: 0.0,
            TRADE_NOTES_KEY: "",
            TRADE_PREFILL_MARKER_KEY: "",
        },
    )
    apply_pending_form_reset(
        st.session_state,
        pending_key=CASH_FLOW_FORM_RESET_PENDING_KEY,
        reset_values={
            CASH_FLOW_AMOUNT_KEY: 0,
            CASH_FLOW_NOTES_KEY: "",
        },
    )

    st.title("거래")
    st.caption("매수/매도와 현금 흐름을 한 화면에서 이어서 기록합니다. 보유현금은 거래와 연동하지 않고 직접 수정한 값만 유지합니다.")
    echarts_error = ""
    try:
        echarts_available = load_echarts_runtime()
    except RuntimeError as exc:
        echarts_available = False
        echarts_error = str(exc)
    feedback_message = consume_session_message(st.session_state, TRADE_PAGE_SUCCESS_MESSAGE_KEY)
    if feedback_message:
        st.success(feedback_message)
    trade_col, cash_flow_col = st.columns((1.45, 1.0), gap="large", vertical_alignment="top")

    with trade_col:
        with st.container(border=True):
            st.subheader("상품 등록")
            st.caption("매입가, 수량/좌수, 매입일을 입력하면 현황과 매매일지에 반영합니다.")
            holding_options = {holding["product_name"]: holding for holding in holdings}
            trade_type = st.radio(
                "거래 유형",
                ["buy", "sell"],
                format_func=label_trade_type,
                key=TRADE_TYPE_KEY,
                horizontal=True,
                label_visibility="collapsed",
            )

            if holding_options and trade_type == "sell":
                selected_holding_name = st.selectbox(
                    "보유 상품",
                    options=list(holding_options),
                    key=f"sell-holding:{account['id']}",
                )
                prefill_trade_from_holding(
                    holding_options[selected_holding_name],
                    marker=f"sell:{account['id']}:{selected_holding_name}",
                )
            else:
                st.session_state[TRADE_PREFILL_MARKER_KEY] = "buy"

            keyup_input = load_keyup_runtime()
            search_query = keyup_input(
                    "상품명 또는 코드",
                    value=str(st.session_state.get(TRADE_SEARCH_QUERY_KEY) or ""),
                    key=TRADE_SEARCH_QUERY_KEY,
                    debounce=150,
                    placeholder="예: K55207BU0715, 0177N0, 파인인덱스",
                )

            cleaned_search_query = str(search_query or "").strip()
            if cleaned_search_query and cleaned_search_query != str(st.session_state.get(TRADE_PRODUCT_NAME_KEY) or "").strip():
                st.session_state[TRADE_PRODUCT_NAME_KEY] = cleaned_search_query
            if len(cleaned_search_query) >= 2:
                suggestions = search_products(cleaned_search_query, limit=8)
                with st.container(border=True, height=260, key="trade-search-suggestions"):
                    if suggestions:
                        for product in suggestions:
                            if st.button(
                                product_search_option_label(product),
                                key=f"product-suggestion:{account['id']}:{product['code']}",
                                width="stretch",
                            ):
                                apply_search_product(product)
                                st.rerun()
                    else:
                        st.caption("검색 결과가 없습니다.")

            symbol = st.text_input(
                "상품 코드",
                key=TRADE_SYMBOL_KEY,
                help="예: 0177N0, 005930, AAPL, K55207BU0715",
            )
            st.caption("ETF는 공개 코드, 펀드는 표준코드로 등록하면 자동 가격 조회를 시도합니다.")

            trade_value_col, quantity_col = st.columns(2, gap="medium")
            with trade_value_col:
                price = st.number_input(trade_price_label(trade_type), min_value=0.0, step=100.0, key=TRADE_PRICE_KEY)
            with quantity_col:
                quantity = st.number_input("수량/좌수", min_value=0.0, step=1.0, key=TRADE_QUANTITY_KEY)

            unit_col, trade_date_col = st.columns(2, gap="medium")
            with unit_col:
                st.selectbox("단위", ["주"], index=0, key=f"trade-unit:{account['id']}")
            with trade_date_col:
                trade_date = st.date_input(trade_date_label(trade_type), key=TRADE_DATE_KEY)

            asset_col, notes_col = st.columns(2, gap="medium")
            with asset_col:
                asset_type = st.selectbox(
                    "자산 구분",
                    ["risk", "safe"],
                    format_func=label_asset_type,
                    key=TRADE_ASSET_TYPE_KEY,
                )
            with notes_col:
                notes = st.text_input("메모", key=TRADE_NOTES_KEY, placeholder="선택 입력")

            submitted = st.button(
                trade_submit_button_label(trade_type),
                width="stretch",
                key=f"trade-save:{account['id']}",
                type="primary",
            )
            if submitted:
                resolved_product_name = str(
                    st.session_state.get(TRADE_PRODUCT_NAME_KEY)
                    or search_query
                    or symbol
                    or ""
                ).strip()
                try:
                    record_trade(
                        int(account["id"]),
                        symbol=symbol,
                        product_name=resolved_product_name,
                        trade_type=trade_type,
                        asset_type=asset_type,
                        quantity=quantity,
                        price=price,
                        trade_date=trade_date.isoformat(),
                        notes=notes,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    mark_rollup_dirty()
                    st.session_state[TRADE_FORM_RESET_PENDING_KEY] = True
                    st.session_state[TRADE_PAGE_SUCCESS_MESSAGE_KEY] = "거래를 저장했습니다."
                    st.rerun()

    with cash_flow_col:
        with st.container(border=True):
            flow_type = st.radio(
                "현금 흐름 구분",
                ["personal_deposit", "employer_deposit", "withdraw"],
                format_func=label_cash_flow_type,
                key=CASH_FLOW_TYPE_KEY,
                horizontal=True,
                label_visibility="collapsed",
            )
            st.subheader(cash_flow_panel_title(flow_type))
            st.caption(cash_flow_panel_caption(flow_type))
            date_col, amount_col, action_col = st.columns((1.15, 2.6, 0.95), gap="small")
            with date_col:
                trade_date = st.date_input("처리일", key=CASH_FLOW_DATE_KEY, label_visibility="collapsed")
            with amount_col:
                amount = st.number_input("금액", min_value=0, step=100000, key=CASH_FLOW_AMOUNT_KEY, label_visibility="collapsed")
            with action_col:
                submitted = st.button(
                    cash_flow_submit_label(flow_type),
                    width="stretch",
                    key=f"cash-flow-save:{account['id']}",
                    type="primary",
                )
            notes = st.text_area("메모", height=90, key=CASH_FLOW_NOTES_KEY, placeholder="메모 선택 입력", label_visibility="collapsed")
            if submitted:
                try:
                    record_cash_flow(
                        int(account["id"]),
                        flow_type=flow_type,
                        amount=amount,
                        trade_date=trade_date.isoformat(),
                        notes=notes,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    mark_rollup_dirty()
                    st.session_state[CASH_FLOW_FORM_RESET_PENDING_KEY] = True
                    st.session_state[TRADE_PAGE_SUCCESS_MESSAGE_KEY] = "현금 흐름을 기록했습니다."
                    st.rerun()

    logs = list_trade_logs(int(account["id"]))
    visible_logs = [row for row in logs if is_visible_trade_log(row)]
    realized = realized_summary(logs)

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("실현 포지션 수", f"{int(realized['sold_count']):,}")
    metric_2.metric("총 매수금액", format_won(realized["total_buy_amount"]))
    metric_3.metric("총 매도금액", format_won(realized["total_sell_amount"]))
    metric_4.metric("실현 수익률", format_pct(realized["total_profit_rate"]))

    realized_positions = realized.get("positions") or []
    if realized_positions:
        chart_frame = pd.DataFrame(realized_positions).sort_values("profit_loss", ascending=False).head(10).copy()
        if echarts_available:
            realized_options = realized_profit_bar_options(chart_frame)
            if realized_options is None:
                st.info("실현손익 차트를 만들 데이터가 아직 없습니다.")
            else:
                st_echarts(
                    options=realized_options,
                    height=f"{DASHBOARD_HOLDINGS_CHART_HEIGHT}px",
                    key=f"realized-profit-bar:{account['id']}",
                )
        else:
            realized_chart = realized_profit_bar_fallback_chart(chart_frame)
            if realized_chart is None:
                st.info("현재 환경에서는 실현손익 차트를 표시할 수 없습니다.")
            else:
                st.altair_chart(realized_chart, width="stretch")

        position_frame = pd.DataFrame(realized_positions)
        position_frame = position_frame[["product_name", "symbol", "asset_type", "buy_amount", "sell_amount", "profit_loss", "profit_rate", "sell_date"]].copy()
        position_frame.columns = ["상품명", "코드", "자산군", "매수금액", "매도금액", "실현손익", "실현수익률(%)", "매도일"]
        position_frame["자산군"] = position_frame["자산군"].map(label_asset_type)
        for column in ("매수금액", "매도금액", "실현손익"):
            position_frame[column] = position_frame[column].map(lambda value: f"{float(value or 0):,.0f}")
        position_frame["실현수익률(%)"] = position_frame["실현수익률(%)"].map(lambda value: f"{float(value or 0):+.2f}")
        st.subheader("실현 손익 요약")
        st.dataframe(
            position_frame.style.map(_holding_value_tone_style, subset=["실현손익", "실현수익률(%)"]),
            width="stretch",
            hide_index=True,
            height=280,
        )

    if visible_logs:
        account_name_map = {int(item["id"]): account_label(item) for item in accounts}
        st.subheader("거래 기록")
        edit_state_key = f"trade-log-editing:{account['id']}"
        delete_state_key = f"trade-log-delete-pending:{account['id']}"
        log_by_id = {int(row["id"]): row for row in visible_logs if row.get("id") is not None}
        editing_log_id = _optional_int(st.session_state.get(edit_state_key))
        delete_log_id = _optional_int(st.session_state.get(delete_state_key))
        if editing_log_id is None and edit_state_key in st.session_state:
            st.session_state.pop(edit_state_key, None)
        if delete_log_id is None and delete_state_key in st.session_state:
            st.session_state.pop(delete_state_key, None)
        with st.container(border=True):
            header_columns = st.columns(TRADE_LOG_TABLE_COLUMN_WEIGHTS, gap="small")
            for column, label in zip(header_columns, TRADE_LOG_TABLE_HEADER_LABELS):
                with column:
                    st.caption(label)

            for row in visible_logs:
                log_id = int(row["id"])
                row_columns = st.columns(TRADE_LOG_TABLE_COLUMN_WEIGHTS, gap="small")
                for column, field_name in zip(row_columns[:-1], TRADE_LOG_TABLE_DISPLAY_FIELDS):
                    with column:
                        cell_value = format_trade_log_cell(row, field_name, account_name_map)
                        if field_name == "trade_type":
                            st.markdown(cell_value, unsafe_allow_html=True)
                        else:
                            st.write(cell_value)
                with row_columns[-1]:
                    if is_trade_log_editable(row):
                        action_col_1, action_col_2 = st.columns(2, gap="small")
                        with action_col_1:
                            if st.button("수정", key=f"trade-log-edit-button:{account['id']}:{log_id}", width="stretch"):
                                st.session_state[edit_state_key] = log_id
                                st.session_state.pop(delete_state_key, None)
                                st.rerun()
                        with action_col_2:
                            if st.button("삭제", key=f"trade-log-delete-button:{account['id']}:{log_id}", width="stretch"):
                                st.session_state[delete_state_key] = log_id
                                st.session_state.pop(edit_state_key, None)
                                st.rerun()
                    else:
                        st.caption("-")
                if editing_log_id == log_id:
                    render_trade_log_edit_form(
                        account,
                        row,
                        edit_state_key=edit_state_key,
                        editing_log_id=log_id,
                    )
                st.divider()

        if editing_log_id is not None and editing_log_id not in log_by_id:
            st.session_state.pop(edit_state_key, None)
        if delete_log_id in log_by_id:
            selected_log = log_by_id[int(delete_log_id)]
            render_trade_log_delete_dialog(
                int(account["id"]),
                int(delete_log_id),
                selected_log,
                delete_state_key=delete_state_key,
            )
        elif delete_log_id is not None:
            st.session_state.pop(delete_state_key, None)
    else:
        st.info("아직 기록된 거래가 없습니다.")


def data_page(account: dict[str, Any], rollup_state: dict[str, Any] | None = None) -> None:
    st.title("데이터")
    st.caption("운영 상태 확인과 원본 데이터 CSV 내보내기를 한 곳에서 처리합니다.")

    account_id = int(account["id"])
    status = backend_status()
    market_status = quote_provider_status() or {}
    holdings = list_holdings(account_id)
    worker_status = get_realtime_worker_status(account_id) or {}
    trade_logs = list_trade_logs(account_id)
    visible_trade_logs = [row for row in trade_logs if is_visible_trade_log(row)]
    snapshot_rows = list_account_snapshots(account_id)
    last_quote_at = latest_realtime_quote_time(account_id)
    snapshot_date = str((rollup_state or {}).get("snapshot_date") or date.today().isoformat()).strip()
    summary = account_summary(account, holdings, trade_logs=trade_logs)
    cumulative_frame = cumulative_contribution_frame(
        trade_logs=trade_logs,
        snapshots=snapshot_rows,
        current_total_value=float(summary["total_value"] or 0),
        current_market_value=float(summary["market_value"] or 0),
        current_cash_balance=float(summary["cash"] or 0),
        current_total_cost=float(summary["total_cost"] or 0),
        current_date=snapshot_date,
    )

    with st.container(border=True):
        st.subheader("운영 상태")
        st.caption(f"기준 계좌: `{account['name']}`")
        status_col_1, status_col_2, status_col_3, status_col_4 = st.columns(4)
        status_col_1.metric("데이터 저장소", "Supabase" if status["name"] == "supabase" else "로컬 SQLite")
        status_col_2.metric("거래 기록", f"{len(visible_trade_logs):,}건", latest_date_text(visible_trade_logs, "trade_date"))
        status_col_3.metric("현재 보유현금", format_won(summary["cash"]))
        status_col_4.metric("자산 스냅샷", f"{len(snapshot_rows):,}건", latest_date_text(snapshot_rows, "snapshot_date"))
        quote_col_1, quote_col_2, quote_col_3 = st.columns(3)
        quote_col_1.metric(
            "KIS REST",
            "사용 가능" if market_status.get("kis_rest_enabled") else "미설정",
            f"env={market_status.get('kis_env', '-')}",
        )
        quote_col_2.metric(
            "KIS WebSocket worker",
            str(worker_status.get("connection_state") or "미확인"),
            str(worker_status.get("last_seen_at") or "-"),
        )
        quote_col_3.metric(
            "마지막 quote 반영",
            str(last_quote_at or "-"),
            str(worker_status.get("last_quote_at") or "-"),
        )
        if status.get("override", "auto") != "auto":
            st.caption(f"백엔드 강제 설정: `{status['override']}`")
        st.caption(f"Supabase 설정 감지: `{'예' if status.get('has_supabase_config') else '아니오'}`")
        config_col_1, config_col_2 = st.columns(2)
        config_col_1.caption(
            f"SUPABASE_URL 설정: `{'예' if status.get('supabase_url_present') else '아니오'}` "
            f"(`{status.get('supabase_url_source', 'unknown')}`)"
        )
        config_col_2.caption(
            f"SUPABASE_KEY 설정: `{'예' if status.get('supabase_key_present') else '아니오'}` "
            f"(`{status.get('supabase_key_source', 'unknown')}`)"
        )
        if status.get("supabase_project_host"):
            st.caption(f"Supabase 프로젝트: `{status['supabase_project_host']}`")
        if status.get("missing_config"):
            missing_text = ", ".join(f"`{item}`" for item in status["missing_config"])
            st.caption(f"누락 설정: {missing_text}")
        if market_status.get("kis_missing_config"):
            missing_text = ", ".join(f"`{item}`" for item in market_status["kis_missing_config"])
            st.caption(f"KIS 누락 설정: {missing_text}")
        if market_status.get("kis_master_cache_updated_at"):
            st.caption(f"KIS 마스터 캐시: `{market_status['kis_master_cache_updated_at']}`")
        for notice in status.get("notices", []):
            st.caption(f"참고: {notice}")

        if status["name"] == "sqlite":
            st.warning("현재 배포본은 로컬 SQLite 저장소를 사용 중입니다. 재배포 환경에서는 초기화될 수 있습니다.")
            if status["reason"]:
                st.caption(f"감지 사유: {status['reason']}")
            st.info(
                "운영 상태가 전환되려면 `setup_supabase.sql` 적용, Streamlit secrets의 `SUPABASE_URL`/`SUPABASE_KEY` 확인, "
                "`Daily Rollup` 실행 상태 확인 순서로 점검하는 것이 좋습니다."
            )
        else:
            st.success("현재 배포본은 Supabase를 사용 중입니다.")

        # 보유 종목 정리 버튼
        st.divider()
        cleanup_col_1, cleanup_col_2 = st.columns([3, 1])
        cleanup_col_1.caption(
            "**보유 종목 정리**: 거래 기록 삭제 후 발생한 orphaned holdings를 정리합니다. "
            "모든 계좌의 보유 종목을 거래 원장 기준으로 재계산합니다."
        )
        if cleanup_col_2.button("🧹 정리 실행", key="cleanup_orphaned_holdings"):
            from src.cleanup import cleanup_orphaned_holdings  # type: ignore

            with st.status("보유 종목을 정리 중입니다...", expanded=True) as cleanup_status:
                result = cleanup_orphaned_holdings()
                cleanup_status.update(
                    label="보유 종목 정리 완료" if result["success"] else "보유 종목 정리 실패",
                    state="complete" if result["success"] else "error",
                )

            if result["success"]:
                st.success(result["message"])
                if result["rebuilt_count"] > 0:
                    st.info(f"대시보드를 새로고침하여 변경 사항을 확인하세요.")
                if result["errors"]:
                    with st.expander(f"⚠️ 오류 상세 ({len(result['errors'])}건)"):
                        for error in result["errors"]:
                            st.caption(f"• {error}")
            else:
                st.error(result["message"])

    with st.container(border=True):
        st.subheader("원금 누적 기록")
        st.caption("최초 입금일부터 현재까지 누적 원금과 현재 평가액 기준 수익률을 함께 봅니다.")
        st.caption("연금(IRP/퇴직연금) 계좌는 회사 납입금을 투자원금에 포함하고, 현재 수익률은 현재 평가액을 기준으로 계산합니다.")
        if cumulative_frame.empty:
            st.info("누적 원금 기록을 만들 현금 흐름 데이터가 아직 없습니다.")
        else:
            latest_row = cumulative_frame.iloc[-1]
            metric_col_1, metric_col_2, metric_col_3 = st.columns(3)
            metric_col_1.metric("누적 투자원금", format_won(latest_row["total_principal"]))
            metric_col_2.metric("현재 평가액", format_won(latest_row["total_value"]))
            metric_col_3.metric(
                "원금 대비 현재 수익률",
                format_pct(latest_row["principal_profit_rate"]),
                metric_delta(latest_row["principal_profit_loss"]),
            )

            display_frame = cumulative_frame[
                [
                    "date",
                    "personal_deposit_delta",
                    "employer_deposit_delta",
                    "withdraw_delta",
                    "company_principal",
                    "total_principal",
                    "total_value",
                    "principal_profit_loss",
                    "principal_profit_rate",
                ]
            ].copy()
            display_frame.columns = [
                "기준일",
                "당일 개인 입금",
                "당일 회사 납입",
                "당일 출금",
                "회사 납입 누계",
                "누적 투자원금",
                "현재 평가액",
                "원금 대비 손익",
                "원금 대비 수익률(%)",
            ]

            def _format_optional_won(value: Any) -> str:
                if pd.isna(value):
                    return "-"
                return format_won(value)

            def _format_optional_pct(value: Any) -> str:
                if pd.isna(value):
                    return "-"
                return format_pct(value)

            for column in (
                "당일 개인 입금",
                "당일 회사 납입",
                "당일 출금",
                "회사 납입 누계",
                "누적 투자원금",
                "현재 평가액",
                "원금 대비 손익",
            ):
                display_frame[column] = display_frame[column].map(_format_optional_won)
            display_frame["원금 대비 수익률(%)"] = display_frame["원금 대비 수익률(%)"].map(_format_optional_pct)
            st.dataframe(display_frame, width="stretch", hide_index=True, height=320)

    for table_name in ("accounts", "holdings", "trade_logs", "daily_account_snapshot"):
        rows = export_dataframe_rows(table_name)
        frame = pd.DataFrame(rows)
        csv_bytes = frame.to_csv(index=False).encode("utf-8-sig") if not frame.empty else b""
        with st.container(border=True):
            table_label = label_table_name(table_name)
            st.subheader(table_label)
            st.write(f"행 수: `{len(frame):,}`")
            if not frame.empty:
                st.dataframe(frame, width="stretch", hide_index=True, height=220)
            else:
                st.info("데이터가 없습니다.")
            st.download_button(
                label=f"{table_label} CSV 다운로드",
                data=csv_bytes,
                file_name=f"{table_name}.csv",
                mime="text/csv",
                width="stretch",
            )


def render_navigation_page(page_name: str) -> None:
    """`st.navigation`으로 선택된 페이지 본문을 렌더링한다."""

    context = st.session_state.get(NAVIGATION_CONTEXT_KEY)
    if not isinstance(context, dict):
        st.warning("페이지 컨텍스트가 없습니다. 앱을 새로고침해 주세요.")
        return

    st.session_state["active_page"] = page_name
    account = context.get("account")
    accounts = context.get("accounts") or []
    holdings = context.get("holdings") or []
    rollup_state = context.get("rollup_state") or {}
    if not isinstance(account, dict):
        st.warning("선택 계좌 정보를 불러오지 못했습니다. 사이드바에서 계좌를 다시 선택해 주세요.")
        return

    if page_name == "Dashboard":
        account_id = int(account["id"])
        live_refresh_interval = dashboard_live_refresh_interval(account_id, holdings)
        if live_refresh_interval and hasattr(st, "fragment"):
            @st.fragment(run_every=live_refresh_interval)
            def render_dashboard_fragment() -> None:
                refreshed_account = get_account(account_id) or account
                refreshed_holdings = list_holdings(account_id)
                dashboard_page(refreshed_account, refreshed_holdings, rollup_state)

            render_dashboard_fragment()
        else:
            dashboard_page(account, holdings, rollup_state)
    elif page_name == "Trades":
        trade_entry_page(account, holdings, accounts)
    else:
        data_page(account, rollup_state)


def build_navigation_pages() -> list[Any]:
    """Streamlit 페이지 라우팅 선언을 반환한다."""

    return [
        st.Page("pages/dashboard.py", title=PAGE_LABELS["Dashboard"], icon=":material/dashboard:", default=True),
        st.Page("pages/trades.py", title=PAGE_LABELS["Trades"], icon=":material/swap_horiz:"),
        st.Page("pages/data.py", title=PAGE_LABELS["Data"], icon=":material/database:"),
    ]


def navigation_page_name(page: Any) -> str:
    """`st.navigation`이 반환한 페이지 객체를 내부 페이지 이름으로 변환한다."""

    try:
        current_url = str(getattr(st.context, "url", "") or "").split("?", 1)[0].rstrip("/")
    except Exception:
        current_url = ""
    if current_url.endswith("/trades"):
        return "Trades"
    if current_url.endswith("/data"):
        return "Data"

    page_title = str(getattr(page, "title", "") or "").strip()
    for page_name, label in PAGE_LABELS.items():
        if page_title == label:
            return page_name

    page_path = str(getattr(page, "url_path", "") or "").strip().strip("/")
    if page_path == "trades":
        return "Trades"
    if page_path == "data":
        return "Data"
    return PAGES[0]


def hide_implicit_pages_navigation() -> None:
    """인증/온보딩 화면에서 `pages/` 자동 내비게이션을 숨긴다."""

    return None


def main() -> None:
    """앱 공통 프레임을 준비하고 Streamlit 내비게이션을 실행한다."""

    init_state()
    inject_app_styles()
    auth_enabled = app_auth.is_enabled()

    if auth_enabled and handle_auth_callback():
        st.rerun()

    if auth_enabled or app_auth.is_demo_user():
        app_auth.refresh_session_state()
    user = app_auth.get_user()
    if not user:
        hide_implicit_pages_navigation()
        if not auth_enabled:
            st.info("Supabase 인증 설정이 없어 실제 로그인은 비활성 상태입니다. 아래 `데모 접속`으로 로컬 테스트 작업공간은 바로 사용할 수 있습니다.")
        auth_page(auth_enabled=auth_enabled)
        return

    initialize_database()
    status = backend_status()
    if status["name"] == "sqlite":
        message = "현재 저장소는 로컬 SQLite 임시 저장소입니다. 재배포 시 초기화될 수 있습니다."
        if status["reason"]:
            message = f"{message} {status['reason']}"
        st.warning(message)
    else:
        st.caption("현재 저장소: Supabase")
    accounts = list_accounts()
    if not accounts:
        hide_implicit_pages_navigation()
        empty_state()
        return

    page = st.navigation(build_navigation_pages(), expanded=True)
    st.session_state["active_page"] = navigation_page_name(page)
    selected_account_id = sidebar(accounts, st.session_state.get("selected_account_id"), user)
    account = get_account(int(selected_account_id))
    if not account:
        st.session_state["selected_account_id"] = None
        if st.session_state.get(INVALID_ACCOUNT_RERUN_GUARD_KEY):
            st.warning("선택한 계좌를 찾지 못해 자동 새로고침을 중단했습니다. 사이드바에서 다른 계좌를 선택하거나 데이터를 다시 확인해 주세요.")
            return
        st.session_state[INVALID_ACCOUNT_RERUN_GUARD_KEY] = True
        st.rerun()
    st.session_state[INVALID_ACCOUNT_RERUN_GUARD_KEY] = False
    holdings = list_holdings(int(account["id"]))
    rollup_state: dict[str, Any] = {"snapshot_date": date.today().isoformat(), "snapshot_updated": False}
    if should_sync_rollup(int(account["id"])):
        try:
            rollup_state.update(
                sync_account_rollup(
                    int(account["id"]),
                    today_date=rollup_state["snapshot_date"],
                )
            )
        except Exception as exc:  # noqa: BLE001
            st.warning(f"당일 자산 스냅샷 저장을 건너뛰었습니다: {exc}")
        else:
            mark_rollup_synced(int(account["id"]))
    st.session_state[NAVIGATION_CONTEXT_KEY] = {
        "account": account,
        "accounts": accounts,
        "holdings": holdings,
        "rollup_state": rollup_state,
    }

    page.run()


if __name__ == "__main__":
    main()

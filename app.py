from __future__ import annotations

import html
import importlib
from datetime import date
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta

try:
    from streamlit_echarts import JsCode, st_echarts
except ImportError:  # pragma: no cover - 의존성 미설치 환경 fallback
    JsCode = None
    st_echarts = None

from src.analytics import (
    account_summary,
    allocation_treemap_nodes,
    build_portfolio_trend,
    cumulative_contribution_frame,
    holdings_frame,
    realized_summary,
)

import src.auth as app_auth
import src.analytics as analytics_module
import src.db as _db
import src.market as market_module

market_module = importlib.reload(market_module)
fetch_latest_price = market_module.fetch_latest_price
search_products = getattr(market_module, "search_products", lambda query, limit=8: [])

create_account = _db.create_account
delete_account = _db.delete_account
adjust_cash_balance = _db.adjust_cash_balance
export_dataframe_rows = _db.export_dataframe_rows
get_account = _db.get_account
initialize_database = _db.initialize_database
list_accounts = _db.list_accounts
list_account_snapshots = _db.list_account_snapshots
list_daily_interest = _db.list_daily_interest
list_holdings = _db.list_holdings
list_trade_logs = _db.list_trade_logs
record_account_snapshot = _db.record_account_snapshot
record_account_transfer = _db.record_account_transfer
record_cash_flow = _db.record_cash_flow
record_trade = _db.record_trade
seed_demo_workspace = _db.seed_demo_workspace
set_holding_price = _db.set_holding_price
backend_status = _db.backend_status
is_accounts_hotfix_error = _db.is_accounts_hotfix_error
sync_account_rollup = _db.sync_account_rollup


def holdings_overview_frame(
    holdings: list[dict[str, Any]],
    *,
    selected_symbol: str | None = None,
    limit: int = 10,
) -> pd.DataFrame:
    """개요 차트용 보유 종목 프레임을 호환성 있게 반환한다."""

    helper = getattr(analytics_module, "holdings_overview_frame", None)
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
    page_icon=":material/account_balance_wallet:",
    layout="wide",
)


PAGES = ("Dashboard", "Trades", "Data")
PENDING_CONFIRMATION_EMAIL_KEY = "pending_confirmation_email"
AUTH_FEEDBACK_KEY = "auth_feedback"
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
TRANSFER_TARGET_ACCOUNT_KEY = "transfer_target_account_id"
TRANSFER_AMOUNT_KEY = "transfer_amount"
TRANSFER_DATE_KEY = "transfer_date"
TRANSFER_NOTES_KEY = "transfer_notes"
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
DETAIL_MEASURE_LABELS = {
    "market_value": "평가금액",
    "profit_rate": "수익률",
    "close": "종가",
}
PERIOD_LABELS = {
    "1mo": "1개월",
    "3mo": "3개월",
    "6mo": "6개월",
    "1y": "1년",
}
DASHBOARD_OVERVIEW_PANEL_HEIGHT = 560
DASHBOARD_OVERVIEW_CHART_HEIGHT = 400
DASHBOARD_DETAIL_CHART_HEIGHT = 300
DASHBOARD_HOLDINGS_TABLE_HEIGHT = 380
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


def label_table_name(value: Any) -> str:
    return TABLE_LABELS.get(str(value), str(value))


def render_operation_error(exc: Exception) -> None:
    """사용자 작업 오류와 필요한 운영 후속 조치를 함께 표시한다."""

    st.error(str(exc))
    if not is_accounts_hotfix_error(exc):
        return

    with st.container(border=True):
        st.caption("운영 조치 필요")
        st.write("현재 계좌 생성과 데모 데이터 시드는 앱 코드가 아니라 운영 Supabase RLS 정책 때문에 차단되고 있습니다.")
        st.write("1. 운영 Supabase SQL Editor에서 `docs/supabase-owner-user-id-hotfix.sql` 또는 최신 `setup_supabase.sql`을 적용합니다.")
        st.write("2. 적용 후 앱에서 `첫 계좌 만들기` 또는 `데모 데이터 불러오기`를 다시 실행합니다.")
        st.write("3. 필요하면 `python scripts/verify_streamlit_deployment.py --click-demo --expect-backend supabase`로 재검증합니다.")


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
    st.session_state.setdefault(TRANSFER_TARGET_ACCOUNT_KEY, None)
    st.session_state.setdefault(TRANSFER_AMOUNT_KEY, 0)
    st.session_state.setdefault(TRANSFER_DATE_KEY, date.today())
    st.session_state.setdefault(TRANSFER_NOTES_KEY, "")


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

    st.markdown(
        """
        <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

        :root {
            --surface: rgba(255, 255, 255, 0.88);
            --surface-strong: rgba(255, 255, 255, 0.96);
            --line-soft: rgba(15, 23, 42, 0.08);
            --text-muted: #526072;
            --ink-strong: #0f172a;
            --brand-deep: #103b42;
            --brand-accent: #d97706;
            --status-good: #0f766e;
            --status-warn: #b45309;
            --panel-radius: 20px;
            --panel-padding: 1.05rem 1.1rem 1.15rem;
            --section-gap: 1rem;
            --chart-gap: 0.85rem;
        }

        html, body, [class*="css"] {
            font-family: 'Pretendard', sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(214, 232, 231, 0.65), transparent 24rem),
                linear-gradient(180deg, #f4f7f6 0%, #eef3f2 45%, #f7f8f7 100%);
        }

        .block-container {
            padding-top: 1.35rem;
            padding-bottom: 3rem;
            max-width: 1580px;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #ecf5f2 0%, #e4eeea 100%);
            border-right: 1px solid rgba(15, 23, 42, 0.08);
        }

        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:has(> [data-testid="stMarkdownContainer"]) {
            gap: 0.35rem;
        }

        [data-testid="stMetric"] {
            background: var(--surface-strong);
            border: 1px solid var(--line-soft);
            border-radius: 18px;
            padding: 0.95rem 1rem;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.04);
        }

        [data-testid="stMetricLabel"] {
            color: var(--text-muted);
            font-weight: 600;
        }

        [data-testid="stMetricValue"] {
            color: var(--ink-strong);
        }

        [data-testid="stButton"] > button,
        [data-testid="stDownloadButton"] > button {
            border-radius: 999px;
            border: 1px solid rgba(16, 59, 66, 0.18);
        }

        [data-testid="stForm"] {
            background: transparent;
        }

        .dashboard-note {
            color: var(--text-muted);
            font-size: 0.9rem;
        }

        .auth-hero {
            position: relative;
            overflow: hidden;
            padding: 2.5rem 2rem 2rem;
            border-radius: 28px;
            background:
                radial-gradient(circle at 18% 18%, rgba(255, 255, 255, 0.24), transparent 16rem),
                radial-gradient(circle at 88% 22%, rgba(245, 158, 11, 0.24), transparent 15rem),
                linear-gradient(135deg, #103b42 0%, #195d67 54%, #0f766e 100%);
            border: 1px solid rgba(255, 255, 255, 0.14);
            box-shadow: 0 24px 60px rgba(16, 59, 66, 0.18);
            margin-bottom: 1rem;
        }

        .auth-hero__eyebrow {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.38rem 0.78rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.14);
            color: rgba(248, 250, 252, 0.88);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .auth-hero__title {
            max-width: 52rem;
            color: #f8fafc;
            font-size: clamp(2.15rem, 4vw, 3.45rem);
            line-height: 1.02;
            letter-spacing: -0.05em;
            margin: 1rem 0 0.8rem;
        }

        .auth-hero__caption {
            max-width: 44rem;
            color: rgba(241, 245, 249, 0.88);
            font-size: 1.02rem;
            line-height: 1.65;
            margin: 0;
        }

        .auth-hero__metrics {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.9rem;
            margin-top: 1.5rem;
        }

        .auth-hero__metric {
            padding: 1rem 1rem 0.95rem;
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.12);
            border: 1px solid rgba(255, 255, 255, 0.16);
            backdrop-filter: blur(12px);
        }

        .auth-hero__metric-label {
            color: rgba(226, 232, 240, 0.82);
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            margin-bottom: 0.45rem;
        }

        .auth-hero__metric-value {
            color: #ffffff;
            font-size: 1.05rem;
            font-weight: 700;
            line-height: 1.3;
        }

        .auth-feature-card {
            height: 100%;
            padding: 1.2rem 1.15rem 1.15rem;
            border-radius: 22px;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(246, 249, 248, 0.94));
            border: 1px solid rgba(16, 59, 66, 0.1);
            box-shadow: 0 16px 38px rgba(15, 23, 42, 0.05);
        }

        .auth-feature-card__index {
            color: #0f766e;
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .auth-feature-card__title {
            color: #103b42;
            font-size: 1.05rem;
            font-weight: 800;
            line-height: 1.3;
            margin-top: 0.55rem;
        }

        .auth-feature-card__desc {
            color: #607285;
            font-size: 0.92rem;
            line-height: 1.55;
            margin-top: 0.45rem;
        }

        .auth-entry-intro {
            color: #607285;
            font-size: 0.95rem;
            line-height: 1.55;
            margin: 1rem 0 0.8rem;
        }

        [data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 0.45rem;
            padding: 0.2rem;
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 18px;
        }

        [data-testid="stTabs"] [data-baseweb="tab"] {
            height: 2.9rem;
            border-radius: 14px;
            padding: 0 1rem;
            color: #526072;
            font-weight: 700;
        }

        [data-testid="stTabs"] [aria-selected="true"] {
            background: linear-gradient(135deg, rgba(15, 118, 110, 0.14), rgba(217, 119, 6, 0.14));
            color: #103b42;
        }

        .auth-panel-eyebrow {
            color: #0f766e;
            font-size: 0.76rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.55rem;
        }

        .auth-panel-title {
            color: #103b42;
            font-size: clamp(1.3rem, 2vw, 1.6rem);
            font-weight: 800;
            line-height: 1.15;
            letter-spacing: -0.03em;
            margin: 0;
        }

        .auth-panel-caption {
            color: #607285;
            font-size: 0.94rem;
            line-height: 1.55;
            margin: 0.4rem 0 1rem;
        }

        .auth-simple-title {
            color: #103b42;
            font-size: clamp(2rem, 3.2vw, 3rem);
            font-weight: 900;
            line-height: 1.05;
            letter-spacing: -0.05em;
            margin: 0 0 1.2rem;
        }

        .auth-demo-points {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.7rem;
            margin: 1rem 0 1rem;
        }

        .auth-demo-point {
            height: 100%;
            padding: 0.9rem 0.95rem;
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid rgba(16, 59, 66, 0.09);
        }

        .auth-demo-point__title {
            color: #103b42;
            font-size: 0.86rem;
            font-weight: 800;
            margin-bottom: 0.28rem;
        }

        .auth-demo-point__desc {
            color: #607285;
            font-size: 0.82rem;
            line-height: 1.45;
        }

        .st-key-auth-panel-login,
        .st-key-auth-panel-sign-up,
        .st-key-auth-demo-panel {
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(250, 251, 250, 0.94));
            border-radius: 22px;
            box-shadow: 0 16px 44px rgba(15, 23, 42, 0.05);
        }

        .st-key-auth-panel-login [data-testid="stTextInput"] input,
        .st-key-auth-panel-sign-up [data-testid="stTextInput"] input {
            min-height: 2.9rem;
            border-radius: 14px;
        }

        .st-key-auth-panel-login [data-testid="stButton"] > button,
        .st-key-auth-panel-sign-up [data-testid="stButton"] > button,
        .st-key-auth-demo-panel [data-testid="stButton"] > button,
        .st-key-auth-panel-login [data-testid="stFormSubmitButton"] > button,
        .st-key-auth-panel-sign-up [data-testid="stFormSubmitButton"] > button {
            min-height: 2.85rem;
            font-weight: 700;
        }

        .dashboard-section-header {
            display: flex;
            flex-direction: column;
            gap: 0.28rem;
            margin-bottom: var(--section-gap);
        }

        .dashboard-section-header--compact {
            margin-bottom: 0.9rem;
        }

        .dashboard-section-header__title {
            color: var(--brand-deep);
            font-size: clamp(1.28rem, 1.55vw, 1.9rem);
            font-weight: 800;
            line-height: 1.1;
            letter-spacing: -0.03em;
            margin: 0;
        }

        .dashboard-section-header__title--compact {
            font-size: clamp(1.12rem, 1.35vw, 1.45rem);
        }

        .dashboard-section-header__caption {
            color: var(--text-muted);
            font-size: 0.94rem;
            line-height: 1.45;
            margin: 0;
        }

        .dashboard-chart-shell {
            display: flex;
            flex-direction: column;
            gap: var(--chart-gap);
        }

        .dashboard-chart-shell__legend {
            margin-top: auto;
        }

        .dashboard-treemap-legend {
            display: flex;
            flex-direction: column;
            gap: 0.42rem;
            margin-top: 0.2rem;
            color: #607285;
            font-size: 0.82rem;
            font-weight: 700;
        }

        .dashboard-treemap-legend__range {
            width: min(360px, 52vw);
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            align-items: stretch;
            margin: 0 auto;
        }

        .dashboard-treemap-legend__bar {
            position: relative;
            width: 100%;
            height: 14px;
            border-radius: 999px;
            border: 1px solid rgba(15, 23, 42, 0.08);
            background: linear-gradient(90deg, #f1646c 0%, #f2b85b 32%, #d6de6b 62%, #82cc80 100%);
            box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.18);
        }

        .dashboard-treemap-legend__labels {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.8rem;
            color: #607285;
            font-size: 0.79rem;
            font-weight: 700;
        }

        .dashboard-treemap-legend__hint {
            color: #607285;
            font-size: 0.78rem;
            font-weight: 600;
            text-align: center;
            line-height: 1.35;
        }

        .dashboard-treemap-legend__marker {
            position: absolute;
            top: -6px;
            width: 18px;
            height: 26px;
            border-radius: 999px;
            background: rgba(15, 118, 110, 0.96);
            border: 2px solid rgba(255, 255, 255, 0.92);
            box-shadow: 0 10px 20px rgba(15, 23, 42, 0.18);
        }

        .dashboard-treemap-legend__marker::after {
            content: "";
            position: absolute;
            left: 50%;
            bottom: -7px;
            width: 2px;
            height: 7px;
            transform: translateX(-50%);
            background: rgba(15, 118, 110, 0.92);
        }

        .dashboard-treemap-legend__marker-label {
            position: absolute;
            left: 50%;
            bottom: calc(100% + 10px);
            transform: translateX(-50%);
            white-space: nowrap;
            background: rgba(15, 23, 42, 0.92);
            color: #F8FAFC;
            border-radius: 999px;
            padding: 0.28rem 0.62rem;
            font-size: 0.74rem;
            font-weight: 700;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.14);
        }

        .dashboard-metric-strip {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 0.85rem;
            margin: 1.1rem 0 1.35rem;
        }

        .dashboard-metric-card {
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 251, 250, 0.98));
            border: 1px solid rgba(37, 99, 235, 0.16);
            border-radius: 16px;
            padding: 1.05rem 1.1rem 1rem;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.04);
            min-height: 9rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .dashboard-metric-card__top {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 0.65rem;
        }

        .dashboard-metric-card__label {
            color: #58677b;
            font-size: 0.86rem;
            font-weight: 700;
            letter-spacing: 0.01em;
        }

        .dashboard-metric-card__action {
            border: 1px solid rgba(37, 99, 235, 0.22);
            border-radius: 10px;
            padding: 0.2rem 0.72rem;
            font-size: 0.84rem;
            font-weight: 700;
            color: #0f3b66;
            background: rgba(255, 255, 255, 0.96);
            white-space: nowrap;
        }

        .dashboard-metric-card__value {
            color: #0d3559;
            font-size: clamp(1.6rem, 2vw, 2.2rem);
            font-weight: 800;
            line-height: 1.08;
            letter-spacing: -0.03em;
            margin-top: 1.2rem;
        }

        .dashboard-metric-card__value--accent {
            color: #b42318;
        }

        .dashboard-metric-card__note {
            margin-top: 0.75rem;
            color: #64748b;
            font-size: 0.82rem;
            line-height: 1.45;
        }

        .dashboard-summary-card__label {
            color: #58677b;
            font-size: 0.86rem;
            font-weight: 700;
            letter-spacing: 0.01em;
            margin: 0;
        }

        .dashboard-summary-card__value {
            color: #0d3559;
            font-size: clamp(1.52rem, 1.9vw, 2.15rem);
            font-weight: 800;
            line-height: 1.04;
            letter-spacing: -0.03em;
            min-height: 2.55rem;
            display: flex;
            align-items: flex-end;
            margin: 0;
            white-space: nowrap;
            overflow: hidden;
        }

        .dashboard-summary-card__value--accent {
            color: #b42318;
        }

        .dashboard-summary-card__header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.55rem;
            min-height: 0;
            margin: 0;
        }

        .dashboard-summary-card__action {
            border: 1px solid rgba(15, 59, 102, 0.16);
            border-radius: 999px;
            padding: 0.28rem 0.78rem;
            font-size: 0.82rem;
            font-weight: 700;
            color: #0f3b66;
            background: rgba(255, 255, 255, 0.96);
            white-space: nowrap;
            line-height: 1.1;
        }

        .dashboard-summary-card__field {
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 5.7rem;
        }

        .st-key-dashboard-card-principal .dashboard-summary-card__field,
        .st-key-dashboard-card-profit .dashboard-summary-card__field,
        .st-key-dashboard-card-profit-rate .dashboard-summary-card__field {
            min-height: 6.7rem;
            justify-content: flex-start;
            gap: 1.6rem;
        }

        .dashboard-summary-card__field--actionable {
            border-radius: 0.85rem;
        }

        .st-key-dashboard-card-cash,
        .st-key-dashboard-card-total-value {
            position: relative;
        }

        .st-key-dashboard-cash-card-overlay,
        .st-key-dashboard-total-value-refresh-overlay {
            position: absolute;
            top: 0.55rem;
            right: 0.8rem;
            z-index: 2;
            width: auto;
            height: auto;
        }

        .st-key-dashboard-cash-card-overlay [data-testid="stElementContainer"],
        .st-key-dashboard-total-value-refresh-overlay [data-testid="stElementContainer"] {
            margin: 0 !important;
            padding: 0 !important;
        }

        .st-key-dashboard-cash-card-overlay [data-testid="stButton"],
        .st-key-dashboard-total-value-refresh-overlay [data-testid="stButton"] {
            width: auto;
        }

        .st-key-dashboard-cash-card-overlay button,
        .st-key-dashboard-total-value-refresh-overlay button {
            min-height: 0;
            padding: 0.28rem 0.78rem;
            border: 1px solid rgba(15, 59, 102, 0.16);
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.96);
            box-shadow: none;
            color: #0f3b66;
            font-size: 0.82rem;
            font-weight: 700;
            line-height: 1.1;
        }

        .st-key-dashboard-cash-card-overlay button:hover,
        .st-key-dashboard-cash-card-overlay button:focus,
        .st-key-dashboard-cash-card-overlay button:focus-visible,
        .st-key-dashboard-total-value-refresh-overlay button:hover,
        .st-key-dashboard-total-value-refresh-overlay button:focus,
        .st-key-dashboard-total-value-refresh-overlay button:focus-visible {
            border-color: rgba(15, 59, 102, 0.24);
            background: rgba(248, 250, 252, 0.98);
            outline: none;
            box-shadow: none;
        }

        .st-key-dashboard-card-cash [data-testid="stNumberInput"] input,
        .st-key-trade-panel-transfer [data-testid="stNumberInput"] input {
            min-height: 2.6rem;
        }

        .st-key-dashboard-card-cash [data-testid="stHorizontalBlock"] {
            align-items: flex-start;
        }

        .st-key-dashboard-card-cash [data-testid="stNumberInput"] label p,
        .st-key-dashboard-panel-selected-trend [data-testid="stSegmentedControl"] label p {
            color: #607285;
            font-weight: 700;
        }

        .st-key-trade-panel-transfer [data-testid="stButton"] > button {
            min-height: 2.65rem;
            font-weight: 700;
        }

        .st-key-trade-panel-transfer [data-baseweb="select"] > div,
        .st-key-trade-panel-transfer [data-baseweb="input"] > div {
            min-height: 2.65rem;
        }

        .st-key-dashboard-panel-market [data-testid="stButton"] > button {
            min-height: 2.65rem;
        }

        @media (max-width: 860px) {
            .auth-hero {
                padding: 2rem 1.35rem 1.5rem;
            }

            .auth-hero__metrics,
            .auth-demo-points {
                grid-template-columns: 1fr;
            }

            .dashboard-metric-strip {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }

            .dashboard-treemap-legend__range {
                width: min(300px, 48vw);
            }
        }

        @media (max-width: 560px) {
            .auth-hero__title {
                font-size: 2rem;
            }

            .dashboard-metric-strip {
                grid-template-columns: 1fr;
            }

            .dashboard-treemap-legend__range {
                width: min(320px, 82vw);
            }

            .dashboard-treemap-legend__labels {
                gap: 0.45rem;
                font-size: 0.72rem;
            }

            .dashboard-treemap-legend__marker-label {
                max-width: min(220px, 74vw);
                overflow: hidden;
                text-overflow: ellipsis;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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
    """초기 인증 화면 상단 제목을 렌더링한다."""

    st.markdown('<h1 class="auth-simple-title">자산관리 대장</h1>', unsafe_allow_html=True)


def render_demo_access_entry() -> None:
    """초기 인증 화면의 데모 접속 패널을 렌더링한다."""

    with st.container(border=True, key="auth-demo-panel"):
        st.markdown('<div class="auth-panel-eyebrow">로그인 없이 바로 확인</div>', unsafe_allow_html=True)
        st.markdown('<h3 class="auth-panel-title">데모 작업공간 시작</h3>', unsafe_allow_html=True)
        st.markdown(
            '<p class="auth-panel-caption">약 5년치 예시 투자 이력, 계좌 간 이체, 현금 흐름, 스냅샷 데이터가 준비된 작업공간으로 즉시 들어갑니다.</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="auth-demo-points">
                <div class="auth-demo-point">
                    <div class="auth-demo-point__title">5년 투자 일지</div>
                    <div class="auth-demo-point__desc">입금, 매수, 매도, 계좌 이체까지 약 5년치 흐름이 이미 채워져 있습니다.</div>
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


def clear_query_params() -> None:
    for key in list(st.query_params.keys()):
        del st.query_params[key]


def handle_auth_callback() -> bool:
    error_description = str(st.query_params.get("error_description") or "").strip()
    error_code = str(st.query_params.get("error_code") or "").strip()
    if error_description:
        suffix = f" ({error_code})" if error_code else ""
        set_auth_feedback("error", f"이메일 확인에 실패했습니다{suffix}: {error_description}")
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
        clear_query_params()
        return True

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
        if tone == "accent":
            value_class += " dashboard-metric-card__value--accent"
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
    if tone == "accent":
        value_class += " dashboard-summary-card__value--accent"
    field_class = "dashboard-summary-card__field"
    if actionable:
        field_class += " dashboard-summary-card__field--actionable"
    action_html = ""
    if action:
        action_html = (
            '<div class="dashboard-summary-card__header">'
            f'<div class="dashboard-summary-card__label">{html.escape(label)}</div>'
            f'<div class="dashboard-summary-card__action">{html.escape(action)}</div>'
            "</div>"
        )
    else:
        action_html = f'<div class="dashboard-summary-card__label">{html.escape(label)}</div>'
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

    updated, errors = refresh_prices(holdings)
    if updated:
        mark_rollup_dirty()
        st.success(f"{updated}개 종목 가격을 갱신했습니다.")
    if errors:
        st.warning("\n".join(errors))
    st.rerun()


def render_dashboard_section_header(title: str, description: str, *, compact: bool = False) -> None:
    """대시보드 섹션 헤더를 동일한 타이포 체계로 렌더링한다."""

    wrapper_class = "dashboard-section-header dashboard-section-header--compact" if compact else "dashboard-section-header"
    title_class = "dashboard-section-header__title dashboard-section-header__title--compact" if compact else "dashboard-section-header__title"
    st.markdown(
        (
            f'<div class="{wrapper_class}">'
            f'<div class="{title_class}">{html.escape(title)}</div>'
            f'<p class="dashboard-section-header__caption">{html.escape(description)}</p>'
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

    st.markdown(
        (
            '<div class="dashboard-treemap-legend">'
            '<div class="dashboard-treemap-legend__range">'
            '<div class="dashboard-treemap-legend__bar">'
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
        .configure_view(stroke=None)
        .configure_axis(
            gridColor="#D7E2E7",
            domainColor="#C8D4DA",
            tickColor="#C8D4DA",
            labelColor="#607285",
            titleColor="#607285",
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
            color=alt.Color("bucket:N", scale=alt.Scale(range=["#B45309", "#0F766E", "#2563EB"])),
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

    nodes = allocation_treemap_nodes(summary, holdings, selected_symbol=selected_symbol)
    if not nodes:
        return None

    leaf_rates = [
        round(float(child.get("profit_rate") or 0), 2)
        for node in nodes
        for child in (node.get("children") or [])
        if child.get("profit_rate") is not None
    ]
    rate_min = min(leaf_rates) if leaf_rates else 0.0
    rate_max = max(leaf_rates) if leaf_rates else 0.0
    visual_min = float(rate_min)
    visual_max = float(rate_max)
    if visual_min == visual_max:
        visual_min -= 0.01
        visual_max += 0.01

    for node in nodes:
        children = node.get("children") or []
        total_value = 0.0
        weighted_rate_total = 0.0
        weighted_rate_weight = 0.0
        for child in children:
            revenue_value = float(child.get("value") or 0)
            profit_rate = child.get("profit_rate")
            child["revenue_value"] = round(revenue_value, 4)
            child_rate = round(float(profit_rate or 0), 4)
            child["value"] = [
                round(revenue_value, 4),
                child_rate,
            ]
            child["itemStyle"] = {
                "borderColor": "#F8FAFC",
                "borderWidth": 1,
                "gapWidth": 1,
            }
            total_value += revenue_value
            if profit_rate is not None:
                weighted_rate_total += revenue_value * float(profit_rate)
                weighted_rate_weight += revenue_value

        parent_rate = (weighted_rate_total / weighted_rate_weight) if weighted_rate_weight else 0.0
        node["revenue_value"] = round(total_value, 4)
        node["profit_rate"] = round(parent_rate, 4)
        node["value"] = [
            round(total_value, 4),
            round(parent_rate, 4),
        ]

    tooltip_formatter = None
    if JsCode is not None:
        tooltip_formatter = JsCode(
            """
            function(info) {
                var rawValue = Array.isArray(info.value) ? info.value[0] : info.value;
                var revenue = Math.round(Number(rawValue || 0)).toLocaleString('ko-KR');
                var path = [];
                if (info.treePathInfo) {
                    for (var i = 1; i < info.treePathInfo.length; i += 1) {
                        path.push(info.treePathInfo[i].name);
                    }
                }
                var lines = [
                    '<div style="font-weight:700; margin-bottom:6px;">' + info.name + '</div>',
                    '평가금액: ₩' + revenue
                ];
                if (path.length > 1) {
                    lines.unshift('<div style="font-size:12px; color:#64748B; margin-bottom:4px;">' + path.join(' → ') + '</div>');
                }
                if (info.data && info.data.profit_rate !== null && info.data.profit_rate !== undefined) {
                    lines.push('수익률: ' + Number(info.data.profit_rate).toFixed(2) + '%');
                }
                return lines.join('<br/>');
            }
            """
        )

    tooltip_config: dict[str, Any] = {
        "backgroundColor": "#FFFFFF",
        "borderColor": "#E2E8F0",
        "borderWidth": 1,
        "borderRadius": 10,
        "padding": [10, 12],
        "textStyle": {"color": "#1E293B", "fontSize": 12},
        "extraCssText": "box-shadow: 0 8px 24px rgba(15, 23, 42, 0.14);",
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
        "backgroundColor": "transparent",
        "animationDurationUpdate": 220,
        "title": {
            "text": "자산군 → 보유 종목",
            "left": "center",
            "top": 0,
            "textStyle": {
                "fontSize": 15,
                "fontWeight": 700,
                "color": "#334155",
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
            "bottom": 8,
            "itemWidth": 14,
            "itemHeight": 220,
            "handleSize": 20,
            "text": ["높은 수익률", "낮은 수익률"],
            "textGap": 6,
            "textStyle": {
                "color": "#64748B",
                "fontSize": 12,
                "fontWeight": 600,
            },
            "inRange": {
                "color": ["#F1646C", "#F2D675", "#9CCB6D"],
            },
            "outOfRange": {
                "colorAlpha": 0.0,
            },
            "borderColor": "#D7DEE5",
            "padding": 0,
        },
        "series": [
            {
                "name": "자산 배분",
                "type": "treemap",
                "top": 36,
                "left": 0,
                "right": 0,
                "bottom": 68,
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
                    "color": "#FFFFFF",
                    "fontWeight": 700,
                    "fontSize": 14,
                    "lineHeight": 18,
                    "overflow": "truncate",
                    "ellipsis": "…",
                },
                "upperLabel": {
                    "show": True,
                    "formatter": label_formatter,
                    "height": 28,
                    "color": "#F8FAFC",
                    "fontWeight": 700,
                    "overflow": "truncate",
                    "ellipsis": "…",
                },
                "itemStyle": {
                    "borderColor": "#5E646B",
                    "borderWidth": 2,
                    "gapWidth": 2,
                    "borderRadius": 2,
                },
                "emphasis": {
                    "focus": "self",
                    "itemStyle": {
                        "borderColor": "#173F46",
                        "borderWidth": 3,
                        "shadowBlur": 16,
                        "shadowColor": "rgba(15, 23, 42, 0.12)",
                    }
                },
                "levels": [
                    {
                        "itemStyle": {
                            "borderColor": "#5E646B",
                            "borderWidth": 3,
                            "gapWidth": 3,
                        },
                        "upperLabel": {
                            "show": True,
                            "height": 30,
                            "color": "#FFFFFF",
                            "backgroundColor": "#5E646B",
                            "padding": [6, 10],
                        },
                    },
                    {
                        "color": ["#F1646C", "#F2D675", "#9CCB6D"],
                        "colorMappingBy": "value",
                        "itemStyle": {
                            "borderColor": "#D5DDE3",
                            "borderWidth": 1,
                            "gapWidth": 1,
                        },
                    },
                ],
                "data": nodes,
            }
        ],
    }


def holdings_bar_options(frame: pd.DataFrame, *, selected_symbol: str | None = None) -> dict[str, Any] | None:
    """보유 종목 수익률 ECharts 막대 옵션을 만든다."""

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
                    "color": "#1D7F78" if rate >= 0 else "#D14D57",
                    "borderColor": "#0F766E" if is_selected else "#FFFFFF",
                    "borderWidth": 3 if is_selected else 0,
                    "shadowBlur": 18 if is_selected else 0,
                    "shadowColor": "rgba(15, 118, 110, 0.22)" if is_selected else "transparent",
                    "opacity": 1 if is_selected else 0.92,
                },
                "label": {
                    "show": True,
                    "position": "top" if rate >= 0 else "bottom",
                    "distance": 8,
                    "formatter": format_pct(rate),
                    "color": "#0D3559" if is_selected else "#4B5D6B",
                    "fontWeight": 700 if is_selected else 600,
                    "opacity": 1 if is_selected or not selected_key else 0.78,
                },
            }
        )

    if not data:
        return None

    minimum = min(rates)
    maximum = max(rates)
    if minimum == maximum:
        minimum -= 2
        maximum += 2
    else:
        minimum = min(minimum, 0)
        maximum = max(maximum, 0)
        padding = max((maximum - minimum) * 0.14, 1.5)
        minimum -= padding
        maximum += padding

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

    return {
        "backgroundColor": "transparent",
        "animationDuration": 260,
        "animationDurationUpdate": 320,
        "grid": {"top": 56, "right": 12, "bottom": 96, "left": 56},
        "tooltip": {
            "trigger": "item",
            "backgroundColor": "rgba(21, 40, 31, 0.92)",
            "borderWidth": 0,
            "textStyle": {"color": "#F8FAFC", "fontSize": 12},
            **({"formatter": tooltip_formatter} if tooltip_formatter is not None else {}),
        },
        "xAxis": {
            "type": "category",
            "data": [item["display_name"] for item in data],
            "axisLabel": {
                "interval": 0,
                "rotate": 32,
                "color": "#607285",
                "fontSize": 11,
                "margin": 14,
            },
            "axisLine": {"lineStyle": {"color": "#C8D4DA"}},
            "axisTick": {"show": False},
        },
        "yAxis": {
            "type": "value",
            "min": round(minimum, 2),
            "max": round(maximum, 2),
            "name": "수익률 (%)",
            "nameTextStyle": {"color": "#607285", "fontWeight": 700},
            "axisLabel": {"color": "#607285", "formatter": "{value}%"},
            "axisLine": {"show": False},
            "splitLine": {"lineStyle": {"color": "#D7E2E7"}},
        },
        "series": [
            {
                "name": "수익률",
                "type": "bar",
                "barWidth": "52%",
                "data": data,
                "itemStyle": {"borderRadius": [10, 10, 0, 0]},
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
        .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8, size=52)
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
                    labelColor="#607285",
                    titleColor="#607285",
                ),
            ),
            y=alt.Y(
                "profit_rate:Q",
                title="수익률 (%)",
                axis=alt.Axis(
                    format=".0f",
                    grid=True,
                    gridColor="#D7E2E7",
                    tickCount=6,
                    labelColor="#607285",
                    titleColor="#607285",
                ),
            ),
            color=alt.Color("tone:N", legend=None, scale=alt.Scale(domain=["수익", "손실"], range=["#1D7F78", "#D14D57"])),
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
        .mark_text(dy=-8, fontSize=11, fontWeight="bold", color="#0D3559")
        .encode(
            x=alt.X("display_name:N", sort=display_order),
            y=alt.Y("profit_rate:Q"),
            text=alt.Text("profit_rate_label:N"),
            opacity=alt.Opacity("selected_opacity:Q", legend=None),
        )
    )
    return style_dashboard_altair_chart(bars + labels, height=DASHBOARD_OVERVIEW_CHART_HEIGHT)


def selected_holding_trend_chart(frame: pd.DataFrame, *, measure: str) -> alt.Chart:
    """선택 종목 단일 추이 차트를 만든다."""

    measure_key = str(measure or "market_value")
    measure_title = label_detail_measure(measure_key)
    measure_format = ",.2f" if measure_key == "close" else (".2f" if measure_key == "profit_rate" else ",.0f")
    return (
        alt.Chart(frame)
        .mark_line(point=True, strokeWidth=3, color="#0F766E")
        .encode(
            x=alt.X("date:T", title="날짜"),
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
    )


def selected_holding_trend_options(
    frame: pd.DataFrame,
    *,
    selected_holding_name: str,
    measure: str,
    period_label: str,
) -> dict[str, Any] | None:
    """선택 종목 트렌드 ECharts 옵션을 만든다."""

    if frame.empty:
        return None

    measure_key = str(measure or "market_value")
    measure_title = label_detail_measure(measure_key)
    working = frame.sort_values("date").copy()
    working["date"] = pd.to_datetime(working["date"])
    date_format = "%m-%d" if str(period_label) in {"1개월", "3개월"} else "%Y-%m"
    x_labels = working["date"].dt.strftime(date_format).tolist()
    full_dates = working["date"].dt.strftime("%Y-%m-%d").tolist()

    series_data: list[dict[str, Any]] = []
    for row, label_date, full_date in zip(working.to_dict(orient="records"), x_labels, full_dates):
        series_data.append(
            {
                "value": round(float(row.get(measure_key) or 0), 4),
                "date": full_date,
                "axis_label": label_date,
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
        "nameTextStyle": {"color": "#607285", "fontWeight": 700, "padding": [0, 0, 0, 4]},
        "axisLine": {"show": False},
        "axisTick": {"show": False},
        "splitLine": {"lineStyle": {"color": "#D7E2E7"}},
        "axisLabel": {"color": "#607285"},
    }
    if axis_label_formatter is not None:
        y_axis_config["axisLabel"]["formatter"] = axis_label_formatter

    return {
        "backgroundColor": "transparent",
        "animationDuration": 260,
        "animationDurationUpdate": 320,
        "title": {
            "text": "선택 종목 트렌드",
            "subtext": f"{selected_holding_name} · {measure_title} · {period_label}",
            "left": "center",
            "top": 6,
            "textStyle": {
                "fontSize": 16,
                "fontWeight": 700,
                "color": "#1E293B",
            },
            "subtextStyle": {
                "fontSize": 11,
                "color": "#64748B",
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
                "color": "#64748B",
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
                    "color": "#94A3B8",
                    "width": 1,
                    "type": "dashed",
                },
            },
            "backgroundColor": "#FFFFFF",
            "borderColor": "#E2E8F0",
            "borderWidth": 1,
            "borderRadius": 12,
            "padding": [10, 12],
            "textStyle": {"color": "#1E293B", "fontSize": 12},
            "extraCssText": "box-shadow: 0 8px 24px rgba(15, 23, 42, 0.14);",
            **({"formatter": tooltip_formatter} if tooltip_formatter is not None else {}),
        },
        "toolbox": {
            "show": True,
            "top": 8,
            "right": 0,
            "itemSize": 16,
            "iconStyle": {
                "borderColor": "#6B7FC8",
            },
            "emphasis": {
                "iconStyle": {
                    "borderColor": "#0B6BDA",
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
            "axisLine": {"lineStyle": {"color": "#C8D4DA"}},
            "axisTick": {"show": False},
            "axisLabel": {
                "color": "#607285",
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
                "borderColor": "#D7DEE5",
                "backgroundColor": "#F8FAFC",
                "fillerColor": "rgba(11, 107, 218, 0.12)",
                "handleSize": 18,
                "brushSelect": False,
                "dataBackground": {
                    "lineStyle": {"color": "rgba(11, 107, 218, 0.55)"},
                    "areaStyle": {"color": "rgba(11, 107, 218, 0.08)"},
                },
                "selectedDataBackground": {
                    "lineStyle": {"color": "#0B6BDA"},
                    "areaStyle": {"color": "rgba(11, 107, 218, 0.16)"},
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
                    "color": "#0B6BDA",
                    "width": 3,
                },
                "itemStyle": {
                    "color": "#FFFFFF",
                    "borderColor": "#0B6BDA",
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
                            {"offset": 0, "color": "rgba(11, 107, 218, 0.22)"},
                            {"offset": 1, "color": "rgba(11, 107, 218, 0.02)"},
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
                                "color": "#94A3B8",
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
    if frame.empty:
        st.info("보유 종목이 없습니다.")
        return

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
    st.dataframe(display, width="stretch", hide_index=True, height=height)


def auth_page(auth_enabled: bool = True) -> None:
    render_auth_landing_header()
    render_auth_feedback()

    pending_email = str(st.session_state.get(PENDING_CONFIRMATION_EMAIL_KEY) or "").strip()
    if pending_email:
        with st.container(border=True):
            st.write(f"이메일 확인 대기: `{pending_email}`")
            st.caption("예전 확인 링크가 열리지 않았다면 여기서 새 메일을 다시 보내고, 가장 최근 메일의 링크를 열어 주세요.")
            if st.button("확인 메일 다시 보내기", key="resend-confirmation", width="stretch"):
                try:
                    app_auth.resend_signup(pending_email)
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))
                else:
                    st.success(f"{pending_email} 주소로 새 확인 메일을 보냈습니다.")

    sign_in_tab, sign_up_tab, demo_tab = st.tabs(["로그인", "계정 만들기", "데모 체험"])

    with sign_in_tab:
        with st.container(border=True, key="auth-panel-login"):
            st.markdown('<div class="auth-panel-eyebrow">기존 사용자</div>', unsafe_allow_html=True)
            st.markdown('<h3 class="auth-panel-title">로그인</h3>', unsafe_allow_html=True)
            st.markdown(
                '<p class="auth-panel-caption">사용자별로 분리된 포트폴리오를 그대로 이어서 확인합니다.</p>',
                unsafe_allow_html=True,
            )
            if not auth_enabled:
                st.info("Supabase 인증 설정이 없어 실제 로그인은 잠시 비활성 상태입니다. 데모 체험은 바로 사용할 수 있습니다.")
            with st.form("sign-in-form", clear_on_submit=False):
                sign_in_email = st.text_input("이메일", key="sign-in-email")
                sign_in_password = st.text_input("비밀번호", type="password", key="sign-in-password")
                sign_in_submitted = st.form_submit_button("로그인", width="stretch", disabled=not auth_enabled)
        if sign_in_submitted:
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

    with sign_up_tab:
        with st.container(border=True, key="auth-panel-sign-up"):
            st.markdown('<div class="auth-panel-eyebrow">처음 시작한다면</div>', unsafe_allow_html=True)
            st.markdown('<h3 class="auth-panel-title">계정 만들기</h3>', unsafe_allow_html=True)
            st.markdown(
                '<p class="auth-panel-caption">확인 메일을 거쳐 개인 작업공간을 만들고, 이후에는 같은 계정으로 계속 이어서 사용합니다.</p>',
                unsafe_allow_html=True,
            )
            if not auth_enabled:
                st.info("Supabase 인증 설정이 없어 실제 계정 만들기는 잠시 비활성 상태입니다. 설정 전에는 데모 체험만 사용할 수 있습니다.")
            with st.form("sign-up-form", clear_on_submit=False):
                sign_up_email = st.text_input("이메일", key="sign-up-email")
                sign_up_password = st.text_input("비밀번호", type="password", key="sign-up-password")
                confirm_password = st.text_input("비밀번호 확인", type="password", key="sign-up-password-confirm")
                sign_up_submitted = st.form_submit_button("계정 만들기", width="stretch", disabled=not auth_enabled)
        if sign_up_submitted:
            if sign_up_password != confirm_password:
                st.error("비밀번호가 서로 다릅니다.")
            else:
                try:
                    response = app_auth.sign_up(email=sign_up_email, password=sign_up_password)
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))
                else:
                    if getattr(response, "session", None):
                        st.session_state[PENDING_CONFIRMATION_EMAIL_KEY] = ""
                        st.success("계정을 만들고 바로 로그인했습니다.")
                        st.rerun()
                    else:
                        st.session_state[PENDING_CONFIRMATION_EMAIL_KEY] = str(sign_up_email or "").strip()
                        set_auth_feedback(
                            "info",
                            "계정을 만들었습니다. 확인 메일을 열어 주세요. 예전 링크가 안 되면 위의 버튼으로 새 메일을 다시 보내면 됩니다.",
                        )
                        st.rerun()

    with demo_tab:
        render_demo_access_entry()


def empty_state() -> None:
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
        with st.container(border=True):
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


def sidebar(accounts: list[dict[str, Any]], selected_account_id: int | None, user: dict[str, Any]) -> tuple[int, str]:
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
            st.caption(f"열려 있는 페이지: `{label_page(st.session_state.get('active_page', PAGES[0]))}`")
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
            st.caption("페이지 이동")
            active_page = st.radio(
                "페이지",
                PAGES,
                index=PAGES.index(st.session_state.get("active_page", PAGES[0])),
                format_func=label_page,
            )
            st.session_state["active_page"] = active_page
            st.caption(f"현재 보기: `{label_page(active_page)}`")

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

    return selected_account_id, st.session_state["active_page"]


def dashboard_page(account: dict[str, Any], holdings: list[dict[str, Any]], rollup_state: dict[str, Any] | None = None) -> None:
    frame = holdings_frame(holdings)
    trade_logs = list_trade_logs(int(account["id"]))
    interest_rows = list_daily_interest(int(account["id"]))
    summary = account_summary(account, holdings, trade_logs=trade_logs, interest_rows=interest_rows)
    display_cash = float(summary["cash"] or 0)
    display_total_value = float(summary["total_value"] or 0)
    display_principal_profit_loss = float(summary["principal_profit_loss"] or 0)
    display_principal_profit_rate = (
        display_principal_profit_loss / float(summary["total_principal"] or 0) * 100
        if float(summary["total_principal"] or 0)
        else 0.0
    )
    account_id = int(account["id"])
    echarts_available = st_echarts is not None
    selection_key = dashboard_holding_selection_key(account_id)
    trend_period_key = dashboard_trend_period_key(account_id)
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
    overview_frame = holdings_overview_frame(holdings, selected_symbol=selected_symbol or None, limit=10)
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
            render_dashboard_summary_card("원금 대비 평가손익", format_won(display_principal_profit_loss), tone="accent")

    with summary_cols[4]:
        with st.container(border=True, key="dashboard-card-profit-rate"):
            render_dashboard_summary_card("원금 대비 수익률", format_pct(display_principal_profit_rate), tone="accent")

    if not echarts_available:
        st.warning("현재 환경에서는 ECharts 모듈을 불러오지 못해 대시보드 차트를 표시할 수 없습니다.")

    with st.container(border=True, height=DASHBOARD_OVERVIEW_PANEL_HEIGHT, key="dashboard-panel-allocation"):
        render_dashboard_section_header("자산 배분", "자산군에서 보유 종목까지 한 번에 보고, 종목을 누르면 아래에서 개별 트렌드를 바로 확인합니다.")
        treemap_options = allocation_treemap_options(
            summary,
            holdings,
            selected_symbol=selected_symbol or None,
        )
        if treemap_options is None:
            st.info("배분을 그릴 데이터가 아직 없습니다.")
        elif not echarts_available:
            st.info("현재 환경에서는 자산 배분 차트를 표시할 수 없습니다.")
        else:
            treemap_selection = st_echarts(
                options=treemap_options,
                height=f"{DASHBOARD_OVERVIEW_CHART_HEIGHT}px",
                key=f"allocation-treemap:{account_id}",
                on_select="rerun",
                selection_mode="points",
            )
            if sync_dashboard_selected_holding(account_id, treemap_selection, holdings=holdings):
                st.rerun()

    trend_col, holdings_col = st.columns((1, 1), gap="large", vertical_alignment="top")

    with trend_col:
        with st.container(border=True, height=DASHBOARD_OVERVIEW_PANEL_HEIGHT, key="dashboard-panel-selected-trend"):
            header_col, period_col, measure_col, action_col = st.columns((1.2, 0.78, 0.82, 0.36), gap="large", vertical_alignment="bottom")
            with header_col:
                render_dashboard_section_header(
                    "선택 종목 트렌드",
                    "자산 배분에서 선택한 종목의 가격과 수익률 흐름을 같은 화면에서 이어서 확인합니다.",
                    compact=True,
                )
            with period_col:
                period = st.segmented_control(
                    "기간",
                    options=["1mo", "3mo", "6mo", "1y"],
                    format_func=label_period,
                    default=period,
                    key=trend_period_key,
                )
            selected_trend_measure = "market_value"
            if selected_symbol and selected_symbol != "CASH":
                with measure_col:
                    selected_trend_measure = st.segmented_control(
                        "표시 지표",
                        options=["market_value", "profit_rate", "close"],
                        format_func=label_detail_measure,
                        default="market_value",
                        key=f"selected-trend-measure:{account_id}",
                    )
            if selected_symbol:
                with action_col:
                    if st.button("선택 해제", key=f"clear-selected-holding:{account_id}", width="stretch"):
                        st.session_state[selection_key] = ""
                        st.rerun()

            if not selected_symbol:
                st.info("자산 배분 트리맵에서 종목 타일을 누르면 여기에서 해당 종목 트렌드가 표시됩니다.")
            elif selected_symbol == "CASH":
                st.info("예수금은 시장 가격 추이가 없어서 개별 트렌드 차트를 표시하지 않습니다.")
            else:
                selected_holding_name = dashboard_selected_holding_name(holdings, selected_symbol)
                selected_holdings = [
                    holding for holding in holdings if normalize_holding_symbol(holding.get("symbol")) == selected_symbol
                ]
                if not selected_holdings:
                    st.info("선택한 종목을 현재 보유 목록에서 찾지 못했습니다.")
                else:
                    st.caption(f"선택 종목: `{selected_holding_name}` · 기준 기간: `{label_period(period)}`")
                    try:
                        with st.spinner(f"{selected_holding_name} 추이를 불러오는 중입니다..."):
                            _, selected_holding_trend = build_portfolio_trend(selected_holdings, period=period)
                    except Exception as exc:  # noqa: BLE001
                        st.warning(f"선택 종목 추이를 불러오지 못했습니다: {exc}")
                    else:
                        if selected_holding_trend.empty:
                            st.info("선택 종목의 시세 이력이 아직 없어 트렌드 차트를 표시할 수 없습니다.")
                        else:
                            selected_frame = selected_holding_trend.sort_values("date").copy()
                            selected_measure = str(selected_trend_measure or "market_value")
                            if echarts_available:
                                trend_options = selected_holding_trend_options(
                                    selected_frame,
                                    selected_holding_name=selected_holding_name,
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
                                )
                                st.altair_chart(
                                    style_dashboard_altair_chart(trend_chart, height=DASHBOARD_DETAIL_CHART_HEIGHT),
                                    width="stretch",
                                )

    with holdings_col:
        with st.container(border=True, height=DASHBOARD_OVERVIEW_PANEL_HEIGHT, key="dashboard-panel-holdings"):
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
                    height=f"{DASHBOARD_OVERVIEW_CHART_HEIGHT}px",
                    key=f"holdings-profit-bar:{account_id}",
                )

    with st.container(border=True, key="dashboard-panel-holdings-table"):
        render_dashboard_section_header("현재 보유 종목", "계좌 전체 포지션을 표로 읽고 현재 선택 종목과 함께 확인합니다.", compact=True)
        show_holdings_table(frame, height=DASHBOARD_HOLDINGS_TABLE_HEIGHT)


def trade_entry_page(account: dict[str, Any], holdings: list[dict[str, Any]], accounts: list[dict[str, Any]]) -> None:
    st.title("거래")
    st.caption("매수/매도, 현금 흐름, 계좌 간 이체를 한 화면에서 이어서 기록합니다.")
    left, right = st.columns((1, 1), gap="large")

    with left:
        st.subheader("매수 / 매도")
        holding_options = {holding["product_name"]: holding for holding in holdings}
        trade_type = st.selectbox(
            "거래 유형",
            ["buy", "sell"],
            format_func=label_trade_type,
            key=TRADE_TYPE_KEY,
        )

        if holding_options and trade_type == "sell":
            selected_holding_name = st.selectbox(
                "보유 종목",
                options=list(holding_options),
                key=f"sell-holding:{account['id']}",
            )
            prefill_trade_from_holding(
                holding_options[selected_holding_name],
                marker=f"sell:{account['id']}:{selected_holding_name}",
            )
        else:
            st.session_state[TRADE_PREFILL_MARKER_KEY] = "buy"
            search_query = st.text_input(
                "종목 검색",
                key=TRADE_SEARCH_QUERY_KEY,
                placeholder="예: 삼성전자, 005930, PLUS 고배당주채권혼합",
            )
            st.caption("검색 결과를 누르면 종목명과 코드가 자동으로 채워집니다.")
            if len(str(search_query or "").strip()) >= 2:
                suggestions = search_products(search_query, limit=8)
                with st.container(border=True):
                    st.caption("자동완성 결과")
                    if suggestions:
                        for product in suggestions:
                            st.button(
                                product_search_label(product),
                                key=f"product-suggestion:{account['id']}:{product['code']}",
                                width="stretch",
                                on_click=apply_search_product,
                                args=(product,),
                            )
                    else:
                        st.caption("검색 결과가 없습니다.")

        symbol = st.text_input(
            "종목 코드 / 심볼",
            key=TRADE_SYMBOL_KEY,
            help="예: 005930, 005930.KS, AAPL, K55207BU0715",
        )
        product_name = st.text_input("종목명", key=TRADE_PRODUCT_NAME_KEY)
        asset_type = st.selectbox(
            "자산군",
            ["risk", "safe"],
            format_func=label_asset_type,
            key=TRADE_ASSET_TYPE_KEY,
        )
        quantity = st.number_input("수량", min_value=0.0, step=1.0, key=TRADE_QUANTITY_KEY)
        price = st.number_input("단가", min_value=0.0, step=100.0, key=TRADE_PRICE_KEY)
        trade_date = st.date_input("거래일", key=TRADE_DATE_KEY)
        notes = st.text_area("메모", height=90, key=TRADE_NOTES_KEY)
        submitted = st.button("거래 저장", width="stretch", key=f"trade-save:{account['id']}")
        if submitted:
            try:
                record_trade(
                    int(account["id"]),
                    symbol=symbol,
                    product_name=product_name,
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
                st.success("거래를 저장했습니다.")
                st.session_state[TRADE_SYMBOL_KEY] = ""
                st.session_state[TRADE_PRODUCT_NAME_KEY] = ""
                st.session_state[TRADE_SEARCH_QUERY_KEY] = ""
                st.session_state[TRADE_QUANTITY_KEY] = 1.0
                st.session_state[TRADE_PRICE_KEY] = 0.0
                st.session_state[TRADE_NOTES_KEY] = ""
                st.rerun()

    with right:
        st.subheader("현금 흐름")
        flow_type = st.selectbox(
            "현금 흐름",
            ["personal_deposit", "employer_deposit", "withdraw"],
            format_func=label_cash_flow_type,
            key=CASH_FLOW_TYPE_KEY,
        )
        amount = st.number_input("금액", min_value=0, step=100000, key=CASH_FLOW_AMOUNT_KEY)
        trade_date = st.date_input("처리일", key=CASH_FLOW_DATE_KEY)
        notes = st.text_area("사유", height=90, key=CASH_FLOW_NOTES_KEY)
        submitted = st.button("현금 기록", width="stretch", key=f"cash-flow-save:{account['id']}")
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
                st.success("현금 흐름을 기록했습니다.")
                st.session_state[CASH_FLOW_AMOUNT_KEY] = 0
                st.session_state[CASH_FLOW_NOTES_KEY] = ""
                st.rerun()

        st.divider()
        with st.container(border=True, key="trade-panel-transfer"):
            st.subheader("계좌 간 이체")
            transfer_targets = [item for item in accounts if int(item["id"]) != int(account["id"])]
            if not transfer_targets:
                st.info("이체하려면 계좌를 하나 더 만들어 주세요.")
            else:
                target_account_options = [int(item["id"]) for item in transfer_targets]
                saved_target_account_id = st.session_state.get(TRANSFER_TARGET_ACCOUNT_KEY)
                default_target_account_id = (
                    saved_target_account_id
                    if saved_target_account_id in target_account_options
                    else target_account_options[0]
                )
                st.caption(f"출금 계좌: `{account_label(account)}`")
                target_account_id = st.selectbox(
                    "입금 계좌",
                    options=target_account_options,
                    index=target_account_options.index(default_target_account_id),
                    format_func=lambda item_id: account_label(
                        next(item for item in transfer_targets if int(item["id"]) == int(item_id))
                    ),
                    key=TRANSFER_TARGET_ACCOUNT_KEY,
                )
                transfer_amount = st.number_input("이체 금액", min_value=0, step=100000, key=TRANSFER_AMOUNT_KEY)
                transfer_date = st.date_input("이체일", key=TRANSFER_DATE_KEY)
                transfer_notes = st.text_area("이체 메모", height=90, key=TRANSFER_NOTES_KEY)
                submitted = st.button("이체 기록", width="stretch", key=f"transfer-save:{account['id']}")
                if submitted:
                    try:
                        record_account_transfer(
                            int(account["id"]),
                            to_account_id=int(target_account_id),
                            amount=transfer_amount,
                            trade_date=transfer_date.isoformat(),
                            notes=transfer_notes,
                        )
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        mark_rollup_dirty()
                        st.success("계좌 이체를 기록했습니다.")
                        st.session_state[TRANSFER_AMOUNT_KEY] = 0
                        st.session_state[TRANSFER_NOTES_KEY] = ""
                        st.rerun()

    logs = list_trade_logs(int(account["id"]))
    realized = realized_summary(logs)

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("실현 포지션 수", f"{int(realized['sold_count']):,}")
    metric_2.metric("총 매수금액", format_won(realized["total_buy_amount"]))
    metric_3.metric("총 매도금액", format_won(realized["total_sell_amount"]))
    metric_4.metric("실현 수익률", format_pct(realized["total_profit_rate"]))

    realized_positions = realized.get("positions") or []
    if realized_positions:
        chart_frame = pd.DataFrame(realized_positions).sort_values("profit_loss", ascending=False).head(10).copy()
        chart_frame["tone"] = chart_frame["profit_loss"].apply(lambda value: "수익" if float(value or 0) >= 0 else "손실")
        chart = (
            alt.Chart(chart_frame)
            .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
            .encode(
                x=alt.X("product_name:N", sort="-y", title="실현 종목"),
                y=alt.Y("profit_loss:Q", title="실현 손익"),
                color=alt.Color("tone:N", scale=alt.Scale(domain=["수익", "손실"], range=["#0F766E", "#B91C1C"])),
                tooltip=[
                    alt.Tooltip("product_name:N", title="종목"),
                    alt.Tooltip("profit_loss:Q", title="손익", format=",.0f"),
                    alt.Tooltip("profit_rate:Q", title="수익률 (%)", format=".2f"),
                ],
            )
        )
        st.altair_chart(chart, width="stretch")

        position_frame = pd.DataFrame(realized_positions)
        position_frame = position_frame[["product_name", "symbol", "asset_type", "buy_amount", "sell_amount", "profit_loss", "profit_rate", "sell_date"]].copy()
        position_frame.columns = ["상품명", "코드", "자산군", "매수금액", "매도금액", "실현손익", "실현수익률(%)", "매도일"]
        position_frame["자산군"] = position_frame["자산군"].map(label_asset_type)
        for column in ("매수금액", "매도금액", "실현손익"):
            position_frame[column] = position_frame[column].map(lambda value: f"{float(value or 0):,.0f}")
        position_frame["실현수익률(%)"] = position_frame["실현수익률(%)"].map(lambda value: f"{float(value or 0):+.2f}")
        st.subheader("실현 손익 요약")
        st.dataframe(position_frame, width="stretch", hide_index=True, height=280)

    if logs:
        account_name_map = {int(item["id"]): account_label(item) for item in accounts}
        log_frame = pd.DataFrame(logs)
        for column_name in ("counterparty_account_id", "cash_delta"):
            if column_name not in log_frame.columns:
                log_frame[column_name] = None if column_name == "counterparty_account_id" else 0.0
        log_frame["counterparty_account"] = log_frame["counterparty_account_id"].map(
            lambda value: account_name_map.get(int(value), "") if pd.notna(value) else ""
        )
        log_frame = log_frame[
            [
                "trade_date",
                "product_name",
                "symbol",
                "trade_type",
                "counterparty_account",
                "asset_type",
                "quantity",
                "price",
                "total_amount",
                "cash_delta",
                "notes",
            ]
        ].copy()
        log_frame.columns = ["거래일", "종목명", "코드", "유형", "상대 계좌", "자산군", "수량", "단가", "총액", "현금증감", "메모"]
        log_frame["유형"] = log_frame["유형"].map(label_transaction_type).fillna(log_frame["유형"])
        log_frame["자산군"] = log_frame["자산군"].map(label_asset_type).fillna(log_frame["자산군"])
        log_frame["수량"] = log_frame["수량"].map(lambda value: f"{float(value or 0):,.4f}".rstrip("0").rstrip("."))
        for column in ("단가", "총액", "현금증감"):
            log_frame[column] = log_frame[column].map(lambda value: f"{float(value or 0):,.0f}")
        st.subheader("거래 기록")
        st.dataframe(log_frame, width="stretch", hide_index=True, height=420)
    else:
        st.info("아직 기록된 거래가 없습니다.")


def data_page(account: dict[str, Any], rollup_state: dict[str, Any] | None = None) -> None:
    st.title("데이터")
    st.caption("운영 상태 확인과 원본 데이터 CSV 내보내기를 한 곳에서 처리합니다.")

    account_id = int(account["id"])
    status = backend_status()
    holdings = list_holdings(account_id)
    trade_logs = list_trade_logs(account_id)
    interest_rows = list_daily_interest(account_id)
    snapshot_rows = list_account_snapshots(account_id)
    snapshot_date = str((rollup_state or {}).get("snapshot_date") or date.today().isoformat()).strip()
    summary = account_summary(account, holdings, trade_logs=trade_logs, interest_rows=interest_rows)
    cash_adjustment_logs = [
        row for row in trade_logs if str(row.get("trade_type") or "").strip().lower() == "cash_adjustment"
    ]
    cumulative_frame = cumulative_contribution_frame(
        trade_logs=trade_logs,
        interest_rows=interest_rows,
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
        status_col_2.metric("거래 기록", f"{len(trade_logs):,}건", latest_date_text(trade_logs, "trade_date"))
        status_col_3.metric("현금 수정 순반영", format_won(summary["cash_flow"]["net_adjustment"]))
        status_col_4.metric("자산 스냅샷", f"{len(snapshot_rows):,}건", latest_date_text(snapshot_rows, "snapshot_date"))
        if cash_adjustment_logs:
            st.caption(
                f"현금 수정 기록 `{len(cash_adjustment_logs):,}`건이 현재 현금과 평가액에 반영됩니다. "
                f"최근 수정일: `{latest_date_text(cash_adjustment_logs, 'trade_date')}`"
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

    with st.container(border=True):
        st.subheader("원금 누적 기록")
        st.caption("최초 입금일부터 현재까지 누적 원금과 현재 평가액 기준 수익률을 함께 봅니다.")
        st.caption("현금 수정과 계좌 이체는 원금이 아닌 순유입 조정으로 반영하며, 현금 이자 적립 기능은 사용하지 않습니다.")
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


def main() -> None:
    init_state()
    inject_app_styles()
    auth_enabled = app_auth.is_enabled()

    if auth_enabled and handle_auth_callback():
        st.rerun()

    if auth_enabled or app_auth.is_demo_user():
        app_auth.refresh_session_state()
    user = app_auth.get_user()
    if not user:
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
        empty_state()
        return

    selected_account_id, active_page = sidebar(accounts, st.session_state.get("selected_account_id"), user)
    account = get_account(int(selected_account_id))
    if not account:
        st.session_state["selected_account_id"] = None
        st.rerun()
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
    if active_page == "Dashboard":
        dashboard_page(account, holdings, rollup_state)
    elif active_page == "Trades":
        trade_entry_page(account, holdings, accounts)
    else:
        data_page(account, rollup_state)


if __name__ == "__main__":
    main()

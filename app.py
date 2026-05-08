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
    projected_today_interest,
    realized_summary,
    snapshot_trend_frame,
)

import src.auth as app_auth
import src.analytics as analytics_module
import src.db as _db
import src.market as market_module

market_module = importlib.reload(market_module)
fetch_latest_price = market_module.fetch_latest_price
search_products = getattr(market_module, "search_products", lambda query, limit=8: [])

create_account = _db.create_account
adjust_cash_balance = _db.adjust_cash_balance
export_dataframe_rows = _db.export_dataframe_rows
get_account = _db.get_account
initialize_database = _db.initialize_database
list_accounts = _db.list_accounts
list_account_snapshots = _db.list_account_snapshots
list_daily_interest = _db.list_daily_interest
list_holdings = _db.list_holdings
list_trade_logs = _db.list_trade_logs
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
    working = working.sort_values("current_value", ascending=False)

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
    "interest": "일별 이자",
    "transfer_out": "계좌 이체 출금",
    "transfer_in": "계좌 이체 입금",
    "cash_adjustment": "현금 조정",
}
TABLE_LABELS = {
    "accounts": "계좌",
    "holdings": "보유 종목",
    "trade_logs": "거래 기록",
    "daily_interest": "일별 이자",
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
DASHBOARD_TREND_CHART_HEIGHT = 340
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
    st.session_state.setdefault(CASH_FLOW_AMOUNT_KEY, 0.0)
    st.session_state.setdefault(CASH_FLOW_DATE_KEY, date.today())
    st.session_state.setdefault(CASH_FLOW_NOTES_KEY, "")
    st.session_state.setdefault(TRANSFER_TARGET_ACCOUNT_KEY, None)
    st.session_state.setdefault(TRANSFER_AMOUNT_KEY, 0.0)
    st.session_state.setdefault(TRANSFER_DATE_KEY, date.today())
    st.session_state.setdefault(TRANSFER_NOTES_KEY, "")


def inject_app_styles() -> None:
    """대시보드 중심 UI 정리를 위한 앱 전역 스타일을 주입한다."""

    st.markdown(
        """
        <style>
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
            align-items: flex-start;
            justify-content: space-between;
            gap: 0.7rem;
            min-height: 2.35rem;
            margin-bottom: 0.85rem;
        }

        .dashboard-summary-card__field {
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 5.1rem;
        }

        .st-key-dashboard-card-cash [data-testid="stButton"] > button {
            min-height: 2.4rem;
            padding: 0.1rem 1rem;
            font-weight: 700;
            white-space: nowrap;
        }

        .st-key-dashboard-card-cash [data-testid="stHorizontalBlock"] {
            align-items: flex-start;
        }

        .st-key-dashboard-card-cash [data-testid="stNumberInput"] label p,
        .st-key-dashboard-panel-trend [data-testid="stSegmentedControl"] label p,
        .st-key-dashboard-panel-trend [data-testid="stMultiSelect"] label p {
            color: #607285;
            font-weight: 700;
        }

        .st-key-dashboard-panel-market [data-testid="stButton"] > button {
            min-height: 2.65rem;
        }

        @media (max-width: 860px) {
            .dashboard-metric-strip {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }

            .dashboard-treemap-legend__range {
                width: min(300px, 48vw);
            }
        }

        @media (max-width: 560px) {
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


def render_demo_access_entry() -> None:
    """초기 인증 화면의 데모 접속 패널을 렌더링한다."""

    with st.container(border=True):
        info_col, action_col = st.columns((1.5, 1), gap="large")
        with info_col:
            st.subheader("데모 접속")
            st.caption("아이디 입력 없이 버튼만 눌러 테스트용 작업공간으로 바로 들어갈 수 있습니다.")
            st.write("임의의 테스트 계좌, 입금, 매수, 이자, 계좌 이동, 스냅샷 데이터를 자동으로 준비합니다.")
        with action_col:
            demo_submitted = st.button(
                "데모 접속",
                key="auth-demo-entry",
                icon=":material/rocket_launch:",
                width="stretch",
                type="primary",
            )
            if app_auth.has_demo_credentials():
                st.caption("설정된 데모 계정이 있으면 그 계정으로, 없으면 로컬 데모 작업공간으로 바로 연결됩니다.")
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


def render_dashboard_summary_card(label: str, value: str, *, tone: str = "") -> None:
    """기본 요약 카드 본문을 렌더링한다."""

    value_class = "dashboard-summary-card__value"
    if tone == "accent":
        value_class += " dashboard-summary-card__value--accent"
    st.markdown(
        (
            '<div class="dashboard-summary-card__field">'
            f'<div class="dashboard-summary-card__label">{html.escape(label)}</div>'
            f'<div class="{value_class}">{html.escape(value)}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


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
    selected_caption = "종목을 클릭하면 같은 종목을 강조하고 수익률 위치를 표시합니다."
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
        float(child.get("profit_rate") or 0)
        for node in nodes
        for child in (node.get("children") or [])
        if child.get("profit_rate") is not None
    ]
    rate_min = min(leaf_rates) if leaf_rates else 0.0
    rate_max = max(leaf_rates) if leaf_rates else 0.0
    for node in nodes:
        for child in node.get("children") or []:
            if child.get("profit_rate") is None:
                child["itemStyle"] = {
                    "color": "#D5E3D4",
                    "borderColor": "#F8FAFC",
                    "borderWidth": 1,
                }
                continue
            is_selected = bool(child.get("is_selected"))
            child["itemStyle"] = {
                "color": profit_rate_color(float(child.get("profit_rate") or 0), rate_min, rate_max),
                "borderColor": "#0F766E" if is_selected else "#F8FAFC",
                "borderWidth": 3 if is_selected else 1,
                "shadowBlur": 20 if is_selected else 0,
                "shadowColor": "rgba(15, 118, 110, 0.22)" if is_selected else "transparent",
            }

    tooltip_formatter = None
    if JsCode is not None:
        tooltip_formatter = JsCode(
            """
            function(info) {
                var value = Number(info.value || 0).toLocaleString('ko-KR');
                var lines = ['<strong>' + info.name + '</strong>', '평가금액: ₩' + value];
                if (info.data && info.data.bucket) {
                    lines.push('구분: ' + info.data.bucket);
                }
                if (info.data && info.data.symbol) {
                    lines.push('심볼: ' + info.data.symbol);
                }
                if (info.data && info.data.profit_rate !== null && info.data.profit_rate !== undefined) {
                    lines.push('수익률: ' + Number(info.data.profit_rate).toFixed(2) + '%');
                }
                return lines.join('<br/>');
            }
            """
        )

    tooltip_config: dict[str, Any] = {
        "backgroundColor": "rgba(21, 40, 31, 0.92)",
        "borderWidth": 0,
        "textStyle": {"color": "#F8FAFC", "fontSize": 12},
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
        "tooltip": tooltip_config,
        "series": [
            {
                "name": "자산 배분",
                "type": "treemap",
                "top": 2,
                "left": 0,
                "right": 0,
                "bottom": 2,
                "roam": False,
                "nodeClick": False,
                "sort": "desc",
                "breadcrumb": {"show": False},
                "visibleMin": 1,
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
                        "colorSaturation": [0.42, 0.82],
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
    chart_frame = frame.copy()
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
                    "show": is_selected,
                    "position": "top" if rate >= 0 else "bottom",
                    "formatter": format_pct(rate),
                    "color": "#0D3559",
                    "fontWeight": 700,
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
                var currentValue = Number(params.data.current_value || 0).toLocaleString('ko-KR');
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
        "grid": {"top": 24, "right": 12, "bottom": 92, "left": 56},
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
    chart_frame = frame.copy()
    chart_frame["tone"] = chart_frame["profit_rate"].apply(lambda value: "수익" if float(value or 0) >= 0 else "손실")
    chart_frame["display_name"] = chart_frame["product_name"].astype(str).apply(
        lambda value: value if len(value) <= 14 else f"{value[:13]}…"
    )
    selected_key = normalize_holding_symbol(selected_symbol)
    chart_frame["selection_symbol"] = chart_frame["selection_symbol"].astype(str).str.strip().str.upper()
    chart_frame["selected_opacity"] = chart_frame["selection_symbol"].apply(
        lambda value: 1.0 if value == selected_key else (0.92 if not selected_key else 0.48)
    )
    display_order = chart_frame["display_name"].tolist()
    chart = (
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
    return style_dashboard_altair_chart(chart, height=DASHBOARD_OVERVIEW_CHART_HEIGHT)


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
    st.title("은퇴 포트폴리오")
    st.caption("사용자별로 분리된 포트폴리오를 관리하려면 로그인해 주세요.")
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

    render_demo_access_entry()
    sign_in_tab, sign_up_tab = st.tabs(["로그인", "계정 만들기"])

    with sign_in_tab:
        with st.form("sign-in-form", clear_on_submit=False):
            email = st.text_input("이메일", key="sign-in-email")
            password = st.text_input("비밀번호", type="password", key="sign-in-password")
            submitted = st.form_submit_button("로그인", width="stretch", disabled=not auth_enabled)
            if not auth_enabled:
                st.caption("Supabase 인증 설정이 없어 실제 로그인은 잠시 비활성 상태입니다.")
        if submitted:
            try:
                app_auth.sign_in(email=email, password=password)
            except Exception as exc:  # noqa: BLE001
                message = str(exc)
                if "Email not confirmed" in message:
                    st.session_state[PENDING_CONFIRMATION_EMAIL_KEY] = str(email or "").strip()
                    set_auth_feedback("warning", "이 이메일은 아직 확인되지 않았습니다. 위의 버튼으로 확인 메일을 다시 보내고, 가장 최근 메일의 링크를 열어 주세요.")
                    st.rerun()
                st.error(message)
            else:
                st.session_state[PENDING_CONFIRMATION_EMAIL_KEY] = ""
                st.success("로그인되었습니다.")
                st.rerun()

    with sign_up_tab:
        with st.form("sign-up-form", clear_on_submit=False):
            email = st.text_input("이메일", key="sign-up-email")
            password = st.text_input("비밀번호", type="password", key="sign-up-password")
            confirm_password = st.text_input("비밀번호 확인", type="password", key="sign-up-password-confirm")
            submitted = st.form_submit_button("계정 만들기", width="stretch", disabled=not auth_enabled)
            if not auth_enabled:
                st.caption("Supabase 인증 설정이 없어 실제 계정 만들기는 잠시 비활성 상태입니다.")
        if submitted:
            if password != confirm_password:
                st.error("비밀번호가 서로 다릅니다.")
            else:
                try:
                    response = app_auth.sign_up(email=email, password=password)
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))
                else:
                    if getattr(response, "session", None):
                        st.session_state[PENDING_CONFIRMATION_EMAIL_KEY] = ""
                        st.success("계정을 만들고 바로 로그인했습니다.")
                        st.rerun()
                    else:
                        st.session_state[PENDING_CONFIRMATION_EMAIL_KEY] = str(email or "").strip()
                        set_auth_feedback(
                            "info",
                            "계정을 만들었습니다. 확인 메일을 열어 주세요. 예전 링크가 안 되면 위의 버튼으로 새 메일을 다시 보내면 됩니다.",
                        )
                        st.rerun()


def empty_state() -> None:
    st.title("은퇴 포트폴리오")
    st.caption("완전히 분리된 별도 Streamlit 앱입니다. 먼저 계좌를 하나 만들면 시작할 수 있습니다.")
    create_col, demo_col = st.columns((1.35, 1), gap="large")

    with create_col:
        with st.form("create-first-account", clear_on_submit=True):
            name = st.text_input("계좌 이름", placeholder="예: IRP, ISA, 미국주식")
            account_type = st.selectbox("계좌 유형", ["retirement", "brokerage"], format_func=label_account_type)
            opening_cash = st.number_input("시작 현금", min_value=0.0, value=0.0, step=100000.0)
            submitted = st.form_submit_button("첫 계좌 만들기", width="stretch")
    if submitted:
        try:
            account_id = create_account(name=name, account_type=account_type, opening_cash=opening_cash)
        except Exception as exc:  # noqa: BLE001
            render_operation_error(exc)
        else:
            st.session_state["selected_account_id"] = account_id
            st.success("계좌를 만들었습니다.")
            st.rerun()

    with demo_col:
        with st.container(border=True):
            st.subheader("데모 모드")
            st.caption("실제 계좌 없이 화면 흐름을 빠르게 확인할 수 있도록 샘플 데이터를 불러옵니다.")
            st.write("연금 계좌, 일반 계좌, 입금, 매수, 이자, 계좌 이동, 스냅샷 예시가 함께 생성됩니다.")
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
                    opening_cash = st.number_input("시작 현금", min_value=0.0, value=0.0, step=100000.0, key="new-account-cash")
                    submitted = st.form_submit_button("계좌 추가", width="stretch")
                if submitted:
                    try:
                        create_account(name=name, account_type=account_type, opening_cash=opening_cash)
                    except Exception as exc:  # noqa: BLE001
                        render_operation_error(exc)
                    else:
                        st.success("계좌를 추가했습니다.")
                        st.rerun()

    return selected_account_id, st.session_state["active_page"]


def dashboard_page(account: dict[str, Any], holdings: list[dict[str, Any]], rollup_state: dict[str, Any] | None = None) -> None:
    frame = holdings_frame(holdings)
    trade_logs = list_trade_logs(int(account["id"]))
    interest_rows = list_daily_interest(int(account["id"]))
    summary = account_summary(account, holdings, trade_logs=trade_logs, interest_rows=interest_rows)
    rollup_date = str((rollup_state or {}).get("snapshot_date") or "").strip()
    today_preview = projected_today_interest(
        account,
        interest_rows=interest_rows,
        as_of=date.fromisoformat(rollup_date) if rollup_date else None,
    )
    total_interest = float(summary["total_interest"] or 0) + today_preview
    display_cash = float(summary["cash"] or 0) + today_preview
    display_total_value = float(summary["total_value"] or 0) + today_preview
    display_principal_profit_loss = float(summary["principal_profit_loss"] or 0) + today_preview
    display_principal_profit_rate = (
        display_principal_profit_loss / float(summary["total_principal"] or 0) * 100
        if float(summary["total_principal"] or 0)
        else 0.0
    )
    display_actual_profit_loss = float(summary["actual_profit_loss"] or 0) + today_preview
    display_actual_profit_rate = (
        display_actual_profit_loss / float(summary["net_flow"] or 0) * 100
        if float(summary["net_flow"] or 0)
        else 0.0
    )
    selection_state_key = dashboard_holding_selection_key(int(account["id"]))
    available_symbols = {normalize_holding_symbol(item.get("symbol")) for item in holdings if normalize_holding_symbol(item.get("symbol"))}
    selected_symbol = normalize_holding_symbol(st.session_state.get(selection_state_key))
    if selected_symbol and selected_symbol not in available_symbols:
        st.session_state.pop(selection_state_key, None)
        selected_symbol = ""
    overview_frame = holdings_overview_frame(holdings, selected_symbol=selected_symbol or None, limit=10)
    legend_stats = holdings_profit_rate_stats(frame, selected_symbol or None)
    cash_edit_state_key = f"dashboard-cash-editing:{account['id']}"
    cash_edit_amount_key = f"dashboard-cash-edit-amount:{account['id']}"
    summary_cols = st.columns(5, gap="small", vertical_alignment="top")

    with summary_cols[0]:
        with st.container(border=True, key="dashboard-card-principal"):
            render_dashboard_summary_card("입금 원금", format_won(summary["total_principal"]))

    with summary_cols[1]:
        with st.container(border=True, key="dashboard-card-cash"):
            header_col, action_col = st.columns((1, 0.52), gap="small", vertical_alignment="top")
            with header_col:
                st.markdown(
                    '<div class="dashboard-summary-card__header"><div class="dashboard-summary-card__label">보유 현금</div></div>',
                    unsafe_allow_html=True,
                )
            with action_col:
                if st.button(
                    "수정" if not st.session_state.get(cash_edit_state_key, False) else "닫기",
                    key=f"dashboard-cash-edit-toggle:{account['id']}",
                    width="stretch",
                ):
                    st.session_state[cash_edit_state_key] = not bool(st.session_state.get(cash_edit_state_key, False))
                    if st.session_state[cash_edit_state_key]:
                        st.session_state[cash_edit_amount_key] = float(display_cash)
                    st.rerun()
            st.markdown(
                (
                    '<div class="dashboard-summary-card__field">'
                    f'<div class="dashboard-summary-card__value">{html.escape(format_won(display_cash))}</div>'
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

            if st.session_state.get(cash_edit_state_key, False):
                st.number_input(
                    "목표 현금 잔액",
                    min_value=0.0,
                    value=float(st.session_state.get(cash_edit_amount_key, display_cash) or 0.0),
                    step=100000.0,
                    key=cash_edit_amount_key,
                )
                save_col, cancel_col = st.columns(2, gap="small")
                with save_col:
                    if st.button("저장", key=f"dashboard-cash-save:{account['id']}", width="stretch"):
                        try:
                            adjust_cash_balance(
                                int(account["id"]),
                                target_amount=float(st.session_state.get(cash_edit_amount_key, display_cash) or 0.0),
                                trade_date=date.today().isoformat(),
                                notes="대시보드 현금 카드 조정",
                            )
                        except ValueError as exc:
                            st.error(str(exc))
                        else:
                            st.session_state[cash_edit_state_key] = False
                            st.success("현금 조정을 기록했습니다.")
                            st.rerun()
                with cancel_col:
                    if st.button("취소", key=f"dashboard-cash-cancel:{account['id']}", width="stretch"):
                        st.session_state[cash_edit_state_key] = False
                        st.rerun()

    with summary_cols[2]:
        with st.container(border=True, key="dashboard-card-total-value"):
            render_dashboard_summary_card("현재 평가액", format_won(display_total_value))

    with summary_cols[3]:
        with st.container(border=True, key="dashboard-card-profit"):
            render_dashboard_summary_card("원금 대비 평가손익", format_won(display_principal_profit_loss), tone="accent")

    with summary_cols[4]:
        with st.container(border=True, key="dashboard-card-profit-rate"):
            render_dashboard_summary_card("원금 대비 수익률", format_pct(display_principal_profit_rate), tone="accent")

    overview_left, overview_right = st.columns((1, 1), gap="large", vertical_alignment="top")
    with overview_left:
        with st.container(border=True, height=DASHBOARD_OVERVIEW_PANEL_HEIGHT, key="dashboard-panel-allocation"):
            render_dashboard_section_header("자산 배분", "자산군에서 보유 종목까지 한 번에 보는 트리맵입니다.")
            treemap_options = allocation_treemap_options(summary, holdings, selected_symbol=selected_symbol or None)
            if treemap_options is None:
                st.info("배분을 그릴 데이터가 아직 없습니다.")
            elif st_echarts is None:
                chart = allocation_chart(summary)
                if chart is None:
                    st.info("배분을 그릴 데이터가 아직 없습니다.")
                else:
                    st.altair_chart(style_dashboard_altair_chart(chart, height=DASHBOARD_OVERVIEW_CHART_HEIGHT), width="stretch")
                    render_dashboard_treemap_legend(legend_stats)
                    st.caption("`streamlit-echarts`가 없는 환경이라 기본 차트로 표시했습니다.")
            else:
                treemap_event = st_echarts(
                    options=treemap_options,
                    events={
                        "click": "function(params){ return (params.data && params.data.symbol) ? params.data.symbol : ''; }"
                    },
                    height=f"{DASHBOARD_OVERVIEW_CHART_HEIGHT}px",
                    key=f"allocation-treemap:{account['id']}",
                )
                clicked_symbol = normalize_holding_symbol(treemap_event)
                if clicked_symbol and clicked_symbol != selected_symbol:
                    st.session_state[selection_state_key] = clicked_symbol
                    st.rerun()
                render_dashboard_treemap_legend(legend_stats)

    with overview_right:
        with st.container(border=True, height=DASHBOARD_OVERVIEW_PANEL_HEIGHT, key="dashboard-panel-holdings"):
            render_dashboard_section_header("보유 종목 수익률", "현재 보유 상위 종목의 수익률 흐름을 우선 확인합니다.")
            if overview_frame.empty:
                st.info("보유 종목이 없어 수익률 차트를 그릴 수 없습니다.")
            elif st_echarts is None:
                chart = holdings_bar_fallback_chart(overview_frame, selected_symbol=selected_symbol or None)
                if chart is None:
                    st.info("보유 종목이 없어 수익률 차트를 그릴 수 없습니다.")
                else:
                    st.altair_chart(chart, width="stretch")
            else:
                bar_options = holdings_bar_options(overview_frame, selected_symbol=selected_symbol or None)
                bar_event = st_echarts(
                    options=bar_options,
                    events={
                        "click": "function(params){ return (params.data && params.data.symbol) ? params.data.symbol : ''; }"
                    },
                    height=f"{DASHBOARD_OVERVIEW_CHART_HEIGHT}px",
                    key=f"holdings-profit-bar:{account['id']}",
                )
                clicked_symbol = normalize_holding_symbol(bar_event)
                if clicked_symbol and clicked_symbol != selected_symbol:
                    st.session_state[selection_state_key] = clicked_symbol
                    st.rerun()

    with st.container(border=True, key="dashboard-panel-market"):
        render_dashboard_section_header("시장 업데이트", "가격 갱신과 코드 입력 규칙을 한 영역에서 정리했습니다.", compact=True)
        if holdings:
            if st.button("현재가 새로고침", width="stretch"):
                updated, errors = refresh_prices(holdings)
                if updated:
                    st.success(f"{updated}개 종목 가격을 갱신했습니다.")
                if errors:
                    st.warning("\n".join(errors))
                st.rerun()
        else:
            st.info("보유 종목이 생기면 여기서 현재가를 한 번에 갱신할 수 있습니다.")
        st.caption("숫자만 입력한 6자리 한국 종목 코드는 자동으로 `.KS`를 붙여 조회합니다. 코스닥/ETF 등은 필요하면 직접 야후 파이낸스 심볼을 넣어 주세요.")

    with st.container(border=True, key="dashboard-panel-holdings-table"):
        render_dashboard_section_header("현재 보유 종목", "계좌 전체 포지션을 표로 읽고, 이후 아래 추이 차트와 이어서 확인합니다.", compact=True)
        show_holdings_table(frame, height=DASHBOARD_HOLDINGS_TABLE_HEIGHT)

    with st.container(border=True, key="dashboard-panel-trend"):
        trend_title_col, period_col = st.columns((1.2, 1), gap="large", vertical_alignment="bottom")
        with trend_title_col:
            render_dashboard_section_header("추이", "총자산 흐름을 먼저 보고, 이어서 종목별 비교를 같은 섹션에서 확인합니다.", compact=True)
        with period_col:
            period = st.segmented_control(
                "기간",
                options=["1mo", "3mo", "6mo", "1y"],
                format_func=label_period,
                default="6mo",
                key=f"trend-period:{account['id']}",
            )
        snapshot_rows = list_account_snapshots(int(account["id"]), start_date=period_start_date(period).isoformat())
        snapshot_frame = snapshot_trend_frame(snapshot_rows, trade_logs=trade_logs, interest_rows=interest_rows)
        portfolio_trend, holding_trend = build_portfolio_trend(holdings, period=period)
        trend_source = snapshot_frame if not snapshot_frame.empty else portfolio_trend
        if trend_source.empty:
            st.info("추이 데이터가 아직 없습니다. 일별 스냅샷이 쌓이기 전에는 보유 종목 시세 이력도 함께 필요합니다.")
            return

        if not snapshot_frame.empty:
            trend_chart = (
                alt.Chart(trend_source)
                .mark_line(point=True, strokeWidth=3)
                .encode(
                    x=alt.X("date:T", title="날짜"),
                    y=alt.Y("total_value:Q", title="포트폴리오 총자산"),
                    tooltip=[
                        alt.Tooltip("date:T", title="날짜"),
                        alt.Tooltip("total_value:Q", title="총자산", format=",.0f"),
                        alt.Tooltip("market_value:Q", title="평가금액", format=",.0f"),
                        alt.Tooltip("cash_balance:Q", title="현금", format=",.0f"),
                        alt.Tooltip("total_principal:Q", title="누적 납입 원금", format=",.0f"),
                        alt.Tooltip("principal_profit_loss:Q", title="원금 대비 손익", format=",.0f"),
                        alt.Tooltip("principal_profit_rate:Q", title="원금 대비 수익률 (%)", format=".2f"),
                        alt.Tooltip("net_flow:Q", title="순유입", format=",.0f"),
                        alt.Tooltip("actual_profit_loss:Q", title="실제 성과", format=",.0f"),
                    ],
                )
            )
        else:
            trend_chart = (
                alt.Chart(trend_source)
                .mark_line(point=True, strokeWidth=3)
                .encode(
                    x=alt.X("date:T", title="날짜"),
                    y=alt.Y("market_value:Q", title="포트폴리오 평가액"),
                    tooltip=[
                        alt.Tooltip("date:T", title="날짜"),
                        alt.Tooltip("market_value:Q", title="평가금액", format=",.0f"),
                        alt.Tooltip("profit_rate:Q", title="수익률 (%)", format=".2f"),
                    ],
                )
            )
        st.altair_chart(style_dashboard_altair_chart(trend_chart, height=DASHBOARD_TREND_CHART_HEIGHT), width="stretch")

        if not snapshot_frame.empty:
            st.caption("일별 스냅샷에 순유입과 실제 성과 기준을 함께 반영해 추이를 보여주고 있습니다.")

        if holding_trend.empty:
            st.info("종목별 비교 추이는 아직 준비되지 않았습니다.")
            return

        latest_names = (
            holding_trend.sort_values(["date", "market_value"], ascending=[True, False])
            .groupby("product_name", as_index=False)
            .tail(1)["product_name"]
            .tolist()
        )
        if not latest_names:
            st.info("종목별 비교 추이는 아직 준비되지 않았습니다.")
            return

        st.divider()
        selection_col, measure_col = st.columns((1.45, 1), gap="large")
        with selection_col:
            selected_names = st.multiselect(
                "비교할 종목",
                options=latest_names,
                default=latest_names[:3],
                key=f"trend-selection:{account['id']}",
            )
        with measure_col:
            detail_measure = st.segmented_control(
                "비교 지표",
                options=["market_value", "profit_rate", "close"],
                format_func=label_detail_measure,
                default="market_value",
                key=f"detail-measure:{account['id']}",
            )
        if selected_names:
            detail_frame = holding_trend[holding_trend["product_name"].isin(selected_names)].copy()
            detail_chart = (
                alt.Chart(detail_frame)
                .mark_line(strokeWidth=2.5)
                .encode(
                    x=alt.X("date:T", title="날짜"),
                    y=alt.Y(f"{detail_measure}:Q", title=label_detail_measure(detail_measure)),
                    color=alt.Color("product_name:N", title="종목"),
                    tooltip=[
                        alt.Tooltip("product_name:N", title="종목"),
                        alt.Tooltip("date:T", title="날짜"),
                        alt.Tooltip(f"{detail_measure}:Q", title=label_detail_measure(detail_measure), format=",.2f"),
                    ],
                )
            )
            st.altair_chart(style_dashboard_altair_chart(detail_chart, height=DASHBOARD_DETAIL_CHART_HEIGHT), width="stretch")


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
        amount = st.number_input("금액", min_value=0.0, step=100000.0, key=CASH_FLOW_AMOUNT_KEY)
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
                st.success("현금 흐름을 기록했습니다.")
                st.session_state[CASH_FLOW_AMOUNT_KEY] = 0.0
                st.session_state[CASH_FLOW_NOTES_KEY] = ""
                st.rerun()

        st.divider()
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
            transfer_amount = st.number_input("이체 금액", min_value=0.0, step=100000.0, key=TRANSFER_AMOUNT_KEY)
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
                    st.success("계좌 이체를 기록했습니다.")
                    st.session_state[TRANSFER_AMOUNT_KEY] = 0.0
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
    rollup_date = str((rollup_state or {}).get("snapshot_date") or "").strip()
    today_preview = projected_today_interest(
        account,
        interest_rows=interest_rows,
        as_of=date.fromisoformat(rollup_date) if rollup_date else None,
    )
    summary = account_summary(account, holdings, trade_logs=trade_logs, interest_rows=interest_rows)
    total_interest = sum(float(row.get("interest_amount") or 0) for row in interest_rows) + today_preview
    cumulative_frame = cumulative_contribution_frame(
        trade_logs=trade_logs,
        interest_rows=interest_rows,
        snapshots=snapshot_rows,
        current_total_value=float(summary["total_value"] or 0) + today_preview,
        current_market_value=float(summary["market_value"] or 0),
        current_cash_balance=float(summary["cash"] or 0) + today_preview,
        current_total_cost=float(summary["total_cost"] or 0),
        current_date=rollup_date or date.today().isoformat(),
    )

    with st.container(border=True):
        st.subheader("운영 상태")
        st.caption(f"기준 계좌: `{account['name']}`")
        status_col_1, status_col_2, status_col_3, status_col_4 = st.columns(4)
        status_col_1.metric("데이터 저장소", "Supabase" if status["name"] == "supabase" else "로컬 SQLite")
        status_col_2.metric("누적 이자", format_won(total_interest))
        status_col_3.metric("이자 롤업", f"{len(interest_rows):,}건", latest_date_text(interest_rows, "date"))
        status_col_4.metric("자산 스냅샷", f"{len(snapshot_rows):,}건", latest_date_text(snapshot_rows, "snapshot_date"))
        if today_preview > 0:
            st.caption(f"{rollup_date or date.today().isoformat()} 예상 현금 이자까지 표시 중입니다: `{format_won(today_preview)}`")
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
        st.caption("최초 입금일부터 현재까지 누적 원금, 회사 납입금, 누적 이자, 현재 평가액 기준 수익률을 함께 봅니다.")
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
                    "interest_delta",
                    "company_principal",
                    "total_principal",
                    "total_interest",
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
                "당일 이자",
                "회사 납입 누계",
                "누적 투자원금",
                "누적 이자",
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
                "당일 이자",
                "회사 납입 누계",
                "누적 투자원금",
                "누적 이자",
                "현재 평가액",
                "원금 대비 손익",
            ):
                display_frame[column] = display_frame[column].map(_format_optional_won)
            display_frame["원금 대비 수익률(%)"] = display_frame["원금 대비 수익률(%)"].map(_format_optional_pct)
            st.dataframe(display_frame, width="stretch", hide_index=True, height=320)

    for table_name in ("accounts", "holdings", "trade_logs", "daily_interest", "daily_account_snapshot"):
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
    rollup_state: dict[str, Any] = {
        "interest_rows_added": 0,
        "interest_rows_updated": 0,
        "interest_rows_removed": 0,
        "historical_snapshots_updated": 0,
        "interest_amount_added": 0.0,
        "snapshot_date": date.today().isoformat(),
        "snapshot_updated": False,
    }
    try:
        rollup_state = sync_account_rollup(int(account["id"]))
    except Exception as exc:  # noqa: BLE001
        st.warning(f"자동 이자 반영을 건너뛰었습니다: {exc}")
    else:
        added_count = int(rollup_state.get("interest_rows_added", 0) or 0)
        updated_count = int(rollup_state.get("interest_rows_updated", 0) or 0)
        removed_count = int(rollup_state.get("interest_rows_removed", 0) or 0)
        historical_snapshot_count = int(rollup_state.get("historical_snapshots_updated", 0) or 0)
        if added_count or updated_count or removed_count or historical_snapshot_count:
            detail_parts: list[str] = []
            if added_count:
                detail_parts.append(f"추가 `{added_count:,}`건")
            if updated_count:
                detail_parts.append(f"재계산 `{updated_count:,}`건")
            if removed_count:
                detail_parts.append(f"제거 `{removed_count:,}`건")
            if historical_snapshot_count:
                detail_parts.append(f"과거 스냅샷 보정 `{historical_snapshot_count:,}`건")
            detail_parts.append(f"순변동 금액: `{format_won(rollup_state['interest_amount_added'])}`")
            st.info(
                "전일까지의 일별 이자 이력을 원장 기준으로 자동 반영했습니다. "
                + ", ".join(detail_parts)
            )
        account = get_account(int(selected_account_id)) or account
    holdings = list_holdings(int(account["id"]))
    if active_page == "Dashboard":
        dashboard_page(account, holdings, rollup_state)
    elif active_page == "Trades":
        trade_entry_page(account, holdings, accounts)
    else:
        data_page(account, rollup_state)


if __name__ == "__main__":
    main()

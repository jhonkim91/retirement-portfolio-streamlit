from __future__ import annotations

import importlib
from datetime import date
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from src.analytics import (
    account_summary,
    build_portfolio_trend,
    holdings_frame,
    realized_summary,
)

import src.auth as app_auth
import src.db as _db
import src.market as market_module

market_module = importlib.reload(market_module)
fetch_latest_price = market_module.fetch_latest_price
search_products = getattr(market_module, "search_products", lambda query, limit=8: [])

create_account = _db.create_account
export_dataframe_rows = _db.export_dataframe_rows
get_account = _db.get_account
initialize_database = _db.initialize_database
list_accounts = _db.list_accounts
list_holdings = _db.list_holdings
list_trade_logs = _db.list_trade_logs
record_cash_flow = _db.record_cash_flow
record_trade = _db.record_trade
set_holding_price = _db.set_holding_price
update_cash_balance = _db.update_cash_balance
backend_status = _db.backend_status


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
PAGE_LABELS = {
    "Dashboard": "대시보드",
    "Trades": "거래",
    "Data": "데이터",
}
ACCOUNT_TYPE_LABELS = {
    "retirement": "연금",
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
    "withdraw": "출금",
}
TABLE_LABELS = {
    "accounts": "계좌",
    "holdings": "보유 종목",
    "trade_logs": "거래 기록",
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


def label_detail_measure(value: Any) -> str:
    return DETAIL_MEASURE_LABELS.get(str(value), str(value))


def label_period(value: Any) -> str:
    return PERIOD_LABELS.get(str(value), str(value))


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
    st.session_state.setdefault(CASH_FLOW_TYPE_KEY, "deposit")
    st.session_state.setdefault(CASH_FLOW_AMOUNT_KEY, 0.0)
    st.session_state.setdefault(CASH_FLOW_DATE_KEY, date.today())
    st.session_state.setdefault(CASH_FLOW_NOTES_KEY, "")


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


def holdings_bar_chart(frame: pd.DataFrame) -> alt.Chart | None:
    if frame.empty:
        return None
    chart_frame = frame.sort_values("current_value", ascending=False).head(10).copy()
    chart_frame["tone"] = chart_frame["profit_rate"].apply(lambda value: "수익" if float(value or 0) >= 0 else "손실")
    return (
        alt.Chart(chart_frame)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X("product_name:N", sort="-y", title="종목"),
            y=alt.Y("profit_rate:Q", title="수익률 (%)"),
            color=alt.Color("tone:N", scale=alt.Scale(domain=["수익", "손실"], range=["#0F766E", "#B91C1C"])),
            tooltip=[
                alt.Tooltip("product_name:N", title="종목"),
                alt.Tooltip("current_value:Q", title="평가금액", format=",.0f"),
                alt.Tooltip("profit_rate:Q", title="수익률 (%)", format=".2f"),
            ],
        )
    )


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
    st.dataframe(display, use_container_width=True, hide_index=True, height=height)


def auth_page() -> None:
    st.title("은퇴 포트폴리오")
    st.caption("사용자별로 분리된 포트폴리오를 관리하려면 로그인해 주세요.")
    render_auth_feedback()

    pending_email = str(st.session_state.get(PENDING_CONFIRMATION_EMAIL_KEY) or "").strip()
    if pending_email:
        with st.container(border=True):
            st.write(f"이메일 확인 대기: `{pending_email}`")
            st.caption("예전 확인 링크가 열리지 않았다면 여기서 새 메일을 다시 보내고, 가장 최근 메일의 링크를 열어 주세요.")
            if st.button("확인 메일 다시 보내기", key="resend-confirmation", use_container_width=True):
                try:
                    app_auth.resend_signup(pending_email)
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))
                else:
                    st.success(f"{pending_email} 주소로 새 확인 메일을 보냈습니다.")

    sign_in_tab, sign_up_tab = st.tabs(["로그인", "계정 만들기"])

    with sign_in_tab:
        with st.form("sign-in-form", clear_on_submit=False):
            email = st.text_input("이메일", key="sign-in-email")
            password = st.text_input("비밀번호", type="password", key="sign-in-password")
            submitted = st.form_submit_button("로그인", use_container_width=True)
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
            submitted = st.form_submit_button("계정 만들기", use_container_width=True)
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
    with st.form("create-first-account", clear_on_submit=True):
        name = st.text_input("계좌 이름", placeholder="예: IRP, ISA, 미국주식")
        account_type = st.selectbox("계좌 유형", ["retirement", "brokerage"], format_func=label_account_type)
        opening_cash = st.number_input("시작 현금", min_value=0.0, value=0.0, step=100000.0)
        submitted = st.form_submit_button("첫 계좌 만들기", use_container_width=True)
    if submitted:
        try:
            account_id = create_account(name=name, account_type=account_type, opening_cash=opening_cash)
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.session_state["selected_account_id"] = account_id
            st.success("계좌를 만들었습니다.")
            st.rerun()


def sidebar(accounts: list[dict[str, Any]], selected_account_id: int | None, user: dict[str, Any]) -> tuple[int, str]:
    account_ids = [int(account["id"]) for account in accounts]
    if selected_account_id not in account_ids:
        selected_account_id = account_ids[0]
        st.session_state["selected_account_id"] = selected_account_id

    with st.sidebar:
        st.title("내 작업공간")
        user_label = user.get("email") or user.get("id") or "로그인 사용자"
        st.caption(f"로그인 계정: `{user_label}`")
        if st.button("로그아웃", use_container_width=True):
            app_auth.sign_out()
            st.session_state["selected_account_id"] = None
            st.rerun()
        st.divider()

        selected_account_id = st.selectbox(
            "계좌",
            options=account_ids,
            index=account_ids.index(selected_account_id),
            format_func=lambda account_id: account_label(next(account for account in accounts if int(account["id"]) == account_id)),
        )
        st.session_state["selected_account_id"] = selected_account_id

        active_page = st.radio(
            "페이지",
            PAGES,
            index=PAGES.index(st.session_state.get("active_page", PAGES[0])),
            format_func=label_page,
        )
        st.session_state["active_page"] = active_page

        st.divider()
        with st.expander("새 계좌 만들기", expanded=False):
            with st.form("new-account-form", clear_on_submit=True):
                name = st.text_input("계좌 이름")
                account_type = st.selectbox("유형", ["retirement", "brokerage"], format_func=label_account_type, key="new-account-type")
                opening_cash = st.number_input("시작 현금", min_value=0.0, value=0.0, step=100000.0, key="new-account-cash")
                submitted = st.form_submit_button("계좌 추가", use_container_width=True)
            if submitted:
                try:
                    create_account(name=name, account_type=account_type, opening_cash=opening_cash)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success("계좌를 추가했습니다.")
                    st.rerun()

    return selected_account_id, st.session_state["active_page"]


def dashboard_page(account: dict[str, Any], holdings: list[dict[str, Any]]) -> None:
    frame = holdings_frame(holdings)
    summary = account_summary(account, holdings)

    st.title(account["name"])
    st.caption(f"계좌 유형: `{label_account_type(account['account_type'])}`")

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("포트폴리오 평가액", format_won(summary["total_value"]))
    metric_2.metric("투입 원금", format_won(summary["total_cost"]))
    metric_3.metric("평가 손익", format_won(summary["profit_loss"]), metric_delta(summary["profit_loss"]))
    metric_4.metric("현금", format_won(summary["cash"]))

    top_left, top_right = st.columns((1, 1), gap="large")
    with top_left:
        st.subheader("자산 배분")
        chart = allocation_chart(summary)
        if chart is None:
            st.info("배분을 그릴 데이터가 아직 없습니다.")
        else:
            st.altair_chart(chart, use_container_width=True)

        st.subheader("현금")
        with st.form("cash-balance-form"):
            amount = st.number_input("현금 잔액 직접 수정", min_value=0.0, value=float(account["cash_balance"] or 0), step=100000.0)
            submitted = st.form_submit_button("현금 저장", use_container_width=True)
        if submitted:
            try:
                update_cash_balance(int(account["id"]), amount)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success("현금을 저장했습니다.")
                st.rerun()

    with top_right:
        st.subheader("보유 종목 수익률")
        chart = holdings_bar_chart(frame)
        if chart is None:
            st.info("보유 종목이 없어 수익률 차트를 그릴 수 없습니다.")
        else:
            st.altair_chart(chart, use_container_width=True)

    action_col_1, action_col_2 = st.columns((1, 2), gap="large")
    with action_col_1:
        if st.button("현재가 새로고침", use_container_width=True):
            updated, errors = refresh_prices(holdings)
            if updated:
                st.success(f"{updated}개 종목 가격을 갱신했습니다.")
            if errors:
                st.warning("\n".join(errors))
            st.rerun()

    with action_col_2:
        st.caption("숫자만 입력한 6자리 한국 종목 코드는 자동으로 `.KS`를 붙여 조회합니다. 코스닥/ETF 등은 필요하면 직접 야후 파이낸스 심볼을 넣어 주세요.")

    st.subheader("현재 보유 종목")
    show_holdings_table(frame, height=360)

    st.subheader("추이")
    period = st.segmented_control(
        "기간",
        options=["1mo", "3mo", "6mo", "1y"],
        format_func=label_period,
        default="6mo",
        key=f"trend-period:{account['id']}",
    )
    portfolio_trend, holding_trend = build_portfolio_trend(holdings, period=period)
    if portfolio_trend.empty:
        st.info("추이 데이터가 잠시 준비되지 않았습니다. 야후 파이낸스 조회 제한이 걸렸거나, 아직 이력이 충분하지 않을 수 있습니다.")
        return

    trend_chart = (
        alt.Chart(portfolio_trend)
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
    st.altair_chart(trend_chart, use_container_width=True)

    latest_names = (
        holding_trend.sort_values(["date", "market_value"], ascending=[True, False])
        .groupby("product_name", as_index=False)
        .tail(1)["product_name"]
        .tolist()
    )
    selected_names = st.multiselect(
        "비교할 종목",
        options=latest_names,
        default=latest_names[:3],
        key=f"trend-selection:{account['id']}",
    )
    if selected_names:
        detail_measure = st.segmented_control(
            "비교 지표",
            options=["market_value", "profit_rate", "close"],
            format_func=label_detail_measure,
            default="market_value",
            key=f"detail-measure:{account['id']}",
        )
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
        st.altair_chart(detail_chart, use_container_width=True)


def trade_entry_page(account: dict[str, Any], holdings: list[dict[str, Any]]) -> None:
    st.title("거래")
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
                                use_container_width=True,
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
        submitted = st.button("거래 저장", use_container_width=True, key=f"trade-save:{account['id']}")
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
        st.subheader("현금 입출금")
        flow_type = st.selectbox(
            "현금 흐름",
            ["deposit", "withdraw"],
            format_func=label_cash_flow_type,
            key=CASH_FLOW_TYPE_KEY,
        )
        amount = st.number_input("금액", min_value=0.0, step=100000.0, key=CASH_FLOW_AMOUNT_KEY)
        trade_date = st.date_input("처리일", key=CASH_FLOW_DATE_KEY)
        notes = st.text_area("사유", height=90, key=CASH_FLOW_NOTES_KEY)
        submitted = st.button("현금 기록", use_container_width=True, key=f"cash-flow-save:{account['id']}")
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
        st.altair_chart(chart, use_container_width=True)

        position_frame = pd.DataFrame(realized_positions)
        position_frame = position_frame[["product_name", "symbol", "asset_type", "buy_amount", "sell_amount", "profit_loss", "profit_rate", "sell_date"]].copy()
        position_frame.columns = ["상품명", "코드", "자산군", "매수금액", "매도금액", "실현손익", "실현수익률(%)", "매도일"]
        position_frame["자산군"] = position_frame["자산군"].map(label_asset_type)
        for column in ("매수금액", "매도금액", "실현손익"):
            position_frame[column] = position_frame[column].map(lambda value: f"{float(value or 0):,.0f}")
        position_frame["실현수익률(%)"] = position_frame["실현수익률(%)"].map(lambda value: f"{float(value or 0):+.2f}")
        st.subheader("실현 손익 요약")
        st.dataframe(position_frame, use_container_width=True, hide_index=True, height=280)

    if logs:
        log_frame = pd.DataFrame(logs)
        log_frame = log_frame[["trade_date", "product_name", "symbol", "trade_type", "asset_type", "quantity", "price", "total_amount", "notes"]].copy()
        log_frame.columns = ["거래일", "종목명", "코드", "유형", "자산군", "수량", "단가", "총액", "메모"]
        log_frame["유형"] = log_frame["유형"].map(label_transaction_type).fillna(log_frame["유형"])
        log_frame["자산군"] = log_frame["자산군"].map(label_asset_type).fillna(log_frame["자산군"])
        log_frame["수량"] = log_frame["수량"].map(lambda value: f"{float(value or 0):,.4f}".rstrip("0").rstrip("."))
        for column in ("단가", "총액"):
            log_frame[column] = log_frame[column].map(lambda value: f"{float(value or 0):,.0f}")
        st.subheader("거래 기록")
        st.dataframe(log_frame, use_container_width=True, hide_index=True, height=420)
    else:
        st.info("아직 기록된 거래가 없습니다.")


def data_page() -> None:
    st.title("데이터")
    st.caption("현재 앱에서 사용하는 데이터를 CSV로 내려받을 수 있습니다.")

    for table_name in ("accounts", "holdings", "trade_logs"):
        rows = export_dataframe_rows(table_name)
        frame = pd.DataFrame(rows)
        csv_bytes = frame.to_csv(index=False).encode("utf-8-sig") if not frame.empty else b""
        with st.container(border=True):
            table_label = label_table_name(table_name)
            st.subheader(table_label)
            st.write(f"행 수: `{len(frame):,}`")
            if not frame.empty:
                st.dataframe(frame, use_container_width=True, hide_index=True, height=220)
            else:
                st.info("데이터가 없습니다.")
            st.download_button(
                label=f"{table_label} CSV 다운로드",
                data=csv_bytes,
                file_name=f"{table_name}.csv",
                mime="text/csv",
                use_container_width=True,
            )


def main() -> None:
    init_state()
    if not app_auth.is_enabled():
        st.error("Supabase 인증이 설정되지 않았습니다. Streamlit secrets에 SUPABASE_URL 과 SUPABASE_KEY 를 넣어 주세요.")
        return

    if handle_auth_callback():
        st.rerun()

    app_auth.refresh_session_state()
    user = app_auth.get_user()
    if not user:
        auth_page()
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

    if active_page == "Dashboard":
        dashboard_page(account, holdings)
    elif active_page == "Trades":
        trade_entry_page(account, holdings)
    else:
        data_page()


if __name__ == "__main__":
    main()

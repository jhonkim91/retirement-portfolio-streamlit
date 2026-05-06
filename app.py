from __future__ import annotations

from datetime import date
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from src.analytics import account_summary, build_portfolio_trend, holdings_frame, realized_summary
from src import db as _db

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
from src.market import fetch_latest_price


st.set_page_config(
    page_title="Retirement Portfolio Streamlit",
    page_icon=":material/account_balance_wallet:",
    layout="wide",
)


PAGES = ("Dashboard", "Trades", "Data")


def format_won(value: Any) -> str:
    return f"₩{float(value or 0):,.0f}"


def format_pct(value: Any) -> str:
    return f"{float(value or 0):+.2f}%"


def metric_delta(value: Any) -> str:
    return f"{float(value or 0):+,.0f}"


def init_state() -> None:
    st.session_state.setdefault("selected_account_id", None)
    st.session_state.setdefault("active_page", PAGES[0])


def account_label(account: dict[str, Any]) -> str:
    account_type = str(account.get("account_type") or "retirement").title()
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
            {"bucket": "Risk", "value": float(allocation.get("risk") or 0)},
            {"bucket": "Safe", "value": float(allocation.get("safe") or 0)},
            {"bucket": "Cash", "value": float(allocation.get("cash") or 0)},
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
    chart_frame["tone"] = chart_frame["profit_rate"].apply(lambda value: "Gain" if float(value or 0) >= 0 else "Loss")
    return (
        alt.Chart(chart_frame)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X("product_name:N", sort="-y", title="Holding"),
            y=alt.Y("profit_rate:Q", title="Return (%)"),
            color=alt.Color("tone:N", scale=alt.Scale(domain=["Gain", "Loss"], range=["#0F766E", "#B91C1C"])),
            tooltip=[
                alt.Tooltip("product_name:N", title="Holding"),
                alt.Tooltip("current_value:Q", title="Current value", format=",.0f"),
                alt.Tooltip("profit_rate:Q", title="Return (%)", format=".2f"),
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
    display["수량"] = display["수량"].map(lambda value: f"{float(value or 0):,.4f}".rstrip("0").rstrip("."))
    for column in ("평단가", "현재가", "원금", "평가금액", "손익"):
        display[column] = display[column].map(lambda value: f"{float(value or 0):,.0f}")
    display["수익률(%)"] = display["수익률(%)"].map(lambda value: f"{float(value or 0):+.2f}")
    st.dataframe(display, use_container_width=True, hide_index=True, height=height)


def empty_state() -> None:
    st.title("Retirement Portfolio Streamlit")
    st.caption("완전히 분리된 별도 Streamlit 앱입니다. 먼저 계좌를 하나 만들면 시작할 수 있습니다.")
    with st.form("create-first-account", clear_on_submit=True):
        name = st.text_input("계좌 이름", placeholder="예: IRP, ISA, 미국주식")
        account_type = st.selectbox("계좌 유형", ["retirement", "brokerage"])
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


def sidebar(accounts: list[dict[str, Any]], selected_account_id: int | None) -> tuple[int, str]:
    account_ids = [int(account["id"]) for account in accounts]
    if selected_account_id not in account_ids:
        selected_account_id = account_ids[0]
        st.session_state["selected_account_id"] = selected_account_id

    with st.sidebar:
        st.title("Workspace")
        selected_account_id = st.selectbox(
            "계좌",
            options=account_ids,
            index=account_ids.index(selected_account_id),
            format_func=lambda account_id: account_label(next(account for account in accounts if int(account["id"]) == account_id)),
        )
        st.session_state["selected_account_id"] = selected_account_id

        active_page = st.radio("페이지", PAGES, index=PAGES.index(st.session_state.get("active_page", PAGES[0])))
        st.session_state["active_page"] = active_page

        st.divider()
        with st.expander("새 계좌 만들기", expanded=False):
            with st.form("new-account-form", clear_on_submit=True):
                name = st.text_input("계좌 이름")
                account_type = st.selectbox("유형", ["retirement", "brokerage"], key="new-account-type")
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
    st.caption(f"Account type: `{account['account_type']}`")

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("Portfolio Value", format_won(summary["total_value"]))
    metric_2.metric("Invested Capital", format_won(summary["total_cost"]))
    metric_3.metric("Unrealized P/L", format_won(summary["profit_loss"]), metric_delta(summary["profit_loss"]))
    metric_4.metric("Cash", format_won(summary["cash"]))

    top_left, top_right = st.columns((1, 1), gap="large")
    with top_left:
        st.subheader("Allocation")
        chart = allocation_chart(summary)
        if chart is None:
            st.info("배분을 그릴 데이터가 아직 없습니다.")
        else:
            st.altair_chart(chart, use_container_width=True)

        st.subheader("Cash")
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
        st.subheader("Holdings Return")
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
        st.caption("숫자만 입력한 6자리 한국 종목 코드는 자동으로 `.KS`를 붙여 조회합니다. 코스닥/ETF 등은 필요하면 직접 Yahoo Finance 심볼을 넣어 주세요.")

    st.subheader("Current Holdings")
    show_holdings_table(frame, height=360)

    st.subheader("Trend")
    period = st.segmented_control("기간", options=["1mo", "3mo", "6mo", "1y"], default="6mo", key=f"trend-period:{account['id']}")
    portfolio_trend, holding_trend = build_portfolio_trend(holdings, period=period)
    if portfolio_trend.empty:
        st.info("추이 차트를 그릴 데이터가 없습니다. 현재가를 먼저 새로고침해 보세요.")
        return

    trend_chart = (
        alt.Chart(portfolio_trend)
        .mark_line(point=True, strokeWidth=3)
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("market_value:Q", title="Portfolio market value"),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("market_value:Q", title="Market value", format=",.0f"),
                alt.Tooltip("profit_rate:Q", title="Return (%)", format=".2f"),
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
            default="market_value",
            key=f"detail-measure:{account['id']}",
        )
        detail_frame = holding_trend[holding_trend["product_name"].isin(selected_names)].copy()
        detail_chart = (
            alt.Chart(detail_frame)
            .mark_line(strokeWidth=2.5)
            .encode(
                x=alt.X("date:T", title="Date"),
                y=alt.Y(f"{detail_measure}:Q", title=detail_measure.replace("_", " ").title()),
                color=alt.Color("product_name:N", title="Holding"),
                tooltip=[
                    alt.Tooltip("product_name:N", title="Holding"),
                    alt.Tooltip("date:T", title="Date"),
                    alt.Tooltip(f"{detail_measure}:Q", title=detail_measure.replace("_", " ").title(), format=",.2f"),
                ],
            )
        )
        st.altair_chart(detail_chart, use_container_width=True)


def trade_entry_page(account: dict[str, Any], holdings: list[dict[str, Any]]) -> None:
    st.title("Trades")
    left, right = st.columns((1, 1), gap="large")

    with left:
        st.subheader("매수 / 매도")
        holding_options = {holding["product_name"]: holding for holding in holdings}
        with st.form("trade-form", clear_on_submit=True):
            trade_type = st.selectbox("거래 유형", ["buy", "sell"])
            if holding_options and trade_type == "sell":
                selected_holding_name = st.selectbox("보유 종목", options=list(holding_options))
                selected_holding = holding_options[selected_holding_name]
                default_symbol = str(selected_holding["symbol"])
                default_name = str(selected_holding["product_name"])
                default_asset_type = str(selected_holding["asset_type"])
            else:
                default_symbol = ""
                default_name = ""
                default_asset_type = "risk"

            symbol = st.text_input("심볼", value=default_symbol, help="예: AAPL, MSFT, 005930, 005930.KS")
            product_name = st.text_input("종목명", value=default_name)
            asset_type = st.selectbox("자산군", ["risk", "safe"], index=0 if default_asset_type == "risk" else 1)
            quantity = st.number_input("수량", min_value=0.0, value=1.0, step=1.0)
            price = st.number_input("단가", min_value=0.0, value=0.0, step=100.0)
            trade_date = st.date_input("거래일", value=date.today())
            notes = st.text_area("메모", height=90)
            submitted = st.form_submit_button("거래 저장", use_container_width=True)
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
                st.rerun()

    with right:
        st.subheader("현금 입출금")
        with st.form("cash-flow-form", clear_on_submit=True):
            flow_type = st.selectbox("현금 흐름", ["deposit", "withdraw"])
            amount = st.number_input("금액", min_value=0.0, value=0.0, step=100000.0)
            trade_date = st.date_input("처리일", value=date.today(), key="cash-flow-date")
            notes = st.text_area("사유", height=90, key="cash-flow-notes")
            submitted = st.form_submit_button("현금 기록", use_container_width=True)
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
                st.rerun()

    logs = list_trade_logs(int(account["id"]))
    realized = realized_summary(logs)

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("Closed Positions", f"{int(realized['sold_count']):,}")
    metric_2.metric("Total Buy", format_won(realized["total_buy_amount"]))
    metric_3.metric("Total Sell", format_won(realized["total_sell_amount"]))
    metric_4.metric("Realized Return", format_pct(realized["total_profit_rate"]))

    realized_positions = realized.get("positions") or []
    if realized_positions:
        chart_frame = pd.DataFrame(realized_positions).sort_values("profit_loss", ascending=False).head(10).copy()
        chart_frame["tone"] = chart_frame["profit_loss"].apply(lambda value: "Gain" if float(value or 0) >= 0 else "Loss")
        chart = (
            alt.Chart(chart_frame)
            .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
            .encode(
                x=alt.X("product_name:N", sort="-y", title="Closed position"),
                y=alt.Y("profit_loss:Q", title="Profit / Loss"),
                color=alt.Color("tone:N", scale=alt.Scale(domain=["Gain", "Loss"], range=["#0F766E", "#B91C1C"])),
                tooltip=[
                    alt.Tooltip("product_name:N", title="Holding"),
                    alt.Tooltip("profit_loss:Q", title="P/L", format=",.0f"),
                    alt.Tooltip("profit_rate:Q", title="Return (%)", format=".2f"),
                ],
            )
        )
        st.altair_chart(chart, use_container_width=True)

        position_frame = pd.DataFrame(realized_positions)
        position_frame = position_frame[["product_name", "symbol", "asset_type", "buy_amount", "sell_amount", "profit_loss", "profit_rate", "sell_date"]].copy()
        position_frame.columns = ["상품명", "코드", "자산군", "매수금액", "매도금액", "실현손익", "실현수익률(%)", "매도일"]
        for column in ("매수금액", "매도금액", "실현손익"):
            position_frame[column] = position_frame[column].map(lambda value: f"{float(value or 0):,.0f}")
        position_frame["실현수익률(%)"] = position_frame["실현수익률(%)"].map(lambda value: f"{float(value or 0):+.2f}")
        st.subheader("Realized Summary")
        st.dataframe(position_frame, use_container_width=True, hide_index=True, height=280)

    if logs:
        log_frame = pd.DataFrame(logs)
        log_frame = log_frame[["trade_date", "product_name", "symbol", "trade_type", "asset_type", "quantity", "price", "total_amount", "notes"]].copy()
        log_frame.columns = ["거래일", "종목명", "코드", "유형", "자산군", "수량", "단가", "총액", "메모"]
        log_frame["수량"] = log_frame["수량"].map(lambda value: f"{float(value or 0):,.4f}".rstrip("0").rstrip("."))
        for column in ("단가", "총액"):
            log_frame[column] = log_frame[column].map(lambda value: f"{float(value or 0):,.0f}")
        st.subheader("Trade Log")
        st.dataframe(log_frame, use_container_width=True, hide_index=True, height=420)
    else:
        st.info("아직 기록된 거래가 없습니다.")


def data_page() -> None:
    st.title("Data")
    st.caption("현재 앱에서 사용하는 로컬 SQLite 데이터를 CSV로 내려받을 수 있습니다.")

    for table_name in ("accounts", "holdings", "trade_logs"):
        rows = export_dataframe_rows(table_name)
        frame = pd.DataFrame(rows)
        csv_bytes = frame.to_csv(index=False).encode("utf-8-sig") if not frame.empty else b""
        with st.container(border=True):
            st.subheader(table_name)
            st.write(f"Rows: `{len(frame):,}`")
            if not frame.empty:
                st.dataframe(frame, use_container_width=True, hide_index=True, height=220)
            else:
                st.info("데이터가 없습니다.")
            st.download_button(
                label=f"{table_name}.csv 다운로드",
                data=csv_bytes,
                file_name=f"{table_name}.csv",
                mime="text/csv",
                use_container_width=True,
            )


def main() -> None:
    initialize_database()
    init_state()
    accounts = list_accounts()
    if not accounts:
        empty_state()
        return

    selected_account_id, active_page = sidebar(accounts, st.session_state.get("selected_account_id"))
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

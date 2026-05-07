from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator


ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("RETIREMENT_DB_PATH", ROOT_DIR / "data" / "portfolio.db"))


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()


def initialize_database() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                account_type TEXT NOT NULL DEFAULT 'retirement',
                cash_balance REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                product_name TEXT NOT NULL,
                asset_type TEXT NOT NULL DEFAULT 'risk',
                quantity REAL NOT NULL DEFAULT 0,
                avg_cost REAL NOT NULL DEFAULT 0,
                current_price REAL NOT NULL DEFAULT 0,
                price_updated_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(account_id, symbol),
                FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS trade_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                symbol TEXT,
                product_name TEXT NOT NULL,
                trade_type TEXT NOT NULL,
                asset_type TEXT NOT NULL DEFAULT 'risk',
                quantity REAL NOT NULL DEFAULT 0,
                price REAL NOT NULL DEFAULT 0,
                total_amount REAL NOT NULL DEFAULT 0,
                trade_date TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
            );
            """
        )
        # Clear empty verification accounts created during automated deploy checks.
        connection.execute(
            """
            DELETE FROM accounts
            WHERE name LIKE 'Auto Test %'
              AND id NOT IN (SELECT account_id FROM holdings)
              AND id NOT IN (SELECT account_id FROM trade_logs)
            """
        )
        connection.commit()


def _fetch_all(query: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(query, parameters).fetchall()
    return [dict(row) for row in rows]


def _fetch_one(query: str, parameters: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with connect() as connection:
        row = connection.execute(query, parameters).fetchone()
    return dict(row) if row else None


def list_accounts() -> list[dict[str, Any]]:
    return _fetch_all("SELECT * FROM accounts ORDER BY name COLLATE NOCASE ASC")


def get_account(account_id: int) -> dict[str, Any] | None:
    return _fetch_one("SELECT * FROM accounts WHERE id = ?", (account_id,))


def create_account(name: str, account_type: str = "retirement", opening_cash: float = 0) -> int:
    cleaned_name = str(name or "").strip()
    if not cleaned_name:
        raise ValueError("계좌 이름을 입력해 주세요.")

    cleaned_type = str(account_type or "retirement").strip().lower()
    if cleaned_type not in {"retirement", "brokerage"}:
        raise ValueError("계좌 유형은 retirement 또는 brokerage만 지원합니다.")

    timestamp = now_iso()
    with connect() as connection:
        try:
            cursor = connection.execute(
                """
                INSERT INTO accounts (name, account_type, cash_balance, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (cleaned_name, cleaned_type, float(opening_cash or 0), timestamp, timestamp),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("같은 이름의 계좌가 이미 있습니다.") from exc
        connection.commit()
        return int(cursor.lastrowid)


def update_cash_balance(account_id: int, amount: float) -> None:
    if float(amount) < 0:
        raise ValueError("현금은 0 이상이어야 합니다.")

    with connect() as connection:
        connection.execute(
            "UPDATE accounts SET cash_balance = ?, updated_at = ? WHERE id = ?",
            (float(amount), now_iso(), account_id),
        )
        connection.commit()


def list_holdings(account_id: int, include_closed: bool = False) -> list[dict[str, Any]]:
    operator = ">=" if include_closed else ">"
    query = f"""
        SELECT *
        FROM holdings
        WHERE account_id = ?
          AND quantity {operator} 0
        ORDER BY current_price * quantity DESC, product_name COLLATE NOCASE ASC
    """
    return _fetch_all(query, (account_id,))


def set_holding_price(holding_id: int, current_price: float, as_of: str | None = None) -> None:
    with connect() as connection:
        connection.execute(
            """
            UPDATE holdings
            SET current_price = ?, price_updated_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (float(current_price or 0), as_of or now_iso(), now_iso(), holding_id),
        )
        connection.commit()


def list_trade_logs(account_id: int) -> list[dict[str, Any]]:
    return _fetch_all(
        """
        SELECT *
        FROM trade_logs
        WHERE account_id = ?
        ORDER BY trade_date DESC, id DESC
        """,
        (account_id,),
    )


def export_dataframe_rows(table_name: str) -> list[dict[str, Any]]:
    if table_name not in {"accounts", "holdings", "trade_logs"}:
        raise ValueError("지원하지 않는 테이블입니다.")
    return _fetch_all(f"SELECT * FROM {table_name} ORDER BY id ASC")


def record_trade(
    account_id: int,
    *,
    symbol: str,
    product_name: str,
    trade_type: str,
    asset_type: str,
    quantity: float,
    price: float,
    trade_date: str,
    notes: str = "",
) -> None:
    cleaned_symbol = str(symbol or "").strip().upper()
    cleaned_name = str(product_name or "").strip()
    cleaned_type = str(trade_type or "").strip().lower()
    cleaned_asset_type = str(asset_type or "risk").strip().lower()

    if cleaned_type not in {"buy", "sell"}:
        raise ValueError("매수/매도 거래만 기록할 수 있습니다.")
    if cleaned_asset_type not in {"risk", "safe"}:
        raise ValueError("자산군은 risk 또는 safe만 지원합니다.")
    if not cleaned_symbol:
        raise ValueError("종목 코드를 입력해 주세요.")
    if not cleaned_name:
        raise ValueError("종목명을 입력해 주세요.")

    share_count = float(quantity or 0)
    trade_price = float(price or 0)
    if share_count <= 0 or trade_price <= 0:
        raise ValueError("수량과 가격은 모두 0보다 커야 합니다.")

    total_amount = share_count * trade_price
    timestamp = now_iso()

    with connect() as connection:
        account_row = connection.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        if not account_row:
            raise ValueError("계좌를 찾을 수 없습니다.")

        holding_row = connection.execute(
            "SELECT * FROM holdings WHERE account_id = ? AND symbol = ?",
            (account_id, cleaned_symbol),
        ).fetchone()

        cash_balance = float(account_row["cash_balance"] or 0)

        if cleaned_type == "buy":
            if cash_balance + 0.000001 < total_amount:
                raise ValueError("현금이 부족합니다. 현금 입금 후 다시 시도해 주세요.")

            if holding_row:
                previous_quantity = float(holding_row["quantity"] or 0)
                previous_cost = float(holding_row["avg_cost"] or 0)
                next_quantity = previous_quantity + share_count
                weighted_avg_cost = ((previous_quantity * previous_cost) + total_amount) / next_quantity
                connection.execute(
                    """
                    UPDATE holdings
                    SET product_name = ?, asset_type = ?, quantity = ?, avg_cost = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        cleaned_name,
                        cleaned_asset_type,
                        next_quantity,
                        weighted_avg_cost,
                        timestamp,
                        int(holding_row["id"]),
                    ),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO holdings (
                        account_id, symbol, product_name, asset_type, quantity, avg_cost, current_price,
                        price_updated_at, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        account_id,
                        cleaned_symbol,
                        cleaned_name,
                        cleaned_asset_type,
                        share_count,
                        trade_price,
                        trade_price,
                        timestamp,
                        timestamp,
                        timestamp,
                    ),
                )

            connection.execute(
                "UPDATE accounts SET cash_balance = ?, updated_at = ? WHERE id = ?",
                (cash_balance - total_amount, timestamp, account_id),
            )
        else:
            if not holding_row:
                raise ValueError("매도할 보유 종목이 없습니다.")

            previous_quantity = float(holding_row["quantity"] or 0)
            if previous_quantity + 0.000001 < share_count:
                raise ValueError("보유 수량보다 많은 수량을 매도할 수 없습니다.")

            next_quantity = previous_quantity - share_count
            avg_cost = float(holding_row["avg_cost"] or 0)
            connection.execute(
                """
                UPDATE holdings
                SET quantity = ?, avg_cost = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    max(next_quantity, 0),
                    avg_cost if next_quantity > 0 else 0,
                    timestamp,
                    int(holding_row["id"]),
                ),
            )
            connection.execute(
                "UPDATE accounts SET cash_balance = ?, updated_at = ? WHERE id = ?",
                (cash_balance + total_amount, timestamp, account_id),
            )

        connection.execute(
            """
            INSERT INTO trade_logs (
                account_id, symbol, product_name, trade_type, asset_type,
                quantity, price, total_amount, trade_date, notes, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                cleaned_symbol,
                cleaned_name,
                cleaned_type,
                cleaned_asset_type,
                share_count,
                trade_price,
                total_amount,
                str(trade_date),
                str(notes or "").strip(),
                timestamp,
            ),
        )
        connection.commit()


def record_cash_flow(
    account_id: int,
    *,
    flow_type: str,
    amount: float,
    trade_date: str,
    notes: str = "",
) -> None:
    cleaned_type = str(flow_type or "").strip().lower()
    if cleaned_type not in {"deposit", "withdraw"}:
        raise ValueError("입금 또는 출금만 기록할 수 있습니다.")

    cash_delta = float(amount or 0)
    if cash_delta <= 0:
        raise ValueError("금액은 0보다 커야 합니다.")

    timestamp = now_iso()
    with connect() as connection:
        account_row = connection.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        if not account_row:
            raise ValueError("계좌를 찾을 수 없습니다.")

        current_cash = float(account_row["cash_balance"] or 0)
        next_cash = current_cash + cash_delta if cleaned_type == "deposit" else current_cash - cash_delta
        if next_cash < -0.000001:
            raise ValueError("현금이 부족합니다.")

        connection.execute(
            "UPDATE accounts SET cash_balance = ?, updated_at = ? WHERE id = ?",
            (next_cash, timestamp, account_id),
        )
        connection.execute(
            """
            INSERT INTO trade_logs (
                account_id, symbol, product_name, trade_type, asset_type,
                quantity, price, total_amount, trade_date, notes, created_at
            )
            VALUES (?, '', ?, ?, 'cash', 1, ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                "Cash Deposit" if cleaned_type == "deposit" else "Cash Withdraw",
                cleaned_type,
                cash_delta,
                cash_delta,
                str(trade_date),
                str(notes or "").strip(),
                timestamp,
            ),
        )
        connection.commit()

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4


ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("RETIREMENT_DB_PATH", ROOT_DIR / "data" / "portfolio.db"))

BUY_SELL_TRADE_TYPES = {"buy", "sell"}
LEGACY_CASH_FLOW_TYPE_MAP = {
    "deposit": "personal_deposit",
    "withdraw": "withdraw",
}
CASH_EVENT_LABELS = {
    "personal_deposit": "개인 입금",
    "employer_deposit": "회사 납입금",
    "withdraw": "일반 출금",
    "interest": "일별 이자",
    "transfer_out": "계좌 이체 출금",
    "transfer_in": "계좌 이체 입금",
    "cash_adjustment": "현금 조정",
}
CASH_EVENT_TYPES = set(CASH_EVENT_LABELS)
EXPORTABLE_TABLES = {"accounts", "holdings", "trade_logs", "daily_account_snapshot"}


def now_iso() -> str:
    """현재 UTC 시각을 ISO 문자열로 반환한다."""

    return datetime.utcnow().replace(microsecond=0).isoformat()


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """SQLite 연결을 열고 작업이 끝나면 자동으로 닫는다."""

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()


def _normalize_cash_flow_type(flow_type: str) -> str:
    normalized = str(flow_type or "").strip().lower()
    return LEGACY_CASH_FLOW_TYPE_MAP.get(normalized, normalized)


def _cash_event_label(trade_type: str) -> str:
    normalized = _normalize_cash_flow_type(trade_type)
    return CASH_EVENT_LABELS.get(normalized, normalized)


def _metadata_json(metadata: dict[str, Any] | None = None) -> str:
    if not metadata:
        return "{}"
    return json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))


def _column_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row["name"]) for row in rows}


def _ensure_trade_log_columns(connection: sqlite3.Connection) -> None:
    columns = _column_names(connection, "trade_logs")
    if "cash_delta" not in columns:
        connection.execute("ALTER TABLE trade_logs ADD COLUMN cash_delta REAL NOT NULL DEFAULT 0")
    if "event_group_id" not in columns:
        connection.execute("ALTER TABLE trade_logs ADD COLUMN event_group_id TEXT")
    if "counterparty_account_id" not in columns:
        connection.execute("ALTER TABLE trade_logs ADD COLUMN counterparty_account_id INTEGER")
    if "metadata_json" not in columns:
        connection.execute("ALTER TABLE trade_logs ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'")


def _migrate_trade_logs(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        UPDATE trade_logs
        SET trade_type = 'personal_deposit'
        WHERE trade_type = 'deposit'
        """
    )
    connection.execute(
        """
        UPDATE trade_logs
        SET metadata_json = '{}'
        WHERE COALESCE(metadata_json, '') = ''
        """
    )
    connection.execute(
        """
        UPDATE trade_logs
        SET asset_type = 'cash',
            quantity = 0,
            price = 0,
            product_name = CASE
                WHEN trade_type = 'personal_deposit' AND COALESCE(product_name, '') IN ('', '현금 입금', '현금 흐름') THEN '개인 입금'
                WHEN trade_type = 'withdraw' AND COALESCE(product_name, '') IN ('', '현금 출금', '현금 흐름') THEN '일반 출금'
                WHEN trade_type = 'interest' AND COALESCE(product_name, '') = '' THEN '일별 이자'
                WHEN trade_type = 'transfer_out' AND COALESCE(product_name, '') = '' THEN '계좌 이체 출금'
                WHEN trade_type = 'transfer_in' AND COALESCE(product_name, '') = '' THEN '계좌 이체 입금'
                WHEN trade_type = 'cash_adjustment' AND COALESCE(product_name, '') = '' THEN '현금 조정'
                WHEN trade_type = 'employer_deposit' AND COALESCE(product_name, '') = '' THEN '회사 납입금'
                ELSE product_name
            END
        WHERE trade_type IN ('personal_deposit', 'employer_deposit', 'withdraw', 'interest', 'transfer_out', 'transfer_in', 'cash_adjustment')
        """
    )
    connection.execute(
        """
        UPDATE trade_logs
        SET cash_delta = CASE
            WHEN trade_type = 'buy' THEN -ABS(total_amount)
            WHEN trade_type = 'sell' THEN ABS(total_amount)
            WHEN trade_type IN ('personal_deposit', 'employer_deposit', 'interest', 'transfer_in') THEN ABS(total_amount)
            WHEN trade_type IN ('withdraw', 'transfer_out') THEN -ABS(total_amount)
            ELSE COALESCE(cash_delta, 0)
        END
        WHERE trade_type IN ('buy', 'sell', 'personal_deposit', 'employer_deposit', 'withdraw', 'interest', 'transfer_out', 'transfer_in')
        """
    )


def _ensure_daily_interest_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_interest (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            interest_amount REAL NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(account_id, date),
            FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_daily_interest_account_date
        ON daily_interest(account_id, date)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_trade_logs_event_group_id
        ON trade_logs(event_group_id)
        """
    )


def _ensure_daily_account_snapshot_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_account_snapshot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            snapshot_date TEXT NOT NULL,
            cash_balance REAL NOT NULL,
            market_value REAL NOT NULL,
            total_value REAL NOT NULL,
            total_cost REAL NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(account_id, snapshot_date),
            FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_daily_account_snapshot_account_date
        ON daily_account_snapshot(account_id, snapshot_date)
        """
    )


def _ensure_realtime_price_ticks_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS realtime_price_ticks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            holding_id INTEGER,
            symbol TEXT NOT NULL,
            price REAL NOT NULL,
            previous_close REAL,
            day_change_rate REAL,
            currency TEXT NOT NULL DEFAULT 'KRW',
            quote_time TEXT NOT NULL,
            ingested_at TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'KIS WebSocket',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE,
            FOREIGN KEY(holding_id) REFERENCES holdings(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_realtime_price_ticks_account_quote_time
        ON realtime_price_ticks(account_id, quote_time DESC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_realtime_price_ticks_symbol_quote_time
        ON realtime_price_ticks(symbol, quote_time DESC)
        """
    )


def _ensure_realtime_worker_status_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS realtime_worker_status (
            account_id INTEGER PRIMARY KEY,
            worker_name TEXT NOT NULL,
            connection_state TEXT NOT NULL,
            last_seen_at TEXT,
            last_quote_at TEXT,
            updated_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
        """
    )


def initialize_database() -> None:
    """로컬 SQLite 스키마를 생성하고 필요한 마이그레이션을 적용한다."""

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
                cash_delta REAL NOT NULL DEFAULT 0,
                event_group_id TEXT,
                counterparty_account_id INTEGER,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                trade_date TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                FOREIGN KEY(counterparty_account_id) REFERENCES accounts(id) ON DELETE SET NULL
            );
            """
        )
        _ensure_trade_log_columns(connection)
        _ensure_daily_interest_table(connection)
        _ensure_daily_account_snapshot_table(connection)
        _ensure_realtime_price_ticks_table(connection)
        _ensure_realtime_worker_status_table(connection)
        _migrate_trade_logs(connection)
        # 자동 배포 검사용 빈 계좌는 남길 필요가 없다.
        connection.execute(
            """
            DELETE FROM accounts
            WHERE name LIKE 'Auto Test %'
              AND id NOT IN (SELECT account_id FROM holdings)
              AND id NOT IN (SELECT account_id FROM trade_logs)
              AND id NOT IN (SELECT account_id FROM daily_interest)
              AND id NOT IN (SELECT account_id FROM daily_account_snapshot)
              AND id NOT IN (SELECT account_id FROM realtime_price_ticks)
              AND id NOT IN (SELECT account_id FROM realtime_worker_status)
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


def _require_account(connection: sqlite3.Connection, account_id: int) -> sqlite3.Row:
    account_row = connection.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if not account_row:
        raise ValueError("계좌를 찾을 수 없습니다.")
    return account_row


def _update_account_cash_balance(
    connection: sqlite3.Connection,
    account_id: int,
    amount: float,
    timestamp: str,
) -> None:
    connection.execute(
        "UPDATE accounts SET cash_balance = ?, updated_at = ? WHERE id = ?",
        (float(amount), timestamp, account_id),
    )


def _insert_trade_log(
    connection: sqlite3.Connection,
    *,
    account_id: int,
    symbol: str,
    product_name: str,
    trade_type: str,
    asset_type: str,
    quantity: float,
    price: float,
    total_amount: float,
    cash_delta: float,
    trade_date: str,
    notes: str,
    created_at: str,
    event_group_id: str | None = None,
    counterparty_account_id: int | None = None,
    metadata_json: str = "{}",
) -> None:
    connection.execute(
        """
        INSERT INTO trade_logs (
            account_id, symbol, product_name, trade_type, asset_type,
            quantity, price, total_amount, cash_delta, event_group_id,
            counterparty_account_id, metadata_json, trade_date, notes, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            account_id,
            symbol,
            product_name,
            trade_type,
            asset_type,
            quantity,
            price,
            total_amount,
            cash_delta,
            event_group_id,
            counterparty_account_id,
            metadata_json,
            str(trade_date),
            str(notes or "").strip(),
            created_at,
        ),
    )


def list_accounts() -> list[dict[str, Any]]:
    """모든 계좌를 이름순으로 반환한다."""

    return _fetch_all("SELECT * FROM accounts ORDER BY name COLLATE NOCASE ASC")


def get_account(account_id: int) -> dict[str, Any] | None:
    """계좌 ID로 단일 계좌를 조회한다."""

    return _fetch_one("SELECT * FROM accounts WHERE id = ?", (account_id,))


def create_account(name: str, account_type: str = "retirement", opening_cash: float = 0) -> int:
    """새 계좌를 생성하고 계좌 ID를 반환한다."""

    cleaned_name = str(name or "").strip()
    if not cleaned_name:
        raise ValueError("계좌 이름을 입력해 주세요.")

    cleaned_type = str(account_type or "retirement").strip().lower()
    if cleaned_type not in {"retirement", "brokerage"}:
        raise ValueError("계좌 유형 값이 올바르지 않습니다.")

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
    """계좌의 현금 잔액을 직접 수정한다."""

    if float(amount) < 0:
        raise ValueError("현금은 0 이상이어야 합니다.")

    with connect() as connection:
        _require_account(connection, account_id)
        _update_account_cash_balance(connection, account_id, float(amount), now_iso())
        connection.commit()


def list_holdings(account_id: int, include_closed: bool = False) -> list[dict[str, Any]]:
    """계좌의 보유 종목을 평가금액 순으로 반환한다."""

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
    """보유 종목의 현재가와 갱신 시각을 저장한다."""

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


def record_realtime_price_tick(
    *,
    account_id: int,
    holding_id: int | None,
    symbol: str,
    price: float,
    previous_close: float | None = None,
    day_change_rate: float | None = None,
    currency: str = "KRW",
    quote_time: str | None = None,
    source: str = "KIS WebSocket",
    metadata_json: dict[str, Any] | None = None,
) -> None:
    """최신가를 holdings에 반영하고 실시간 tick 이력을 적재한다."""

    timestamp = str(quote_time or now_iso())
    with connect() as connection:
        _require_account(connection, account_id)
        if holding_id is not None:
            connection.execute(
                """
                UPDATE holdings
                SET current_price = ?, price_updated_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (float(price), timestamp, now_iso(), holding_id),
            )
        connection.execute(
            """
            INSERT INTO realtime_price_ticks (
                account_id, holding_id, symbol, price, previous_close, day_change_rate,
                currency, quote_time, ingested_at, source, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                holding_id,
                str(symbol or "").strip().upper(),
                float(price),
                float(previous_close) if previous_close is not None else None,
                float(day_change_rate) if day_change_rate is not None else None,
                str(currency or "KRW").strip().upper() or "KRW",
                timestamp,
                now_iso(),
                str(source or "KIS WebSocket").strip() or "KIS WebSocket",
                _metadata_json(metadata_json),
            ),
        )
        connection.commit()


def list_realtime_price_ticks(account_id: int, *, limit: int = 200) -> list[dict[str, Any]]:
    """계좌별 실시간 tick 이력을 최신순으로 반환한다."""

    return _fetch_all(
        """
        SELECT *
        FROM realtime_price_ticks
        WHERE account_id = ?
        ORDER BY quote_time DESC, id DESC
        LIMIT ?
        """,
        (account_id, int(limit)),
    )


def upsert_realtime_worker_status(
    *,
    account_id: int,
    worker_name: str,
    connection_state: str,
    last_seen_at: str | None = None,
    last_quote_at: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> None:
    """계좌별 실시간 worker 상태를 저장하거나 갱신한다."""

    timestamp = now_iso()
    with connect() as connection:
        _require_account(connection, account_id)
        connection.execute(
            """
            INSERT INTO realtime_worker_status (
                account_id, worker_name, connection_state, last_seen_at,
                last_quote_at, updated_at, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_id) DO UPDATE SET
                worker_name = excluded.worker_name,
                connection_state = excluded.connection_state,
                last_seen_at = excluded.last_seen_at,
                last_quote_at = excluded.last_quote_at,
                updated_at = excluded.updated_at,
                metadata_json = excluded.metadata_json
            """,
            (
                account_id,
                str(worker_name or "").strip() or "kis-quote-worker",
                str(connection_state or "").strip() or "unknown",
                str(last_seen_at or "").strip() or None,
                str(last_quote_at or "").strip() or None,
                timestamp,
                _metadata_json(metadata_json),
            ),
        )
        connection.commit()


def get_realtime_worker_status(account_id: int) -> dict[str, Any] | None:
    """계좌별 실시간 worker 상태를 반환한다."""

    return _fetch_one("SELECT * FROM realtime_worker_status WHERE account_id = ?", (account_id,))


def latest_realtime_quote_time(account_id: int) -> str:
    """계좌별 가장 최근 실시간 quote 반영 시각을 반환한다."""

    row = _fetch_one(
        """
        SELECT quote_time
        FROM realtime_price_ticks
        WHERE account_id = ?
        ORDER BY quote_time DESC, id DESC
        LIMIT 1
        """,
        (account_id,),
    )
    if row and row.get("quote_time"):
        return str(row["quote_time"])
    holding_row = _fetch_one(
        """
        SELECT MAX(price_updated_at) AS quote_time
        FROM holdings
        WHERE account_id = ?
        """,
        (account_id,),
    )
    return str((holding_row or {}).get("quote_time") or "")


def list_trade_logs(account_id: int) -> list[dict[str, Any]]:
    """계좌의 거래 원장 이벤트를 최신순으로 반환한다."""

    return _fetch_all(
        """
        SELECT *
        FROM trade_logs
        WHERE account_id = ?
        ORDER BY trade_date DESC, id DESC
        """,
        (account_id,),
    )


def list_daily_interest(account_id: int) -> list[dict[str, Any]]:
    """계좌의 기존 일별 이자 기록을 날짜순으로 반환한다."""

    return _fetch_all(
        """
        SELECT *
        FROM daily_interest
        WHERE account_id = ?
        ORDER BY date ASC, id ASC
        """,
        (account_id,),
    )


def list_account_snapshots(account_id: int, start_date: str | None = None) -> list[dict[str, Any]]:
    """계좌의 일별 스냅샷을 조회한다."""

    if start_date:
        return _fetch_all(
            """
            SELECT *
            FROM daily_account_snapshot
            WHERE account_id = ?
              AND snapshot_date >= ?
            ORDER BY snapshot_date ASC, id ASC
            """,
            (account_id, str(start_date)),
        )
    return _fetch_all(
        """
        SELECT *
        FROM daily_account_snapshot
        WHERE account_id = ?
        ORDER BY snapshot_date ASC, id ASC
        """,
        (account_id,),
    )


def export_dataframe_rows(table_name: str) -> list[dict[str, Any]]:
    """내보내기 가능한 테이블의 전체 행을 반환한다."""

    if table_name not in EXPORTABLE_TABLES:
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
    """매수 또는 매도 거래를 저장하고 현금 잔액을 함께 갱신한다."""

    cleaned_symbol = str(symbol or "").strip().upper()
    cleaned_name = str(product_name or "").strip()
    cleaned_type = str(trade_type or "").strip().lower()
    cleaned_asset_type = str(asset_type or "risk").strip().lower()

    if cleaned_type not in BUY_SELL_TRADE_TYPES:
        raise ValueError("매수/매도 거래만 기록할 수 있습니다.")
    if cleaned_asset_type not in {"risk", "safe"}:
        raise ValueError("자산군 값이 올바르지 않습니다.")
    if not cleaned_symbol:
        raise ValueError("종목 코드를 입력해 주세요.")
    if not cleaned_name:
        raise ValueError("종목명을 입력해 주세요.")

    share_count = float(quantity or 0)
    trade_price = float(price or 0)
    if share_count <= 0 or trade_price <= 0:
        raise ValueError("수량과 단가는 모두 0보다 커야 합니다.")

    total_amount = share_count * trade_price
    cash_delta = -total_amount if cleaned_type == "buy" else total_amount
    timestamp = now_iso()

    with connect() as connection:
        account_row = _require_account(connection, account_id)
        holding_row = connection.execute(
            "SELECT * FROM holdings WHERE account_id = ? AND symbol = ?",
            (account_id, cleaned_symbol),
        ).fetchone()

        current_cash = float(account_row["cash_balance"] or 0)
        next_cash = current_cash + cash_delta
        if next_cash < -0.000001:
            raise ValueError("현금이 부족합니다. 현금 입금 후 다시 시도해 주세요.")

        if cleaned_type == "buy":
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

        _update_account_cash_balance(connection, account_id, next_cash, timestamp)
        _insert_trade_log(
            connection,
            account_id=account_id,
            symbol=cleaned_symbol,
            product_name=cleaned_name,
            trade_type=cleaned_type,
            asset_type=cleaned_asset_type,
            quantity=share_count,
            price=trade_price,
            total_amount=total_amount,
            cash_delta=cash_delta,
            trade_date=trade_date,
            notes=notes,
            created_at=timestamp,
            metadata_json=_metadata_json(),
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
    """현금 입금/출금 이벤트를 원장에 기록한다."""

    cleaned_type = _normalize_cash_flow_type(flow_type)
    if cleaned_type not in {"personal_deposit", "employer_deposit", "withdraw"}:
        raise ValueError("개인 입금, 회사 납입금, 일반 출금만 기록할 수 있습니다.")

    total_amount = float(amount or 0)
    if total_amount <= 0:
        raise ValueError("금액은 0보다 커야 합니다.")

    cash_delta = total_amount if cleaned_type in {"personal_deposit", "employer_deposit"} else -total_amount
    timestamp = now_iso()

    with connect() as connection:
        account_row = _require_account(connection, account_id)
        current_cash = float(account_row["cash_balance"] or 0)
        next_cash = current_cash + cash_delta
        if next_cash < -0.000001:
            raise ValueError("현금이 부족합니다.")

        _update_account_cash_balance(connection, account_id, next_cash, timestamp)
        _insert_trade_log(
            connection,
            account_id=account_id,
            symbol="",
            product_name=_cash_event_label(cleaned_type),
            trade_type=cleaned_type,
            asset_type="cash",
            quantity=0,
            price=0,
            total_amount=total_amount,
            cash_delta=cash_delta,
            trade_date=trade_date,
            notes=notes,
            created_at=timestamp,
            metadata_json=_metadata_json(),
        )
        connection.commit()


def adjust_cash_balance(
    account_id: int,
    *,
    target_amount: float,
    trade_date: str,
    notes: str,
) -> None:
    """목표 현금 잔액에 맞추도록 현금 조정 이벤트를 기록한다."""

    next_cash = float(target_amount or 0)
    if next_cash < 0:
        raise ValueError("현금 잔액은 0 이상이어야 합니다.")

    cleaned_notes = str(notes or "").strip()
    if not cleaned_notes:
        raise ValueError("현금 조정 사유를 입력해 주세요.")

    timestamp = now_iso()
    with connect() as connection:
        account_row = _require_account(connection, account_id)
        current_cash = float(account_row["cash_balance"] or 0)
        cash_delta = next_cash - current_cash
        if abs(cash_delta) <= 0.000001:
            raise ValueError("현재 현금과 동일해 조정할 내용이 없습니다.")

        _update_account_cash_balance(connection, account_id, next_cash, timestamp)
        _insert_trade_log(
            connection,
            account_id=account_id,
            symbol="",
            product_name=_cash_event_label("cash_adjustment"),
            trade_type="cash_adjustment",
            asset_type="cash",
            quantity=0,
            price=0,
            total_amount=abs(cash_delta),
            cash_delta=cash_delta,
            trade_date=trade_date,
            notes=cleaned_notes,
            created_at=timestamp,
            metadata_json=_metadata_json({"target_amount": round(next_cash, 4)}),
        )
        connection.commit()


def record_daily_interest(account_id: int, *, interest_date: str, amount: float) -> None:
    """이자 기능 제거 이후 호출을 차단한다."""

    raise RuntimeError("현금 이자 적립 기능은 제거되었습니다.")


def record_account_snapshot(
    account_id: int,
    *,
    snapshot_date: str,
    cash_balance: float,
    market_value: float,
    total_value: float,
    total_cost: float,
) -> None:
    """계좌의 일별 총자산 스냅샷을 저장한다."""

    timestamp = now_iso()
    with connect() as connection:
        _require_account(connection, account_id)
        connection.execute(
            """
            INSERT INTO daily_account_snapshot (
                account_id, snapshot_date, cash_balance, market_value, total_value, total_cost, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_id, snapshot_date) DO UPDATE SET
                cash_balance = excluded.cash_balance,
                market_value = excluded.market_value,
                total_value = excluded.total_value,
                total_cost = excluded.total_cost,
                updated_at = excluded.updated_at
            """,
            (
                account_id,
                str(snapshot_date),
                float(cash_balance or 0),
                float(market_value or 0),
                float(total_value or 0),
                float(total_cost or 0),
                timestamp,
                timestamp,
            ),
        )
        connection.commit()


def record_account_transfer(
    from_account_id: int,
    *,
    to_account_id: int,
    amount: float,
    trade_date: str,
    notes: str = "",
) -> None:
    """두 계좌 사이의 현금 이체를 출금/입금 2건으로 기록한다."""

    if int(from_account_id) == int(to_account_id):
        raise ValueError("같은 계좌로는 이체할 수 없습니다.")

    transfer_amount = float(amount or 0)
    if transfer_amount <= 0:
        raise ValueError("이체 금액은 0보다 커야 합니다.")

    timestamp = now_iso()
    group_id = str(uuid4())
    with connect() as connection:
        from_account = _require_account(connection, from_account_id)
        to_account = _require_account(connection, to_account_id)

        from_cash = float(from_account["cash_balance"] or 0)
        to_cash = float(to_account["cash_balance"] or 0)
        next_from_cash = from_cash - transfer_amount
        next_to_cash = to_cash + transfer_amount
        if next_from_cash < -0.000001:
            raise ValueError("이체할 현금이 부족합니다.")

        _update_account_cash_balance(connection, from_account_id, next_from_cash, timestamp)
        _update_account_cash_balance(connection, to_account_id, next_to_cash, timestamp)
        _insert_trade_log(
            connection,
            account_id=from_account_id,
            symbol="",
            product_name=_cash_event_label("transfer_out"),
            trade_type="transfer_out",
            asset_type="cash",
            quantity=0,
            price=0,
            total_amount=transfer_amount,
            cash_delta=-transfer_amount,
            trade_date=trade_date,
            notes=notes,
            created_at=timestamp,
            event_group_id=group_id,
            counterparty_account_id=to_account_id,
            metadata_json=_metadata_json(),
        )
        _insert_trade_log(
            connection,
            account_id=to_account_id,
            symbol="",
            product_name=_cash_event_label("transfer_in"),
            trade_type="transfer_in",
            asset_type="cash",
            quantity=0,
            price=0,
            total_amount=transfer_amount,
            cash_delta=transfer_amount,
            trade_date=trade_date,
            notes=notes,
            created_at=timestamp,
            event_group_id=group_id,
            counterparty_account_id=from_account_id,
            metadata_json=_metadata_json(),
        )
        connection.commit()

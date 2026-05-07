from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from supabase import create_client

from src import sqlite_db
from scripts.import_legacy_data import build_product_code_lookup, resolve_trade_symbol


DEFAULT_SOURCE_PATH = Path(r"C:\Users\JKKIM\retirement-portfolio\tmp_migration_source_data.json")
DEFAULT_SUPABASE_URL = "https://iyszkybxostbjfzbbymq.supabase.co"


def env_value(name: str, default: str = "") -> str:
    return str(os.getenv(name, default)).strip()


SUPABASE_URL = env_value("SUPABASE_URL", DEFAULT_SUPABASE_URL)
SUPABASE_KEY = env_value("SUPABASE_KEY")
SOURCE_PATH = Path(env_value("MIGRATION_SOURCE_PATH", str(DEFAULT_SOURCE_PATH)))

PASSWORD_MAP = {
    "jhonkim2025@gmail.com": env_value("JHONKIM_PASSWORD"),
    "sspd1013@naver.com": env_value("SSPD1013_PASSWORD"),
}
TARGET_EMAILS = {
    email.strip().lower()
    for email in env_value("SQLITE_SEED_EMAILS").split(",")
    if email.strip()
}


def require_config() -> None:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL is missing.")
    if not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_KEY is missing.")
    if not SOURCE_PATH.exists():
        raise RuntimeError(f"Migration source file not found: {SOURCE_PATH}")


def load_source_data() -> dict[str, Any]:
    data = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("Migration source file must contain a JSON object.")
    return data


def sign_in(email: str, password: str) -> dict[str, str]:
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    response = client.auth.sign_in_with_password({"email": email, "password": password})
    if not response.session or not response.user:
        raise RuntimeError(f"Sign-in did not return a session for {email}.")
    return {
        "user_id": response.user.id,
        "email": response.user.email,
    }


def clear_user_namespace(user_id: str) -> None:
    prefix = f"{user_id}::%"
    with sqlite_db.connect() as connection:
        connection.execute("DELETE FROM accounts WHERE name LIKE ?", (prefix,))
        connection.commit()


def insert_account(user_id: str, account: dict[str, Any]) -> int:
    profile = account["profile"]
    cash = account.get("cash") or {}
    created_at = str(profile.get("created_at") or cash.get("updated_at") or sqlite_db.now_iso())
    updated_at = str(cash.get("updated_at") or sqlite_db.now_iso())

    with sqlite_db.connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO accounts (name, account_type, cash_balance, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                f"{user_id}::{profile['account_name']}",
                str(profile.get("account_type") or "retirement"),
                float(cash.get("amount") or 0),
                created_at,
                updated_at,
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def insert_holding(account_id: int, product: dict[str, Any]) -> None:
    quantity = float(product.get("quantity") or 0)
    if quantity <= 0 or str(product.get("status") or "").strip().lower() != "holding":
        return

    created_at = str(product.get("created_at") or sqlite_db.now_iso())
    with sqlite_db.connect() as connection:
        connection.execute(
            """
            INSERT INTO holdings (
                account_id, symbol, product_name, asset_type, quantity, avg_cost,
                current_price, price_updated_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                str(product.get("product_code") or "").strip().upper(),
                str(product.get("product_name") or "").strip(),
                str(product.get("asset_type") or "risk").strip().lower(),
                quantity,
                float(product.get("purchase_price") or 0),
                float(product.get("current_price") or product.get("purchase_price") or 0),
                created_at,
                created_at,
                sqlite_db.now_iso(),
            ),
        )
        connection.commit()


def insert_trade_log(
    account_id: int,
    log: dict[str, Any],
    *,
    product_code_by_id: dict[int, str],
    product_code_by_name: dict[str, str],
) -> None:
    trade_type = str(log.get("trade_type") or "").strip().lower()
    if trade_type not in {"buy", "sell", "deposit", "withdraw"}:
        return

    symbol = resolve_trade_symbol(log, product_code_by_id, product_code_by_name)
    with sqlite_db.connect() as connection:
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
                symbol,
                str(log.get("product_name") or "").strip(),
                trade_type,
                str(log.get("asset_type") or "risk").strip().lower(),
                float(log.get("quantity") or 0),
                float(log.get("price") or 0),
                float(log.get("total_amount") or 0),
                str(log.get("trade_date") or "")[:10],
                str(log.get("notes") or "").strip(),
                str(log.get("created_at") or sqlite_db.now_iso()),
            ),
        )
        connection.commit()


def seed_user(user_data: dict[str, Any]) -> dict[str, Any]:
    user = user_data.get("user") or {}
    email = str(user.get("email") or "").strip().lower()
    password = PASSWORD_MAP.get(email)
    if not email or not password:
        raise RuntimeError(f"No SQLite seed credentials configured for {email or 'unknown user'}.")

    auth = sign_in(email, password)
    user_id = auth["user_id"]
    clear_user_namespace(user_id)

    summary_accounts: list[dict[str, Any]] = []
    for account in user_data.get("accounts") or []:
        account_id = insert_account(user_id, account)
        products = account.get("products") or []
        trade_logs = account.get("trade_logs") or []
        product_code_by_id, product_code_by_name = build_product_code_lookup(products)

        for product in products:
            insert_holding(account_id, product)
        for log in trade_logs:
            insert_trade_log(
                account_id,
                log,
                product_code_by_id=product_code_by_id,
                product_code_by_name=product_code_by_name,
            )

        summary_accounts.append(
            {
                "name": account["profile"]["account_name"],
                "holding_count": sum(
                    1
                    for product in products
                    if str(product.get("status") or "").strip().lower() == "holding"
                    and float(product.get("quantity") or 0) > 0
                ),
                "trade_log_count": len(trade_logs),
            }
        )

    return {
        "email": email,
        "user_id": user_id,
        "account_count": len(summary_accounts),
        "accounts": summary_accounts,
    }


def main() -> None:
    require_config()
    sqlite_db.initialize_database()
    source = load_source_data()
    results: dict[str, Any] = {}

    for legacy_name, user_data in source.items():
        email = str((user_data.get("user") or {}).get("email") or "").strip().lower()
        if TARGET_EMAILS and email not in TARGET_EMAILS:
            continue
        results[legacy_name] = seed_user(user_data)

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

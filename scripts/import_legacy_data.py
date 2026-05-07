from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from supabase import create_client


DEFAULT_SOURCE_PATH = Path(r"C:\Users\JKKIM\retirement-portfolio\tmp_migration_source_data.json")
DEFAULT_SUPABASE_URL = "https://iyszkybxostbjfzbbymq.supabase.co"
DEFAULT_PASSWORD = "854854"


def env_value(name: str, default: str = "") -> str:
    return str(os.getenv(name, default)).strip()


SUPABASE_URL = env_value("SUPABASE_URL", DEFAULT_SUPABASE_URL)
SUPABASE_KEY = env_value("SUPABASE_KEY")
SOURCE_PATH = Path(env_value("MIGRATION_SOURCE_PATH", str(DEFAULT_SOURCE_PATH)))


EMAIL_MAP = {
    "김정규": "jhonkim2025@gmail.com",
    "이상은": "sspd1013@naver.com",
}

PASSWORD_MAP = {
    "jhonkim2025@gmail.com": env_value("JHONKIM_PASSWORD", DEFAULT_PASSWORD),
    "sspd1013@naver.com": env_value("SSPD1013_PASSWORD", DEFAULT_PASSWORD),
}


def normalize_name(value: Any) -> str:
    return str(value or "").strip().casefold()


def build_product_code_lookup(products: list[dict[str, Any]]) -> tuple[dict[int, str], dict[str, str]]:
    by_id: dict[int, str] = {}
    by_name: dict[str, str] = {}

    for product in products:
        code = str(product.get("product_code") or "").strip().upper()
        if not code:
            continue

        product_id = product.get("id")
        if product_id is not None:
            try:
                by_id[int(product_id)] = code
            except (TypeError, ValueError):
                pass

        product_name = normalize_name(product.get("product_name"))
        if product_name and product_name not in by_name:
            by_name[product_name] = code

    return by_id, by_name


def resolve_trade_symbol(log: dict[str, Any], by_id: dict[int, str], by_name: dict[str, str]) -> str:
    explicit = str(log.get("symbol") or "").strip().upper()
    if explicit:
        return explicit

    product_id = log.get("product_id")
    if product_id is not None:
        try:
            code = by_id.get(int(product_id))
        except (TypeError, ValueError):
            code = None
        if code:
            return code

    product_name = normalize_name(log.get("product_name"))
    if product_name:
        code = by_name.get(product_name)
        if code:
            return code

    return ""


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


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


def resolve_email(legacy_name: str) -> str:
    if legacy_name in EMAIL_MAP:
        return EMAIL_MAP[legacy_name]
    raise RuntimeError(f"No email mapping configured for legacy user: {legacy_name}")


def sign_in(email: str, password: str) -> dict[str, Any]:
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    response = client.auth.sign_in_with_password({"email": email, "password": password})
    if not response.session or not response.user:
        raise RuntimeError(f"Sign-in did not return a session for {email}.")
    return {
        "access_token": response.session.access_token,
        "user_id": response.user.id,
        "email": response.user.email,
    }


def request_json(
    method: str,
    path: str,
    *,
    access_token: str,
    params: dict[str, Any] | None = None,
    json_data: dict[str, Any] | None = None,
    prefer_return: bool = True,
) -> Any:
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    if prefer_return:
        headers["Prefer"] = "return=representation"

    response = requests.request(
        method=method,
        url=urljoin(f"{SUPABASE_URL}/", path.lstrip("/")),
        headers=headers,
        params=params,
        json=json_data,
        timeout=20,
    )
    response.raise_for_status()
    if not response.text.strip():
        return None
    return response.json()


def get_account(access_token: str, stored_name: str) -> dict[str, Any] | None:
    rows = request_json(
        "GET",
        "/rest/v1/accounts",
        access_token=access_token,
        params={"name": f"eq.{stored_name}", "select": "*"},
    )
    if isinstance(rows, list) and rows:
        return rows[0]
    return None


def create_or_update_account(
    *,
    access_token: str,
    user_id: str,
    profile: dict[str, Any],
    cash_amount: float,
) -> dict[str, Any]:
    stored_name = f"{user_id}::{profile['account_name']}"
    payload = {
        "name": stored_name,
        "account_type": str(profile.get("account_type") or "retirement"),
        "cash_balance": float(cash_amount or 0),
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }

    existing = get_account(access_token, stored_name)
    if existing:
        updated = request_json(
            "PATCH",
            "/rest/v1/accounts",
            access_token=access_token,
            params={"id": f"eq.{existing['id']}"},
            json_data={
                "account_type": payload["account_type"],
                "cash_balance": payload["cash_balance"],
                "updated_at": payload["updated_at"],
            },
        )
        return updated[0] if isinstance(updated, list) and updated else existing

    created = request_json(
        "POST",
        "/rest/v1/accounts",
        access_token=access_token,
        json_data=payload,
    )
    if isinstance(created, list):
        return created[0]
    return created


def clear_account_children(access_token: str, account_id: int) -> None:
    request_json(
        "DELETE",
        "/rest/v1/holdings",
        access_token=access_token,
        params={"account_id": f"eq.{account_id}"},
        prefer_return=False,
    )
    request_json(
        "DELETE",
        "/rest/v1/trade_logs",
        access_token=access_token,
        params={"account_id": f"eq.{account_id}"},
        prefer_return=False,
    )


def insert_holding(access_token: str, account_id: int, product: dict[str, Any]) -> None:
    quantity = float(product.get("quantity") or 0)
    if quantity <= 0 or str(product.get("status") or "").lower() != "holding":
        return

    payload = {
        "account_id": int(account_id),
        "symbol": str(product.get("product_code") or "").strip().upper(),
        "product_name": str(product.get("product_name") or "").strip(),
        "asset_type": str(product.get("asset_type") or "risk").strip().lower(),
        "quantity": quantity,
        "avg_cost": float(product.get("purchase_price") or 0),
        "current_price": float(product.get("current_price") or product.get("purchase_price") or 0),
        "price_updated_at": str(product.get("created_at") or now_iso()),
        "created_at": str(product.get("created_at") or now_iso()),
        "updated_at": now_iso(),
    }
    request_json("POST", "/rest/v1/holdings", access_token=access_token, json_data=payload)


def insert_trade_log(
    access_token: str,
    account_id: int,
    log: dict[str, Any],
    *,
    product_code_by_id: dict[int, str],
    product_code_by_name: dict[str, str],
) -> None:
    trade_type = str(log.get("trade_type") or "").strip().lower()
    if trade_type not in {"buy", "sell", "deposit", "withdraw"}:
        return

    resolved_symbol = resolve_trade_symbol(log, product_code_by_id, product_code_by_name)

    payload = {
        "account_id": int(account_id),
        "symbol": resolved_symbol or None,
        "product_name": str(log.get("product_name") or "").strip(),
        "trade_type": trade_type,
        "asset_type": str(log.get("asset_type") or "risk").strip().lower(),
        "quantity": float(log.get("quantity") or 0),
        "price": float(log.get("price") or 0),
        "total_amount": float(log.get("total_amount") or 0),
        "trade_date": str(log.get("trade_date") or "")[:10],
        "notes": str(log.get("notes") or ""),
        "created_at": str(log.get("created_at") or now_iso()),
    }
    request_json("POST", "/rest/v1/trade_logs", access_token=access_token, json_data=payload)


def import_user(legacy_name: str, user_data: dict[str, Any]) -> dict[str, Any]:
    email = resolve_email(legacy_name)
    password = PASSWORD_MAP.get(email) or DEFAULT_PASSWORD
    auth = sign_in(email, password)
    access_token = auth["access_token"]
    user_id = auth["user_id"]

    accounts = user_data.get("accounts") or []
    imported_accounts: list[dict[str, Any]] = []

    for account in accounts:
        profile = account["profile"]
        cash = account.get("cash") or {}
        products = account.get("products") or []
        trade_logs = account.get("trade_logs") or []
        product_code_by_id, product_code_by_name = build_product_code_lookup(products)

        account_row = create_or_update_account(
            access_token=access_token,
            user_id=user_id,
            profile=profile,
            cash_amount=float(cash.get("amount") or 0),
        )
        account_id = int(account_row["id"])
        clear_account_children(access_token, account_id)

        for product in products:
            insert_holding(access_token, account_id, product)
        for log in trade_logs:
            insert_trade_log(
                access_token,
                account_id,
                log,
                product_code_by_id=product_code_by_id,
                product_code_by_name=product_code_by_name,
            )

        imported_accounts.append(
            {
                "name": profile["account_name"],
                "account_id": account_id,
                "cash_amount": float(cash.get("amount") or 0),
                "holding_count": sum(
                    1
                    for product in products
                    if str(product.get("status") or "").lower() == "holding"
                    and float(product.get("quantity") or 0) > 0
                ),
                "trade_log_count": len(trade_logs),
            }
        )

    return {
        "email": email,
        "user_id": user_id,
        "account_count": len(imported_accounts),
        "accounts": imported_accounts,
    }


def main() -> None:
    require_config()
    source = load_source_data()
    results: dict[str, Any] = {}
    failures: dict[str, str] = {}

    for legacy_name, user_data in source.items():
        try:
            results[legacy_name] = import_user(legacy_name, user_data)
        except Exception as exc:  # noqa: BLE001
            failures[legacy_name] = str(exc)

    print(json.dumps({"imported": results, "failed": failures}, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

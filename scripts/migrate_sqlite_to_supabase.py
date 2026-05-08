from __future__ import annotations

import argparse
import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urljoin

import requests
from supabase import create_client


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DB = ROOT_DIR / "data" / "portfolio.db"
DEFAULT_SUPABASE_URL = "https://iyszkybxostbjfzbbymq.supabase.co"
ACCOUNT_NAMESPACE_SEPARATOR = "::"
BUY_SELL_TRADE_TYPES = {"buy", "sell"}
POSITIVE_CASH_TYPES = {"personal_deposit", "employer_deposit", "interest", "transfer_in"}
NEGATIVE_CASH_TYPES = {"withdraw", "transfer_out"}
CASH_EVENT_NAME_MAP = {
    "personal_deposit": "개인 입금",
    "employer_deposit": "회사 납입금",
    "withdraw": "일반 출금",
    "interest": "일별 이자",
    "transfer_out": "계좌 이체 출금",
    "transfer_in": "계좌 이체 입금",
    "cash_adjustment": "현금 조정",
}
LEGACY_TRADE_TYPE_MAP = {
    "deposit": "personal_deposit",
    "withdraw": "withdraw",
}
LEGACY_EMPLOYER_DEPOSIT_NAMES = {"회사 현금입금", "회사 납입금"}


@dataclass
class AccountMigrationPlan:
    """계좌별 마이그레이션 예정 정보를 담는다."""

    source_account_id: int
    visible_name: str
    account_type: str
    cash_balance: float
    holding_count: int
    trade_log_count: int
    daily_interest_count: int
    snapshot_count: int


def env_value(name: str, default: str = "") -> str:
    """환경변수를 문자열로 읽는다."""

    return str(os.getenv(name, default)).strip()


def parse_args() -> argparse.Namespace:
    """명령행 인자를 해석한다."""

    parser = argparse.ArgumentParser(
        description="로컬 SQLite 포트폴리오 데이터를 Supabase 사용자 네임스페이스로 이관합니다. 기본값은 dry-run입니다."
    )
    parser.add_argument(
        "--source-db",
        default=env_value("MIGRATION_SOURCE_DB", str(DEFAULT_SOURCE_DB)),
        help="원본 SQLite 경로",
    )
    parser.add_argument(
        "--source-namespace",
        default=env_value("MIGRATION_SOURCE_NAMESPACE"),
        help="원본 계좌 이름의 사용자 네임스페이스. 비우면 DB에서 자동 추론합니다.",
    )
    parser.add_argument(
        "--target-email",
        default=env_value("MIGRATION_TARGET_EMAIL"),
        help="대상 Supabase 사용자 이메일. dry-run에서는 비워 둘 수 있습니다.",
    )
    parser.add_argument(
        "--password-env",
        default=env_value("MIGRATION_PASSWORD_ENV", "MIGRATION_TARGET_PASSWORD"),
        help="대상 사용자 비밀번호를 읽을 환경변수 이름",
    )
    parser.add_argument(
        "--supabase-url",
        default=env_value("SUPABASE_URL", DEFAULT_SUPABASE_URL),
        help="대상 Supabase URL",
    )
    parser.add_argument(
        "--supabase-key-env",
        default=env_value("MIGRATION_SUPABASE_KEY_ENV", "SUPABASE_KEY"),
        help="Supabase 공개 키를 읽을 환경변수 이름",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="실제 Supabase에 쓰기를 수행합니다. 지정하지 않으면 dry-run만 실행합니다.",
    )
    parser.add_argument(
        "--json-output",
        help="결과 JSON 저장 경로",
    )
    return parser.parse_args()


@contextmanager
def connect_sqlite(db_path: Path) -> Iterator[sqlite3.Connection]:
    """원본 SQLite에 연결한다."""

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def sqlite_table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    """지정한 테이블 존재 여부를 반환한다."""

    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return bool(row)


def sqlite_column_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    """SQLite 테이블의 컬럼 이름 집합을 반환한다."""

    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row["name"]) for row in rows}


def split_account_name(name: str) -> tuple[str, str]:
    """이름공간이 포함된 계좌명을 분리한다."""

    raw_name = str(name or "").strip()
    if ACCOUNT_NAMESPACE_SEPARATOR not in raw_name:
        return "", raw_name
    namespace, visible_name = raw_name.split(ACCOUNT_NAMESPACE_SEPARATOR, 1)
    return namespace.strip(), visible_name.strip()


def list_source_namespaces(connection: sqlite3.Connection) -> dict[str, int]:
    """원본 SQLite에 존재하는 계좌 네임스페이스별 개수를 반환한다."""

    namespace_counts: dict[str, int] = {}
    rows = connection.execute("SELECT name FROM accounts ORDER BY id").fetchall()
    for row in rows:
        namespace, _ = split_account_name(str(row["name"]))
        namespace_counts[namespace] = namespace_counts.get(namespace, 0) + 1
    return namespace_counts


def resolve_source_namespace(connection: sqlite3.Connection, requested: str) -> str:
    """이관할 원본 네임스페이스를 결정한다."""

    if requested:
        return requested

    namespace_counts = list_source_namespaces(connection)
    namespaces = [namespace for namespace in namespace_counts if namespace]
    if len(namespaces) == 1:
        return namespaces[0]
    if not namespaces:
        raise RuntimeError("계좌 네임스페이스를 찾지 못했습니다. 원본 DB가 비어 있거나 이름 형식이 다릅니다.")
    raise RuntimeError(
        "여러 네임스페이스가 감지되었습니다. --source-namespace 로 대상 네임스페이스를 지정해 주세요: "
        + ", ".join(sorted(namespaces))
    )


def load_table_rows(
    connection: sqlite3.Connection,
    table_name: str,
    *,
    account_id: int,
    order_by: str = "id",
) -> list[dict[str, Any]]:
    """계좌 기준 자식 테이블 행을 읽는다."""

    if not sqlite_table_exists(connection, table_name):
        return []
    rows = connection.execute(
        f"SELECT * FROM {table_name} WHERE account_id = ? ORDER BY {order_by}",
        (account_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def normalize_trade_type(value: Any) -> str:
    """구/신 스키마의 거래 유형을 현재 스키마 기준으로 정규화한다."""

    normalized = str(value or "").strip().lower()
    return LEGACY_TRADE_TYPE_MAP.get(normalized, normalized)


def normalize_trade_type_with_context(row: dict[str, Any]) -> str:
    """레거시 상품명 힌트까지 반영해 거래 유형을 정규화한다."""

    normalized = normalize_trade_type(row.get("trade_type"))
    product_name = str(row.get("product_name") or "").strip()
    if normalized == "personal_deposit" and product_name in LEGACY_EMPLOYER_DEPOSIT_NAMES:
        return "employer_deposit"
    return normalized


def default_product_name(trade_type: str, current_name: str) -> str:
    """현금 이벤트일 때 비어 있는 상품명을 기본 한글 라벨로 채운다."""

    if current_name:
        return current_name
    return CASH_EVENT_NAME_MAP.get(trade_type, current_name)


def parse_metadata_json(value: Any) -> dict[str, Any]:
    """메타데이터 JSON을 dict로 정규화한다."""

    if isinstance(value, dict):
        return dict(value)
    text = str(value or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}
    if isinstance(payload, dict):
        return payload
    return {"raw": payload}


def compute_cash_delta(row: dict[str, Any], trade_type: str) -> float:
    """cash_delta 컬럼이 없거나 비어 있으면 거래 유형 기준으로 계산한다."""

    raw_cash_delta = row.get("cash_delta")
    if raw_cash_delta not in (None, ""):
        try:
            return float(raw_cash_delta)
        except (TypeError, ValueError):
            pass

    total_amount = float(row.get("total_amount") or 0)
    if trade_type == "buy":
        return -abs(total_amount)
    if trade_type == "sell":
        return abs(total_amount)
    if trade_type in POSITIVE_CASH_TYPES:
        return abs(total_amount)
    if trade_type in NEGATIVE_CASH_TYPES:
        return -abs(total_amount)
    return 0.0


def load_source_bundle(connection: sqlite3.Connection, namespace: str) -> dict[str, Any]:
    """원본 SQLite에서 대상 네임스페이스 데이터를 구조화해 읽는다."""

    accounts: list[dict[str, Any]] = []
    account_rows = connection.execute(
        "SELECT * FROM accounts WHERE name LIKE ? ORDER BY id",
        (f"{namespace}{ACCOUNT_NAMESPACE_SEPARATOR}%",),
    ).fetchall()

    trade_log_columns = sqlite_column_names(connection, "trade_logs") if sqlite_table_exists(connection, "trade_logs") else set()

    for account_row in account_rows:
        account_dict = dict(account_row)
        _, visible_name = split_account_name(str(account_dict["name"]))
        holdings = load_table_rows(connection, "holdings", account_id=int(account_dict["id"]))
        trade_logs = load_table_rows(connection, "trade_logs", account_id=int(account_dict["id"]), order_by="trade_date, id")
        daily_interest = load_table_rows(connection, "daily_interest", account_id=int(account_dict["id"]), order_by="date, id")
        snapshots = load_table_rows(
            connection,
            "daily_account_snapshot",
            account_id=int(account_dict["id"]),
            order_by="snapshot_date, id",
        )

        normalized_logs: list[dict[str, Any]] = []
        for log in trade_logs:
            trade_type = normalize_trade_type_with_context(log)
            product_name = default_product_name(trade_type, str(log.get("product_name") or "").strip())
            asset_type = str(log.get("asset_type") or "").strip().lower() or "risk"
            if trade_type not in BUY_SELL_TRADE_TYPES:
                asset_type = "cash"

            normalized_logs.append(
                {
                    "account_id": int(account_dict["id"]),
                    "symbol": str(log.get("symbol") or "").strip().upper() or None,
                    "product_name": product_name,
                    "trade_type": trade_type,
                    "asset_type": asset_type,
                    "quantity": float(log.get("quantity") or 0),
                    "price": float(log.get("price") or 0),
                    "total_amount": float(log.get("total_amount") or 0),
                    "cash_delta": compute_cash_delta(log, trade_type),
                    "event_group_id": str(log.get("event_group_id") or "").strip() or None,
                    "counterparty_account_id": int(log["counterparty_account_id"]) if log.get("counterparty_account_id") not in (None, "") else None,
                    "metadata_json": parse_metadata_json(log.get("metadata_json")) if "metadata_json" in trade_log_columns else {},
                    "trade_date": str(log.get("trade_date") or "")[:10],
                    "notes": str(log.get("notes") or "").strip(),
                    "created_at": str(log.get("created_at") or ""),
                }
            )

        accounts.append(
            {
                "source_account_id": int(account_dict["id"]),
                "source_stored_name": str(account_dict["name"]),
                "visible_name": visible_name,
                "account_type": str(account_dict.get("account_type") or "retirement"),
                "cash_balance": float(account_dict.get("cash_balance") or 0),
                "created_at": str(account_dict.get("created_at") or ""),
                "updated_at": str(account_dict.get("updated_at") or ""),
                "holdings": holdings,
                "trade_logs": normalized_logs,
                "daily_interest": daily_interest,
                "daily_account_snapshot": snapshots,
            }
        )

    plans = [
        AccountMigrationPlan(
            source_account_id=int(account["source_account_id"]),
            visible_name=str(account["visible_name"]),
            account_type=str(account["account_type"]),
            cash_balance=float(account["cash_balance"]),
            holding_count=len(account["holdings"]),
            trade_log_count=len(account["trade_logs"]),
            daily_interest_count=len(account["daily_interest"]),
            snapshot_count=len(account["daily_account_snapshot"]),
        )
        for account in accounts
    ]

    return {
        "source_namespace": namespace,
        "account_count": len(accounts),
        "accounts": accounts,
        "plan": [asdict(plan) for plan in plans],
        "summary": {
            "cash_balance_total": round(sum(float(account["cash_balance"]) for account in accounts), 2),
            "holding_count_total": sum(len(account["holdings"]) for account in accounts),
            "trade_log_count_total": sum(len(account["trade_logs"]) for account in accounts),
            "daily_interest_count_total": sum(len(account["daily_interest"]) for account in accounts),
            "snapshot_count_total": sum(len(account["daily_account_snapshot"]) for account in accounts),
        },
    }


def require_write_config(args: argparse.Namespace) -> tuple[str, str]:
    """실제 쓰기에 필요한 인증 정보를 확인한다."""

    if not args.target_email:
        raise RuntimeError("--write 사용 시 --target-email 또는 MIGRATION_TARGET_EMAIL 이 필요합니다.")

    password = env_value(args.password_env)
    if not password:
        raise RuntimeError(
            f"--write 사용 시 대상 사용자 비밀번호 환경변수 `{args.password_env}` 가 필요합니다."
        )

    supabase_key = env_value(args.supabase_key_env)
    if not supabase_key:
        raise RuntimeError(
            f"--write 사용 시 Supabase 키 환경변수 `{args.supabase_key_env}` 가 필요합니다."
        )
    return password, supabase_key


def sign_in_to_target(*, supabase_url: str, supabase_key: str, email: str, password: str) -> dict[str, str]:
    """대상 Supabase 사용자로 로그인해 액세스 토큰과 사용자 ID를 얻는다."""

    client = create_client(supabase_url, supabase_key)
    response = client.auth.sign_in_with_password({"email": email, "password": password})
    if not response.session or not response.user:
        raise RuntimeError(f"대상 사용자 로그인에 실패했습니다: {email}")
    return {
        "access_token": str(response.session.access_token),
        "user_id": str(response.user.id),
        "email": str(response.user.email or email),
    }


def request_json(
    *,
    method: str,
    supabase_url: str,
    supabase_key: str,
    access_token: str,
    path: str,
    params: dict[str, Any] | None = None,
    json_data: dict[str, Any] | None = None,
    prefer_return: bool = True,
) -> Any:
    """Supabase REST API로 요청을 보낸다."""

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    if prefer_return:
        headers["Prefer"] = "return=representation"

    response = requests.request(
        method=method,
        url=urljoin(f"{supabase_url}/", path.lstrip("/")),
        headers=headers,
        params=params,
        json=json_data,
        timeout=20,
    )
    response.raise_for_status()
    if not response.text.strip():
        return None
    return response.json()


def get_remote_account(*, supabase_url: str, supabase_key: str, access_token: str, stored_name: str) -> dict[str, Any] | None:
    """대상 사용자 네임스페이스에 이미 존재하는 계좌를 조회한다."""

    rows = request_json(
        method="GET",
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        access_token=access_token,
        path="/rest/v1/accounts",
        params={"name": f"eq.{stored_name}", "select": "*"},
    )
    if isinstance(rows, list) and rows:
        return rows[0]
    return None


def create_or_update_remote_account(
    *,
    supabase_url: str,
    supabase_key: str,
    access_token: str,
    user_id: str,
    account: dict[str, Any],
) -> dict[str, Any]:
    """대상 Supabase에 계좌를 만들거나 갱신한다."""

    stored_name = f"{user_id}{ACCOUNT_NAMESPACE_SEPARATOR}{account['visible_name']}"
    payload = {
        "name": stored_name,
        "account_type": str(account["account_type"]),
        "cash_balance": float(account["cash_balance"]),
        "created_at": str(account["created_at"] or ""),
        "updated_at": str(account["updated_at"] or ""),
    }

    existing = get_remote_account(
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        access_token=access_token,
        stored_name=stored_name,
    )
    if existing:
        updated = request_json(
            method="PATCH",
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            access_token=access_token,
            path="/rest/v1/accounts",
            params={"id": f"eq.{existing['id']}"},
            json_data={
                "account_type": payload["account_type"],
                "cash_balance": payload["cash_balance"],
                "updated_at": payload["updated_at"],
            },
        )
        return updated[0] if isinstance(updated, list) and updated else existing

    created = request_json(
        method="POST",
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        access_token=access_token,
        path="/rest/v1/accounts",
        json_data=payload,
    )
    if isinstance(created, list):
        return created[0]
    return created


def clear_remote_account_children(
    *,
    supabase_url: str,
    supabase_key: str,
    access_token: str,
    account_id: int,
) -> None:
    """대상 계좌의 자식 테이블을 비워 재이관에 대비한다."""

    for table_name in ("holdings", "trade_logs", "daily_interest", "daily_account_snapshot"):
        request_json(
            method="DELETE",
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            access_token=access_token,
            path=f"/rest/v1/{table_name}",
            params={"account_id": f"eq.{account_id}"},
            prefer_return=False,
        )


def insert_remote_row(
    *,
    supabase_url: str,
    supabase_key: str,
    access_token: str,
    table_name: str,
    payload: dict[str, Any],
) -> None:
    """지정한 Supabase 테이블에 단일 행을 추가한다."""

    request_json(
        method="POST",
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        access_token=access_token,
        path=f"/rest/v1/{table_name}",
        json_data=payload,
    )


def migrate_accounts(
    *,
    supabase_url: str,
    supabase_key: str,
    access_token: str,
    user_id: str,
    bundle: dict[str, Any],
) -> dict[str, Any]:
    """원본 번들을 대상 Supabase 계정으로 실제 이관한다."""

    account_id_map: dict[int, int] = {}
    remote_accounts: list[dict[str, Any]] = []

    # 계좌 ID 매핑을 먼저 확보해야 이체 상대 계좌를 정확히 연결할 수 있다.
    for account in bundle["accounts"]:
        remote_account = create_or_update_remote_account(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            access_token=access_token,
            user_id=user_id,
            account=account,
        )
        remote_account_id = int(remote_account["id"])
        account_id_map[int(account["source_account_id"])] = remote_account_id
        remote_accounts.append(
            {
                "visible_name": account["visible_name"],
                "source_account_id": int(account["source_account_id"]),
                "target_account_id": remote_account_id,
            }
        )

    for target_account_id in account_id_map.values():
        clear_remote_account_children(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            access_token=access_token,
            account_id=target_account_id,
        )

    inserted_counts = {
        "accounts": len(account_id_map),
        "holdings": 0,
        "trade_logs": 0,
        "daily_interest": 0,
        "daily_account_snapshot": 0,
    }

    for account in bundle["accounts"]:
        target_account_id = account_id_map[int(account["source_account_id"])]

        for holding in account["holdings"]:
            symbol = str(holding.get("symbol") or "").strip().upper()
            if not symbol:
                continue
            insert_remote_row(
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                access_token=access_token,
                table_name="holdings",
                payload={
                    "account_id": target_account_id,
                    "symbol": symbol,
                    "product_name": str(holding.get("product_name") or "").strip(),
                    "asset_type": str(holding.get("asset_type") or "risk").strip().lower(),
                    "quantity": float(holding.get("quantity") or 0),
                    "avg_cost": float(holding.get("avg_cost") or 0),
                    "current_price": float(holding.get("current_price") or 0),
                    "price_updated_at": str(holding.get("price_updated_at") or ""),
                    "created_at": str(holding.get("created_at") or ""),
                    "updated_at": str(holding.get("updated_at") or ""),
                },
            )
            inserted_counts["holdings"] += 1

        for entry in account["daily_interest"]:
            insert_remote_row(
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                access_token=access_token,
                table_name="daily_interest",
                payload={
                    "account_id": target_account_id,
                    "date": str(entry.get("date") or "")[:10],
                    "interest_amount": float(entry.get("interest_amount") or 0),
                    "created_at": str(entry.get("created_at") or ""),
                },
            )
            inserted_counts["daily_interest"] += 1

        for snapshot in account["daily_account_snapshot"]:
            insert_remote_row(
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                access_token=access_token,
                table_name="daily_account_snapshot",
                payload={
                    "account_id": target_account_id,
                    "snapshot_date": str(snapshot.get("snapshot_date") or "")[:10],
                    "cash_balance": float(snapshot.get("cash_balance") or 0),
                    "market_value": float(snapshot.get("market_value") or 0),
                    "total_value": float(snapshot.get("total_value") or 0),
                    "total_cost": float(snapshot.get("total_cost") or 0),
                    "created_at": str(snapshot.get("created_at") or ""),
                    "updated_at": str(snapshot.get("updated_at") or ""),
                },
            )
            inserted_counts["daily_account_snapshot"] += 1

    for account in bundle["accounts"]:
        target_account_id = account_id_map[int(account["source_account_id"])]
        for trade_log in account["trade_logs"]:
            counterparty_id = trade_log.get("counterparty_account_id")
            insert_remote_row(
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                access_token=access_token,
                table_name="trade_logs",
                payload={
                    "account_id": target_account_id,
                    "symbol": trade_log.get("symbol"),
                    "product_name": str(trade_log.get("product_name") or "").strip(),
                    "trade_type": str(trade_log.get("trade_type") or "").strip().lower(),
                    "asset_type": str(trade_log.get("asset_type") or "risk").strip().lower(),
                    "quantity": float(trade_log.get("quantity") or 0),
                    "price": float(trade_log.get("price") or 0),
                    "total_amount": float(trade_log.get("total_amount") or 0),
                    "cash_delta": float(trade_log.get("cash_delta") or 0),
                    "event_group_id": trade_log.get("event_group_id"),
                    "counterparty_account_id": account_id_map.get(int(counterparty_id)) if counterparty_id else None,
                    "metadata_json": trade_log.get("metadata_json") or {},
                    "trade_date": str(trade_log.get("trade_date") or "")[:10],
                    "notes": str(trade_log.get("notes") or "").strip(),
                    "created_at": str(trade_log.get("created_at") or ""),
                },
            )
            inserted_counts["trade_logs"] += 1

    return {
        "target_user_id": user_id,
        "target_accounts": remote_accounts,
        "inserted_counts": inserted_counts,
    }


def maybe_write_json(path_value: str | None, payload: dict[str, Any]) -> str | None:
    """경로가 주어지면 JSON 결과를 UTF-8로 저장한다."""

    if not path_value:
        return None
    output_path = Path(path_value).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(output_path)


def main() -> int:
    """스크립트 진입점."""

    args = parse_args()
    source_db = Path(args.source_db).expanduser().resolve()
    if not source_db.exists():
        raise SystemExit(f"원본 SQLite 파일을 찾지 못했습니다: {source_db}")

    with connect_sqlite(source_db) as connection:
        namespace = resolve_source_namespace(connection, str(args.source_namespace or "").strip())
        bundle = load_source_bundle(connection, namespace)

    result: dict[str, Any] = {
        "mode": "write" if args.write else "dry-run",
        "source_db": str(source_db),
        "source_namespace": bundle["source_namespace"],
        "target_email": args.target_email,
        "plan": bundle["plan"],
        "summary": bundle["summary"],
    }

    if args.write:
        password, supabase_key = require_write_config(args)
        auth = sign_in_to_target(
            supabase_url=args.supabase_url,
            supabase_key=supabase_key,
            email=args.target_email,
            password=password,
        )
        result["migration"] = migrate_accounts(
            supabase_url=args.supabase_url,
            supabase_key=supabase_key,
            access_token=auth["access_token"],
            user_id=auth["user_id"],
            bundle=bundle,
        )
    else:
        result["next_step"] = (
            "--write 없이 실행되어 실제 Supabase 쓰기는 수행하지 않았습니다. "
            "운영 쓰기 전에는 대상 사용자 비밀번호와 SUPABASE_KEY를 환경변수로 지정한 뒤 --write를 명시해야 합니다."
        )

    output_path = maybe_write_json(args.json_output, result)
    if output_path:
        result["json_output"] = output_path

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

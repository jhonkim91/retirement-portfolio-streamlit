from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src import sqlite_db  # noqa: E402


DEFAULT_SUPABASE_URL = "https://iyszkybxostbjfzbbymq.supabase.co"
DEFAULT_ROLLUP_TIMEZONE = "Asia/Seoul"
SERVICE_ROLE_ENV_NAMES = ("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_ADMIN_KEY")


@dataclass
class RollupResult:
    """계좌별 일별 롤업 처리 결과를 담는다."""

    account_id: int
    account_name: str
    interest_added: float
    cash_balance: float
    market_value: float
    total_value: float
    dry_run: bool = False


def now_iso() -> str:
    """현재 UTC 시각을 ISO 문자열로 반환한다."""

    return datetime.utcnow().replace(microsecond=0).isoformat()


def parse_args() -> argparse.Namespace:
    """명령행 인자를 해석한다."""

    parser = argparse.ArgumentParser(description="퇴직 포트폴리오의 일별 이자와 자산 스냅샷을 적립한다.")
    parser.add_argument("--date", dest="target_date", help="처리 기준일(YYYY-MM-DD). 기본값은 전일.")
    parser.add_argument("--annual-rate", dest="annual_rate", type=float, default=0.05, help="연이율. 기본값은 0.05")
    parser.add_argument(
        "--timezone",
        dest="rollup_timezone",
        default=str(os.getenv("ROLLUP_TIMEZONE", DEFAULT_ROLLUP_TIMEZONE)).strip() or DEFAULT_ROLLUP_TIMEZONE,
        help="기준 시간대. 기본값은 ROLLUP_TIMEZONE 또는 Asia/Seoul",
    )
    parser.add_argument(
        "--backend",
        choices=("auto", "sqlite", "supabase"),
        default="auto",
        help="실행 백엔드 선택. 기본값은 auto",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="쓰기 없이 읽기와 계산만 수행한다.",
    )
    return parser.parse_args()


def resolve_target_date(raw_value: str | None, timezone_name: str) -> date:
    """처리 기준일을 결정한다."""

    if raw_value:
        return date.fromisoformat(str(raw_value))
    return datetime.now(ZoneInfo(timezone_name)).date() - timedelta(days=1)


def compute_position_totals(holdings: list[dict[str, Any]]) -> tuple[float, float]:
    """보유 종목 목록에서 평가금액과 원가 합계를 계산한다."""

    market_value = 0.0
    total_cost = 0.0
    for holding in holdings:
        quantity = float(holding.get("quantity") or 0)
        avg_cost = float(holding.get("avg_cost") or 0)
        current_price = float(holding.get("current_price") or 0)
        market_value += quantity * current_price
        total_cost += quantity * avg_cost
    return round(market_value, 4), round(total_cost, 4)


def choose_backend(preferred: str) -> str:
    """실행 백엔드를 결정한다."""

    if preferred in {"sqlite", "supabase"}:
        return preferred
    if get_service_role_key():
        return "supabase"
    return "sqlite"


def get_supabase_url() -> str:
    """Supabase URL을 읽는다."""

    return str(os.getenv("SUPABASE_URL", DEFAULT_SUPABASE_URL)).strip()


def get_service_role_key() -> str:
    """Supabase 관리자 키를 읽는다."""

    for env_name in SERVICE_ROLE_ENV_NAMES:
        value = str(os.getenv(env_name, "")).strip()
        if value:
            return value
    return ""


class SupabaseAdminClient:
    """서비스 롤 키로 Supabase REST API를 호출하는 최소 클라이언트."""

    def __init__(self, url: str, service_role_key: str) -> None:
        if not url or not service_role_key:
            raise ValueError("Supabase 관리자 실행에는 SUPABASE_URL 과 SUPABASE_SERVICE_ROLE_KEY 가 필요합니다.")
        self.url = url.rstrip("/")
        self.service_role_key = service_role_key

    @property
    def headers(self) -> dict[str, str]:
        """Supabase REST 호출 헤더를 반환한다."""

        return {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def request(
        self,
        method: str,
        table: str,
        *,
        data: dict[str, Any] | None = None,
        filters: dict[str, str] | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any] | None:
        """Supabase REST API를 호출한다."""

        response = requests.request(
            method=method,
            url=f"{self.url}/rest/v1/{table}",
            json=data,
            params=filters or {},
            headers=self.headers,
            timeout=20,
        )
        response.raise_for_status()
        if method == "DELETE":
            return None
        payload = response.json()
        if method in {"POST", "PATCH"}:
            return payload[0] if isinstance(payload, list) and payload else payload
        return payload

    def list_accounts(self) -> list[dict[str, Any]]:
        """전체 계좌를 조회한다."""

        rows = self.request("GET", "accounts") or []
        return list(rows) if isinstance(rows, list) else []

    def list_holdings(self, account_id: int) -> list[dict[str, Any]]:
        """계좌의 보유 종목을 조회한다."""

        rows = self.request("GET", "holdings", filters={"account_id": f"eq.{account_id}"}) or []
        return list(rows) if isinstance(rows, list) else []

    def has_interest_for_date(self, account_id: int, target_date: str) -> bool:
        """해당 일자의 이자 기록 존재 여부를 확인한다."""

        rows = self.request(
            "GET",
            "daily_interest",
            filters={
                "account_id": f"eq.{account_id}",
                "date": f"eq.{target_date}",
            },
        ) or []
        return bool(rows)

    def update_account_cash(self, account_id: int, cash_balance: float) -> None:
        """계좌 현금 잔액을 갱신한다."""

        self.request(
            "PATCH",
            "accounts",
            data={"cash_balance": float(cash_balance), "updated_at": now_iso()},
            filters={"id": f"eq.{account_id}"},
        )

    def record_interest(self, account_id: int, target_date: str, amount: float) -> None:
        """일별 이자를 상세 테이블과 거래 원장에 함께 기록한다."""

        timestamp = now_iso()
        self.request(
            "POST",
            "daily_interest",
            data={
                "account_id": account_id,
                "date": target_date,
                "interest_amount": float(amount),
                "created_at": timestamp,
            },
        )
        self.request(
            "POST",
            "trade_logs",
            data={
                "account_id": account_id,
                "symbol": "",
                "product_name": "일별 이자",
                "trade_type": "interest",
                "asset_type": "cash",
                "quantity": 0,
                "price": 0,
                "total_amount": float(amount),
                "cash_delta": float(amount),
                "event_group_id": None,
                "counterparty_account_id": None,
                "metadata_json": {},
                "trade_date": target_date,
                "notes": "일별 이자 적립",
                "created_at": timestamp,
            },
        )

    def upsert_snapshot(
        self,
        account_id: int,
        *,
        snapshot_date: str,
        cash_balance: float,
        market_value: float,
        total_value: float,
        total_cost: float,
    ) -> None:
        """일별 계좌 스냅샷을 저장하거나 갱신한다."""

        timestamp = now_iso()
        existing = self.request(
            "GET",
            "daily_account_snapshot",
            filters={
                "account_id": f"eq.{account_id}",
                "snapshot_date": f"eq.{snapshot_date}",
            },
        ) or []
        payload = {
            "account_id": account_id,
            "snapshot_date": snapshot_date,
            "cash_balance": float(cash_balance),
            "market_value": float(market_value),
            "total_value": float(total_value),
            "total_cost": float(total_cost),
            "updated_at": timestamp,
        }
        if existing:
            snapshot_id = int(existing[0]["id"])
            self.request(
                "PATCH",
                "daily_account_snapshot",
                data=payload,
                filters={"id": f"eq.{snapshot_id}"},
            )
            return
        payload["created_at"] = timestamp
        self.request("POST", "daily_account_snapshot", data=payload)


def run_sqlite_rollup(target_date: date, annual_rate: float, dry_run: bool = False) -> list[RollupResult]:
    """SQLite 백엔드에 대해 일별 롤업을 수행한다."""

    sqlite_db.initialize_database()
    results: list[RollupResult] = []
    target_iso = target_date.isoformat()

    for account in sqlite_db.list_accounts():
        account_id = int(account["id"])
        account_name = str(account.get("name") or account_id)
        cash_balance = float(account.get("cash_balance") or 0)
        interest_added = 0.0
        interest_rows = sqlite_db.list_daily_interest(account_id)
        already_recorded = any(str(row.get("date")) == target_iso for row in interest_rows)

        if not already_recorded and cash_balance > 0 and annual_rate > 0:
            interest_added = round(cash_balance * annual_rate / 365, 4)
            if interest_added > 0:
                cash_balance += interest_added
                if not dry_run:
                    sqlite_db.record_daily_interest(account_id, interest_date=target_iso, amount=interest_added)

        holdings = sqlite_db.list_holdings(account_id, include_closed=True)
        market_value, total_cost = compute_position_totals(holdings)
        total_value = round(cash_balance + market_value, 4)
        if not dry_run:
            sqlite_db.record_account_snapshot(
                account_id,
                snapshot_date=target_iso,
                cash_balance=cash_balance,
                market_value=market_value,
                total_value=total_value,
                total_cost=total_cost,
            )
        results.append(
            RollupResult(
                account_id=account_id,
                account_name=account_name,
                interest_added=interest_added,
                cash_balance=round(cash_balance, 4),
                market_value=market_value,
                total_value=total_value,
                dry_run=dry_run,
            )
        )
    return results


def run_supabase_rollup(target_date: date, annual_rate: float, dry_run: bool = False) -> list[RollupResult]:
    """Supabase 관리자 모드에서 일별 롤업을 수행한다."""

    client = SupabaseAdminClient(get_supabase_url(), get_service_role_key())
    results: list[RollupResult] = []
    target_iso = target_date.isoformat()

    for account in client.list_accounts():
        account_id = int(account["id"])
        account_name = str(account.get("name") or account_id)
        cash_balance = float(account.get("cash_balance") or 0)
        interest_added = 0.0

        if not client.has_interest_for_date(account_id, target_iso) and cash_balance > 0 and annual_rate > 0:
            interest_added = round(cash_balance * annual_rate / 365, 4)
            if interest_added > 0:
                cash_balance += interest_added
                if not dry_run:
                    client.record_interest(account_id, target_iso, interest_added)
                    client.update_account_cash(account_id, cash_balance)

        holdings = client.list_holdings(account_id)
        market_value, total_cost = compute_position_totals(holdings)
        total_value = round(cash_balance + market_value, 4)
        if not dry_run:
            client.upsert_snapshot(
                account_id,
                snapshot_date=target_iso,
                cash_balance=cash_balance,
                market_value=market_value,
                total_value=total_value,
                total_cost=total_cost,
            )
        results.append(
            RollupResult(
                account_id=account_id,
                account_name=account_name,
                interest_added=interest_added,
                cash_balance=round(cash_balance, 4),
                market_value=market_value,
                total_value=total_value,
                dry_run=dry_run,
            )
        )
    return results


def print_results(results: list[RollupResult], target_date: date, backend: str, dry_run: bool) -> None:
    """처리 결과를 콘솔에 출력한다."""

    mode = "dry-run" if dry_run else "apply"
    print(f"[daily-rollup] mode={mode} backend={backend} date={target_date.isoformat()} accounts={len(results)}")
    for item in results:
        print(
            " | ".join(
                [
                    f"account_id={item.account_id}",
                    f"name={item.account_name}",
                    f"interest_added={item.interest_added:.4f}",
                    f"cash_balance={item.cash_balance:.4f}",
                    f"market_value={item.market_value:.4f}",
                    f"total_value={item.total_value:.4f}",
                ]
            )
        )


def main() -> None:
    """스크립트 진입점."""

    args = parse_args()
    target_date = resolve_target_date(args.target_date, args.rollup_timezone)
    backend = choose_backend(args.backend)
    dry_run = bool(args.dry_run)

    if backend == "supabase":
        results = run_supabase_rollup(target_date, args.annual_rate, dry_run=dry_run)
    else:
        results = run_sqlite_rollup(target_date, args.annual_rate, dry_run=dry_run)

    print_results(results, target_date, backend, dry_run)


if __name__ == "__main__":
    main()

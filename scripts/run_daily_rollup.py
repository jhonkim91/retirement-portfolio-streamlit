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
from src.valuation import (  # noqa: E402
    build_price_lookup_for_trade_logs,
    first_principal_deposit_date,
    rebuild_daily_valuation_snapshots,
)


DEFAULT_SUPABASE_URL = "https://iyszkybxostbjfzbbymq.supabase.co"
DEFAULT_ROLLUP_TIMEZONE = "Asia/Seoul"
SERVICE_ROLE_ENV_NAMES = ("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_ADMIN_KEY")


@dataclass
class RollupResult:
    """계좌별 스냅샷 처리 결과를 담는다."""

    account_id: int
    account_name: str
    cash_balance: float
    market_value: float
    total_value: float
    snapshot_updated: bool
    valuation_snapshot_count: int = 0
    dry_run: bool = False


def now_iso() -> str:
    """현재 UTC 시각을 ISO 문자열로 반환한다."""

    return datetime.utcnow().replace(microsecond=0).isoformat()


def parse_args() -> argparse.Namespace:
    """명령행 인자를 해석한다."""

    parser = argparse.ArgumentParser(description="퇴직 포트폴리오의 일별 자산 스냅샷을 저장한다.")
    parser.add_argument("--date", dest="target_date", help="처리 기준일(YYYY-MM-DD). 기본값은 전일.")
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

    def list_trade_logs(self, account_id: int) -> list[dict[str, Any]]:
        """계좌의 거래 원장을 조회한다."""

        rows = self.request("GET", "trade_logs", filters={"account_id": f"eq.{account_id}"}) or []
        logs = list(rows) if isinstance(rows, list) else []
        return sorted(logs, key=lambda row: (str(row.get("trade_date") or ""), int(row.get("id") or 0)))

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

    def delete_valuation_snapshots(self, account_id: int) -> None:
        """계좌의 기존 입금 기준 평가 스냅샷을 삭제한다."""

        self.request("DELETE", "daily_valuation_snapshot", filters={"account_id": f"eq.{account_id}"})

    def upsert_valuation_snapshots(self, account_id: int, snapshots: list[dict[str, Any]]) -> None:
        """입금 기준 평가 스냅샷을 batch upsert한다."""

        if not snapshots:
            return

        timestamp = now_iso()
        rows: list[dict[str, Any]] = []
        for snapshot in snapshots:
            row = dict(snapshot)
            row["account_id"] = account_id
            row["updated_at"] = timestamp
            row.setdefault("created_at", timestamp)
            rows.append(row)

        headers = dict(self.headers)
        headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
        response = requests.post(
            f"{self.url}/rest/v1/daily_valuation_snapshot",
            json=rows,
            params={"on_conflict": "account_id,valuation_date"},
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()


def rebuild_sqlite_valuation_snapshots(account: dict[str, Any], target_date: date, dry_run: bool = False) -> int:
    """SQLite 계좌의 입금 기준 평가 스냅샷을 재계산한다."""

    account_id = int(account["id"])
    trade_logs = sqlite_db.list_trade_logs(account_id)
    price_lookup = build_price_lookup_for_trade_logs(
        trade_logs,
        start_date=first_principal_deposit_date(trade_logs),
        end_date=target_date,
    )
    snapshots = rebuild_daily_valuation_snapshots(
        account=account,
        trade_logs=trade_logs,
        price_lookup=price_lookup,
        end_date=target_date,
        today_date=datetime.now(ZoneInfo(DEFAULT_ROLLUP_TIMEZONE)).date(),
        calculation_reason="daily_rollup",
    )
    if not dry_run:
        sqlite_db.delete_valuation_snapshots(account_id)
        if snapshots:
            sqlite_db.record_valuation_snapshots(account_id, snapshots)
    return len(snapshots)


def rebuild_supabase_valuation_snapshots(
    client: SupabaseAdminClient,
    account: dict[str, Any],
    target_date: date,
    dry_run: bool = False,
) -> int:
    """Supabase 계좌의 입금 기준 평가 스냅샷을 재계산한다."""

    account_id = int(account["id"])
    trade_logs = client.list_trade_logs(account_id)
    price_lookup = build_price_lookup_for_trade_logs(
        trade_logs,
        start_date=first_principal_deposit_date(trade_logs),
        end_date=target_date,
    )
    snapshots = rebuild_daily_valuation_snapshots(
        account=account,
        trade_logs=trade_logs,
        price_lookup=price_lookup,
        end_date=target_date,
        today_date=datetime.now(ZoneInfo(DEFAULT_ROLLUP_TIMEZONE)).date(),
        calculation_reason="daily_rollup",
    )
    if not dry_run:
        client.delete_valuation_snapshots(account_id)
        if snapshots:
            client.upsert_valuation_snapshots(account_id, snapshots)
    return len(snapshots)


def run_sqlite_rollup(target_date: date, dry_run: bool = False) -> list[RollupResult]:
    """SQLite 백엔드에 대해 일별 스냅샷 저장을 수행한다."""

    sqlite_db.initialize_database()
    results: list[RollupResult] = []
    target_iso = target_date.isoformat()

    for account in sqlite_db.list_accounts():
        account_id = int(account["id"])
        account_name = str(account.get("name") or account_id)
        cash_balance = float(account.get("cash_balance") or 0)
        holdings = sqlite_db.list_holdings(account_id, include_closed=True)
        market_value, total_cost = compute_position_totals(holdings)
        total_value = round(cash_balance + market_value, 4)
        snapshot_rows = sqlite_db.list_account_snapshots(account_id, start_date=target_iso)
        existing_snapshot = next(
            (
                row
                for row in snapshot_rows
                if str(row.get("snapshot_date") or "").strip() == target_iso
            ),
            None,
        )
        snapshot_updated = not (
            existing_snapshot
            and round(float(existing_snapshot.get("cash_balance") or 0), 4) == round(cash_balance, 4)
            and round(float(existing_snapshot.get("market_value") or 0), 4) == market_value
            and round(float(existing_snapshot.get("total_value") or 0), 4) == total_value
            and round(float(existing_snapshot.get("total_cost") or 0), 4) == total_cost
        )
        if snapshot_updated and not dry_run:
            sqlite_db.record_account_snapshot(
                account_id,
                snapshot_date=target_iso,
                cash_balance=cash_balance,
                market_value=market_value,
                total_value=total_value,
                total_cost=total_cost,
            )
        valuation_snapshot_count = rebuild_sqlite_valuation_snapshots(account, target_date, dry_run=dry_run)
        results.append(
            RollupResult(
                account_id=account_id,
                account_name=account_name,
                cash_balance=round(cash_balance, 4),
                market_value=market_value,
                total_value=total_value,
                snapshot_updated=snapshot_updated,
                valuation_snapshot_count=valuation_snapshot_count,
                dry_run=dry_run,
            )
        )
    return results


def run_supabase_rollup(target_date: date, dry_run: bool = False) -> list[RollupResult]:
    """Supabase 관리자 모드에서 일별 스냅샷 저장을 수행한다."""

    client = SupabaseAdminClient(get_supabase_url(), get_service_role_key())
    results: list[RollupResult] = []
    target_iso = target_date.isoformat()

    for account in client.list_accounts():
        account_id = int(account["id"])
        account_name = str(account.get("name") or account_id)
        cash_balance = float(account.get("cash_balance") or 0)
        holdings = client.list_holdings(account_id)
        market_value, total_cost = compute_position_totals(holdings)
        total_value = round(cash_balance + market_value, 4)
        existing = client.request(
            "GET",
            "daily_account_snapshot",
            filters={
                "account_id": f"eq.{account_id}",
                "snapshot_date": f"eq.{target_iso}",
            },
        ) or []
        existing_snapshot = existing[0] if existing else None
        snapshot_updated = not (
            existing_snapshot
            and round(float(existing_snapshot.get("cash_balance") or 0), 4) == round(cash_balance, 4)
            and round(float(existing_snapshot.get("market_value") or 0), 4) == market_value
            and round(float(existing_snapshot.get("total_value") or 0), 4) == total_value
            and round(float(existing_snapshot.get("total_cost") or 0), 4) == total_cost
        )
        if snapshot_updated and not dry_run:
            client.upsert_snapshot(
                account_id,
                snapshot_date=target_iso,
                cash_balance=cash_balance,
                market_value=market_value,
                total_value=total_value,
                total_cost=total_cost,
            )
        valuation_snapshot_count = rebuild_supabase_valuation_snapshots(client, account, target_date, dry_run=dry_run)
        results.append(
            RollupResult(
                account_id=account_id,
                account_name=account_name,
                cash_balance=round(cash_balance, 4),
                market_value=market_value,
                total_value=total_value,
                snapshot_updated=snapshot_updated,
                valuation_snapshot_count=valuation_snapshot_count,
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
                    f"cash_balance={item.cash_balance:.4f}",
                    f"market_value={item.market_value:.4f}",
                    f"total_value={item.total_value:.4f}",
                    f"snapshot_updated={'yes' if item.snapshot_updated else 'no'}",
                    f"valuation_snapshots={item.valuation_snapshot_count}",
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
        results = run_supabase_rollup(target_date, dry_run=dry_run)
    else:
        results = run_sqlite_rollup(target_date, dry_run=dry_run)

    print_results(results, target_date, backend, dry_run)


if __name__ == "__main__":
    main()

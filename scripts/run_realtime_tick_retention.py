from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import requests


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src import sqlite_db  # noqa: E402


DEFAULT_SUPABASE_URL = "https://iyszkybxostbjfzbbymq.supabase.co"
DEFAULT_RETENTION_TIMEZONE = "Asia/Seoul"
DEFAULT_RAW_RETENTION_DAYS = 7
DEFAULT_INTRADAY_RETENTION_DAYS = 90
DEFAULT_DAILY_RETENTION_DAYS = 0
SERVICE_ROLE_ENV_NAMES = ("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_ADMIN_KEY")
BAR_INTERVAL_SECONDS = {"1m": 60, "5m": 300, "1d": 86400}


@dataclass(frozen=True)
class RetentionPolicy:
    """실시간 tick 보존/집계 기준을 담는다."""

    raw_retention_days: int = DEFAULT_RAW_RETENTION_DAYS
    intraday_retention_days: int = DEFAULT_INTRADAY_RETENTION_DAYS
    daily_retention_days: int = DEFAULT_DAILY_RETENTION_DAYS
    timezone_name: str = DEFAULT_RETENTION_TIMEZONE
    intraday_intervals: tuple[str, ...] = ("1m", "5m")

    def validate(self) -> None:
        """정책값이 운영 가능한 범위인지 확인한다."""

        if self.raw_retention_days < 1:
            raise ValueError("raw_retention_days는 1 이상이어야 합니다.")
        if self.intraday_retention_days <= self.raw_retention_days:
            raise ValueError("intraday_retention_days는 raw_retention_days보다 커야 합니다.")
        if self.daily_retention_days < 0:
            raise ValueError("daily_retention_days는 0 이상이어야 합니다.")
        unknown_intervals = sorted(set(self.intraday_intervals) - set(BAR_INTERVAL_SECONDS))
        if unknown_intervals:
            raise ValueError(f"지원하지 않는 bar interval: {', '.join(unknown_intervals)}")
        ZoneInfo(self.timezone_name)


@dataclass
class RetentionSummary:
    """tick retention 실행 결과 요약."""

    backend: str
    dry_run: bool
    source_ticks: int = 0
    raw_ticks_to_delete: int = 0
    raw_ticks_deleted: int = 0
    stale_intraday_bars_to_delete: int = 0
    stale_intraday_bars_deleted: int = 0
    stale_daily_bars_to_delete: int = 0
    stale_daily_bars_deleted: int = 0
    bars_by_interval: dict[str, int] = field(default_factory=dict)

    def print(self) -> None:
        """CLI에서 읽기 쉬운 형태로 요약을 출력한다."""

        mode = "dry-run" if self.dry_run else "apply"
        print(f"[realtime-tick-retention] mode={mode} backend={self.backend}")
        print(f"[realtime-tick-retention] source_ticks={self.source_ticks:,}")
        for interval in sorted(self.bars_by_interval):
            print(f"[realtime-tick-retention] bars_{interval}={self.bars_by_interval[interval]:,}")
        print(
            "[realtime-tick-retention] "
            f"raw_ticks_deleted={self.raw_ticks_deleted:,}/{self.raw_ticks_to_delete:,}"
        )
        print(
            "[realtime-tick-retention] "
            f"stale_intraday_bars_deleted={self.stale_intraday_bars_deleted:,}/{self.stale_intraday_bars_to_delete:,}"
        )
        if self.stale_daily_bars_to_delete:
            print(
                "[realtime-tick-retention] "
                f"stale_daily_bars_deleted={self.stale_daily_bars_deleted:,}/{self.stale_daily_bars_to_delete:,}"
            )


def now_iso() -> str:
    """현재 UTC 시각을 ISO 문자열로 반환한다."""

    return datetime.utcnow().replace(microsecond=0).isoformat()


def parse_timestamp(value: Any, timezone_name: str) -> datetime:
    """tick 시각 문자열을 지정 시간대 기준 aware datetime으로 파싱한다."""

    raw_value = str(value or "").strip()
    if not raw_value:
        raise ValueError("비어 있는 timestamp는 파싱할 수 없습니다.")

    candidate = raw_value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(candidate)
    timezone = ZoneInfo(timezone_name)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone)
    return parsed.astimezone(timezone)


def naive_iso(value: datetime) -> str:
    """기존 quote_time 저장 형식과 맞춘 naive ISO 문자열을 반환한다."""

    return value.replace(tzinfo=None, microsecond=0).isoformat(timespec="seconds")


def bucket_start(value: datetime, interval: str) -> datetime:
    """시각을 interval bucket 시작 시각으로 내린다."""

    if interval == "1d":
        return value.replace(hour=0, minute=0, second=0, microsecond=0)

    interval_seconds = BAR_INTERVAL_SECONDS[interval]
    seconds_since_midnight = value.hour * 3600 + value.minute * 60 + value.second
    floored_seconds = seconds_since_midnight - (seconds_since_midnight % interval_seconds)
    return value.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(seconds=floored_seconds)


def normalize_tick(row: dict[str, Any], timezone_name: str) -> dict[str, Any]:
    """집계에 필요한 tick 필드를 정규화한다."""

    parsed_quote_time = parse_timestamp(row.get("quote_time"), timezone_name)
    return {
        "id": int(row.get("id") or 0),
        "account_id": int(row["account_id"]),
        "symbol": str(row.get("symbol") or "").strip().upper(),
        "price": float(row.get("price") or 0),
        "previous_close": row.get("previous_close"),
        "day_change_rate": row.get("day_change_rate"),
        "currency": str(row.get("currency") or "KRW").strip().upper() or "KRW",
        "quote_time": naive_iso(parsed_quote_time),
        "parsed_quote_time": parsed_quote_time,
    }


def aggregate_ticks(
    rows: Iterable[dict[str, Any]],
    *,
    intervals: Iterable[str],
    timezone_name: str,
) -> list[dict[str, Any]]:
    """tick 목록을 OHLC bar 목록으로 집계한다."""

    bars: dict[tuple[int, str, str, str], dict[str, Any]] = {}
    normalized_rows = sorted(
        (normalize_tick(row, timezone_name) for row in rows),
        key=lambda row: (row["account_id"], row["symbol"], row["parsed_quote_time"], row["id"]),
    )
    aggregated_at = now_iso()
    for row in normalized_rows:
        for interval in intervals:
            bucket = naive_iso(bucket_start(row["parsed_quote_time"], interval))
            key = (row["account_id"], row["symbol"], interval, bucket)
            price = float(row["price"])
            if key not in bars:
                bars[key] = {
                    "account_id": row["account_id"],
                    "symbol": row["symbol"],
                    "interval": interval,
                    "bucket_start": bucket,
                    "open_price": price,
                    "high_price": price,
                    "low_price": price,
                    "close_price": price,
                    "previous_close": row["previous_close"],
                    "day_change_rate": row["day_change_rate"],
                    "tick_count": 1,
                    "currency": row["currency"],
                    "first_quote_at": row["quote_time"],
                    "last_quote_at": row["quote_time"],
                    "aggregated_at": aggregated_at,
                    "source": "tick-retention",
                    "metadata_json": {"source_table": "realtime_price_ticks"},
                }
                continue

            bar = bars[key]
            bar["high_price"] = max(float(bar["high_price"]), price)
            bar["low_price"] = min(float(bar["low_price"]), price)
            bar["close_price"] = price
            bar["tick_count"] = int(bar["tick_count"]) + 1
            bar["last_quote_at"] = row["quote_time"]
            bar["previous_close"] = row["previous_close"]
            bar["day_change_rate"] = row["day_change_rate"]
            bar["currency"] = row["currency"]
            bar["aggregated_at"] = aggregated_at
    return list(bars.values())


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


def choose_backend(preferred: str) -> str:
    """실행 백엔드를 결정한다."""

    if preferred in {"sqlite", "supabase"}:
        return preferred
    if get_service_role_key():
        return "supabase"
    return "sqlite"


class SQLiteTickRetentionStore:
    """SQLite realtime tick 보존 정책 실행 저장소."""

    backend = "sqlite"

    def fetch_ticks(self, *, start_at: str | None = None, end_at: str) -> list[dict[str, Any]]:
        """집계 대상 tick을 시간 범위로 조회한다."""

        sqlite_db.initialize_database()
        conditions = ["quote_time < ?"]
        parameters: list[Any] = [end_at]
        if start_at is not None:
            conditions.append("quote_time >= ?")
            parameters.append(start_at)
        query = f"""
            SELECT *
            FROM realtime_price_ticks
            WHERE {' AND '.join(conditions)}
            ORDER BY quote_time ASC, id ASC
        """
        with sqlite_db.connect() as connection:
            rows = connection.execute(query, tuple(parameters)).fetchall()
        return [dict(row) for row in rows]

    def upsert_bars(self, bars: list[dict[str, Any]]) -> int:
        """집계 bar를 저장한다."""

        if not bars:
            return 0
        with sqlite_db.connect() as connection:
            connection.executemany(
                """
                INSERT INTO realtime_price_bars (
                    account_id, symbol, interval, bucket_start, open_price, high_price,
                    low_price, close_price, previous_close, day_change_rate, tick_count,
                    currency, first_quote_at, last_quote_at, aggregated_at, source, metadata_json
                )
                VALUES (
                    :account_id, :symbol, :interval, :bucket_start, :open_price, :high_price,
                    :low_price, :close_price, :previous_close, :day_change_rate, :tick_count,
                    :currency, :first_quote_at, :last_quote_at, :aggregated_at, :source, :metadata_json
                )
                ON CONFLICT(account_id, symbol, interval, bucket_start) DO UPDATE SET
                    open_price = excluded.open_price,
                    high_price = excluded.high_price,
                    low_price = excluded.low_price,
                    close_price = excluded.close_price,
                    previous_close = excluded.previous_close,
                    day_change_rate = excluded.day_change_rate,
                    tick_count = excluded.tick_count,
                    currency = excluded.currency,
                    first_quote_at = excluded.first_quote_at,
                    last_quote_at = excluded.last_quote_at,
                    aggregated_at = excluded.aggregated_at,
                    source = excluded.source,
                    metadata_json = excluded.metadata_json
                """,
                [{**bar, "metadata_json": json.dumps(bar.get("metadata_json") or {}, separators=(",", ":"))} for bar in bars],
            )
            connection.commit()
        return len(bars)

    def count_raw_ticks_before(self, cutoff: str) -> int:
        """삭제 대상 raw tick 수를 반환한다."""

        with sqlite_db.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM realtime_price_ticks WHERE quote_time < ?",
                (cutoff,),
            ).fetchone()
        return int(row["count"] if row else 0)

    def delete_raw_ticks_before(self, cutoff: str) -> int:
        """raw 보존 기간을 지난 tick을 삭제한다."""

        with sqlite_db.connect() as connection:
            cursor = connection.execute("DELETE FROM realtime_price_ticks WHERE quote_time < ?", (cutoff,))
            connection.commit()
        return int(cursor.rowcount or 0)

    def count_intraday_bars_before(self, cutoff: str) -> int:
        """보존 기간을 지난 1분/5분봉 수를 반환한다."""

        with sqlite_db.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM realtime_price_bars
                WHERE interval IN ('1m', '5m') AND bucket_start < ?
                """,
                (cutoff,),
            ).fetchone()
        return int(row["count"] if row else 0)

    def delete_intraday_bars_before(self, cutoff: str) -> int:
        """90일 초과 1분/5분봉을 삭제한다."""

        with sqlite_db.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM realtime_price_bars WHERE interval IN ('1m', '5m') AND bucket_start < ?",
                (cutoff,),
            )
            connection.commit()
        return int(cursor.rowcount or 0)

    def count_daily_bars_before(self, cutoff: str) -> int:
        """일봉 추가 보존 기간을 지난 bar 수를 반환한다."""

        with sqlite_db.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM realtime_price_bars WHERE interval = '1d' AND bucket_start < ?",
                (cutoff,),
            ).fetchone()
        return int(row["count"] if row else 0)

    def delete_daily_bars_before(self, cutoff: str) -> int:
        """설정된 경우 오래된 일봉을 삭제한다."""

        with sqlite_db.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM realtime_price_bars WHERE interval = '1d' AND bucket_start < ?",
                (cutoff,),
            )
            connection.commit()
        return int(cursor.rowcount or 0)


class SupabaseTickRetentionStore:
    """Supabase REST API 기반 realtime tick 보존 정책 실행 저장소."""

    backend = "supabase"

    def __init__(self, url: str, service_role_key: str, *, page_size: int = 1000) -> None:
        if not url or not service_role_key:
            raise ValueError("Supabase 실행에는 SUPABASE_URL 과 SUPABASE_SERVICE_ROLE_KEY 가 필요합니다.")
        self.url = url.rstrip("/")
        self.service_role_key = service_role_key
        self.page_size = int(page_size)

    @property
    def headers(self) -> dict[str, str]:
        """Supabase REST 호출 헤더를 반환한다."""

        return {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
        }

    def request(
        self,
        method: str,
        table: str,
        *,
        params: list[tuple[str, Any]] | None = None,
        data: Any = None,
        prefer: str | None = None,
    ) -> requests.Response:
        """Supabase REST API를 호출한다."""

        headers = dict(self.headers)
        if prefer:
            headers["Prefer"] = prefer
        response = requests.request(
            method,
            f"{self.url}/rest/v1/{table}",
            params=params or [],
            json=data,
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        return response

    def count_rows(self, table: str, params: list[tuple[str, Any]]) -> int:
        """PostgREST count 헤더로 대상 row 수를 반환한다."""

        response = self.request(
            "GET",
            table,
            params=[("select", "id"), *params, ("limit", 0)],
            prefer="count=exact",
        )
        content_range = str(response.headers.get("content-range") or response.headers.get("Content-Range") or "")
        if "/" in content_range:
            total = content_range.rsplit("/", 1)[-1]
            return 0 if total == "*" else int(total)
        return 0

    def fetch_ticks(self, *, start_at: str | None = None, end_at: str) -> list[dict[str, Any]]:
        """집계 대상 tick을 시간 범위로 조회한다."""

        filters: list[tuple[str, Any]] = [
            ("select", "*"),
            ("quote_time", f"lt.{end_at}"),
            ("order", "quote_time.asc,id.asc"),
        ]
        if start_at is not None:
            filters.append(("quote_time", f"gte.{start_at}"))

        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            response = self.request(
                "GET",
                "realtime_price_ticks",
                params=[*filters, ("limit", self.page_size), ("offset", offset)],
            )
            batch = response.json()
            if not isinstance(batch, list) or not batch:
                break
            rows.extend(batch)
            if len(batch) < self.page_size:
                break
            offset += self.page_size
        return rows

    def upsert_bars(self, bars: list[dict[str, Any]]) -> int:
        """집계 bar를 저장한다."""

        if not bars:
            return 0
        payload = [
            {
                **bar,
                "metadata_json": bar.get("metadata_json") or {},
            }
            for bar in bars
        ]
        for index in range(0, len(payload), 500):
            self.request(
                "POST",
                "realtime_price_bars",
                params=[("on_conflict", "account_id,symbol,interval,bucket_start")],
                data=payload[index : index + 500],
                prefer="resolution=merge-duplicates,return=minimal",
            )
        return len(bars)

    def count_raw_ticks_before(self, cutoff: str) -> int:
        """삭제 대상 raw tick 수를 반환한다."""

        return self.count_rows("realtime_price_ticks", [("quote_time", f"lt.{cutoff}")])

    def delete_raw_ticks_before(self, cutoff: str) -> int:
        """raw 보존 기간을 지난 tick을 삭제한다."""

        count = self.count_raw_ticks_before(cutoff)
        self.request("DELETE", "realtime_price_ticks", params=[("quote_time", f"lt.{cutoff}")])
        return count

    def count_intraday_bars_before(self, cutoff: str) -> int:
        """보존 기간을 지난 1분/5분봉 수를 반환한다."""

        return self.count_rows(
            "realtime_price_bars",
            [("interval", "in.(1m,5m)"), ("bucket_start", f"lt.{cutoff}")],
        )

    def delete_intraday_bars_before(self, cutoff: str) -> int:
        """90일 초과 1분/5분봉을 삭제한다."""

        count = self.count_intraday_bars_before(cutoff)
        self.request(
            "DELETE",
            "realtime_price_bars",
            params=[("interval", "in.(1m,5m)"), ("bucket_start", f"lt.{cutoff}")],
        )
        return count

    def count_daily_bars_before(self, cutoff: str) -> int:
        """일봉 추가 보존 기간을 지난 bar 수를 반환한다."""

        return self.count_rows("realtime_price_bars", [("interval", "eq.1d"), ("bucket_start", f"lt.{cutoff}")])

    def delete_daily_bars_before(self, cutoff: str) -> int:
        """설정된 경우 오래된 일봉을 삭제한다."""

        count = self.count_daily_bars_before(cutoff)
        self.request("DELETE", "realtime_price_bars", params=[("interval", "eq.1d"), ("bucket_start", f"lt.{cutoff}")])
        return count


def run_retention(store: Any, policy: RetentionPolicy, *, apply_changes: bool, as_of: datetime | None = None) -> RetentionSummary:
    """보존 정책에 따라 tick 집계와 삭제를 실행한다."""

    policy.validate()
    timezone = ZoneInfo(policy.timezone_name)
    current_time = as_of.astimezone(timezone) if as_of and as_of.tzinfo else (as_of or datetime.now(timezone))
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone)

    raw_cutoff = naive_iso(current_time - timedelta(days=policy.raw_retention_days))
    intraday_cutoff = naive_iso(current_time - timedelta(days=policy.intraday_retention_days))
    summary = RetentionSummary(backend=store.backend, dry_run=not apply_changes)

    intraday_ticks = store.fetch_ticks(start_at=intraday_cutoff, end_at=raw_cutoff)
    daily_ticks = store.fetch_ticks(start_at=None, end_at=intraday_cutoff)
    summary.source_ticks = len(intraday_ticks) + len(daily_ticks)

    bars = aggregate_ticks(intraday_ticks, intervals=policy.intraday_intervals, timezone_name=policy.timezone_name)
    bars.extend(aggregate_ticks(daily_ticks, intervals=("1d",), timezone_name=policy.timezone_name))
    for bar in bars:
        interval = str(bar["interval"])
        summary.bars_by_interval[interval] = summary.bars_by_interval.get(interval, 0) + 1

    summary.raw_ticks_to_delete = store.count_raw_ticks_before(raw_cutoff)
    summary.stale_intraday_bars_to_delete = store.count_intraday_bars_before(intraday_cutoff)
    if policy.daily_retention_days > 0:
        daily_cutoff = naive_iso(current_time - timedelta(days=policy.daily_retention_days))
        summary.stale_daily_bars_to_delete = store.count_daily_bars_before(daily_cutoff)
    else:
        daily_cutoff = ""

    if not apply_changes:
        return summary

    store.upsert_bars(bars)
    summary.raw_ticks_deleted = store.delete_raw_ticks_before(raw_cutoff)
    summary.stale_intraday_bars_deleted = store.delete_intraday_bars_before(intraday_cutoff)
    if daily_cutoff:
        summary.stale_daily_bars_deleted = store.delete_daily_bars_before(daily_cutoff)
    return summary


def parse_args() -> argparse.Namespace:
    """명령행 인자를 해석한다."""

    parser = argparse.ArgumentParser(description="실시간 시세 tick을 1분/5분/일봉으로 집계하고 보존 기간을 지난 raw tick을 정리한다.")
    parser.add_argument("--backend", choices=("auto", "sqlite", "supabase"), default="auto", help="실행 백엔드 선택")
    parser.add_argument("--apply", action="store_true", help="집계 저장과 삭제를 실제 실행한다. 기본값은 dry-run이다.")
    parser.add_argument("--as-of", dest="as_of", help="정책 기준 시각(ISO). 기본값은 현재 시각")
    parser.add_argument(
        "--timezone",
        default=str(os.getenv("RETENTION_TIMEZONE", DEFAULT_RETENTION_TIMEZONE)).strip() or DEFAULT_RETENTION_TIMEZONE,
        help="quote_time 해석 기준 시간대. 기본값은 Asia/Seoul",
    )
    parser.add_argument(
        "--raw-retention-days",
        type=int,
        default=int(os.getenv("REALTIME_TICK_RAW_RETENTION_DAYS", DEFAULT_RAW_RETENTION_DAYS)),
        help="원본 tick 보관 일수. 기본값은 7",
    )
    parser.add_argument(
        "--intraday-retention-days",
        type=int,
        default=int(os.getenv("REALTIME_BAR_INTRADAY_RETENTION_DAYS", DEFAULT_INTRADAY_RETENTION_DAYS)),
        help="1분/5분봉 보관 일수. 기본값은 90",
    )
    parser.add_argument(
        "--daily-retention-days",
        type=int,
        default=int(os.getenv("REALTIME_BAR_DAILY_RETENTION_DAYS", DEFAULT_DAILY_RETENTION_DAYS)),
        help="일봉 보관 일수. 0이면 일봉은 삭제하지 않는다.",
    )
    parser.add_argument(
        "--intervals",
        default="1m,5m",
        help="raw 보관 기간 이후 생성할 intraday interval 목록. 기본값은 1m,5m",
    )
    parser.add_argument("--supabase-page-size", type=int, default=1000, help="Supabase tick 조회 page size")
    return parser.parse_args()


def build_store(backend: str, *, supabase_page_size: int) -> Any:
    """선택된 backend 저장소를 생성한다."""

    resolved_backend = choose_backend(backend)
    if resolved_backend == "supabase":
        return SupabaseTickRetentionStore(get_supabase_url(), get_service_role_key(), page_size=supabase_page_size)
    sqlite_db.initialize_database()
    return SQLiteTickRetentionStore()


def main() -> int:
    """CLI 진입점."""

    args = parse_args()
    intervals = tuple(item.strip() for item in str(args.intervals or "").split(",") if item.strip())
    policy = RetentionPolicy(
        raw_retention_days=int(args.raw_retention_days),
        intraday_retention_days=int(args.intraday_retention_days),
        daily_retention_days=int(args.daily_retention_days),
        timezone_name=str(args.timezone),
        intraday_intervals=intervals or ("1m", "5m"),
    )
    as_of = parse_timestamp(args.as_of, policy.timezone_name) if args.as_of else None
    store = build_store(str(args.backend), supabase_page_size=int(args.supabase_page_size))
    summary = run_retention(store, policy, apply_changes=bool(args.apply), as_of=as_of)
    summary.print()
    if not args.apply:
        print("[realtime-tick-retention] dry-run입니다. 실제 집계/삭제는 --apply를 붙여 실행하세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

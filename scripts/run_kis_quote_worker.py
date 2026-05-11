from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src import sqlite_db  # noqa: E402
from src.kis import (  # noqa: E402
    KIS_WS_QUOTE_TR_ID,
    KisApiClient,
    is_kis_domestic_symbol,
    kis_settings,
    normalize_domestic_code,
    parse_websocket_message,
    websocket_subscription_message,
)


DEFAULT_SUPABASE_URL = "https://iyszkybxostbjfzbbymq.supabase.co"
LOCAL_SECRETS_PATH = ROOT_DIR / ".streamlit" / "secrets.toml"
SERVICE_ROLE_ENV_NAMES = ("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_ADMIN_KEY")
REALTIME_SCHEMA_TABLES = ("realtime_worker_status", "realtime_price_ticks")
_LOCAL_STREAMLIT_SECRETS_CACHE: dict[str, Any] | None = None


def now_iso() -> str:
    """현재 UTC 시각을 ISO 문자열로 반환한다."""

    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())


def parse_args() -> argparse.Namespace:
    """명령행 인자를 해석한다."""

    parser = argparse.ArgumentParser(description="KIS WebSocket 실시간 quote worker")
    parser.add_argument("--backend", choices=("auto", "sqlite", "supabase"), default="auto")
    parser.add_argument("--account-id", type=int, action="append", help="특정 계좌만 구독할 때 사용한다.")
    parser.add_argument("--worker-name", default="kis-quote-worker", help="상태 테이블에 저장할 worker 이름")
    parser.add_argument("--reconnect-delay", type=int, default=5, help="재연결 기본 대기(초)")
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="저장소/스키마 선행 조건만 점검하고 종료한다.",
    )
    return parser.parse_args()


def load_local_streamlit_secrets() -> dict[str, Any]:
    """로컬 `.streamlit/secrets.toml` 값을 읽는다."""

    global _LOCAL_STREAMLIT_SECRETS_CACHE
    if _LOCAL_STREAMLIT_SECRETS_CACHE is not None:
        return _LOCAL_STREAMLIT_SECRETS_CACHE

    if not LOCAL_SECRETS_PATH.exists():
        _LOCAL_STREAMLIT_SECRETS_CACHE = {}
        return _LOCAL_STREAMLIT_SECRETS_CACHE

    try:
        with LOCAL_SECRETS_PATH.open("rb") as file:
            data = tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError):
        _LOCAL_STREAMLIT_SECRETS_CACHE = {}
        return _LOCAL_STREAMLIT_SECRETS_CACHE

    _LOCAL_STREAMLIT_SECRETS_CACHE = data if isinstance(data, dict) else {}
    return _LOCAL_STREAMLIT_SECRETS_CACHE


def read_config_value(name: str, default: str = "") -> str:
    """환경 변수 우선, 없으면 로컬 Streamlit 시크릿에서 설정값을 읽는다."""

    env_value = str(os.getenv(name, "")).strip()
    if env_value:
        return env_value

    local_value = load_local_streamlit_secrets().get(name)
    if local_value not in (None, ""):
        return str(local_value).strip()
    return str(default).strip()


def get_supabase_url() -> str:
    """Supabase REST URL을 읽는다."""

    return read_config_value("SUPABASE_URL", DEFAULT_SUPABASE_URL)


def get_service_role_key() -> str:
    """Supabase 서비스 롤 키를 읽는다."""

    for env_name in SERVICE_ROLE_ENV_NAMES:
        value = read_config_value(env_name)
        if value:
            return value
    return ""


def choose_backend(preferred: str) -> str:
    """worker 저장소 백엔드를 결정한다."""

    if preferred in {"sqlite", "supabase"}:
        return preferred
    return "supabase" if get_service_role_key() else "sqlite"


@dataclass
class HoldingRef:
    """실시간 최신가를 덮어쓸 대상 holding 참조."""

    account_id: int
    holding_id: int
    symbol: str
    product_name: str


class QuoteStorage:
    """worker가 사용하는 저장소 인터페이스."""

    def list_target_holdings(self, account_ids: set[int] | None = None) -> list[HoldingRef]:
        raise NotImplementedError

    def record_quote(self, holding: HoldingRef, quote: dict[str, Any]) -> None:
        raise NotImplementedError

    def update_account_status(
        self,
        account_id: int,
        *,
        worker_name: str,
        connection_state: str,
        last_seen_at: str | None = None,
        last_quote_at: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> None:
        raise NotImplementedError

    def known_account_ids(self, account_ids: set[int] | None = None) -> list[int]:
        raise NotImplementedError

    def verify_runtime_ready(self) -> None:
        """worker 실행 전 저장소 선행 조건을 점검한다."""

        return None


class SQLiteQuoteStorage(QuoteStorage):
    """로컬 SQLite 기반 quote 저장소."""

    def __init__(self) -> None:
        sqlite_db.initialize_database()

    def known_account_ids(self, account_ids: set[int] | None = None) -> list[int]:
        rows = sqlite_db.list_accounts()
        ids = [int(row["id"]) for row in rows]
        if account_ids:
            ids = [item for item in ids if item in account_ids]
        return ids

    def list_target_holdings(self, account_ids: set[int] | None = None) -> list[HoldingRef]:
        holdings: list[HoldingRef] = []
        for account_id in self.known_account_ids(account_ids):
            for row in sqlite_db.list_holdings(account_id):
                symbol = normalize_domestic_code(row.get("symbol"))
                if float(row.get("quantity") or 0) <= 0 or not is_kis_domestic_symbol(symbol):
                    continue
                holdings.append(
                    HoldingRef(
                        account_id=account_id,
                        holding_id=int(row["id"]),
                        symbol=symbol,
                        product_name=str(row.get("product_name") or symbol),
                    )
                )
        return holdings

    def record_quote(self, holding: HoldingRef, quote: dict[str, Any]) -> None:
        sqlite_db.record_realtime_price_tick(
            account_id=holding.account_id,
            holding_id=holding.holding_id,
            symbol=holding.symbol,
            price=float(quote["price"]),
            previous_close=_maybe_float(quote.get("previous_close")),
            day_change_rate=_maybe_float(quote.get("day_change_rate")),
            currency=str(quote.get("currency") or "KRW"),
            quote_time=str(quote.get("quote_time") or now_iso()),
            source=str(quote.get("source") or "KIS WebSocket"),
            metadata_json=quote.get("metadata"),
        )

    def update_account_status(
        self,
        account_id: int,
        *,
        worker_name: str,
        connection_state: str,
        last_seen_at: str | None = None,
        last_quote_at: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> None:
        sqlite_db.upsert_realtime_worker_status(
            account_id=account_id,
            worker_name=worker_name,
            connection_state=connection_state,
            last_seen_at=last_seen_at,
            last_quote_at=last_quote_at,
            metadata_json=metadata_json,
        )


class SupabaseAdminClient(QuoteStorage):
    """서비스 롤 키로 실시간 quote를 기록하는 최소 Supabase 클라이언트."""

    def __init__(self, url: str, service_role_key: str) -> None:
        if not url or not service_role_key:
            raise ValueError("Supabase worker 실행에는 SUPABASE_URL 과 SUPABASE_SERVICE_ROLE_KEY 가 필요합니다.")
        self.url = url.rstrip("/")
        self.service_role_key = service_role_key

    @property
    def headers(self) -> dict[str, str]:
        """Supabase REST 헤더를 반환한다."""

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
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any] | None:
        """Supabase REST API를 호출한다."""

        response = requests.request(
            method=method,
            url=f"{self.url}/rest/v1/{table}",
            json=data,
            params={key: str(value) for key, value in (filters or {}).items()},
            headers=self.headers,
            timeout=20,
        )
        response.raise_for_status()
        if method == "DELETE":
            return None
        if method in {"POST", "PATCH"} and (response.status_code == 204 or not response.content):
            return None
        payload = response.json()
        if method in {"POST", "PATCH"}:
            return payload[0] if isinstance(payload, list) and payload else payload
        return payload

    def verify_runtime_ready(self) -> None:
        """운영 Supabase에 realtime worker용 테이블이 노출됐는지 확인한다."""

        missing_tables: list[str] = []
        for table_name in REALTIME_SCHEMA_TABLES:
            try:
                self.request("GET", table_name, filters={"limit": 1})
            except requests.HTTPError as exc:
                if _is_missing_supabase_table_error(exc, table_name):
                    missing_tables.append(table_name)
                    continue
                raise

        if missing_tables:
            missing_labels = ", ".join(f"public.{table}" for table in missing_tables)
            raise RuntimeError(
                "운영 Supabase REST에서 "
                f"{missing_labels} 테이블을 찾지 못했습니다. "
                "최신 setup_supabase.sql을 SQL Editor에 적용하고 Data API schema cache가 갱신됐는지 확인한 뒤 다시 실행해 주세요."
            )

    def known_account_ids(self, account_ids: set[int] | None = None) -> list[int]:
        rows = self.request("GET", "accounts") or []
        ids = [int(row["id"]) for row in rows if row.get("id") is not None]
        if account_ids:
            ids = [item for item in ids if item in account_ids]
        return ids

    def list_target_holdings(self, account_ids: set[int] | None = None) -> list[HoldingRef]:
        holdings: list[HoldingRef] = []
        for account_id in self.known_account_ids(account_ids):
            rows = self.request(
                "GET",
                "holdings",
                filters={"account_id": f"eq.{account_id}", "quantity": "gt.0"},
            ) or []
            for row in rows:
                symbol = normalize_domestic_code(row.get("symbol"))
                if not is_kis_domestic_symbol(symbol):
                    continue
                holdings.append(
                    HoldingRef(
                        account_id=account_id,
                        holding_id=int(row["id"]),
                        symbol=symbol,
                        product_name=str(row.get("product_name") or symbol),
                    )
                )
        return holdings

    def record_quote(self, holding: HoldingRef, quote: dict[str, Any]) -> None:
        quote_time = str(quote.get("quote_time") or now_iso())
        self.request(
            "PATCH",
            "holdings",
            data={
                "current_price": float(quote["price"]),
                "price_updated_at": quote_time,
                "updated_at": now_iso(),
            },
            filters={"id": f"eq.{holding.holding_id}"},
        )
        self.request(
            "POST",
            "realtime_price_ticks",
            data={
                "account_id": holding.account_id,
                "holding_id": holding.holding_id,
                "symbol": holding.symbol,
                "price": float(quote["price"]),
                "previous_close": _maybe_float(quote.get("previous_close")),
                "day_change_rate": _maybe_float(quote.get("day_change_rate")),
                "currency": str(quote.get("currency") or "KRW"),
                "quote_time": quote_time,
                "ingested_at": now_iso(),
                "source": str(quote.get("source") or "KIS WebSocket"),
                "metadata_json": dict(quote.get("metadata") or {}),
            },
        )

    def update_account_status(
        self,
        account_id: int,
        *,
        worker_name: str,
        connection_state: str,
        last_seen_at: str | None = None,
        last_quote_at: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "worker_name": str(worker_name or "").strip() or "kis-quote-worker",
            "connection_state": str(connection_state or "").strip() or "unknown",
            "last_seen_at": str(last_seen_at or "").strip() or None,
            "last_quote_at": str(last_quote_at or "").strip() or None,
            "updated_at": now_iso(),
            "metadata_json": dict(metadata_json or {}),
        }
        existing = self.request("GET", "realtime_worker_status", filters={"account_id": f"eq.{account_id}"}) or []
        if existing:
            self.request("PATCH", "realtime_worker_status", data=payload, filters={"account_id": f"eq.{account_id}"})
            return
        self.request("POST", "realtime_worker_status", data={"account_id": account_id, **payload})


def _maybe_float(value: Any) -> float | None:
    """숫자 후보 값을 float로 바꾼다."""

    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _is_missing_supabase_table_error(exc: Exception, table_name: str) -> bool:
    """Supabase REST schema cache에 대상 테이블이 없는지 판별한다."""

    if not isinstance(exc, requests.HTTPError) or exc.response is None:
        return False

    if exc.response.status_code != 404:
        return False

    detail = exc.response.text.strip().replace("\n", " ").lower()
    return "schema cache" in detail and (
        f"public.{table_name}".lower() in detail or f"'{table_name.lower()}'" in detail
    )


def build_storage(backend: str) -> QuoteStorage:
    """worker 저장소 구현체를 생성한다."""

    if backend == "supabase":
        return SupabaseAdminClient(get_supabase_url(), get_service_role_key())
    return SQLiteQuoteStorage()


def update_status_for_accounts(
    storage: QuoteStorage,
    account_ids: list[int],
    *,
    worker_name: str,
    connection_state: str,
    last_seen_at: str | None = None,
    last_quote_at: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> None:
    """여러 계좌의 worker 상태를 한 번에 갱신한다."""

    for account_id in account_ids:
        storage.update_account_status(
            account_id,
            worker_name=worker_name,
            connection_state=connection_state,
            last_seen_at=last_seen_at,
            last_quote_at=last_quote_at,
            metadata_json=metadata_json,
        )


def main() -> int:
    """KIS WebSocket quote worker 본체를 실행한다."""

    args = parse_args()
    backend = choose_backend(args.backend)
    storage = build_storage(backend)
    settings = kis_settings()
    if not settings["enabled"]:
        raise ValueError("KIS_APP_KEY 와 KIS_APP_SECRET 을 설정해야 quote worker를 실행할 수 있습니다.")

    try:
        import websocket
    except ImportError as exc:  # pragma: no cover - 런타임 의존성
        raise RuntimeError("`websocket-client` 패키지가 필요합니다. `pip install -r requirements.txt` 후 다시 시도해 주세요.") from exc

    selected_account_ids = set(args.account_id or [])
    storage.verify_runtime_ready()
    preflight_account_ids = storage.known_account_ids(selected_account_ids or None)
    preflight_holdings = storage.list_target_holdings(selected_account_ids or None)
    print(
        "quote worker 사전 점검 완료: "
        f"backend={backend} accounts={len(preflight_account_ids)} holdings={len(preflight_holdings)}",
        flush=True,
    )
    if args.preflight_only:
        return 0

    backoff_seconds = max(int(args.reconnect_delay or 5), 1)
    client = KisApiClient()
    active_account_ids = list(preflight_account_ids)
    previous_signal_handlers: dict[int, Any] = {}

    def raise_keyboard_interrupt(signum: int, _frame: Any) -> None:
        """SIGINT/SIGTERM을 KeyboardInterrupt로 바꿔 정리 루틴을 타게 한다."""

        raise KeyboardInterrupt(f"signal:{signum}")

    for sig in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
        if sig is None:
            continue
        previous_signal_handlers[int(sig)] = signal.getsignal(sig)
        signal.signal(sig, raise_keyboard_interrupt)

    try:
        while True:
            holdings = storage.list_target_holdings(selected_account_ids or None)
            account_ids = storage.known_account_ids(selected_account_ids or None)
            active_account_ids = list(account_ids)
            if not holdings:
                update_status_for_accounts(
                    storage,
                    account_ids,
                    worker_name=args.worker_name,
                    connection_state="idle",
                    last_seen_at=now_iso(),
                    metadata_json={"reason": "국내 KIS 실시간 구독 대상 보유 종목이 없습니다.", "backend": backend},
                )
                print("구독할 국내 보유 종목이 없어 30초 뒤 다시 확인합니다.", flush=True)
                time.sleep(30)
                continue

            holdings_by_symbol: dict[str, list[HoldingRef]] = {}
            for holding in holdings:
                holdings_by_symbol.setdefault(holding.symbol, []).append(holding)
            subscribed_symbols = sorted(holdings_by_symbol)
            reconnect_state = {"delay_seconds": backoff_seconds}

            def on_open(ws: Any) -> None:
                approval_key = client.get_approval_key()
                for symbol in subscribed_symbols:
                    ws.send(websocket_subscription_message(approval_key, symbol, subscribe=True))
                    time.sleep(0.08)
                reconnect_state["delay_seconds"] = max(int(args.reconnect_delay or 5), 1)
                update_status_for_accounts(
                    storage,
                    account_ids,
                    worker_name=args.worker_name,
                    connection_state="connected",
                    last_seen_at=now_iso(),
                    metadata_json={"backend": backend, "symbols": subscribed_symbols, "tr_id": KIS_WS_QUOTE_TR_ID},
                )
                print(f"KIS WebSocket 연결 완료: {len(subscribed_symbols)}개 종목 구독", flush=True)

            def on_message(ws: Any, message: str) -> None:
                parsed = parse_websocket_message(message)
                if not parsed:
                    return
                if parsed["message_type"] == "control":
                    if parsed.get("tr_id") == "PINGPONG":
                        try:
                            ws.send(message, opcode=websocket.ABNF.OPCODE_PING)
                        except Exception:
                            pass
                        return
                    update_status_for_accounts(
                        storage,
                        account_ids,
                        worker_name=args.worker_name,
                        connection_state="connected",
                        last_seen_at=now_iso(),
                        metadata_json={
                            "backend": backend,
                            "symbols": subscribed_symbols,
                            "control_message": str(parsed.get("message") or ""),
                        },
                    )
                    return

                symbol = str(parsed.get("symbol") or "").strip().upper()
                if symbol not in holdings_by_symbol:
                    return
                quote_time = str(parsed.get("quote_time") or now_iso())
                for holding_ref in holdings_by_symbol[symbol]:
                    storage.record_quote(holding_ref, parsed)
                    storage.update_account_status(
                        holding_ref.account_id,
                        worker_name=args.worker_name,
                        connection_state="connected",
                        last_seen_at=now_iso(),
                        last_quote_at=quote_time,
                        metadata_json={"backend": backend, "last_symbol": symbol, "symbols": subscribed_symbols},
                    )

            def on_error(_ws: Any, error: Any) -> None:
                message = str(error or "알 수 없는 WebSocket 오류")
                update_status_for_accounts(
                    storage,
                    account_ids,
                    worker_name=args.worker_name,
                    connection_state="error",
                    last_seen_at=now_iso(),
                    metadata_json={"backend": backend, "error": message, "symbols": subscribed_symbols},
                )
                print(f"KIS WebSocket 오류: {message}", flush=True)

            def on_close(_ws: Any, status_code: Any, close_message: Any) -> None:
                update_status_for_accounts(
                    storage,
                    account_ids,
                    worker_name=args.worker_name,
                    connection_state="disconnected",
                    last_seen_at=now_iso(),
                    metadata_json={
                        "backend": backend,
                        "status_code": status_code,
                        "close_message": str(close_message or ""),
                        "symbols": subscribed_symbols,
                    },
                )
                print(f"KIS WebSocket 연결 종료: code={status_code} message={close_message}", flush=True)

            ws_app = websocket.WebSocketApp(
                client.ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
            )
            print(f"KIS quote worker 시작: backend={backend} env={settings['env']} ws={client.ws_url}", flush=True)
            ws_app.run_forever(ping_interval=20, ping_timeout=10)
            backoff_seconds = reconnect_state["delay_seconds"]
            print(f"{backoff_seconds}초 뒤 KIS WebSocket 재연결을 시도합니다.", flush=True)
            time.sleep(backoff_seconds)
            backoff_seconds = min(backoff_seconds * 2, 60)
    except KeyboardInterrupt:
        update_status_for_accounts(
            storage,
            active_account_ids,
            worker_name=args.worker_name,
            connection_state="stopped",
            last_seen_at=now_iso(),
            metadata_json={"backend": backend, "reason": "종료 신호를 받아 worker를 중지했습니다."},
        )
        print("종료 신호를 받아 KIS quote worker를 중지합니다.", flush=True)
        return 0
    finally:
        for sig_num, previous_handler in previous_signal_handlers.items():
            signal.signal(sig_num, previous_handler)


if __name__ == "__main__":
    raise SystemExit(main())

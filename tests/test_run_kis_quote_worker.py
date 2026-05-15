from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import requests


def _load_quote_worker_module():
    """테스트 대상 worker 스크립트를 동적으로 불러온다."""

    module_name = "test_run_kis_quote_worker_module"
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_kis_quote_worker.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("run_kis_quote_worker.py 모듈을 불러오지 못했습니다.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


quote_worker = _load_quote_worker_module()


def _http_error(status_code: int, detail: str, table_name: str) -> requests.HTTPError:
    """테스트용 Supabase HTTPError를 생성한다."""

    response = requests.Response()
    response.status_code = status_code
    response._content = detail.encode("utf-8")
    response.url = f"https://example.supabase.co/rest/v1/{table_name}"
    request = requests.Request("GET", response.url).prepare()
    response.request = request
    return requests.HTTPError(detail, response=response, request=request)


class QuoteWorkerConfigTests(unittest.TestCase):
    """worker 설정값 로딩 동작을 검증한다."""

    def tearDown(self) -> None:
        quote_worker._LOCAL_STREAMLIT_SECRETS_CACHE = None

    def test_get_service_role_key_reads_local_streamlit_secrets_when_env_missing(self) -> None:
        """환경 변수가 없으면 로컬 Streamlit 시크릿에서 service role을 읽는다."""

        with tempfile.TemporaryDirectory() as temp_dir:
            secrets_path = Path(temp_dir) / "secrets.toml"
            secrets_path.write_text('SUPABASE_SERVICE_ROLE_KEY = "local-service-role"\n', encoding="utf-8")
            with patch.object(quote_worker, "LOCAL_SECRETS_PATH", secrets_path):
                quote_worker._LOCAL_STREAMLIT_SECRETS_CACHE = None
                with patch.dict(os.environ, {}, clear=True):
                    self.assertEqual(quote_worker.get_service_role_key(), "local-service-role")

    def test_get_service_role_key_prefers_env_over_local_streamlit_secrets(self) -> None:
        """같은 키가 있으면 환경 변수 값을 우선 사용한다."""

        with tempfile.TemporaryDirectory() as temp_dir:
            secrets_path = Path(temp_dir) / "secrets.toml"
            secrets_path.write_text('SUPABASE_SERVICE_ROLE_KEY = "local-service-role"\n', encoding="utf-8")
            with patch.object(quote_worker, "LOCAL_SECRETS_PATH", secrets_path):
                quote_worker._LOCAL_STREAMLIT_SECRETS_CACHE = None
                with patch.dict(os.environ, {"SUPABASE_SERVICE_ROLE_KEY": "env-service-role"}, clear=True):
                    self.assertEqual(quote_worker.get_service_role_key(), "env-service-role")


class SupabaseRealtimeSchemaPreflightTests(unittest.TestCase):
    """Supabase realtime 스키마 사전 점검을 검증한다."""

    @patch.object(quote_worker.SupabaseAdminClient, "request", return_value=[])
    def test_verify_runtime_ready_passes_when_required_tables_are_accessible(self, request_mock) -> None:
        """필수 realtime 테이블이 모두 보이면 예외 없이 통과한다."""

        client = quote_worker.SupabaseAdminClient("https://example.supabase.co", "service-role")

        client.verify_runtime_ready()

        self.assertEqual(request_mock.call_count, 2)

    @patch.object(quote_worker.SupabaseAdminClient, "request")
    def test_verify_runtime_ready_reports_missing_realtime_tables(self, request_mock) -> None:
        """realtime 테이블이 schema cache에 없으면 적용 SQL을 안내한다."""

        def side_effect(method: str, table: str, **_: object):
            if table == "realtime_worker_status":
                raise _http_error(
                    404,
                    "Could not find the table 'public.realtime_worker_status' in the schema cache",
                    table,
                )
            if table == "realtime_price_ticks":
                raise _http_error(
                    404,
                    "Could not find the table 'public.realtime_price_ticks' in the schema cache",
                    table,
                )
            return []

        request_mock.side_effect = side_effect
        client = quote_worker.SupabaseAdminClient("https://example.supabase.co", "service-role")

        with self.assertRaises(RuntimeError) as context:
            client.verify_runtime_ready()

        message = str(context.exception)
        self.assertIn("setup_supabase.sql", message)
        self.assertIn("realtime_worker_status", message)
        self.assertIn("realtime_price_ticks", message)


class QuoteWorkerShutdownTests(unittest.TestCase):
    """worker 종료 신호 처리 동작을 검증한다."""

    def test_main_marks_worker_stopped_on_keyboard_interrupt(self) -> None:
        """장기 실행 worker가 중단되면 상태를 stopped로 남기고 0으로 종료한다."""

        fake_args = type(
            "Args",
            (),
            {
                "backend": "supabase",
                "account_id": None,
                "worker_name": "kis-quote-worker",
                "reconnect_delay": 5,
                "preflight_only": False,
            },
        )()

        class FakeStorage:
            """main 테스트용 최소 저장소."""

            def verify_runtime_ready(self) -> None:
                return None

            def known_account_ids(self, account_ids=None):
                return [24]

            def list_target_holdings(self, account_ids=None):
                return [
                    quote_worker.HoldingRef(
                        account_id=24,
                        holding_id=14,
                        symbol="005930",
                        product_name="삼성전자",
                    )
                ]

        class FakeWebSocketApp:
            """run_forever 시점에 종료 신호를 흉내 낸다."""

            def __init__(self, *args, **kwargs) -> None:
                return None

            def run_forever(self, *args, **kwargs) -> None:
                raise KeyboardInterrupt

        fake_websocket = type("FakeWebSocketModule", (), {"WebSocketApp": FakeWebSocketApp, "ABNF": object()})
        status_updates: list[dict[str, object]] = []

        def record_status(storage, account_ids, *, worker_name, connection_state, last_seen_at=None, last_quote_at=None, metadata_json=None):
            status_updates.append(
                {
                    "account_ids": list(account_ids),
                    "worker_name": worker_name,
                    "connection_state": connection_state,
                    "metadata_json": dict(metadata_json or {}),
                }
            )

        with patch.object(quote_worker, "parse_args", return_value=fake_args), \
            patch.object(quote_worker, "choose_backend", return_value="supabase"), \
            patch.object(quote_worker, "build_storage", return_value=FakeStorage()), \
            patch.object(quote_worker, "kis_settings", return_value={"enabled": True, "env": "prod"}), \
            patch.object(quote_worker, "KisApiClient", return_value=type("FakeClient", (), {"ws_url": "ws://example"})()), \
            patch.dict(sys.modules, {"websocket": fake_websocket}), \
            patch.object(quote_worker, "update_status_for_accounts", side_effect=record_status):
            result = quote_worker.main()

        self.assertEqual(result, 0)
        self.assertTrue(status_updates)
        self.assertEqual(status_updates[-1]["connection_state"], "stopped")
        self.assertEqual(status_updates[-1]["account_ids"], [24])

    def test_main_stops_after_signal_even_when_websocket_returns_normally(self) -> None:
        """종료 신호가 WebSocket 내부에서 처리돼도 재연결하지 않고 stopped를 남긴다."""

        fake_args = type(
            "Args",
            (),
            {
                "backend": "supabase",
                "account_id": None,
                "worker_name": "kis-quote-worker",
                "reconnect_delay": 5,
                "preflight_only": False,
            },
        )()

        class FakeStorage:
            """main 테스트용 최소 저장소."""

            def verify_runtime_ready(self) -> None:
                return None

            def known_account_ids(self, account_ids=None):
                return [24]

            def list_target_holdings(self, account_ids=None):
                return [
                    quote_worker.HoldingRef(
                        account_id=24,
                        holding_id=14,
                        symbol="005930",
                        product_name="삼성전자",
                    )
                ]

        registered_handlers: dict[int, object] = {}

        def fake_signal(sig, handler):
            sig_num = int(sig)
            previous_handler = registered_handlers.get(sig_num, quote_worker.signal.SIG_DFL)
            registered_handlers[sig_num] = handler
            return previous_handler

        class FakeWebSocketApp:
            """run_forever 중 종료 신호가 들어온 상황을 흉내 낸다."""

            close_called = False

            def __init__(self, *args, **kwargs) -> None:
                return None

            def run_forever(self, *args, **kwargs) -> None:
                handler = registered_handlers[int(quote_worker.signal.SIGTERM)]
                handler(int(quote_worker.signal.SIGTERM), None)

            def close(self) -> None:
                FakeWebSocketApp.close_called = True

        fake_websocket = type("FakeWebSocketModule", (), {"WebSocketApp": FakeWebSocketApp, "ABNF": object()})
        status_updates: list[dict[str, object]] = []

        def record_status(storage, account_ids, *, worker_name, connection_state, last_seen_at=None, last_quote_at=None, metadata_json=None):
            status_updates.append(
                {
                    "account_ids": list(account_ids),
                    "worker_name": worker_name,
                    "connection_state": connection_state,
                    "metadata_json": dict(metadata_json or {}),
                }
            )

        with patch.object(quote_worker, "parse_args", return_value=fake_args), \
            patch.object(quote_worker, "choose_backend", return_value="supabase"), \
            patch.object(quote_worker, "build_storage", return_value=FakeStorage()), \
            patch.object(quote_worker, "kis_settings", return_value={"enabled": True, "env": "prod"}), \
            patch.object(quote_worker, "KisApiClient", return_value=type("FakeClient", (), {"ws_url": "ws://example"})()), \
            patch.object(quote_worker.signal, "signal", side_effect=fake_signal), \
            patch.dict(sys.modules, {"websocket": fake_websocket}), \
            patch.object(quote_worker, "update_status_for_accounts", side_effect=record_status):
            result = quote_worker.main()

        self.assertEqual(result, 0)
        self.assertTrue(FakeWebSocketApp.close_called)
        self.assertTrue(status_updates)
        self.assertEqual(status_updates[-1]["connection_state"], "stopped")
        self.assertEqual(status_updates[-1]["account_ids"], [24])


class QuoteWorkerStatusPersistenceTests(unittest.TestCase):
    """worker 상태 갱신 시 마지막 quote 시각 보존을 검증한다."""

    def test_supabase_status_update_preserves_last_quote_at_when_omitted(self) -> None:
        """재연결 상태 갱신에서 새 quote 시각이 없으면 기존 last_quote_at을 지우지 않는다."""

        client = quote_worker.SupabaseAdminClient("https://example.supabase.co", "service-role")
        calls: list[dict[str, object]] = []

        def fake_request(method: str, table: str, *, data=None, filters=None):
            calls.append(
                {
                    "method": method,
                    "table": table,
                    "data": dict(data or {}),
                    "filters": dict(filters or {}),
                }
            )
            if method == "GET":
                return [{"account_id": 24, "last_quote_at": "2026-05-12T15:59:50"}]
            return None

        client.request = fake_request  # type: ignore[method-assign]

        client.update_account_status(
            24,
            worker_name="kis-quote-worker",
            connection_state="disconnected",
            last_seen_at="2026-05-12T16:00:10",
            metadata_json={"reason": "ping/pong timed out"},
        )

        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1]["method"], "PATCH")
        self.assertNotIn("last_quote_at", calls[1]["data"])


if __name__ == "__main__":
    unittest.main()

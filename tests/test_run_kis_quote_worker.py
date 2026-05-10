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


if __name__ == "__main__":
    unittest.main()

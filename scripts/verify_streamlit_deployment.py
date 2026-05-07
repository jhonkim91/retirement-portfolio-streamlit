from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    from playwright.sync_api import Frame, Locator, Page, sync_playwright
except ImportError:  # pragma: no cover - optional runtime dependency
    Frame = Any  # type: ignore[assignment]
    Locator = Any  # type: ignore[assignment]
    Page = Any  # type: ignore[assignment]
    sync_playwright = None


DEFAULT_APP_URL = "https://retirement-portfolio-app-nh2vq9ferqnpehsslbykbe.streamlit.app/"
DEFAULT_WAIT_MS = 8_000
PAGE_LABELS = {
    "dashboard": "대시보드",
    "trades": "거래",
    "data": "데이터",
}
PAGE_LABEL_INDEX = {
    "dashboard": 2,
    "trades": 3,
    "data": 4,
}


@dataclass
class DeploymentSummary:
    """배포 웹 앱 점검 결과를 저장한다."""

    url: str
    target_page: str
    logged_in: bool
    workspace_visible: bool
    status_panel_visible: bool
    backend_storage: str
    backend_storage_code: str
    total_interest: str
    interest_rollup: str
    latest_interest_date: str
    snapshot_count: str
    latest_snapshot_date: str
    supabase_config_status: str
    backend_override: str
    reason: str
    status_message: str
    text_output: str | None = None
    screenshot_output: str | None = None


def parse_args() -> argparse.Namespace:
    """명령행 인자를 해석한다."""

    parser = argparse.ArgumentParser(description="배포된 Streamlit 앱에 로그인해 저장소 상태를 검증한다.")
    parser.add_argument("--url", default=str(os.getenv("STREAMLIT_APP_URL", DEFAULT_APP_URL)).strip(), help="검증할 앱 URL")
    parser.add_argument("--email", default=str(os.getenv("STREAMLIT_VERIFY_EMAIL", "")).strip(), help="로그인 이메일")
    parser.add_argument("--password", default=str(os.getenv("STREAMLIT_VERIFY_PASSWORD", "")).strip(), help="로그인 비밀번호")
    parser.add_argument(
        "--page",
        choices=tuple(PAGE_LABELS),
        default="data",
        help="로그인 후 이동할 페이지",
    )
    parser.add_argument(
        "--expect-backend",
        choices=("any", "sqlite", "supabase"),
        default="any",
        help="기대하는 저장소 종류",
    )
    parser.add_argument("--screenshot", help="전체 페이지 스크린샷 저장 경로")
    parser.add_argument("--text-output", help="본문 텍스트 저장 경로")
    parser.add_argument("--wait-ms", type=int, default=DEFAULT_WAIT_MS, help="화면 전환 대기 시간(ms)")
    return parser.parse_args()


def ensure_playwright_available() -> None:
    """Playwright 사용 가능 여부를 확인한다."""

    if sync_playwright is None:
        raise RuntimeError(
            "playwright가 설치되어 있지 않습니다. "
            "`python -m pip install playwright` 와 `python -m playwright install chromium` 를 먼저 실행해 주세요."
        )


def configure_stdout() -> None:
    """Windows 콘솔에서도 UTF-8 JSON을 안정적으로 출력한다."""

    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def extract_lines(text: str) -> list[str]:
    """본문 텍스트를 의미 있는 줄 단위로 정리한다."""

    return [line.strip() for line in text.splitlines() if line.strip()]


def find_value_after_label(lines: list[str], label: str) -> str:
    """지정한 레이블 다음에 나오는 첫 값을 반환한다."""

    for index, line in enumerate(lines):
        if line == label:
            for value in lines[index + 1 :]:
                if value and value != label:
                    return value
    return ""


def find_values_after_label(lines: list[str], label: str, count: int = 2) -> list[str]:
    """지정한 레이블 뒤의 값을 여러 개 반환한다."""

    values: list[str] = []
    found_label = False
    for line in lines:
        if not found_label:
            if line == label:
                found_label = True
            continue
        values.append(line)
        if len(values) >= count:
            return values
    while len(values) < count:
        values.append("")
    return values


def find_prefixed_value(lines: list[str], prefix: str) -> str:
    """접두사로 시작하는 줄의 값을 반환한다."""

    for line in lines:
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip(" `")
    return ""


def normalize_backend_code(value: str) -> str:
    """표시 문자열을 저장소 코드로 변환한다."""

    lowered = str(value or "").strip().lower()
    if "supabase" in lowered:
        return "supabase"
    if "sqlite" in lowered:
        return "sqlite"
    return "unknown"


def select_app_frame(page: Page) -> Frame:
    """Streamlit 앱이 렌더링된 프레임을 찾는다."""

    for frame in page.frames:
        if "/~/+/" in frame.url:
            return frame
    raise RuntimeError("Streamlit 앱 프레임을 찾지 못했습니다.")


def body_text(frame: Frame, timeout_ms: int) -> str:
    """프레임 본문 텍스트를 읽는다."""

    return frame.locator("body").inner_text(timeout=timeout_ms)


def has_workspace_context(text: str) -> bool:
    """본문 텍스트에 작업공간 문맥이 보이는지 판별한다."""

    normalized = " ".join(extract_lines(text))
    markers = ("내 작업공간", "WORKSPACE CONTEXT", "로그인 계정")
    return any(marker in normalized for marker in markers) and "로그아웃" in normalized


def choose_button(
    frame: Frame,
    text: str,
    fallback_index: int | None = None,
    prefer_last: bool = False,
) -> Locator:
    """보이는 버튼 중 일치하는 버튼을 찾고, 필요하면 인덱스로 대체한다."""

    buttons = frame.locator("button")
    matched_buttons: list[Locator] = []
    for index in range(buttons.count()):
        button = buttons.nth(index)
        try:
            if not button.is_visible():
                continue
            if button.inner_text(timeout=1_500).strip() == text:
                matched_buttons.append(button)
        except Exception:
            continue
    if matched_buttons:
        return matched_buttons[-1] if prefer_last else matched_buttons[0]
    if fallback_index is not None and buttons.count() > fallback_index:
        return buttons.nth(fallback_index)
    raise RuntimeError(f"버튼을 찾지 못했습니다: {text}")


def choose_page_label(frame: Frame, page_name: str) -> Locator:
    """사이드바 페이지 레이블을 찾는다."""

    target_text = PAGE_LABELS[page_name]
    labels = frame.locator("label")
    for index in range(labels.count()):
        label = labels.nth(index)
        try:
            if label.inner_text(timeout=1_500).strip() == target_text:
                return label
        except Exception:
            continue
    fallback_index = PAGE_LABEL_INDEX[page_name]
    if labels.count() > fallback_index:
        return labels.nth(fallback_index)
    raise RuntimeError(f"페이지 레이블을 찾지 못했습니다: {target_text}")


def wait_for_workspace(page: Page, timeout_ms: int) -> Frame:
    """로그인 후 작업공간이 나타날 때까지 기다린다."""

    deadline = time.monotonic() + (timeout_ms / 1000)
    last_text = ""
    while time.monotonic() < deadline:
        frame = select_app_frame(page)
        last_text = body_text(frame, min(5_000, timeout_ms))
        if has_workspace_context(last_text):
            return frame
        page.wait_for_timeout(1_000)
    raise RuntimeError(f"로그인 후 작업공간을 찾지 못했습니다. 마지막 화면: {last_text[:600]}")


def login_if_needed(page: Page, email: str, password: str, timeout_ms: int) -> Frame:
    """로그인 페이지가 보이면 로그인하고, 이미 로그인 상태면 그대로 진행한다."""

    frame = select_app_frame(page)
    current_text = body_text(frame, timeout_ms)
    if has_workspace_context(current_text):
        return frame

    inputs = frame.locator("input")
    if inputs.count() < 2:
        raise RuntimeError("로그인 입력창을 찾지 못했습니다.")

    inputs.nth(0).fill(email)
    inputs.nth(1).fill(password)
    choose_button(frame, "로그인", fallback_index=6, prefer_last=True).click()
    page.wait_for_timeout(timeout_ms)
    return wait_for_workspace(page, timeout_ms)


def open_target_page(page: Page, frame: Frame, page_name: str, timeout_ms: int) -> Frame:
    """지정한 페이지로 이동한다."""

    choose_page_label(frame, page_name).click()
    page.wait_for_timeout(timeout_ms)
    return select_app_frame(page)


def build_summary(url: str, target_page: str, text: str) -> DeploymentSummary:
    """본문 텍스트에서 배포 상태 요약을 생성한다."""

    lines = extract_lines(text)
    backend_storage = find_value_after_label(lines, "데이터 저장소")
    interest_rollup, latest_interest_date = find_values_after_label(lines, "이자 롤업")
    snapshot_count, latest_snapshot_date = find_values_after_label(lines, "자산 스냅샷")
    status_message = ""
    for line in lines:
        if line.startswith("현재 배포본은 "):
            status_message = line
            break

    return DeploymentSummary(
        url=url,
        target_page=target_page,
        logged_in="로그인 계정" in text and "로그아웃" in text,
        workspace_visible=has_workspace_context(text),
        status_panel_visible="운영 상태" in text,
        backend_storage=backend_storage,
        backend_storage_code=normalize_backend_code(backend_storage),
        total_interest=find_value_after_label(lines, "누적 이자"),
        interest_rollup=interest_rollup,
        latest_interest_date=latest_interest_date,
        snapshot_count=snapshot_count,
        latest_snapshot_date=latest_snapshot_date,
        supabase_config_status=find_prefixed_value(lines, "Supabase 설정 감지:"),
        backend_override=find_prefixed_value(lines, "백엔드 강제 설정:"),
        reason=find_prefixed_value(lines, "감지 사유:"),
        status_message=status_message,
    )


def maybe_write_output(path_value: str | None, content: str) -> str | None:
    """출력 경로가 있으면 파일로 저장한다."""

    if not path_value:
        return None
    output_path = Path(path_value).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return str(output_path)


def maybe_capture_screenshot(page: Page, path_value: str | None) -> str | None:
    """스크린샷 경로가 있으면 이미지를 저장한다."""

    if not path_value:
        return None
    output_path = Path(path_value).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(output_path), full_page=True)
    return str(output_path)


def verify_deployment(args: argparse.Namespace) -> DeploymentSummary:
    """배포 웹 앱을 열고 상태를 검증한다."""

    if not args.email or not args.password:
        raise ValueError("--email/--password 또는 STREAMLIT_VERIFY_EMAIL/STREAMLIT_VERIFY_PASSWORD 가 필요합니다.")

    ensure_playwright_available()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 2200})
        page.goto(args.url, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(args.wait_ms)
        frame = login_if_needed(page, args.email, args.password, args.wait_ms)
        frame = open_target_page(page, frame, args.page, max(4_000, args.wait_ms // 2))
        text = body_text(frame, 15_000)
        summary = build_summary(args.url, args.page, text)
        summary.text_output = maybe_write_output(args.text_output, text)
        summary.screenshot_output = maybe_capture_screenshot(page, args.screenshot)
        browser.close()
        return summary


def main() -> int:
    """스크립트 진입점."""

    configure_stdout()
    args = parse_args()
    try:
        summary = verify_deployment(args)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    payload = asdict(summary)
    payload["ok"] = True
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if args.expect_backend != "any" and summary.backend_storage_code != args.expect_backend:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

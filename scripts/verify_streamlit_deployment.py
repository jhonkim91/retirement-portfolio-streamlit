from __future__ import annotations

import argparse
import json
import os
import sys
import time
import tomllib
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
}
PAGE_LABEL_INDEX = {
    "dashboard": 2,
    "trades": 3,
}
PAGE_READY_MARKERS = {
    "dashboard": ("자산 배분", "선택 종목 트렌드"),
    "trades": ("상품 등록", "예상 매입금액", "거래 기록"),
}
LOCAL_SECRETS_PATH = Path(".streamlit/secrets.toml")


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
    trade_log_count: str
    latest_trade_date: str
    cash_adjustment_net: str
    snapshot_count: str
    latest_snapshot_date: str
    supabase_config_status: str
    supabase_url_status: str
    supabase_key_status: str
    supabase_project: str
    missing_config: str
    backend_override: str
    reason: str
    status_message: str
    allocation_status: str
    onboarding_visible: bool
    onboarding_error: str
    hotfix_required: bool
    auth_error: str
    rate_limited: bool
    demo_button_clicked: bool
    demo_seeded: bool
    text_output: str | None = None
    screenshot_output: str | None = None


def load_local_streamlit_secrets() -> dict[str, Any]:
    """로컬 `.streamlit/secrets.toml` 값을 읽어 검증 기본값에 사용한다."""

    if not LOCAL_SECRETS_PATH.exists():
        return {}

    try:
        with LOCAL_SECRETS_PATH.open("rb") as file:
            data = tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError):
        return {}

    return data if isinstance(data, dict) else {}


def verify_secret(name: str, default: str = "") -> str:
    """환경 변수 우선, 없으면 로컬 Streamlit 시크릿에서 검증 값을 읽는다."""

    env_value = str(os.getenv(name, "")).strip()
    if env_value:
        return env_value

    local_value = load_local_streamlit_secrets().get(name)
    if local_value not in (None, ""):
        return str(local_value).strip()
    return str(default).strip()


def parse_args() -> argparse.Namespace:
    """명령행 인자를 해석한다."""

    parser = argparse.ArgumentParser(description="배포된 Streamlit 앱에 로그인해 저장소 상태를 검증한다.")
    parser.add_argument("--url", default=str(os.getenv("STREAMLIT_APP_URL", DEFAULT_APP_URL)).strip(), help="검증할 앱 URL")
    parser.add_argument("--email", default=verify_secret("STREAMLIT_VERIFY_EMAIL"), help="로그인 이메일")
    parser.add_argument("--password", default=verify_secret("STREAMLIT_VERIFY_PASSWORD"), help="로그인 비밀번호")
    parser.add_argument(
        "--page",
        choices=tuple(PAGE_LABELS),
        default="dashboard",
        help="로그인 후 이동할 페이지",
    )
    parser.add_argument(
        "--expect-backend",
        choices=("any", "sqlite", "supabase"),
        default="any",
        help="기대하는 저장소 종류",
    )
    parser.add_argument(
        "--expect-allocation-status",
        default="",
        help="대시보드 자산 배분 상태 칩에 기대하는 텍스트",
    )
    parser.add_argument("--screenshot", help="전체 페이지 스크린샷 저장 경로")
    parser.add_argument("--text-output", help="본문 텍스트 저장 경로")
    parser.add_argument("--debug-dir", help="실패 분석용 단계별 텍스트/스크린샷 저장 디렉터리")
    parser.add_argument(
        "--storage-state",
        help="Playwright storage state JSON 경로. 있으면 재사용하고, 로그인 성공 후 갱신한다.",
    )
    parser.add_argument("--wait-ms", type=int, default=DEFAULT_WAIT_MS, help="화면 전환 대기 시간(ms)")
    parser.add_argument(
        "--click-demo",
        action="store_true",
        help="?⑤낫???붾㈃???곕え ?곗씠??踰꾪듉???대┃?댁꽌 RLS ?⑥?吏? ?곗씠???앹꽦 ?щ?瑜?寃利앺븳??",
    )
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


def infer_backend_storage(lines: list[str]) -> str:
    """화면 문구에서 저장소 종류를 추정한다."""

    backend_storage = find_value_after_label(lines, "데이터 저장소")
    if backend_storage:
        return backend_storage

    backend_storage = find_prefixed_value(lines, "현재 저장소:")
    if backend_storage:
        return backend_storage

    for line in lines:
        if not line.startswith("현재 저장소는"):
            continue
        if "Supabase" in line:
            return "Supabase"
        if "SQLite" in line:
            return "SQLite"
    return ""


def find_config_source(lines: list[str], prefix: str) -> str:
    """설정 표시 줄에서 실제 값 출처만 추출한다."""

    value = find_prefixed_value(lines, prefix)
    if not value:
        return ""

    if "(" in value and ")" in value:
        suffix = value.split("(", 1)[1].split(")", 1)[0].strip()
        if suffix:
            return suffix
    return value


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
    return page.main_frame


def body_text(frame: Frame, timeout_ms: int) -> str:
    """프레임 본문 텍스트를 읽는다."""

    return frame.locator("body").inner_text(timeout=timeout_ms)


def has_workspace_context(text: str) -> bool:
    """본문 텍스트에 작업공간 문맥이 보이는지 판별한다."""

    normalized = " ".join(extract_lines(text))
    markers = ("내 작업공간", "WORKSPACE CONTEXT", "로그인 계정", "RetirementPort", "내 계좌")
    return any(marker in normalized for marker in markers) and "로그아웃" in normalized


def has_onboarding_context(text: str) -> bool:
    """로그인 후 첫 계좌 생성 전 온보딩 화면인지 판별한다."""

    normalized = " ".join(extract_lines(text))
    has_storage_marker = "현재 저장소:" in normalized or "현재 저장소는" in normalized
    required_markers = ("첫 계좌 만들기", "계좌 이름", "시작 현금")
    return has_storage_marker and all(marker in normalized for marker in required_markers)


def has_authenticated_context(text: str) -> bool:
    """로그인 이후 앱 내부 화면인지 판별한다."""

    return has_workspace_context(text) or has_onboarding_context(text)


def has_target_page_content(text: str, page_name: str) -> bool:
    """지정한 페이지의 핵심 마커가 보이는지 판별한다."""

    markers = PAGE_READY_MARKERS.get(page_name, ())
    if not markers:
        return True
    normalized = " ".join(extract_lines(text))
    return all(marker in normalized for marker in markers)


def extract_auth_error(lines: list[str]) -> str:
    """로그인 화면에 노출된 인증/제한 오류 문구를 추출한다."""

    markers = (
        "rate limit",
        "too many requests",
        "invalid login",
        "invalid credentials",
        "email not confirmed",
        "request rate limit reached",
    )
    for line in lines:
        lowered = line.lower()
        if any(marker in lowered for marker in markers):
            return line
    return ""


def resolve_optional_output_path(path_value: str | None) -> Path | None:
    """옵션 문자열이 있으면 절대 경로 `Path`로 변환한다."""

    if not path_value:
        return None
    return Path(path_value).expanduser().resolve()


def current_page_text(page: Page, timeout_ms: int = 5_000) -> str:
    """현재 페이지에서 읽을 수 있는 본문 텍스트를 최대한 회수한다."""

    try:
        return body_text(select_app_frame(page), timeout_ms)
    except Exception:
        pass

    try:
        return page.locator("body").inner_text(timeout=timeout_ms)
    except Exception:
        return ""


def capture_debug_artifacts(page: Page, debug_dir: str | None, step_name: str) -> dict[str, str]:
    """지정한 단계의 텍스트/스크린샷을 디버그 디렉터리에 저장한다."""

    output_dir = resolve_optional_output_path(debug_dir)
    if output_dir is None:
        return {}

    output_dir.mkdir(parents=True, exist_ok=True)
    normalized_name = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in step_name).strip("-")
    normalized_name = normalized_name or "debug"

    text_path = output_dir / f"{normalized_name}.txt"
    screenshot_path = output_dir / f"{normalized_name}.png"
    url_path = output_dir / f"{normalized_name}.url.txt"

    text_path.write_text(current_page_text(page), encoding="utf-8")
    url_path.write_text(page.url, encoding="utf-8")
    try:
        page.screenshot(path=str(screenshot_path), full_page=True)
    except Exception:
        pass

    return {
        "text": str(text_path),
        "screenshot": str(screenshot_path),
        "url": str(url_path),
    }


def format_debug_dir_hint(debug_dir: str | None) -> str:
    """디버그 디렉터리가 있으면 예외 메시지에 덧붙일 힌트를 만든다."""

    output_dir = resolve_optional_output_path(debug_dir)
    if output_dir is None:
        return ""
    return f" 디버그 산출물: {output_dir}"


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

    nav_links = frame.locator('a[data-testid="stSidebarNavLink"], [data-testid="stPageLink"] a')
    for index in range(nav_links.count()):
        link = nav_links.nth(index)
        try:
            if not link.is_visible():
                continue
            link_lines = extract_lines(link.inner_text(timeout=1_500))
            if target_text in link_lines:
                return link
        except Exception:
            continue

    labels = frame.locator("label")
    for index in range(labels.count()):
        label = labels.nth(index)
        try:
            if label.is_visible() and label.inner_text(timeout=1_500).strip() == target_text:
                return label
        except Exception:
            continue
    fallback_index = PAGE_LABEL_INDEX[page_name]
    if labels.count() > fallback_index:
        return labels.nth(fallback_index)
    raise RuntimeError(f"페이지 레이블을 찾지 못했습니다: {target_text}")


def click_demo_button(frame: Frame) -> bool:
    """?⑤낫???붾㈃???곕え ?곗씠??踰꾪듉???대┃?섍퀬 ?깃났 ?щ?瑜?諛섑솚?쒕떎."""

    buttons = frame.locator("button")
    for index in range(buttons.count()):
        button = buttons.nth(index)
        try:
            if not button.is_visible():
                continue
            if "데모 데이터 불러오기" in button.inner_text(timeout=1_500):
                button.click()
                return True
        except Exception:
            continue
    return False


def wait_for_authenticated_app(page: Page, timeout_ms: int) -> Frame:
    """로그인 후 앱 내부 화면이 나타날 때까지 기다린다."""

    deadline = time.monotonic() + (timeout_ms / 1000)
    last_text = ""
    while time.monotonic() < deadline:
        frame = select_app_frame(page)
        last_text = body_text(frame, min(5_000, timeout_ms))
        if has_authenticated_context(last_text):
            return frame
        page.wait_for_timeout(1_000)
    lines = extract_lines(last_text)
    auth_error = extract_auth_error(lines)
    if auth_error:
        raise RuntimeError(f"로그인 후 앱 내부 화면을 찾지 못했습니다. 인증 오류: {auth_error}")
    raise RuntimeError(f"로그인 후 앱 내부 화면을 찾지 못했습니다. 마지막 화면: {last_text[:600]}")


def login_if_needed(page: Page, email: str, password: str, timeout_ms: int) -> Frame:
    """로그인 페이지가 보이면 로그인하고, 이미 로그인 상태면 그대로 진행한다."""

    frame = select_app_frame(page)
    current_text = body_text(frame, timeout_ms)
    if has_authenticated_context(current_text):
        return frame

    inputs = frame.locator("input")
    if inputs.count() < 2:
        raise RuntimeError("로그인 입력창을 찾지 못했습니다.")

    inputs.nth(0).fill(email)
    inputs.nth(1).fill(password)
    choose_button(frame, "로그인", fallback_index=6, prefer_last=True).click()
    page.wait_for_timeout(timeout_ms)
    return wait_for_authenticated_app(page, timeout_ms)


def open_target_page(page: Page, frame: Frame, page_name: str, timeout_ms: int) -> Frame:
    """지정한 페이지로 이동한다."""

    choose_page_label(frame, page_name).click()
    page.wait_for_timeout(timeout_ms)
    return select_app_frame(page)


def wait_for_target_page(page: Page, page_name: str, timeout_ms: int) -> tuple[Frame, str]:
    """지정한 페이지의 핵심 본문이 렌더링될 때까지 기다린다."""

    deadline = time.monotonic() + (timeout_ms / 1000)
    last_text = ""
    last_frame = select_app_frame(page)
    while time.monotonic() < deadline:
        last_frame = select_app_frame(page)
        last_text = body_text(last_frame, min(5_000, timeout_ms))
        if has_target_page_content(last_text, page_name):
            return last_frame, last_text
        page.wait_for_timeout(1_000)
    markers = ", ".join(PAGE_READY_MARKERS.get(page_name, ()))
    raise RuntimeError(f"{page_name} 페이지 핵심 마커를 찾지 못했습니다: {markers}. 마지막 화면: {last_text[:600]}")


def extract_onboarding_error(lines: list[str]) -> str:
    """?⑤낫???붾㈃??蹂댁씠?붾뒗 ?ㅻ쪟 臾몄옄?댁쓣 寃異쒗븳??"""

    for line in lines:
        lowered = line.lower()
        if "supabase post accounts" in lowered or "row-level security" in lowered or "owner_user_id" in lowered:
            return line
    return ""


def build_summary(url: str, target_page: str, text: str) -> DeploymentSummary:
    """본문 텍스트에서 배포 상태 요약을 생성한다."""

    lines = extract_lines(text)
    backend_storage = infer_backend_storage(lines)
    status_panel_visible = "운영 상태" in text
    if status_panel_visible:
        trade_log_count, latest_trade_date = find_values_after_label(lines, "거래 기록")
        snapshot_count, latest_snapshot_date = find_values_after_label(lines, "자산 스냅샷")
    else:
        trade_log_count, latest_trade_date = "", ""
        snapshot_count, latest_snapshot_date = "", ""
    onboarding_visible = has_onboarding_context(text)
    onboarding_error = extract_onboarding_error(lines)
    hotfix_required = "owner_user_id" in onboarding_error.lower() or "row-level security" in onboarding_error.lower()
    auth_error = extract_auth_error(lines)
    rate_limited = "rate limit" in auth_error.lower() or "too many requests" in auth_error.lower()
    demo_seeded = has_workspace_context(text)
    status_message = ""
    for line in lines:
        if line.startswith("현재 배포본은 "):
            status_message = line
            break
    allocation_status = find_value_after_label(lines, "자산 배분")
    if allocation_status in {"-", "+"}:
        allocation_status = ""

    return DeploymentSummary(
        url=url,
        target_page=target_page,
        logged_in=has_authenticated_context(text),
        workspace_visible=has_workspace_context(text),
        status_panel_visible=status_panel_visible,
        backend_storage=backend_storage,
        backend_storage_code=normalize_backend_code(backend_storage),
        trade_log_count=trade_log_count,
        latest_trade_date=latest_trade_date,
        cash_adjustment_net=find_value_after_label(lines, "현금 수정 순반영"),
        snapshot_count=snapshot_count,
        latest_snapshot_date=latest_snapshot_date,
        supabase_config_status=find_prefixed_value(lines, "Supabase 설정 감지:"),
        supabase_url_status=find_config_source(lines, "SUPABASE_URL 설정:"),
        supabase_key_status=find_config_source(lines, "SUPABASE_KEY 설정:"),
        supabase_project=find_prefixed_value(lines, "Supabase 프로젝트:"),
        missing_config=find_prefixed_value(lines, "누락 설정:"),
        backend_override=find_prefixed_value(lines, "백엔드 강제 설정:"),
        reason=find_prefixed_value(lines, "감지 사유:"),
        status_message=status_message,
        allocation_status=allocation_status,
        onboarding_visible=onboarding_visible,
        onboarding_error=onboarding_error,
        hotfix_required=hotfix_required,
        auth_error=auth_error,
        rate_limited=rate_limited,
        demo_button_clicked=False,
        demo_seeded=demo_seeded,
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
        context_kwargs: dict[str, Any] = {"viewport": {"width": 1440, "height": 2200}}
        storage_state_path = resolve_optional_output_path(args.storage_state)
        if storage_state_path is not None and storage_state_path.exists():
            context_kwargs["storage_state"] = str(storage_state_path)
        context = browser.new_context(**context_kwargs)
        page = context.new_page()

        try:
            page.goto(args.url, wait_until="domcontentloaded", timeout=120_000)
            page.wait_for_timeout(args.wait_ms)
            capture_debug_artifacts(page, args.debug_dir, "01-opened")

            frame = login_if_needed(page, args.email, args.password, args.wait_ms)
            if storage_state_path is not None:
                storage_state_path.parent.mkdir(parents=True, exist_ok=True)
                context.storage_state(path=str(storage_state_path))
            capture_debug_artifacts(page, args.debug_dir, "02-authenticated")

            text = body_text(frame, 15_000)
            demo_button_clicked = False
            if args.click_demo and has_onboarding_context(text):
                demo_button_clicked = click_demo_button(frame)
                if demo_button_clicked:
                    page.wait_for_timeout(args.wait_ms)
                    frame = select_app_frame(page)
                    text = body_text(frame, 15_000)
                    capture_debug_artifacts(page, args.debug_dir, "03-after-demo")
            if has_workspace_context(text):
                frame = open_target_page(page, frame, args.page, max(4_000, args.wait_ms // 2))
                frame, text = wait_for_target_page(page, args.page, max(12_000, args.wait_ms * 2))
                capture_debug_artifacts(page, args.debug_dir, f"04-page-{args.page}")
            summary = build_summary(args.url, args.page, text)
            summary.demo_button_clicked = demo_button_clicked
            summary.demo_seeded = has_workspace_context(text)
            summary.text_output = maybe_write_output(args.text_output, text)
            summary.screenshot_output = maybe_capture_screenshot(page, args.screenshot)
            return summary
        except Exception as exc:
            capture_debug_artifacts(page, args.debug_dir, "99-error")
            last_text = current_page_text(page)
            auth_error = extract_auth_error(extract_lines(last_text))
            if auth_error:
                raise RuntimeError(
                    f"{exc} 마지막 인증 화면 오류: {auth_error}.{format_debug_dir_hint(args.debug_dir)}"
                ) from exc
            raise RuntimeError(f"{exc}.{format_debug_dir_hint(args.debug_dir)}") from exc
        finally:
            context.close()
            browser.close()


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
    if args.expect_allocation_status and summary.allocation_status != args.expect_allocation_status:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

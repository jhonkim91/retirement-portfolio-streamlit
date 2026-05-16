from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

try:
    import yaml
except ImportError:  # pragma: no cover - optional dev dependency
    yaml = None

try:
    from playwright.sync_api import Browser, Frame, Locator, sync_playwright
except ImportError:  # pragma: no cover - optional dev dependency
    Browser = Any  # type: ignore[assignment]
    Frame = Any  # type: ignore[assignment]
    Locator = Any  # type: ignore[assignment]
    sync_playwright = None


APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = APP_ROOT / "config" / "capture_blocks.yaml"
DEFAULT_OUT_DIR = APP_ROOT / "artifacts" / "ui_captures"
DEFAULT_LOCAL_URL = "http://localhost:8501/?demo=1&capture=1"
DEFAULT_WAIT_MS = 30_000
CAPTURE_REFERENCE_DATE = "2026-05-15"
SIDEBAR_EXPANDED_MIN_WIDTH = 1024
VIEWPORTS: dict[str, dict[str, int]] = {
    "desktop": {"width": 1440, "height": 1200},
    "tablet": {"width": 768, "height": 1024},
    "mobile": {"width": 390, "height": 844},
}
CAPTURE_STABILITY_CSS = """
*, *::before, *::after {
    animation: none !important;
    animation-delay: 0s !important;
    animation-duration: 0s !important;
    transition: none !important;
    transition-delay: 0s !important;
    transition-duration: 0s !important;
    scroll-behavior: auto !important;
    caret-color: transparent !important;
}

[data-testid="stSpinner"],
[data-testid="stStatusWidget"],
[data-testid="stProgress"],
[data-testid="stSkeleton"] {
    animation: none !important;
    transition: none !important;
}
"""
CAPTURE_INIT_SCRIPT = f"""
(() => {{
  const css = {json.dumps(CAPTURE_STABILITY_CSS)};
  const install = () => {{
    if (!document.head || document.getElementById('portfolio-ui-capture-stability')) return;
    const style = document.createElement('style');
    style.id = 'portfolio-ui-capture-stability';
    style.textContent = css;
    document.head.appendChild(style);
  }};
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', install, {{ once: true }});
  }} else {{
    install();
  }}
}})();
"""
STREAMLIT_BUSY_SELECTORS = (
    '[data-testid="stSpinner"]',
    '[data-testid="stProgress"]',
    '[data-testid="stSkeleton"]',
    '.stSpinner',
)


@dataclass(frozen=True)
class CaptureBlock:
    """YAML에 정의된 UI 캡처 블록 설정이다."""

    name: str
    selector: str
    output: str
    required: bool = False


@dataclass
class LocalServer:
    """캡처 스크립트가 직접 실행한 Streamlit 프로세스 정보다."""

    process: subprocess.Popen[Any]
    log_file: Any
    log_path: Path


def parse_args() -> argparse.Namespace:
    """명령행 옵션을 파싱한다."""

    parser = argparse.ArgumentParser(description="Streamlit 앱 UI 캡처 산출물을 생성한다.")
    parser.add_argument("--url", default="", help="접속할 앱 URL. 지정하지 않으면 CAPTURE_BASE_URL 또는 로컬 앱을 사용한다.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="캡처 산출물 루트 디렉터리")
    parser.add_argument("--viewport", choices=("desktop", "tablet", "mobile", "all"), default="desktop", help="캡처할 viewport")
    parser.add_argument("--strict", action="store_true", help="required=false 블록 누락도 실패로 처리한다.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="캡처 블록 YAML 설정 경로")
    parser.add_argument("--wait-ms", type=int, default=DEFAULT_WAIT_MS, help="페이지와 selector 대기 시간(ms)")
    return parser.parse_args()


def load_capture_blocks(config_path: Path) -> list[CaptureBlock]:
    """캡처 블록 YAML을 읽어 검증된 설정 목록으로 반환한다."""

    if yaml is None:
        raise RuntimeError("pyyaml이 설치되어 있지 않습니다. `python -m pip install -r requirements-dev.txt`를 실행해 주세요.")
    if not config_path.exists():
        raise FileNotFoundError(f"캡처 설정 파일을 찾지 못했습니다: {config_path}")

    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    raw_blocks = config.get("blocks")
    if not isinstance(raw_blocks, list):
        raise ValueError("capture_blocks.yaml에는 `blocks` 목록이 필요합니다.")

    blocks: list[CaptureBlock] = []
    for index, raw_block in enumerate(raw_blocks, start=1):
        if not isinstance(raw_block, dict):
            raise ValueError(f"blocks[{index}] 항목은 객체여야 합니다.")
        name = str(raw_block.get("name") or "").strip()
        selector = str(raw_block.get("selector") or "").strip()
        output = str(raw_block.get("output") or "").strip()
        required = bool(raw_block.get("required", False))
        if not name or not selector or not output:
            raise ValueError(f"blocks[{index}]에는 name, selector, output이 모두 필요합니다.")
        if Path(output).is_absolute() or ".." in Path(output).parts:
            raise ValueError(f"blocks[{index}] output은 blocks 디렉터리 내부 상대 경로여야 합니다: {output}")
        blocks.append(CaptureBlock(name=name, selector=selector, output=output, required=required))
    return blocks


def resolve_viewports(viewport_option: str) -> list[tuple[str, dict[str, int]]]:
    """CLI viewport 옵션을 실제 캡처할 viewport 목록으로 변환한다."""

    if viewport_option == "all":
        return list(VIEWPORTS.items())
    return [(viewport_option, VIEWPORTS[viewport_option])]


def run_git_command(*args: str) -> str:
    """git 명령 결과를 한 줄 문자열로 반환한다."""

    try:
        result = subprocess.run(
            ["git", *args],
            cwd=APP_ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return "unknown"
    return result.stdout.strip() or "unknown"


def path_for_manifest(path: Path) -> str:
    """manifest에 기록할 저장소 기준 상대 경로를 만든다."""

    try:
        return str(path.resolve().relative_to(APP_ROOT))
    except ValueError:
        return str(path.resolve())


def url_is_reachable(url: str, timeout_seconds: float = 1.5) -> bool:
    """지정 URL이 HTTP 응답을 반환하는지 확인한다."""

    try:
        request = Request(url, headers={"User-Agent": "ui-capture/1.0"})
        with urlopen(request, timeout=timeout_seconds) as response:
            return 200 <= int(response.status) < 500
    except (OSError, URLError, ValueError):
        return False


def wait_for_url(url: str, timeout_seconds: float) -> None:
    """지정 URL이 응답할 때까지 대기한다."""

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if url_is_reachable(url):
            return
        time.sleep(0.5)
    raise RuntimeError(f"Streamlit 앱이 제한 시간 안에 응답하지 않았습니다: {url}")


def start_streamlit_if_needed(url: str, capture_root: Path) -> LocalServer | None:
    """외부 URL이 없을 때 로컬 Streamlit 앱을 실행한다."""

    if url_is_reachable(url):
        print(f"[capture] 기존 앱 URL에 접속합니다: {url}")
        return None

    parsed = urlparse(url)
    port = parsed.port or 8501
    runtime_dir = capture_root / "_runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    log_path = runtime_dir / "streamlit-server.log"
    db_path = runtime_dir / "capture-portfolio.db"
    log_file = log_path.open("w", encoding="utf-8")

    env = os.environ.copy()
    env.setdefault("PORTFOLIO_BACKEND", "sqlite")
    env.setdefault("RETIREMENT_DB_PATH", str(db_path))
    env.setdefault("PORTFOLIO_CAPTURE_REFERENCE_DATE", CAPTURE_REFERENCE_DATE)
    env.setdefault("PORTFOLIO_CAPTURE_MODE", "1")
    env.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")

    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.headless",
        "true",
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(port),
        "--server.fileWatcherType",
        "none",
    ]
    print(f"[capture] 로컬 Streamlit 앱을 실행합니다: {' '.join(command)}")
    process = subprocess.Popen(
        command,
        cwd=APP_ROOT,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_for_url(url, timeout_seconds=45)
    except Exception:
        stop_streamlit_server(LocalServer(process=process, log_file=log_file, log_path=log_path))
        raise
    return LocalServer(process=process, log_file=log_file, log_path=log_path)


def stop_streamlit_server(server: LocalServer | None) -> None:
    """캡처 스크립트가 실행한 Streamlit 프로세스를 종료한다."""

    if server is None:
        return
    process = server.process
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
    server.log_file.close()


def ensure_playwright_available() -> None:
    """Python Playwright 런타임 설치 여부를 확인한다."""

    if sync_playwright is None:
        raise RuntimeError(
            "playwright가 설치되어 있지 않습니다. "
            "`python -m pip install -r requirements-dev.txt`와 `python -m playwright install chromium`을 실행해 주세요."
        )


def install_capture_init_script(page: Any) -> None:
    """페이지 로드 전에 캡처 안정화 CSS를 주입하도록 예약한다."""

    try:
        page.add_init_script(CAPTURE_INIT_SCRIPT)
    except Exception:
        return


def inject_capture_stability_styles(page: Any) -> None:
    """현재 페이지와 iframe에 animation/transition 비활성화 CSS를 주입한다."""

    for frame in list(getattr(page, "frames", []) or []):
        try:
            frame.add_style_tag(content=CAPTURE_STABILITY_CSS)
        except Exception:
            continue


def wait_for_animation_frames(page: Any) -> None:
    """브라우저 레이아웃이 두 번 이상 갱신될 때까지 짧게 대기한다."""

    try:
        page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
        )
    except Exception:
        return


def visible_busy_count(frame: Frame) -> int:
    """frame 안에 보이는 Streamlit loading/spinner 요소 개수를 반환한다."""

    selector = ",".join(STREAMLIT_BUSY_SELECTORS)
    try:
        return int(
            frame.evaluate(
                """
                (selector) => Array.from(document.querySelectorAll(selector)).filter((element) => {
                  const rect = element.getBoundingClientRect();
                  const style = window.getComputedStyle(element);
                  return rect.width > 0
                    && rect.height > 0
                    && style.display !== 'none'
                    && style.visibility !== 'hidden'
                    && Number(style.opacity || 1) !== 0;
                }).length
                """,
                selector,
            )
        )
    except Exception:
        return 0


def wait_for_streamlit_idle(page: Any, wait_ms: int) -> None:
    """Streamlit spinner, progress, skeleton이 사라질 때까지 대기한다."""

    deadline = time.monotonic() + (wait_ms / 1000)
    while time.monotonic() < deadline:
        busy_count = sum(visible_busy_count(frame) for frame in list(getattr(page, "frames", []) or []))
        if busy_count == 0:
            return
        time.sleep(0.25)
    print("[capture] warning: loading/spinner 요소가 제한 시간 안에 사라지지 않았습니다.", file=sys.stderr)


def reset_scroll_positions(page: Any) -> None:
    """full page 캡처 전 window와 Streamlit 내부 스크롤 컨테이너를 최상단으로 되돌린다."""

    script = """
    () => {
      window.scrollTo(0, 0);
      document.documentElement.scrollTop = 0;
      document.body.scrollTop = 0;
      for (const element of Array.from(document.querySelectorAll('*'))) {
        if (element.scrollTop > 0) element.scrollTop = 0;
        if (element.scrollLeft > 0) element.scrollLeft = 0;
      }
    }
    """
    for frame in list(getattr(page, "frames", []) or []):
        try:
            frame.evaluate(script)
        except Exception:
            continue
    wait_for_animation_frames(page)


def ensure_sidebar_default_state(page: Any, viewport_width: int) -> None:
    """캡처 전 Streamlit sidebar를 viewport별 기본 상태로 고정한다."""

    should_expand = int(viewport_width) >= SIDEBAR_EXPANDED_MIN_WIDTH
    try:
        changed = bool(
            page.evaluate(
                """
                (shouldExpand) => {
                  const isVisible = (element) => {
                    if (!element) return false;
                    const rect = element.getBoundingClientRect();
                    const style = window.getComputedStyle(element);
                    return rect.width > 0
                      && rect.height > 0
                      && style.display !== 'none'
                      && style.visibility !== 'hidden'
                      && Number(style.opacity || 1) !== 0;
                  };
                  const clickFirst = (selectors, pattern) => {
                    for (const selector of selectors) {
                      for (const element of Array.from(document.querySelectorAll(selector))) {
                        const label = [
                          element.getAttribute('aria-label') || '',
                          element.getAttribute('title') || '',
                          element.textContent || ''
                        ].join(' ');
                        if (isVisible(element) && pattern.test(label)) {
                          element.click();
                          return true;
                        }
                      }
                    }
                    return false;
                  };
                  const sidebar = document.querySelector('[data-testid="stSidebar"]');
                  const sidebarVisible = isVisible(sidebar);
                  if (shouldExpand && !sidebarVisible) {
                    return clickFirst(
                      [
                        '[data-testid="collapsedControl"] button',
                        'button[aria-label]',
                        'button[title]'
                      ],
                      /open sidebar|expand sidebar|사이드바 열기|sidebar/i
                    );
                  }
                  if (!shouldExpand && sidebarVisible) {
                    return clickFirst(
                      [
                        '[data-testid="stSidebar"] button[aria-label]',
                        '[data-testid="stSidebar"] button[title]',
                        'button[aria-label]',
                        'button[title]'
                      ],
                      /close sidebar|collapse sidebar|사이드바 닫기/i
                    );
                  }
                  return false;
                }
                """,
                should_expand,
            )
        )
    except Exception:
        changed = False
    state_label = "expanded" if should_expand else "collapsed"
    print(f"[capture] sidebar default state: {state_label}{' (updated)' if changed else ''}")
    if changed:
        page.wait_for_timeout(600)


def frame_selector_score(frame: Frame, blocks: list[CaptureBlock]) -> int:
    """frame 안에서 캡처 selector가 몇 개 발견되는지 계산한다."""

    score = 0
    for block in blocks:
        try:
            if frame.locator(block.selector).count() > 0:
                score += 1
        except Exception:
            continue
    return score


def select_capture_frame(page: Any, blocks: list[CaptureBlock], timeout_ms: int) -> Frame:
    """캡처 selector가 가장 많이 존재하는 앱 본문 frame을 선택한다."""

    deadline = time.monotonic() + (timeout_ms / 1000)
    best_frame = page.main_frame
    best_score = 0
    while time.monotonic() < deadline:
        frames = [page.main_frame, *[frame for frame in page.frames if frame is not page.main_frame]]
        for frame in frames:
            score = frame_selector_score(frame, blocks)
            if score > best_score:
                best_frame = frame
                best_score = score
        if best_score > 0:
            return best_frame
        time.sleep(0.5)
    return best_frame


def first_visible_locator(frame: Frame, selector: str) -> Locator | None:
    """selector와 일치하는 첫 번째 visible locator를 반환한다."""

    locator = frame.locator(selector)
    try:
        count = locator.count()
    except Exception:
        return None
    for index in range(min(count, 20)):
        candidate = locator.nth(index)
        try:
            if candidate.is_visible(timeout=500):
                return candidate
        except Exception:
            continue
    return None


def wait_for_required_blocks(frame: Frame, blocks: list[CaptureBlock], *, strict: bool, timeout_ms: int) -> list[CaptureBlock]:
    """필수 캡처 블록이 화면에 나타날 때까지 대기하고 누락 목록을 반환한다."""

    required_blocks = [block for block in blocks if block.required or strict]
    if not required_blocks:
        return []

    deadline = time.monotonic() + (timeout_ms / 1000)
    missing_blocks = required_blocks
    while time.monotonic() < deadline:
        missing_blocks = [block for block in required_blocks if first_visible_locator(frame, block.selector) is None]
        if not missing_blocks:
            return []
        time.sleep(0.5)
    return missing_blocks


def wait_for_page_settle(page: Any, wait_ms: int) -> None:
    """Streamlit 초기 렌더링과 차트 렌더링이 안정화될 시간을 준다."""

    try:
        page.wait_for_load_state("domcontentloaded", timeout=wait_ms)
    except Exception:
        pass
    try:
        page.wait_for_load_state("networkidle", timeout=min(wait_ms, 8_000))
    except Exception:
        pass
    try:
        page.evaluate("() => document.fonts ? document.fonts.ready : true")
    except Exception:
        pass
    inject_capture_stability_styles(page)
    wait_for_streamlit_idle(page, wait_ms)
    wait_for_animation_frames(page)
    page.wait_for_timeout(2_500)
    wait_for_animation_frames(page)


def wait_for_chart_canvas(page: Any, wait_ms: int) -> None:
    """ECharts 같은 canvas 기반 컴포넌트가 있으면 렌더링을 짧게 기다린다."""

    deadline = time.monotonic() + (min(wait_ms, 10_000) / 1000)
    while time.monotonic() < deadline:
        for frame in list(getattr(page, "frames", []) or []):
            try:
                locator = first_visible_locator(frame, "canvas")
            except Exception:
                locator = None
            if locator is not None:
                page.wait_for_timeout(2_000)
                wait_for_animation_frames(page)
                return
        time.sleep(0.25)
    page.wait_for_timeout(2_000)


def query_flag_enabled(url: str, key: str) -> bool:
    """URL query parameter가 캡처 안전 모드 값을 포함하는지 확인한다."""

    values = parse_qs(urlparse(url).query).get(key, [])
    return any(str(value).strip().lower() in {"1", "true", "yes", "demo"} for value in values)


def capture_viewport(
    browser: Browser,
    *,
    url: str,
    timestamp: str,
    viewport_name: str,
    viewport_size: dict[str, int],
    viewport_dir: Path,
    blocks: list[CaptureBlock],
    strict: bool,
    wait_ms: int,
    page: Any | None = None,
) -> bool:
    """단일 viewport의 전체 화면과 블록별 스크린샷을 생성한다."""

    viewport_dir.mkdir(parents=True, exist_ok=True)
    blocks_dir = viewport_dir / "blocks"
    blocks_dir.mkdir(parents=True, exist_ok=True)
    full_page_path = viewport_dir / "full_page.png"
    manifest_path = viewport_dir / "manifest.json"
    missing_selectors: list[dict[str, str]] = []
    captured_blocks: list[dict[str, Any]] = []
    success = True
    error_message = ""

    manifest: dict[str, Any] = {
        "capture_timestamp": timestamp,
        "git_commit_hash": run_git_command("rev-parse", "HEAD"),
        "branch_name": run_git_command("rev-parse", "--abbrev-ref", "HEAD"),
        "app_url": url,
        "viewport": {"name": viewport_name, **viewport_size},
        "full_page_output_path": path_for_manifest(full_page_path),
        "blocks": captured_blocks,
        "missing_selectors": missing_selectors,
        "strict": strict,
        "safety_mode": {
            "demo_query": query_flag_enabled(url, "demo"),
            "capture_query": query_flag_enabled(url, "capture"),
        },
        "status": "running",
    }

    owns_context = page is None
    context = browser.new_context(viewport=viewport_size, device_scale_factor=1) if owns_context else None
    active_page = page or context.new_page()
    try:
        print(f"[capture] {viewport_name} 접속: {url}")
        install_capture_init_script(active_page)
        active_page.set_viewport_size(viewport_size)
        current_url = str(getattr(active_page, "url", "") or "")
        if current_url and current_url != "about:blank":
            active_page.wait_for_timeout(2_000)
        else:
            active_page.goto(url, wait_until="domcontentloaded", timeout=wait_ms)
        wait_for_page_settle(active_page, wait_ms)
        ensure_sidebar_default_state(active_page, int(viewport_size["width"]))
        wait_for_page_settle(active_page, wait_ms)
        frame = select_capture_frame(active_page, blocks, timeout_ms=min(wait_ms, 10_000))
        missing_required = wait_for_required_blocks(frame, blocks, strict=strict, timeout_ms=wait_ms)
        for block in missing_required:
            print(
                f"[capture] missing selector before block capture: "
                f"viewport={viewport_name} name={block.name} selector={block.selector} required=true",
                file=sys.stderr,
            )
        wait_for_chart_canvas(active_page, wait_ms)
        wait_for_streamlit_idle(active_page, wait_ms)
        inject_capture_stability_styles(active_page)
        reset_scroll_positions(active_page)

        active_page.screenshot(path=str(full_page_path), full_page=True)
        for block in blocks:
            block_path = blocks_dir / block.output
            entry = {
                **asdict(block),
                "output_path": path_for_manifest(block_path),
                "status": "pending",
                "message": "",
            }
            captured_blocks.append(entry)

            locator = first_visible_locator(frame, block.selector)
            if locator is None:
                entry["status"] = "missing"
                entry["message"] = "selector를 찾지 못했거나 visible 상태가 아닙니다."
                missing_selectors.append({"name": block.name, "selector": block.selector})
                if block.required or strict:
                    success = False
                    print(
                        f"[capture] missing selector: viewport={viewport_name} "
                        f"name={block.name} selector={block.selector} required={str(block.required).lower()}",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f"[capture] optional selector 누락: viewport={viewport_name} "
                        f"name={block.name} selector={block.selector}",
                        file=sys.stderr,
                    )
                continue

            try:
                locator.scroll_into_view_if_needed(timeout=5_000)
                locator.screenshot(path=str(block_path), timeout=wait_ms)
            except Exception as exc:
                entry["status"] = "failed"
                entry["message"] = str(exc)
                if block.required or strict:
                    success = False
                else:
                    print(f"[capture] optional block 캡처 실패: {block.name}: {exc}", file=sys.stderr)
                continue

            entry["status"] = "success"

    except Exception as exc:
        success = False
        error_message = str(exc)
    finally:
        if owns_context and context is not None:
            context.close()

    manifest["status"] = "success" if success else "failed"
    if error_message:
        manifest["error"] = error_message
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if error_message:
        print(f"[capture] {viewport_name} 실패: {error_message}", file=sys.stderr)
    if missing_selectors:
        missing_summary = ", ".join(f"{item['name']}={item['selector']}" for item in missing_selectors)
        print(f"[capture] {viewport_name} missing selectors: {missing_summary}", file=sys.stderr)
    if not error_message:
        print(f"[capture] {viewport_name} manifest: {manifest_path}")
    return success


def resolve_capture_url(cli_url: str) -> tuple[str, bool]:
    """CLI, 환경 변수, 로컬 기본값 순서로 캡처 URL을 결정한다."""

    explicit_url = str(cli_url or "").strip()
    if explicit_url:
        return explicit_url, True
    env_url = str(os.getenv("CAPTURE_BASE_URL", "")).strip()
    if env_url:
        return env_url, True
    return DEFAULT_LOCAL_URL, False


def main() -> int:
    """캡처 작업을 실행하고 성공 여부를 프로세스 종료 코드로 반환한다."""

    args = parse_args()
    ensure_playwright_available()

    config_path = Path(args.config).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    capture_root = out_dir / timestamp
    capture_root.mkdir(parents=True, exist_ok=True)
    blocks = load_capture_blocks(config_path)
    url, external_url = resolve_capture_url(args.url)
    if not query_flag_enabled(url, "demo") or not query_flag_enabled(url, "capture"):
        print(
            "[capture] 경고: URL에 demo=1&capture=1이 모두 포함되어 있지 않습니다. "
            "실제 사용자 데이터가 화면에 노출되지 않는지 확인하세요.",
            file=sys.stderr,
        )

    server: LocalServer | None = None
    if not external_url:
        server = start_streamlit_if_needed(url, capture_root)

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                viewports = resolve_viewports(args.viewport)
                if len(viewports) > 1:
                    context = browser.new_context(viewport=viewports[0][1], device_scale_factor=1)
                    shared_page = context.new_page()
                    try:
                        results = [
                            capture_viewport(
                                browser,
                                url=url,
                                timestamp=timestamp,
                                viewport_name=viewport_name,
                                viewport_size=viewport_size,
                                viewport_dir=capture_root / viewport_name,
                                blocks=blocks,
                                strict=bool(args.strict),
                                wait_ms=int(args.wait_ms),
                                page=shared_page,
                            )
                            for viewport_name, viewport_size in viewports
                        ]
                    finally:
                        context.close()
                else:
                    results = [
                        capture_viewport(
                            browser,
                            url=url,
                            timestamp=timestamp,
                            viewport_name=viewport_name,
                            viewport_size=viewport_size,
                            viewport_dir=capture_root / viewport_name,
                            blocks=blocks,
                            strict=bool(args.strict),
                            wait_ms=int(args.wait_ms),
                        )
                        for viewport_name, viewport_size in viewports
                    ]
            finally:
                browser.close()
    finally:
        stop_streamlit_server(server)

    print(f"[capture] 산출물 루트: {capture_root}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

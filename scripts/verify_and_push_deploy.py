from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EXCLUDED_PATTERNS = (
    "artifacts/*",
    ".playtools/*",
    ".playtools2/*",
    ".playwright-browsers/*",
    ".vscode/*",
    "__pycache__/*",
    "data/portfolio.db",
    "post-migration-dashboard.txt",
    "streamlit_echarts/*",
    "tmp_source.png",
)


@dataclass(frozen=True)
class RepoChange:
    """`git status --short` 한 줄을 정규화한 변경 정보."""

    path: str
    status: str
    is_untracked: bool


@dataclass(frozen=True)
class ChangePlan:
    """배포 스크립트가 다룰 변경 파일 분류 결과."""

    stage_paths: tuple[str, ...]
    blocked_untracked_paths: tuple[str, ...]
    excluded_paths: tuple[str, ...]


@dataclass(frozen=True)
class CommandSummary:
    """실행한 명령과 종료 코드를 기록한다."""

    command: str
    returncode: int


class CommandExecutionError(RuntimeError):
    """외부 명령 실패를 상위 흐름에 전달한다."""

    def __init__(self, command: list[str], completed: subprocess.CompletedProcess[str]) -> None:
        self.command = command
        self.completed = completed
        message = (
            f"명령이 실패했습니다: {' '.join(command)}\n"
            f"exit_code={completed.returncode}\n"
            f"stdout={completed.stdout.strip()}\n"
            f"stderr={completed.stderr.strip()}"
        )
        super().__init__(message)


def parse_args() -> argparse.Namespace:
    """명령행 인자를 해석한다."""

    parser = argparse.ArgumentParser(
        description="저장소 검증 통과 후 커밋, 푸시, 배포 검증까지 자동으로 실행한다."
    )
    parser.add_argument("--remote", default="origin", help="푸시 대상 Git 원격 이름")
    parser.add_argument("--branch", default="", help="푸시 대상 브랜치. 비우면 현재 브랜치를 사용한다.")
    parser.add_argument("--commit-message", default="", help="커밋 메시지. 스테이징 대상이 있으면 필수다.")
    parser.add_argument(
        "--include-untracked",
        nargs="*",
        default=(),
        help="자동 커밋에 포함할 비추적 파일 경로 목록",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=(),
        help="기본 제외 패턴 외에 추가로 제외할 경로 패턴",
    )
    parser.add_argument(
        "--expect-backend",
        choices=("any", "sqlite", "supabase"),
        default="supabase",
        help="배포 검증에서 기대하는 저장소 종류",
    )
    parser.add_argument(
        "--page",
        choices=("dashboard", "trades", "data"),
        default="data",
        help="배포 검증에서 열 페이지",
    )
    parser.add_argument("--wait-ms", type=int, default=12_000, help="배포 검증 대기 시간(ms)")
    parser.add_argument("--url", default="", help="배포 검증 대상 앱 URL. 비우면 기본 URL을 사용한다.")
    parser.add_argument("--skip-push", action="store_true", help="검증과 커밋만 하고 푸시는 생략한다.")
    parser.add_argument(
        "--skip-remote-verify",
        action="store_true",
        help="git push 이후 원격 Streamlit 검증을 생략한다.",
    )
    parser.add_argument("--dry-run", action="store_true", help="실행 계획만 출력하고 실제 변경은 하지 않는다.")
    return parser.parse_args()


def run_command(command: list[str], *, dry_run: bool = False) -> CommandSummary:
    """명령을 실행하고 실패 시 예외를 던진다."""

    if dry_run:
        return CommandSummary(command=" ".join(command), returncode=0)

    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise CommandExecutionError(command, completed)
    return CommandSummary(command=" ".join(command), returncode=completed.returncode)


def current_branch_name() -> str:
    """현재 Git 브랜치 이름을 반환한다."""

    completed = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def parse_status_line(line: str) -> RepoChange:
    """`git status --short` 한 줄을 `RepoChange`로 바꾼다."""

    status = line[:2]
    payload = line[3:].strip()
    path = payload.split(" -> ", 1)[-1]
    return RepoChange(path=path, status=status, is_untracked=status == "??")


def list_repo_changes() -> tuple[RepoChange, ...]:
    """현재 작업 트리 변경 목록을 읽는다."""

    completed = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    return tuple(parse_status_line(line) for line in lines)


def is_excluded_path(path: str, extra_patterns: Iterable[str] = ()) -> bool:
    """자동 커밋에서 제외할 경로인지 판별한다."""

    patterns = tuple(DEFAULT_EXCLUDED_PATTERNS) + tuple(extra_patterns)
    normalized_path = path.strip().replace("\\", "/")
    for pattern in patterns:
        normalized_pattern = str(pattern).strip().replace("\\", "/")
        if not normalized_pattern:
            continue
        if normalized_path == normalized_pattern:
            return True
        if fnmatch(normalized_path, normalized_pattern):
            return True
        if normalized_pattern.endswith("/*") and normalized_path.startswith(normalized_pattern[:-1]):
            return True
    return False


def classify_repo_changes(
    changes: Iterable[RepoChange],
    *,
    include_untracked: Iterable[str] = (),
    extra_excluded_patterns: Iterable[str] = (),
) -> ChangePlan:
    """변경 파일을 스테이징 대상, 차단 대상, 제외 대상으로 분류한다."""

    include_untracked_set = {path.strip().replace("\\", "/") for path in include_untracked if str(path).strip()}
    stage_paths: list[str] = []
    blocked_untracked_paths: list[str] = []
    excluded_paths: list[str] = []

    for change in changes:
        normalized_path = change.path.strip().replace("\\", "/")
        if is_excluded_path(normalized_path, extra_excluded_patterns):
            excluded_paths.append(normalized_path)
            continue
        if change.is_untracked and normalized_path not in include_untracked_set:
            blocked_untracked_paths.append(normalized_path)
            continue
        stage_paths.append(normalized_path)

    return ChangePlan(
        stage_paths=tuple(dict.fromkeys(stage_paths)),
        blocked_untracked_paths=tuple(dict.fromkeys(blocked_untracked_paths)),
        excluded_paths=tuple(dict.fromkeys(excluded_paths)),
    )


def ensure_reviewable_state(plan: ChangePlan) -> None:
    """자동 커밋 전 사용자가 검토해야 할 상태가 남아 있으면 중단한다."""

    if plan.blocked_untracked_paths:
        joined_paths = ", ".join(plan.blocked_untracked_paths)
        raise ValueError(
            "검토가 필요한 비추적 파일이 남아 있습니다. "
            f"`--include-untracked`로 명시해 주세요: {joined_paths}"
        )


def build_local_verify_commands() -> tuple[list[str], ...]:
    """저장소 기준 로컬 검증 명령 목록을 반환한다."""

    return (
        [sys.executable, "-m", "compileall", "app.py", "src", "scripts", "tests"],
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
    )


def run_local_verifications(*, dry_run: bool = False) -> tuple[CommandSummary, ...]:
    """저장소 기준 로컬 검증을 순서대로 실행한다."""

    return tuple(run_command(command, dry_run=dry_run) for command in build_local_verify_commands())


def stage_paths(paths: Iterable[str], *, dry_run: bool = False) -> CommandSummary | None:
    """스테이징할 경로가 있으면 `git add`를 실행한다."""

    normalized_paths = [path for path in paths if str(path).strip()]
    if not normalized_paths:
        return None
    return run_command(["git", "add", "--", *normalized_paths], dry_run=dry_run)


def has_staged_changes() -> bool:
    """현재 인덱스에 커밋할 변경이 있는지 확인한다."""

    completed = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=REPO_ROOT,
        capture_output=False,
        check=False,
    )
    return completed.returncode == 1


def current_head_sha() -> str:
    """현재 HEAD 커밋 SHA를 반환한다."""

    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def create_commit(commit_message: str, *, dry_run: bool = False) -> CommandSummary:
    """현재 스테이지 내용을 새 커밋으로 기록한다."""

    if not commit_message.strip():
        raise ValueError("커밋할 변경이 있으면 `--commit-message`가 필요합니다.")
    return run_command(["git", "commit", "-m", commit_message.strip()], dry_run=dry_run)


def push_branch(remote: str, branch: str, *, dry_run: bool = False) -> CommandSummary:
    """지정한 원격 브랜치로 푸시한다."""

    return run_command(["git", "push", remote, branch], dry_run=dry_run)


def build_remote_verify_command(
    *,
    page: str,
    expect_backend: str,
    wait_ms: int,
    url: str = "",
) -> tuple[list[str], Path, Path]:
    """배포 검증 명령과 산출물 경로를 생성한다."""

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    artifacts_dir = REPO_ROOT / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    text_output = artifacts_dir / f"deploy-verify-{timestamp}.txt"
    screenshot_output = artifacts_dir / f"deploy-verify-{timestamp}.png"
    command = [
        sys.executable,
        "scripts/verify_streamlit_deployment.py",
        "--page",
        page,
        "--expect-backend",
        expect_backend,
        "--wait-ms",
        str(wait_ms),
        "--text-output",
        str(text_output),
        "--screenshot",
        str(screenshot_output),
    ]
    if url.strip():
        command.extend(["--url", url.strip()])
    return command, text_output, screenshot_output


def run_remote_verification(
    *,
    page: str,
    expect_backend: str,
    wait_ms: int,
    url: str = "",
    dry_run: bool = False,
) -> tuple[CommandSummary, str, str]:
    """배포된 Streamlit 앱에 대해 원격 검증을 실행한다."""

    command, text_output, screenshot_output = build_remote_verify_command(
        page=page,
        expect_backend=expect_backend,
        wait_ms=wait_ms,
        url=url,
    )
    summary = run_command(command, dry_run=dry_run)
    return summary, str(text_output), str(screenshot_output)


def main() -> int:
    """스크립트 진입점."""

    args = parse_args()
    branch = args.branch.strip() or current_branch_name()
    changes = list_repo_changes()
    plan = classify_repo_changes(
        changes,
        include_untracked=args.include_untracked,
        extra_excluded_patterns=args.exclude,
    )

    payload: dict[str, object] = {
        "ok": False,
        "branch": branch,
        "remote": args.remote,
        "stage_paths": list(plan.stage_paths),
        "blocked_untracked_paths": list(plan.blocked_untracked_paths),
        "excluded_paths": list(plan.excluded_paths),
        "local_verifications": [],
        "stage_command": None,
        "commit_command": None,
        "push_command": None,
        "remote_verify_command": None,
        "commit_sha": current_head_sha(),
        "remote_verify_artifacts": {},
        "dry_run": bool(args.dry_run),
    }

    try:
        ensure_reviewable_state(plan)

        local_verifications = run_local_verifications(dry_run=args.dry_run)
        payload["local_verifications"] = [asdict(item) for item in local_verifications]

        stage_summary = stage_paths(plan.stage_paths, dry_run=args.dry_run)
        if stage_summary is not None:
            payload["stage_command"] = asdict(stage_summary)

        if args.dry_run:
            payload["ok"] = True
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0

        if has_staged_changes():
            commit_summary = create_commit(args.commit_message, dry_run=False)
            payload["commit_command"] = asdict(commit_summary)
            payload["commit_sha"] = current_head_sha()

        if not args.skip_push:
            push_summary = push_branch(args.remote, branch, dry_run=False)
            payload["push_command"] = asdict(push_summary)

        if not args.skip_push and not args.skip_remote_verify:
            verify_summary, text_output, screenshot_output = run_remote_verification(
                page=args.page,
                expect_backend=args.expect_backend,
                wait_ms=args.wait_ms,
                url=args.url,
                dry_run=False,
            )
            payload["remote_verify_command"] = asdict(verify_summary)
            payload["remote_verify_artifacts"] = {
                "text_output": text_output,
                "screenshot_output": screenshot_output,
            }

    except (CommandExecutionError, ValueError) as exc:
        payload["error"] = str(exc)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    payload["ok"] = True
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

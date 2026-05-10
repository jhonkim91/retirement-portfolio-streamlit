from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


def load_module():
    """배포 자동화 스크립트 모듈을 동적으로 불러온다."""

    module_path = Path(__file__).resolve().parents[1] / "scripts" / "verify_and_push_deploy.py"
    spec = importlib.util.spec_from_file_location("verify_and_push_deploy", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


deploy_script = load_module()


class ParseStatusLineTests(unittest.TestCase):
    """Git 상태 파서의 기본 분기들을 검증한다."""

    def test_parse_status_line_reads_modified_path(self) -> None:
        """수정된 tracked 파일은 경로와 상태를 그대로 읽는다."""

        change = deploy_script.parse_status_line(" M app.py")

        self.assertEqual(change.path, "app.py")
        self.assertEqual(change.status, " M")
        self.assertFalse(change.is_untracked)

    def test_parse_status_line_reads_rename_target(self) -> None:
        """rename 상태는 새 경로를 기준으로 저장한다."""

        change = deploy_script.parse_status_line("R  old_name.py -> new_name.py")

        self.assertEqual(change.path, "new_name.py")
        self.assertEqual(change.status, "R ")
        self.assertFalse(change.is_untracked)


class ExcludedPathTests(unittest.TestCase):
    """자동 커밋 제외 경로 판별을 검증한다."""

    def test_is_excluded_path_matches_repo_runtime_artifacts(self) -> None:
        """로컬 DB와 산출물은 기본 제외 경로로 처리한다."""

        self.assertTrue(deploy_script.is_excluded_path("data/portfolio.db"))
        self.assertTrue(deploy_script.is_excluded_path("artifacts/deploy-verify-1.png"))
        self.assertFalse(deploy_script.is_excluded_path("src/db.py"))


class ClassifyRepoChangesTests(unittest.TestCase):
    """변경 파일 분류 계획을 검증한다."""

    def test_classify_repo_changes_blocks_untracked_without_explicit_include(self) -> None:
        """비추적 파일은 명시적으로 포함하지 않으면 차단 대상으로 남긴다."""

        changes = (
            deploy_script.RepoChange(path="src/db.py", status=" M", is_untracked=False),
            deploy_script.RepoChange(path="scripts/new_tool.py", status="??", is_untracked=True),
            deploy_script.RepoChange(path="artifacts/debug.png", status="??", is_untracked=True),
        )

        plan = deploy_script.classify_repo_changes(changes)

        self.assertEqual(plan.stage_paths, ("src/db.py",))
        self.assertEqual(plan.blocked_untracked_paths, ("scripts/new_tool.py",))
        self.assertEqual(plan.excluded_paths, ("artifacts/debug.png",))

    def test_classify_repo_changes_includes_selected_untracked_paths(self) -> None:
        """명시적으로 허용한 비추적 파일은 스테이징 대상으로 올린다."""

        changes = (
            deploy_script.RepoChange(path="scripts/new_tool.py", status="??", is_untracked=True),
            deploy_script.RepoChange(path="tests/test_new_tool.py", status="??", is_untracked=True),
        )

        plan = deploy_script.classify_repo_changes(
            changes,
            include_untracked=("scripts/new_tool.py", "tests/test_new_tool.py"),
        )

        self.assertEqual(plan.stage_paths, ("scripts/new_tool.py", "tests/test_new_tool.py"))
        self.assertEqual(plan.blocked_untracked_paths, ())
        self.assertEqual(plan.excluded_paths, ())


if __name__ == "__main__":
    unittest.main()

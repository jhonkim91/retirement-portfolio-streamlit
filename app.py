from __future__ import annotations

import importlib
import sys
import types
from types import ModuleType
from typing import Any


_APP_CORE: ModuleType | None = None


def _load_app_core() -> ModuleType:
    """앱 코어 모듈을 실제 사용 시점에 지연 로드한다."""

    global _APP_CORE
    if _APP_CORE is None:
        _APP_CORE = importlib.import_module("src.ui.app_core")
    return _APP_CORE


def __getattr__(name: str) -> Any:
    """기존 `app.py` 공개 함수/상수 접근을 앱 코어로 위임한다."""

    return getattr(_load_app_core(), name)


def __dir__() -> list[str]:
    """대화형 도구에서 앱 코어 공개 이름을 함께 보여준다."""

    return sorted(set(globals()) | set(dir(_load_app_core())))


class _AppCompatModule(types.ModuleType):
    """기존 `app` 모듈 monkey patch를 `app_core` 전역에도 반영한다."""

    def __setattr__(self, name: str, value: object) -> None:
        if not name.startswith("__"):
            core = _load_app_core()
            if hasattr(core, name):
                setattr(core, name, value)
        super().__setattr__(name, value)


sys.modules[__name__].__class__ = _AppCompatModule


def main() -> None:
    """Streamlit 엔트리포인트에서 앱 라우터를 실행한다."""

    _load_app_core().main()


def _is_streamlit_script_run() -> bool:
    """Streamlit ScriptRunner 안에서 실행 중인지 확인한다."""

    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


if __name__ in {"__main__", "main"} or _is_streamlit_script_run():
    main()

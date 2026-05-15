from __future__ import annotations

from src.ui import app_core


def main() -> None:
    """대시보드 페이지를 렌더링한다."""

    app_core.render_navigation_page("Dashboard")


main()

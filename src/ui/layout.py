"""공통 레이아웃 렌더링 헬퍼 호환 모듈."""

from __future__ import annotations

from src.ui.app_core import (
    inject_app_styles,
    render_dashboard_metric_strip,
    render_dashboard_reference_time,
    render_dashboard_section_header,
    render_dashboard_summary_card,
)

__all__ = [
    "inject_app_styles",
    "render_dashboard_metric_strip",
    "render_dashboard_reference_time",
    "render_dashboard_section_header",
    "render_dashboard_summary_card",
]

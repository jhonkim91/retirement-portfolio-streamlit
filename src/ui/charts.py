"""대시보드 차트 렌더링 헬퍼 호환 모듈."""

from __future__ import annotations

from src.ui.app_core import (
    allocation_chart,
    allocation_treemap_options,
    holdings_bar_fallback_chart,
    holdings_bar_options,
    realized_profit_bar_fallback_chart,
    realized_profit_bar_options,
    selected_holding_trend_chart,
    selected_holding_trend_options,
    style_dashboard_altair_chart,
)

__all__ = [
    "allocation_chart",
    "allocation_treemap_options",
    "holdings_bar_fallback_chart",
    "holdings_bar_options",
    "realized_profit_bar_fallback_chart",
    "realized_profit_bar_options",
    "selected_holding_trend_chart",
    "selected_holding_trend_options",
    "style_dashboard_altair_chart",
]

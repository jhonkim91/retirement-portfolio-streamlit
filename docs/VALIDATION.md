# VALIDATION

## 문서 목적
- 최신 대표 검증 결과 1세트를 기록한다.
- 과거 상세 이력은 `docs/archive/`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-17`

## 최신 대표 검증 결과
- 작업 범위: Dashboard 자산 배분 트리맵 예수금 중립색 처리 및 운영 배포.
- 원인: 운영 `main`에서는 예수금 leaf가 수익률 0% 값으로 rollup되어 visualMap 색상표의 보라색 계열로 표시됐다.
- 수정: 예수금을 `node_kind="cash"`, `profit_rate=None`, `FEARGREED_FLAT_COLOR`로 처리하고 수익률 색상표 계산에서 제외했다.
- 회귀 테스트: 예수금 node metadata, 중립색, visualMap 범위, 라벨 formatter를 `tests/test_analytics.py`와 `tests/test_app_dashboard.py`에 고정했다.
- 환경: Python 3.11, Streamlit Cloud 운영 앱.

## 명령 검증
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest tests.test_app_dashboard.AllocationTreemapVisualMapTests.test_allocation_treemap_renders_cash_as_neutral_without_profit_rate_mapping tests.test_analytics.AccountSummaryTests.test_allocation_treemap_nodes_groups_holdings_and_cash` 성공, 2 tests
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 282 tests
- 운영 Streamlit Cloud `?demo=1&capture=1` 대시보드에서 예수금 회색 표시 확인 완료.

## 검증 범위
- 예수금 node가 현금 자산으로 metadata를 유지하는지 검증.
- 예수금이 수익률 visualMap min/max 계산에서 제외되고 회색 중립색으로 표시되는지 검증.
- 운영 데모 대시보드에서 예수금 표시가 반영됐는지 확인.

## 미수행 항목
- 운영 DB 데이터 직접 수정은 수행하지 않았다.

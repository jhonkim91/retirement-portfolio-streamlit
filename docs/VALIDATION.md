# VALIDATION

## 문서 목적
- 최신 대표 검증 결과 1세트를 기록한다.
- 과거 상세 이력은 `docs/archive/`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-15`

## 최신 대표 검증 결과
- 작업 범위: Dashboard KPI 카드 값 급등 원인 점검과 평가 스냅샷 현금 산정 보정
- 원인: 오늘 평가 스냅샷에서 `account.cash_balance`를 무조건 실제 현금으로 사용해, 매수/매도로 줄어든 원장 현금과 보유 평가액이 이중 계산될 수 있었다.
- 확인: 로컬 재현 계좌에서 `account.cash_balance=17,400,000`, 거래 원장 현금 합계 `9,643,800`으로 불일치했고, 이 때문에 `입금 대비 손익`과 `수익률`이 과대 표시됐다.
- 수정: 오늘 `account.cash_balance`가 거래 원장 기준 현금과 원 단위로 맞을 때만 실제 현금으로 사용하고, 크게 어긋나면 원장 기준 `implied_cash`로 fallback한다.
- 유지: 저장소 스키마와 DB 데이터는 변경하지 않았다.
- 환경: 로컬 Python 3.11, Streamlit bare mode 테스트 실행.

## 명령 검증
- `python -m unittest tests.test_valuation tests.test_app_dashboard` 성공, 134 tests
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 276 tests

## 검증 범위
- 오늘 실제 현금이 원장 현금과 맞는 경우 기존처럼 actual cash를 사용하는지 검증
- 오늘 실제 현금이 매수/매도를 반영하지 않은 값이면 ledger/implied cash로 fallback하는지 검증
- `dashboard_previous_day_delta_value()`가 날짜 정렬 후 마지막 두 `principal_profit_loss`/`principal_profit_rate` 값을 비교하는지 검증
- `build_dashboard_metric_specs()`가 손익 KPI에 `전일 대비 +₩...`, 수익률 KPI에 `전일 대비 +...%p` caption을 넣는지 검증
- `render_dashboard_metric_card_option2()`가 델타 tone class를 렌더링하는지 검증

## 미수행 항목
- 로컬/운영 Streamlit 브라우저 화면 검증과 배포는 수행하지 않았다.

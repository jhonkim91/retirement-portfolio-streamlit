# VALIDATION

## 문서 목적
- 최신 대표 검증 결과 1세트를 기록한다.
- 과거 상세 이력은 `docs/archive/`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-15`

## 최신 대표 검증 결과
- 작업 범위: 평가액 기록/원화 표시 금액의 원 단위 반올림 보정
- 원인: 평가 스냅샷 금액 컬럼은 내부 계산값을 소수점 4자리로 저장할 수 있었고, Python 기본 포맷은 `.5` 금액에서 일반 반올림과 다른 결과가 날 수 있었다.
- 수정: 평가 스냅샷의 금액 컬럼은 `Decimal ROUND_HALF_UP` 기준으로 원 단위 정수로 산출한다.
- 수정: `format_won()`, `dashboard_format_won()`, 거래 기록 금액 표시도 동일한 원 단위 일반 반올림 helper를 사용한다.
- 유지: 수익률 `profit_rate`와 퍼센트 표시는 기존 소수점 표시를 유지한다.
- 회귀 테스트: 평가 스냅샷 금액 컬럼과 UI 원화 표시에서 `.5` 금액이 원 단위로 반올림되는지 검증했다.
- 환경: 로컬 Python 3.11, Streamlit bare mode 테스트 실행.

## 명령 검증
- `python -m compileall src/valuation.py src/ui/app_core.py tests/test_valuation.py tests/test_app_dashboard.py` 성공
- `python -m unittest tests.test_valuation tests.test_app_dashboard` 성공, 121 tests
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 253 tests
- `git push origin main` 성공, 배포 코드 커밋 `2c1a2ed2ebfa1ca45bb9dd2a56fcbcedc7296b5c`
- `python scripts/verify_streamlit_deployment.py --page valuation --expect-backend supabase --wait-ms 30000 --text-output artifacts/deploy-verify-won-rounding-20260515-0404.txt --screenshot artifacts/deploy-verify-won-rounding-20260515-0404.png --debug-dir artifacts/deploy-verify-won-rounding-20260515-0404-debug` 성공

## 검증 범위
- 평가 스냅샷의 `company_principal`, `invested_cost`, `actual_cash_balance`, `cash_value`, `holdings_market_value`, `valuation_amount`, `profit_loss`가 원 단위 정수로 산출되는지 검증
- 반올림된 `valuation_amount`와 `company_principal` 기준으로 `profit_loss`와 `profit_rate`가 계산되는지 검증
- 원화 표시 helper와 거래 기록 금액 표시가 `.5` 금액을 원 단위로 일반 반올림하는지 검증
- 전체 unittest suite가 기존 기능 회귀 없이 통과하는지 검증
- 원격 Streamlit 평가액 기록 페이지가 로그인 후 Supabase backend로 로드되는지 검증

## 미수행 항목
- 운영 `daily_valuation_snapshot` 재작성은 운영 DB 파생 데이터 변경이므로 수행하지 않았다.

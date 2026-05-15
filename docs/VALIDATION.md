# VALIDATION

## 문서 목적
- 최신 대표 검증 결과 1세트를 기록한다.
- 과거 상세 이력은 `docs/archive/`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-15`

## 최신 대표 검증 결과
- 작업 범위: 평가액 기록 현금흐름 산식 재점검 및 실제 일별 현금 우선 보정
- 원인: 과거 평가액 기록이 같은 날짜 `daily_account_snapshot.cash_balance`가 있어도 거래 원장 기반 현금 추정값을 우선 사용해, 중복/비정상 거래 기록이 있는 계좌에서 현금과 수익률이 크게 부풀려졌다.
- 추가 원인: 보유 수량 없이 먼저 들어온 매도 기록도 현금 유입으로 반영되어, 잘못 입력된 매도 데이터가 평가 현금을 증가시킬 수 있었다.
- 수정: 오늘은 `accounts.cash_balance`, 과거일은 `daily_account_snapshot.cash_balance`가 있으면 실제 현금을 사용하고, 스냅샷이 없는 날짜만 거래 원장 기반 현금으로 fallback한다.
- 수정: 매도 현금 유입은 FIFO lot에 실제 매칭된 수량 비율만 반영해 미매칭 매도가 평가 현금을 부풀리지 않도록 했다.
- 회귀 테스트: 일별 계좌 스냅샷 현금 우선 적용, 미매칭 매도 현금 부풀림 방지, daily rollup 스냅샷 현금 전달을 검증했다.
- 운영 read-only 점검: `jhonkim2025@gmail.com`의 미래에셋(account 23), 신한(account 24) 계좌에 대해 거래 원장, 일별 계좌 스냅샷, 평가 스냅샷을 조회했다.
- 환경: 로컬 Python 3.11, Streamlit bare mode 테스트 실행.

## 명령 검증
- `python -m compileall src/valuation.py src/ui/app_core.py src/db.py scripts/run_daily_rollup.py tests/test_valuation.py tests/test_run_daily_rollup.py` 성공
- `python -m unittest tests.test_valuation tests.test_app_dashboard tests.test_run_daily_rollup` 성공, 120 tests
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 251 tests
- `git push origin main` 성공, 배포 코드 커밋 `01a005aaab717a29db431032d0e0d43ade3b521e`
- `python scripts/verify_streamlit_deployment.py --page valuation --expect-backend supabase --wait-ms 30000 --text-output artifacts/deploy-verify-valuation-cashflow-20260515-0352.txt --screenshot artifacts/deploy-verify-valuation-cashflow-20260515-0352.png --debug-dir artifacts/deploy-verify-valuation-cashflow-20260515-0352-debug` 성공

## 검증 범위
- 평가액 기록 산식이 오늘 실제 현금, 과거 일별 계좌 스냅샷 현금, 원장 fallback 순서로 현금을 선택하는지 검증
- 과거 실제 현금이 적용될 때 `cash_source`, `actual_cash_balance`, `valuation_amount`가 일관되게 계산되는지 검증
- 보유 lot에 매칭되지 않는 매도 기록이 현금과 향후 lot을 변경하지 않는지 검증
- daily rollup과 수동 재계산 경로가 `daily_account_snapshot` 목록을 평가 스냅샷 재계산에 전달하는지 검증
- 전체 unittest suite가 기존 기능 회귀 없이 통과하는지 검증
- 원격 Streamlit 평가액 기록 페이지가 로그인 후 Supabase backend로 로드되는지 검증
- 운영 Supabase 데이터는 read-only 조회만 수행했고, 거래 기록 삭제/수정이나 평가 스냅샷 재작성은 수행하지 않았다.

## 계좌 산출 점검
- 미래에셋(account 23): 원장 기준 현금 합계가 `6,433,337,639.53719`원까지 부풀려져 있었고, 주요 원인은 1,000배 수준 중복 거래 id `874`-`879` 및 미매칭 매도성 기록 id `901`이었다.
- 신한(account 24): 원장 기준 현금 합계가 `1,795,205.722`원이었고, 1,000배 수준 중복 거래 id `899`, `900`을 제외하면 `80,483.722`원으로 실제 현금 `82,071`원에 근접했다.
- 신한 2026-05-14 산출 예시: 상품 평가액 `925,595`원 + 실제 현금 `82,071`원 = 보유 평가액 `1,007,666`원, 입금 원금 `800,000`원, 손익 `207,666`원, 수익률 `25.96%`.
- 미래에셋 2026-05-14 산출 예시: 상품 평가액 `32,952,885`원 + 실제 현금 `17,449`원 = 보유 평가액 `32,970,334`원, 입금 원금 `17,500,000`원, 손익 `15,470,334`원, 수익률 `88.40%`.

## 미수행 항목
- 운영 거래 원장의 중복/비정상 거래 id 삭제 또는 수정은 destructive 작업이므로 수행하지 않았다.
- 운영 `daily_valuation_snapshot` 재작성은 운영 DB 파생 데이터 변경이므로 수행하지 않았다.

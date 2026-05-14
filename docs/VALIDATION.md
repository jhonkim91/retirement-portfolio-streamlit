# VALIDATION

## 문서 목적
- 최신 대표 검증 결과 1세트를 기록한다.
- 과거 상세 이력은 `docs/archive/`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-14`

## 최신 대표 검증 결과
- 작업 범위: 입금액 기준 일별 평가액 기록 기능 추가
- 추가 UI 조정: 사이드바 연금 유형 뱃지 제거, Dashboard 히어로 전일 대비 자산 증감 표시, 입금 대비 손익/수익률 KPI 차트 확대
- 현금 계산 수정: 평가액 기록의 과거 현금을 `입금원금 - 잔여매입원가`가 아니라 거래 원장의 `cash_delta` 누적 기준으로 계산
- 신규 저장소: Supabase/SQLite `daily_valuation_snapshot` 테이블, RLS/GRANT, batch upsert, 조회/삭제 wrapper 추가
- 신규 계산: `src/valuation.py`에서 `employer_deposit`, `personal_deposit`, legacy `deposit`, `opening_cash`를 입금 원금으로 누적하고 FIFO 잔여 매입원가, 원장 현금, 오늘 실제 현금, 가격 fallback 종목을 계산
- 현금 원장: 매도 실현손익, 이자, 배당, 수수료, 현금 조정처럼 `cash_delta`가 있는 이벤트를 평가 현금에 반영
- 경고 수정: Supabase 평가 스냅샷 저장 전 중복 계좌 재조회로 정상 계좌에서도 “계좌를 찾을 수 없습니다”가 표시될 수 있는 경로를 제거
- 신규 가격 조회: 거래 로그 종목별 날짜 범위 가격 이력을 KIS/Naver/yfinance 경로로 조회하고 실패 종목은 빈 series로 넘겨 lot 단가 fallback 적용
- 신규 UI: `평가액 기록` 별도 페이지 추가, Dashboard 상단은 오늘 평가 스냅샷이 있으면 `보유 평가액`/`입금 원금` 기준으로 표시
- Dashboard 히어로: `전일 대비` 값은 추이 데이터의 마지막 두 `total_value` 차이로 계산
- 신규 편집: 평가액 기록 CSV 저장/불러오기와 `data_editor` 기반 수동 수정 저장 추가
- 재계산 hook: 거래 저장/수정/삭제, 현금 흐름, CSV import 완료, 수동 가격 refresh, daily rollup에서 계좌별 1회 재계산
- 배치 연동: `scripts/run_daily_rollup.py`가 기존 `daily_account_snapshot`과 신규 `daily_valuation_snapshot`을 함께 처리
- 환경: 로컬 Python 3.11, Streamlit, SQLite backend 검증

## 명령 검증
- `python -m compileall app.py src scripts tests pages` 성공
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 235 tests
- `python -m pytest tests/test_valuation.py tests/test_db.py tests/test_app_dashboard.py` 성공, 154 tests
- `git diff --check -- .streamlit/app.css src/ui/app_core.py tests/test_app_dashboard.py` 성공
- `python -m pytest tests/test_app_dashboard.py tests/test_db.py tests/test_valuation.py tests/test_verify_streamlit_deployment.py` 성공, 166 tests
- `python -m pytest tests/test_valuation.py tests/test_db.py tests/test_app_dashboard.py tests/test_run_daily_rollup.py tests/test_verify_streamlit_deployment.py` 성공, 164 tests
- `git diff --check -- README.md docs/VALIDATION.md setup_supabase.sql migrations/2026-05-14_add_daily_valuation_snapshot.sql src/valuation.py src/market.py src/sqlite_db.py src/db.py src/ui/app_core.py scripts/run_daily_rollup.py scripts/verify_streamlit_deployment.py pages/valuation.py tests/test_valuation.py tests/test_db.py tests/test_setup_supabase_sql.py tests/test_app_dashboard.py tests/test_run_daily_rollup.py tests/test_verify_streamlit_deployment.py` 성공
- `curl -sS --max-time 5 http://127.0.0.1:8501/_stcore/health` 결과 `ok`

## 브라우저 검증
- 명령:
```bash
python scripts/verify_streamlit_deployment.py \
  --url https://retirement-portfolio-app-nh2vq9ferqnpehsslbykbe.streamlit.app/ \
  --page valuation \
  --expect-backend supabase \
  --wait-ms 12000 \
  --screenshot artifacts/deploy-valuation-ledger-cash.png \
  --text-output artifacts/deploy-valuation-ledger-cash.txt \
  --debug-dir artifacts/deploy-valuation-ledger-cash-debug
```
- 결과: 성공, `ok=true`
- 확인값: `target_page=valuation`, `logged_in=true`, `backend_storage=Supabase`, `backend_storage_code=supabase`, `workspace_visible=true`
- 산출물: `artifacts/deploy-valuation-ledger-cash.png`, `artifacts/deploy-valuation-ledger-cash.txt`, `artifacts/deploy-valuation-ledger-cash-debug/`

## 운영 데이터 검증
- 대상: Supabase 운영 `jhonkim2025@gmail.com`
- 재계산 기준일: `2026-05-14`
- 결과: account 23 스냅샷 686건, account 24 스냅샷 99건 재계산 저장
- 입금 원장이 없는 account 25/26은 평가 스냅샷 0건으로 정리
- IRP account 24 확인값: `2026-05-07` 원장 현금 `80,483.722`, `2026-05-14` 실제 현금 `82,071`, 보유 평가액 `1,007,666`

## 계산 검증 범위
- 최초 입금성 거래 발생일부터 series 생성
- 과거 날짜 `implied_cash`에 원장 현금 누적값 저장
- 오늘 날짜 `actual` cash 계산
- `personal_deposit` 원금 포함
- FIFO 매도 후 잔여 매입원가 차감
- 매도 실현이익이 과거 원장 현금을 증가시키는지 검증
- 배당/이자/수수료 등 `cash_delta` 이벤트가 원금이 아니라 원장 현금에 반영되는지 검증
- 직전 영업일 종가 사용
- 매입가 fallback 및 `missing_price_symbols` 기록
- 원금 초과 매입 `over_invested_amount`
- 회사 납입금 없이 개인 입금만 있어도 결과 생성
- CSV 저장 프레임을 수정한 뒤 다시 저장 payload로 변환
- CSV/편집 프레임에서 빈 파생값을 저장 전 자동 계산

## DB/스키마 검증 범위
- SQLite `record/list/delete_valuation_snapshots()` 저장/조회/삭제와 `missing_price_symbols` JSON list 정규화
- Supabase batch upsert payload와 `on_conflict=account_id,valuation_date`
- Supabase/SQLite `adjust_cash_balance()`가 현금 수정분을 `cash_adjustment` 원장 이벤트로 남기는지 검증
- cache 무효화 경로
- `setup_supabase.sql` 및 migration의 신규 테이블, 인덱스, RLS, 정책명, 명시적 GRANT

## UI/배치 검증 범위
- `PAGES`, `PAGE_LABELS`, 사이드바, navigation page name에 `평가액 기록` 연결
- Dashboard가 오늘 평가 스냅샷을 summary보다 우선 사용
- Dashboard 문구가 `보유 평가액`, `입금 원금`, `현재 보유현금`, `입금 대비 손익`, `입금 대비 수익률`로 표시
- Dashboard 히어로가 입금 대비 손익 대신 전일 대비 총자산 증감을 표시
- 사이드바 계좌 카드가 `연금(IRP/퇴직연금)` 유형 뱃지를 렌더링하지 않음
- 입금 대비 손익/수익률 KPI 카드의 sparkline 표시 영역 확대
- 평가액 기록 페이지가 CSV 저장, CSV 불러오기, 화면 수정 저장 UI를 제공
- `scripts/run_daily_rollup.py`가 기존 daily account snapshot과 신규 valuation snapshot을 함께 처리

## 미수행 항목
- Supabase 스테이징 DB는 별도 검증하지 않았다.

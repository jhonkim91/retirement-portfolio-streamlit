# VALIDATION

## 문서 목적
- 최신 대표 검증 결과 1세트를 기록한다.
- 과거 상세 이력은 `docs/archive/`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-15`

## 최신 대표 검증 결과
- 작업 범위: 평가액 기록 수익률 계산 보정
- 원인: 일반 출금은 원장 현금에서는 차감됐지만 수익률 분모인 평가 원금에서는 차감되지 않아 출금 이후 손익률이 왜곡될 수 있었음
- 수정: `daily_valuation_snapshot.company_principal` 저장값은 기존 컬럼명을 유지하되 일반 출금을 차감한 순입금 원금으로 계산
- 예외 유지: 계좌 간 `transfer_out`은 기존 원금 기준과 동일하게 원금 차감 대상에서 제외
- UI 문구: 평가액 기록 안내를 순입금 원금 기준으로 조정
- 작업 범위: 실시간 테이블 retention 전용 인덱스 보강
- 신규 Supabase 인덱스: `realtime_price_ticks(quote_time, id)`, `realtime_price_ticks(holding_id) WHERE holding_id IS NOT NULL`, `realtime_price_bars(interval, bucket_start)`
- 신규 migration: `migrations/2026-05-15_reinforce_realtime_indexes.sql`; `CREATE INDEX CONCURRENTLY` 사용으로 transaction block 없이 작성
- SQLite fallback: 동일 목적 인덱스를 초기화 루틴에 추가
- retention 조회 변경: Supabase/SQLite tick 범위 조회 정렬을 `quote_time ASC, id ASC`로 변경하고, 집계 정확도는 기존 `aggregate_ticks()` 내부 정렬로 유지
- 작업 범위: 입금액 기준 일별 평가액 기록 기능 추가
- 추가 운영 점검: `migrations/2026-05-14_normalize_temporal_columns.sql` 적용 전 Supabase temporal 컬럼 cast 실패 행 점검
- 추가 worker 수정: KIS WebSocket worker가 GitHub Actions timeout 종료 신호를 WebSocket 오류로 처리한 뒤 재연결하다 `137`로 kill되는 흐름을 방지
- 추가 UI 조정: 사이드바 연금 유형 뱃지 제거, Dashboard 히어로 전일 대비 자산 증감 표시, 입금 대비 손익/수익률 KPI 차트 확대
- 현금 계산 수정: 평가액 기록의 과거 현금을 `입금원금 - 잔여매입원가`가 아니라 거래 원장의 `cash_delta` 누적 기준으로 계산
- 정렬 수정: 평가액 기록 스냅샷 조회/표시를 최신 기준일 우선으로 변경
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
- `python -m compileall src/valuation.py src/ui/app_core.py tests/test_valuation.py` 성공
- `python -m unittest tests.test_valuation tests.test_app_dashboard` 성공, 112 tests
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 244 tests
- `git diff --check -- src/valuation.py src/ui/app_core.py tests/test_valuation.py` 성공
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest tests.test_setup_supabase_sql tests.test_realtime_tick_retention` 성공, 13 tests
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 241 tests
- `RETIREMENT_DB_PATH=/tmp/retirement-retention-verify.db python scripts/run_realtime_tick_retention.py --backend sqlite --as-of 2026-05-13T00:00:00` 성공, dry-run `source_ticks=0`
- `git diff --check -- setup_supabase.sql migrations/2026-05-15_reinforce_realtime_indexes.sql src/sqlite_db.py scripts/run_realtime_tick_retention.py tests/test_setup_supabase_sql.py tests/test_realtime_tick_retention.py` 성공
- `python -m unittest tests.test_run_kis_quote_worker` 성공, 7 tests
- `python scripts/run_kis_quote_worker.py --backend sqlite --preflight-only` 성공, `accounts=8`, `holdings=34`
- `python scripts/run_kis_quote_worker.py --backend supabase --preflight-only` 성공, `accounts=4`, `holdings=6`
- `python -m compileall app.py src scripts tests pages` 성공
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 237 tests
- `python -m pytest tests/test_db.py -k "valuation_snapshots"` 성공, 3 tests
- `python -m pytest tests/test_run_daily_rollup.py` 성공, 1 test
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
  --screenshot artifacts/deploy-valuation-newest-first.png \
  --text-output artifacts/deploy-valuation-newest-first.txt \
  --debug-dir artifacts/deploy-valuation-newest-first-debug
```
- 결과: 성공, `ok=true`
- 확인값: `target_page=valuation`, `logged_in=true`, `backend_storage=Supabase`, `backend_storage_code=supabase`, `workspace_visible=true`
- 산출물: `artifacts/deploy-valuation-newest-first.png`, `artifacts/deploy-valuation-newest-first.txt`, `artifacts/deploy-valuation-newest-first-debug/`

## 운영 데이터 검증
- 대상: Supabase 운영 `jhonkim2025@gmail.com`
- 재계산 기준일: `2026-05-14`
- 결과: account 23 스냅샷 686건, account 24 스냅샷 99건 재계산 저장
- 입금 원장이 없는 account 25/26은 평가 스냅샷 0건으로 정리
- IRP account 24 확인값: `2026-05-07` 원장 현금 `80,483.722`, `2026-05-14` 실제 현금 `82,071`, 보유 평가액 `1,007,666`

## Supabase Migration 사전 점검
- 대상: 운영 Supabase project `iyszkybxostbjfzbbymq`
- migration: `migrations/2026-05-14_normalize_temporal_columns.sql`
- 방식: `pg_input_is_valid()` 기반 read-only SQL로 `date(left10)`/`timestamptz` 변환 가능 여부 확인
- 결과: 대상 컬럼 전체 `invalid_rows=0`
- 확인 row 수:
  - `accounts`: 4 rows
  - `holdings`: 28 rows
  - `trade_logs`: 86 rows
  - `daily_interest`: 0 rows
  - `daily_account_snapshot`: 25 rows
  - `realtime_price_ticks`: 12,449 rows
  - `realtime_worker_status`: 4 rows
- 주의: 운영 DB에는 현재 `public.realtime_price_bars`가 없어, 해당 migration 전체 적용 전에는 cast 실패가 아니라 테이블 존재 조건을 먼저 맞춰야 한다.

## KIS Worker 운영 점검
- 최신 GitHub Actions `KIS Realtime Worker` run `25845045857` 확인: `2026-05-14T06:13:25Z` 시작, `2026-05-14T09:59:45Z` 완료, conclusion `success`
- 최신 job `75938329587` 확인: `KIS realtime worker 실행` 단계가 `2026-05-14T06:14:09Z`부터 `2026-05-14T09:59:39Z`까지 실행
- 운영 Supabase `realtime_worker_status`: account 23/24/25/26 모두 `connection_state=stopped`, `stop_reason=github-actions-session-complete`
- 운영 Supabase `realtime_price_ticks`: 총 12,449건, 최초 quote `2026-05-11T09:50:53`, 최신 quote `2026-05-14T15:59:40`, 4개 계좌/7개 종목 기록
- 운영 로그 관찰: 세션 중 `ping/pong timed out` 이후 5초 재연결과 `KIS WebSocket 연결 완료: 6개 종목 구독` 복구가 반복됨
- 수정: 종료 신호 수신 시 WebSocket을 닫고 재연결 루프로 복귀하지 않도록 worker shutdown flag를 추가했으며, workflow timeout은 `--signal=SIGINT`로 맞춤

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
- SQLite 평가 스냅샷 조회가 최신 기준일 우선 순서를 반환하는지 검증
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
- 평가액 기록 표와 CSV 원본 프레임이 최근 기준일에서 과거 기준일 순서로 표시됨
- `scripts/run_daily_rollup.py`가 기존 daily account snapshot과 신규 valuation snapshot을 함께 처리

## 미수행 항목
- Supabase 스테이징 DB는 별도 검증하지 않았다.

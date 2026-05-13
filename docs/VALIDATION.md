# VALIDATION

## 기준
- 이 문서는 `Memory.md`에서 분리한 검증 이력 요약이다.
- 날짜별 상세 원문은 `docs/archive/memory-YYYY-MM-DD.md`에 보존했다.
- 정리 기준일은 `2026-05-13`이다.
- 최신 검증 결과는 각 작업 완료 시 대표 명령만 갱신한다.

## 최신 대표 검증 결과
- DESIGN-04 KPI 반응형 grid 패치: `python -m compileall src/ui/app_core.py tests/test_app_dashboard.py` 성공.
- DESIGN-04 KPI 반응형 grid 패치: `python -m unittest tests.test_app_dashboard.ThemeStylesheetTests` 성공, 6 tests.
- DESIGN-04 KPI 반응형 grid 패치: `python -m compileall app.py src scripts tests pages` 성공.
- DESIGN-04 KPI 반응형 grid 패치: `python -m unittest discover -s tests -p "test_*.py"` 성공, 155 tests.
- DESIGN-04 KPI 반응형 브라우저 검증: 로컬 Streamlit `http://127.0.0.1:8534` 데모 대시보드 1180/820/560px에서 `.dashboard-summary-card=5`, `bodyOverflows=false`, 560px `minHeight=0px`, header `column/flex-start` 확인.
- DESIGN-02 KPI 카드 위계 패치: `python -m compileall src/ui/app_core.py tests/test_app_dashboard.py` 성공.
- DESIGN-02 KPI 카드 위계 패치: `python -m unittest tests.test_app_dashboard.ThemeStylesheetTests` 성공, 6 tests.
- DESIGN-02 KPI 카드 위계 패치: `python -m compileall app.py src scripts tests pages` 성공.
- DESIGN-02 KPI 카드 위계 패치: `python -m unittest discover -s tests -p "test_*.py"` 성공, 155 tests.
- DESIGN-02 KPI 카드 브라우저 검증: 로컬 Streamlit `http://127.0.0.1:8533` 데모 대시보드에서 `.dashboard-summary-card=5`, `borderRadius=24px`, `beforeHeight=3px`, `bodyOverflows=false` 확인.
- CSS radius/shadow 토큰 패치: `python -m compileall app.py src scripts tests pages` 성공.
- CSS radius/shadow 토큰 패치: `python -m unittest tests.test_app_dashboard.ThemeStylesheetTests` 성공, 5 tests.
- CSS radius/shadow 토큰 패치: `python -m unittest discover -s tests -p "test_*.py"` 성공, 154 tests.
- realtime tick retention 패치: `python -m compileall scripts/run_realtime_tick_retention.py src/sqlite_db.py tests/test_realtime_tick_retention.py tests/test_setup_supabase_sql.py` 성공.
- realtime tick retention 패치: `python -m unittest tests.test_realtime_tick_retention tests.test_setup_supabase_sql` 성공, 8 tests.
- realtime tick retention dry-run: `python scripts/run_realtime_tick_retention.py --backend sqlite --as-of 2026-05-13T00:00:00` 성공.
- realtime tick retention 포함 전체 검증: `python -m compileall app.py src scripts tests pages` 성공.
- realtime tick retention 포함 전체 검증: `python -m unittest discover -s tests -p "test_*.py"` 성공, 154 tests.
- 실시간 상태 fragment 패치: `python -m compileall src/ui/app_core.py tests/test_app_dashboard.py` 성공.
- 실시간 상태 fragment 패치: `python -m unittest tests.test_app_dashboard.RealtimeStatusFragmentTests tests.test_app_dashboard.DashboardAllocationStatusTests` 성공, 13 tests.
- 실시간 상태 fragment 패치: `python -m compileall app.py src scripts tests pages` 성공.
- 실시간 상태 fragment 패치: `python -m unittest discover -s tests -p "test_*.py"` 성공, 150 tests.
- DESIGN-07 모바일 거래 페이지 overflow 패치: `python -m compileall src/ui/app_core.py tests/test_app_dashboard.py` 성공.
- DESIGN-07 모바일 거래 페이지 overflow 패치: `python -m unittest tests.test_app_dashboard.ThemeStylesheetTests` 성공.
- DESIGN-07 모바일 거래 페이지 overflow 패치: `python -m compileall app.py src scripts tests pages` 성공.
- DESIGN-07 모바일 거래 페이지 overflow 패치: `python -m unittest discover -s tests -p "test_*.py"` 성공, 147 tests.
- DESIGN-07 브라우저 검증: 로컬 Streamlit `http://127.0.0.1:8532` 375px 거래 페이지에서 `.st-key-trade-form-cols` 존재, form block `flex-direction=column`, `bodyOverflows=false` 확인.
- DESIGN-04 데이터 페이지 테이블 테마 통일 패치: `python -m compileall src/ui/app_core.py tests/test_app_dashboard.py` 성공.
- DESIGN-04 데이터 페이지 테이블 테마 통일 패치: `python -m unittest tests.test_app_dashboard.HoldingsTableDisplayTests` 성공, 7 tests.
- DESIGN-04 데이터 페이지 테이블 테마 통일 패치: `python -m compileall app.py src scripts tests pages` 성공.
- DESIGN-04 데이터 페이지 테이블 테마 통일 패치: `python -m unittest discover -s tests -p "test_*.py"` 성공, 146 tests.
- DESIGN-04 브라우저 검증: 로컬 Streamlit `http://127.0.0.1:8531` 데모 데이터 페이지에서 `.holdings-table-shell=2`, `table.holdings-table=2`, `stDataFrame=3`, context warning 없음.
- DESIGN-02 선택 종목 트렌드 컨트롤 nowrap 패치: `python -m compileall src/ui/app_core.py tests/test_app_dashboard.py` 성공.
- DESIGN-02 선택 종목 트렌드 컨트롤 nowrap 패치: `python -m unittest tests.test_app_dashboard.ThemeStylesheetTests tests.test_app_dashboard.TradeFormResetTests.test_dashboard_selected_trend_period_options_exclude_today` 성공.
- DESIGN-02 선택 종목 트렌드 컨트롤 nowrap 패치: `python -m compileall app.py src scripts tests pages` 성공.
- DESIGN-02 선택 종목 트렌드 컨트롤 nowrap 패치: `python -m unittest discover -s tests -p "test_*.py"` 성공, 144 tests.
- DESIGN-01 상단 요약 카드 높이 정렬 패치: `python -m compileall src/ui/app_core.py tests/test_app_dashboard.py` 성공.
- DESIGN-01 상단 요약 카드 높이 정렬 패치: `python -m unittest tests.test_app_dashboard.ThemeStylesheetTests` 성공.
- DESIGN-01 상단 요약 카드 높이 정렬 패치: `python -m compileall app.py src scripts tests pages` 성공.
- DESIGN-01 상단 요약 카드 높이 정렬 패치: `python -m unittest discover -s tests -p "test_*.py"` 성공, 144 tests.
- DESIGN-05 거래유형 배지 스타일 패치: `python -m compileall src/ui/app_core.py tests/test_app_dashboard.py` 성공.
- DESIGN-05 거래유형 배지 스타일 패치: `python -m unittest tests.test_app_dashboard` 성공, 47 tests.
- DESIGN-05 거래유형 배지 스타일 패치: `python -m compileall app.py src scripts tests pages` 성공.
- DESIGN-05 거래유형 배지 스타일 패치: `python -m unittest discover -s tests -p "test_*.py"` 성공, 144 tests.
- DESIGN-03 트리맵 경계선/여백 패치: `python -m compileall src/ui/app_core.py tests/test_app_dashboard.py` 성공.
- DESIGN-03 트리맵 경계선/여백 패치: `python -m unittest tests.test_app_dashboard.AllocationTreemapVisualMapTests` 성공.
- DESIGN-03 트리맵 경계선/여백 패치: `python -m compileall app.py src scripts tests pages` 성공.
- DESIGN-03 트리맵 경계선/여백 패치: `python -m unittest discover -s tests -p "test_*.py"` 성공, 143 tests.
- BUG-03 거래기록 삭제 캐시 무효화 패치: `python -m compileall src/db.py tests/test_db.py` 성공.
- BUG-03 거래기록 삭제 캐시 무효화 패치: `python -m unittest tests.test_db.DataCacheTests` 성공.
- BUG-03 거래기록 삭제 캐시 무효화 패치: `python -m compileall app.py src scripts tests pages` 성공.
- BUG-03 거래기록 삭제 캐시 무효화 패치: `python -m unittest discover -s tests -p "test_*.py"` 성공, 142 tests.
- `python3 -m compileall app.py src scripts tests` 성공 기록 있음.
- `python3 -m unittest discover -s tests -p "test_*.py"` 성공 기록 있음.
- `python -m compileall app.py src scripts tests pages` 성공 기록 있음.
- `python scripts/run_kis_quote_worker.py --backend sqlite --preflight-only` 성공 기록 있음.
- `python3 scripts/verify_streamlit_deployment.py --page data --expect-backend supabase --wait-ms 12000` 성공 기록 있음.
- Streamlit Cloud 대시보드/거래/데이터 페이지 원격 검증 성공 기록 있음.

## 2026-05-13 검증 요약
- DESIGN-04 KPI 카드 반응형 grid 보강 검증.
  - `.dashboard-metric-strip` breakpoint를 `1180px=3열`, `820px=2열`, `560px=1열` 기준으로 추가.
  - `820px` 이하 섹션 헤더 상태 영역 세로 정렬과 `560px` 이하 카드 min-height/padding/value font 보정을 스타일시트 테스트로 확인.
  - 로컬 Streamlit 데모 대시보드 1180/820/560px에서 가로 overflow가 없고 560px 모바일 보정이 적용됨을 Playwright로 확인.
- DESIGN-02 KPI 카드 시각적 위계 보강 검증.
  - 대시보드 요약/metric 카드에 gradient surface, `--radius-xl`, `--shadow-card`, hover shadow, 상단 accent bar 적용.
  - 렌더러가 카드 tone class와 delta class를 출력하는지 단위 테스트로 확인.
  - 로컬 Streamlit 데모 대시보드 브라우저 검증에서 KPI 카드 스타일 적용과 가로 overflow 없음 확인.
- CSS radius/shadow 디자인 토큰 교체 검증.
  - `.streamlit/app.css` 상단 `:root`의 radius/shadow 토큰을 `--radius-*`, `--shadow-*` 구조로 정리.
  - 기존 `--card-shadow` CSS 변수 정의와 참조를 제거하고 주요 카드/패널 shadow를 새 토큰으로 전환.
  - 스타일시트 회귀 테스트와 전체 compileall/unittest discover 성공.
- realtime tick 보존/집계 정책 검증.
  - `setup_supabase.sql`에 `realtime_price_bars` 테이블, 인덱스, grant, RLS 정책 추가.
  - SQLite fallback에 같은 bar 테이블을 추가하고 `scripts/run_realtime_tick_retention.py`로 7일 raw, 90일 1분/5분봉, 90일 초과 일봉 정책을 구현.
  - 기본 실행은 dry-run이며 `--apply`를 명시한 경우에만 집계 저장과 raw tick 삭제를 수행.
  - SQLite retention 단위 테스트, setup SQL 회귀 테스트, CLI dry-run, 전체 compileall/unittest discover 성공.
- 실시간 worker/quote 상태 영역 fragment 갱신 검증.
  - 대시보드 기준시각, 자산 배분 상태 칩, 데이터 페이지 KIS worker/마지막 quote metric을 `st.fragment(run_every="10s")`로 분리.
  - 대시보드 전체 자동 rerun fragment는 제거하고 상태 표시 조각만 독립 갱신하도록 조정.
  - fragment 적용 범위 회귀 테스트와 전체 compileall/unittest discover 성공.
- DESIGN-07 모바일 거래 페이지 2열 입력 영역 overflow 보강 검증.
  - 거래/현금흐름 상위 2열을 `trade-form-cols` key 컨테이너로 감싸 모바일 CSS 적용 범위를 명시.
  - `max-width: 768px`에서 거래 입력 영역의 Streamlit horizontal block/column을 단일 컬럼으로 전환.
  - 로컬 Streamlit 375px 모바일 뷰포트에서 거래 페이지 body overflow가 없음을 확인.
  - 스타일시트 회귀 테스트와 전체 compileall/unittest discover 성공.
- DESIGN-04 데이터 페이지 보유종목/거래기록 테이블 테마 통일 검증.
  - 데이터 페이지 export preview 중 `holdings`, `trade_logs`를 `.holdings-table` HTML 테이블로 렌더링.
  - `accounts`, `daily_account_snapshot`, 원금 누적 기록은 기존 `st.dataframe` 표시 유지.
  - 로컬 Streamlit 데모 데이터 페이지에서 보유종목/거래기록 custom table DOM 확인.
  - 전체 compileall과 unittest discover 성공.
- DESIGN-02 선택 종목 트렌드 컨트롤 1행 유지 검증.
  - 대시보드 전용 기간 라벨을 `1M`, `3M`, `6M`, `1Y`로 단축하고 범용 기간 라벨은 기존 한국어 표기를 유지.
  - trend-controls 내부 column/select `min-width: 0` 규칙을 추가해 좁은 PC 폭에서 불필요한 wrapping을 줄임.
  - 전체 compileall과 unittest discover 성공.
- DESIGN-01 상단 요약 카드 높이 정렬 검증.
  - `.st-key-dashboard-summary-strip [data-testid="stHorizontalBlock"] > div` 기반 Flexbox stretch 규칙 추가.
  - 요약 카드 전용 `stVerticalBlockBorderWrapper` 의존 selector 제거를 스타일시트 테스트로 확인.
  - 전체 compileall과 unittest discover 성공.
- DESIGN-05 거래유형 배지 스타일 보강 검증.
  - `personal_deposit`, `employer_deposit`, `withdraw` 배지 스타일 추가.
  - 거래 기록 표의 `trade_type` 셀에서 현금흐름 유형도 `<span>` 배지 HTML로 반환되는지 단위 테스트로 확인.
  - 전체 compileall과 unittest discover 성공.
- DESIGN-03 자산 배분 트리맵 경계선/여백 정렬 검증.
  - ECharts treemap `upperLabel` 높이와 글자 크기를 고정하고 `gapWidth=0`, `borderWidth=1`을 적용.
  - series/level/leaf 스타일이 같은 경계 규칙을 사용하는지 단위 테스트로 확인.
  - 전체 compileall과 unittest discover 성공.
- BUG-03 거래기록 삭제 후 캐시 잔상 방지 검증.
  - `delete_trade_log()` 성공 후 `mark_data_dirty()`와 DB 조회 캐시 clear 실행 순서 단위 테스트 추가.
  - 삭제 실패 시 캐시 무효화 후처리가 실행되지 않음을 단위 테스트로 확인.
  - 전체 compileall과 unittest discover 성공.
- realtime worker 상태 보존/복구 검증.
  - `python3 -m compileall app.py src scripts tests` 성공.
  - `python3 -m unittest discover -s tests -p "test_*.py"` 성공.
  - `python3 -m unittest tests.test_run_kis_quote_worker tests.test_db` 성공.
  - 운영 Supabase `realtime_worker_status.last_quote_at` 복구 후 보존 확인.
  - 원격 데이터 페이지에서 worker 상태와 마지막 quote 반영 시각 노출 확인.
- GitHub Actions 실주행 검증.
  - `KIS Realtime Worker` manual run `25771266167` 실행.
  - job 로그에서 WebSocket 연결, `ping/pong timed out`, 재연결, 종료코드 `137`, 최종 `success` 확인.
  - run 종료 후 계좌 `24`, `25`, `26`의 `last_quote_at` 보존 확인.
- `setup_supabase.sql` 정책 재실행 안정화 검증.
  - `.venv`에 `pglast` 설치 후 `setup_supabase.sql` 전체 파싱 성공.
  - 괄호 개수 점검에서 open/close 균형 확인.
  - `python3 -m unittest tests.test_setup_supabase_sql` 성공.
  - 전체 compileall과 unittest discover 성공.
  - 데이터 페이지 배포 검증 성공.

## 2026-05-12 검증 요약
- KRX/Naver chart fallback 검증.
  - 전체 compileall 성공.
  - `tests.test_market`, 선택 종목/트리맵 관련 테스트 성공.
  - `0162Z0`, `0113D0` Naver 분봉/일봉 직접 조회 성공.
  - Streamlit Cloud 대시보드 검증 성공.
- `st.navigation` 전환 및 Streamlit Cloud 복구 검증.
  - `python -m compileall app.py src scripts tests pages` 성공.
  - `python -m unittest discover -s tests -p "test_*.py"` 성공.
  - `python scripts/run_kis_quote_worker.py --backend sqlite --preflight-only` 성공.
  - 원격 대시보드/거래/데이터 페이지에서 로그인, Supabase backend, 주요 마커 확인.
- UI 레이아웃 검증.
  - 대시보드/거래 페이지 원격 검증 성공.
  - 로컬 Streamlit + Playwright/agent-browser로 대시보드 높이, 카드 clipping, 페이지 전환 확인.

## 2026-05-11 검증 요약
- 현금 스냅샷 계산 수정 검증.
  - `python3 -m compileall src/db.py tests/test_db.py` 성공.
  - `python3 -m unittest tests.test_db` 성공.
  - 전체 compileall과 unittest discover 성공.
  - 로컬 SQLite와 운영 Supabase 스냅샷 재대조 결과 추가 보정 필요 없음.
- 거래/현금 정책 검증.
  - 보유현금 수동 유지, 매수 현금 부족 차단 해제, 음수 현금 helper 경로 수정 관련 단위/통합 테스트 성공.
  - 로컬 Streamlit 재현에서 현금 부족 차단 문구와 `StreamlitAPIException` 제거 확인.
- 배포 검증 스크립트 보강 검증.
  - `tests.test_verify_streamlit_deployment` 성공.
  - allocation status parsing과 expectation 검증 성공.
  - `--storage-state`, `--debug-dir` 옵션 검증 기록 있음.
- GitHub Actions 검증.
  - `Daily Rollup` manual dry-run 성공.
  - `KIS Realtime Worker` manual 1분 run 성공.
  - `Node.js 20 actions are deprecated` 경고 문구 미발견.

## 반복 사용 검증 명령
```powershell
python -m compileall app.py src scripts tests pages
python -m unittest discover -s tests -p "test_*.py"
python scripts/run_kis_quote_worker.py --backend sqlite --preflight-only
python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase --wait-ms 15000
python scripts/verify_streamlit_deployment.py --page trades --expect-backend supabase --wait-ms 15000
python scripts/verify_streamlit_deployment.py --page data --expect-backend supabase --wait-ms 12000
```

## 대표 검증 산출물
- `artifacts/deploy-verify-data-worker-status-20260513/*`
- `artifacts/deploy-verify-data-after-push-aab9d67/*`
- `artifacts/deploy-verify-dashboard-20260513-run1/*`
- `artifacts/deploy-verify-dashboard-20260513-run2/*`
- `artifacts/dashboard-height-final-verified.png`
- `artifacts/local-streamlit-8530-dashboard-navigation-final.png`
- `artifacts/local-streamlit-8530-trades-navigation-final.png`
- `artifacts/local-streamlit-8530-data-navigation-final.png`

## 현재 미검증 또는 추가 확인 필요
- Supabase SQL Editor에서 `setup_supabase.sql` 전체 또는 문제 정책 블록 직접 재실행.
- KIS WebSocket worker 장시간 장중 실행에서 재연결/상태 복구가 운영 요구와 맞는지 확인.
- 모바일 viewport 기준 대시보드 트리맵/보유 종목 표/거래 입력 폼 가독성 검증.
- 로딩 스피너/스켈레톤 UI가 장시간 작업 전체에 일관 적용됐는지 점검.

## 상세 원문 위치
- `docs/archive/memory-2026-05-11.md`
- `docs/archive/memory-2026-05-12.md`
- `docs/archive/memory-2026-05-13.md`
- `docs/archive/memory-2026-05-15.md`

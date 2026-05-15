# Memory.md

## 문서 목적
- 현재 프로젝트 상태와 다음 작업에 필요한 최소 정보만 유지한다.
- 상세 검증 이력은 `docs/VALIDATION.md`, 완료 변경 이력은 `docs/CHANGELOG.md`, 설계 결정은 `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-15`

## 작업 상태
- [x] 입금액 기준 일별 평가액 기록 기능 추가
- [x] Supabase/SQLite `daily_valuation_snapshot` 테이블, 인덱스, RLS, 정책, GRANT 정의
- [x] `src/valuation.py` 순수 계산 로직과 재계산/저장 서비스 함수 추가
- [x] `src/db.py`, `src/sqlite_db.py` 평가 스냅샷 저장/조회/삭제 wrapper 추가
- [x] 거래 UI, CSV import, 수동 가격 갱신, daily rollup 재계산 hook 추가
- [x] Dashboard 스냅샷 우선 표시와 `평가액 기록` 페이지 추가
- [x] 평가액 기록 시작일과 원금을 회사 납입금 단독 기준에서 개인 입금 포함 입금성 거래 기준으로 변경
- [x] Supabase 평가 스냅샷 저장 전 중복 계좌 재조회로 발생하던 “계좌를 찾을 수 없습니다” 경고 방지
- [x] 평가액 기록 CSV 저장/불러오기와 화면 수정 저장 기능 추가
- [x] 사이드바 연금 유형 뱃지 제거, Dashboard 히어로 전일 대비 증감 표시, 손익/수익률 KPI 차트 확대
- [x] 평가액 기록 과거 현금을 단순 원금-잔여원가에서 거래 원장 `cash_delta` 누적 기준으로 변경
- [x] 평가액 기록 스냅샷 조회/표시 순서를 최신 기준일 우선으로 변경
- [x] 계산/DB/스키마/UI/배치 회귀 테스트 추가 및 통과
- [x] Supabase 운영 DB에 `migrations/2026-05-14_add_daily_valuation_snapshot.sql` 적용 및 평가 스냅샷 재계산
- [x] 운영 `jhonkim2025` 계정 평가 스냅샷을 원장 현금 기준으로 재계산
- [x] 기존 `migrations/2026-05-14_normalize_temporal_columns.sql` 적용 전 cast 실패 행 여부 점검
- [x] KIS WebSocket worker 장시간 실행 중 재연결/상태 복구를 장중 운영 로그 기준으로 추가 점검
- [ ] temporal normalize migration 실제 적용 전 운영 `realtime_price_bars` 테이블 생성/노출 여부 결정

## 프로젝트 개요
- 유형: `Python + Streamlit`
- 진입점: `app.py`
- 앱 코어: `src/ui/app_core.py`
- 공개 페이지: `pages/dashboard.py`, `pages/trades.py`, `pages/valuation.py`
- 저장소: `Supabase` 우선, 필요 시 `SQLite`
- 로컬 SQLite DB: `data/portfolio.db`
- 시세: `KIS REST/WebSocket` 우선, KRX/Naver fallback, 일부 `yfinance` fallback
- UI 설정: `.streamlit/config.toml`, `.streamlit/app.css`
- 배포 앱: `https://retirement-portfolio-app-nh2vq9ferqnpehsslbykbe.streamlit.app/`

## 최근 변경 파일
- `setup_supabase.sql`: `daily_valuation_snapshot` 테이블, 인덱스, RLS 정책 4종, 명시적 GRANT 추가
- `migrations/2026-05-14_add_daily_valuation_snapshot.sql`: 신규 평가 스냅샷 테이블 migration 추가
- `src/valuation.py`: 입금 원금 기준 일별 평가 스냅샷 계산, 원장 현금 누적, 가격 lookup 구성, 재계산/저장 서비스 추가
- `src/market.py`: 날짜 범위 가격 이력 조회 helper 추가
- `src/sqlite_db.py`: SQLite 평가 스냅샷 테이블 생성 및 저장/조회/삭제 구현, 최신 기준일 우선 조회, 현금 직접 수정 시 `cash_adjustment` 원장 기록 추가
- `src/db.py`: Supabase/SQLite 공통 wrapper, Supabase batch upsert, 최신 기준일 우선 조회, cache 무효화, export table 반영, Supabase 현금 직접 수정 `cash_adjustment` 기록 추가
- `src/ui/app_core.py`: Dashboard 스냅샷 우선 표시, 평가액 기록 페이지, 거래/CSV/가격 갱신 후 재계산 hook 추가
- `src/ui/app_core.py`: 평가액 기록 CSV 저장/불러오기, `data_editor` 기반 수동 수정 저장 추가
- `src/ui/app_core.py`: 사이드바 계좌 카드의 연금 유형 뱃지 렌더링 제거, Dashboard 히어로는 전일 대비 총자산 증감을 표시
- `.streamlit/app.css`: 사이드바 단일 계좌 이름 박스 스타일과 손익/수익률 KPI sparkline 확대 스타일 추가
- `pages/valuation.py`: Streamlit 평가액 기록 페이지 진입점 추가
- `scripts/run_daily_rollup.py`: 기존 일별 계좌 스냅샷 저장 후 평가 스냅샷도 재계산 저장
- `scripts/run_kis_quote_worker.py`: 종료 신호가 WebSocket 내부에서 오류 콜백으로 흡수돼도 재연결하지 않고 `stopped` 상태를 남기도록 보강
- `.github/workflows/kis-realtime-worker.yml`: 장중 worker timeout 종료 신호를 `SIGINT`로 명시
- `scripts/verify_streamlit_deployment.py`: `valuation` 페이지 검증 대상 추가
- `tests/test_valuation.py`, `tests/test_run_daily_rollup.py`: 신규 계산/배치 테스트 추가
- `tests/test_db.py`, `tests/test_setup_supabase_sql.py`, `tests/test_app_dashboard.py`, `tests/test_verify_streamlit_deployment.py`, `tests/test_run_kis_quote_worker.py`: 신규 저장소/스키마/UI/worker 검증 확장
- `README.md`, `docs/VALIDATION.md`: 기능/검증 문서 갱신

## 핵심 설계 결정
- 기존 `account_summary`와 `daily_account_snapshot` 계산은 유지하고, 입금 기준 이력은 별도 `daily_valuation_snapshot`에 저장한다.
- `company_principal` 컬럼은 기존 스키마명을 유지하되 `employer_deposit`, `personal_deposit`, legacy `deposit`, `opening_cash`를 입금 원금으로 누적한다.
- 매수 lot은 FIFO로 쌓고 매도는 FIFO 기준으로 잔여 수량과 잔여 매입원가를 차감한다.
- 과거 날짜 현금은 거래 원장의 `cash_delta`를 누적한 원장 현금을 사용하고, 오늘 날짜는 `account.cash_balance` 실제 현금을 사용한다.
- 매도 실현손익, 이자, 배당, 수수료, 현금 조정처럼 `cash_delta`가 있는 이벤트는 원금이 아니라 원장 현금에 반영한다.
- UI/배치에서 넘기는 오늘 기준일은 Asia/Seoul 날짜를 사용한다.
- 가격은 해당일 종가, 없으면 직전 종가, 그래도 없으면 lot 단가를 사용한다. `missing_price_symbols`에는 lot 단가 fallback 종목만 기록한다.
- `source_hash`에는 거래 원장, 가격 lookup 요약, 오늘 실제 현금, 기준 날짜를 포함해 가격 갱신 재계산도 구분한다.
- `rebuild_and_save_daily_valuation_snapshots()`는 stale row 방지를 위해 계좌의 기존 평가 스냅샷을 삭제한 뒤 전체 series를 다시 저장한다.
- realtime tick마다 재계산하지 않고 거래 UI, CSV import 완료, 수동 가격 refresh, daily rollup에서 계좌별 1회 재계산한다.
- Dashboard는 오늘 평가 스냅샷이 있으면 `보유 평가액`, `입금 원금`, `현재 보유현금`, `입금 대비 손익`, `입금 대비 수익률`을 우선 표시한다.
- 평가액 기록 조회와 화면 표시는 `valuation_date DESC, id DESC` 최신 기준일 우선 순서를 사용한다.
- Dashboard 히어로의 `전일 대비` 값은 입금 대비 손익이 아니라 추이 데이터의 마지막 두 `total_value` 차이로 계산한다.
- 사이드바 계좌 카드에서는 계좌명만 표시하고 `연금(IRP/퇴직연금)` 유형 뱃지는 표시하지 않는다.
- 스냅샷이 없으면 기존 summary와 `daily_account_snapshot` 기반 표시로 fallback한다.
- KIS WebSocket worker는 운영 중 `ping/pong timed out` 후 재연결할 수 있지만, 종료 신호 수신 시에는 WebSocket을 닫고 재연결 루프 대신 `stopped` 상태 저장 경로로 이동한다.

## 실행 명령
```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```
- 로컬호스트가 응답하지 않거나 파일 감시자 이슈가 있으면 다음처럼 실행한다.
```powershell
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.fileWatcherType none
```

## 최신 검증 결과
- Supabase 운영 `migrations/2026-05-14_normalize_temporal_columns.sql` 사전 cast 점검: 대상 temporal 컬럼 전체 `invalid_rows=0`; 단, 운영 DB에 `public.realtime_price_bars`가 없어 migration 전체 적용 전 테이블 선행 적용 여부 확인 필요
- GitHub Actions `KIS Realtime Worker` 최신 run `25845045857` 성공, 운영 Supabase tick 총 12,449건 및 account 23/24/25/26 `stopped` 상태 확인
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
- 로컬 Streamlit 서버 `http://127.0.0.1:8501` health `ok`
- `python scripts/verify_streamlit_deployment.py --url https://retirement-portfolio-app-nh2vq9ferqnpehsslbykbe.streamlit.app/ --page valuation --expect-backend supabase --wait-ms 12000 --screenshot artifacts/deploy-valuation-newest-first.png ...` 성공, `ok=true`
- Supabase 운영 `jhonkim2025` 계정 재계산: account 23 스냅샷 686건, account 24 스냅샷 99건, account 25/26은 입금 원장 없음으로 0건

## Git/GitHub 상태
- 기본 브랜치: `main`
- 최근 커밋: `d4b0797 Document valuation newest-first deploy check`
- 워크트리에는 이번 요청 전부터 `data/portfolio.db`, `.streamlit/app.css`, `src/auth.py`, `docs/review_report.md` 삭제, 로컬 도구 디렉터리, 산출물 등 여러 변경/미추적 파일이 함께 있었다.
- 커밋 시 요청 관련 파일만 선별하고 `data/portfolio.db`, `.local/`, `.playtools*/`, `.playwright-browsers/`, `.vscode/`, `artifacts/`, `data/kis_cache/` 등 로컬 산출물은 제외한다.

## 운영 시크릿 메모
- 앱용: `SUPABASE_URL`, `SUPABASE_KEY`
- 관리자/배치용: `SUPABASE_SERVICE_ROLE_KEY`
- KIS용: `KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_ENV`
- 배포 검증용: `STREAMLIT_VERIFY_EMAIL`, `STREAMLIT_VERIFY_PASSWORD`
- 실제 값은 `.streamlit/secrets.toml`, Streamlit Cloud secrets, GitHub Actions secrets, OS 환경 변수에만 둔다.

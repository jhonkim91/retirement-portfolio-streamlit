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
- [x] Supabase/SQLite 실시간 tick retention 전용 인덱스 보강
- [x] 평가액 기록 수익률 계산 시 일반 출금을 순입금 원금에서 차감
- [x] 거래 기록 선택 삭제 UI/로직 추가
- [x] 거래 기록 선택 삭제 시 연관 매도 자동 포함으로 음수 보유수량 오류 방지
- [x] 평가액 기록 현금값을 일별 실제 계좌 스냅샷 현금 우선으로 보정
- [x] 평가액 기록/원화 표시 금액을 원 단위 일반 반올림으로 보정
- [x] 1,000배 총액 중복 거래와 국내 종목 코드 접미사 차이로 인한 평가/실현손익 왜곡 보정
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
- `src/trade_log_filters.py`: 같은 날짜/유형/종목/수량/단가에서 총액만 1,000배 수준으로 큰 중복 매수/매도 행을 계산 입력에서 제외하는 helper 추가
- `src/valuation.py`, `src/analytics.py`: 평가 스냅샷과 실현손익 계산에서 중복 총액 행 제외, 국내 종목 `.KS/.KQ` 접미사와 앞자리 0 차이를 같은 종목으로 정규화
- `tests/test_valuation.py`, `tests/test_analytics.py`: 총액 스케일 중복 제외와 국내 종목 코드 정규화 회귀 테스트 추가
- `artifacts/trade_logs_23_reconciled.csv`, `artifacts/valuation_snapshots_23_recalculated.csv`: `trade_logs_23.csv`, `valuation_snapshots_23.csv` 기준 재산출 파일
- `src/valuation.py`: 평가 스냅샷 금액 컬럼을 소수점 4자리 저장 대신 원 단위 일반 반올림 값으로 산출
- `src/ui/app_core.py`: 원화 표시 helper와 거래 금액 표시를 원 단위 일반 반올림으로 통일
- `tests/test_valuation.py`, `tests/test_app_dashboard.py`: `.5` 금액 반올림과 평가 스냅샷 원 단위 저장 회귀 테스트 추가
- `src/valuation.py`: 일별 계좌 스냅샷 현금이 있으면 평가액 기록 현금값에 실제 현금을 우선 사용하고, 보유 수량 없이 먼저 들어온 매도는 매칭 수량만 현금 유입 반영
- `src/db.py`, `src/ui/app_core.py`, `scripts/run_daily_rollup.py`: daily rollup/manual rebuild 평가 스냅샷 재계산 시 `daily_account_snapshot` 목록 전달
- `tests/test_valuation.py`, `tests/test_run_daily_rollup.py`: 과거 실제 현금 우선 적용과 미매칭 매도 현금 부풀림 방지 회귀 테스트 추가
- `src/ui/app_core.py`: 거래 기록 선택 삭제 시 선택 매수 제거로 음수 보유수량을 만드는 연관 매도 기록을 삭제 확인 대상에 자동 포함
- `tests/test_app_dashboard.py`: 연관 매도 자동 포함과 기존 원장 불일치 차단 회귀 테스트 추가
- `src/ui/app_core.py`: 거래 기록 표에 행 선택 체크박스, 현재 페이지 선택, 선택 해제, 선택 삭제 toolbar, 선택 삭제 확인 dialog 추가
- `tests/test_app_dashboard.py`: 거래 기록 선택 상태 helper와 선택 삭제 dialog/source 회귀 테스트 추가
- `src/valuation.py`, `src/ui/app_core.py`, `tests/test_valuation.py`: 평가액 기록 수익률을 일반 출금을 차감한 순입금 원금 기준으로 보정
- `setup_supabase.sql`, `migrations/2026-05-15_reinforce_realtime_indexes.sql`, `src/sqlite_db.py`, `scripts/run_realtime_tick_retention.py`: realtime retention 인덱스와 조회 정렬 보강
- `setup_supabase.sql`, `migrations/2026-05-14_add_daily_valuation_snapshot.sql`, `src/valuation.py`, `src/db.py`, `src/sqlite_db.py`, `pages/valuation.py`: 입금액 기준 일별 평가액 기록 기능 추가

## 핵심 설계 결정
- 기존 `account_summary`와 `daily_account_snapshot` 계산은 유지하고, 입금 기준 이력은 별도 `daily_valuation_snapshot`에 저장한다.
- `company_principal` 컬럼은 기존 스키마명을 유지하되 `employer_deposit`, `personal_deposit`, legacy `deposit`, `opening_cash`에서 일반 출금을 차감한 순입금 원금으로 계산한다.
- 매수 lot은 FIFO로 쌓고 매도는 FIFO 기준으로 잔여 수량과 잔여 매입원가를 차감한다.
- 과거 날짜 현금은 같은 날짜 `daily_account_snapshot.cash_balance`가 있으면 실제 현금을 사용하고, 없으면 거래 원장의 `cash_delta`를 누적한 원장 현금으로 fallback한다. 오늘 날짜는 `account.cash_balance` 실제 현금을 사용한다.
- 매도 실현손익, 이자, 배당, 수수료, 현금 조정처럼 `cash_delta`가 있는 이벤트는 원금이 아니라 원장 현금에 반영한다.
- UI/배치에서 넘기는 오늘 기준일은 Asia/Seoul 날짜를 사용한다.
- 가격은 해당일 종가, 없으면 직전 종가, 그래도 없으면 lot 단가를 사용한다. `missing_price_symbols`에는 lot 단가 fallback 종목만 기록한다.
- `source_hash`에는 거래 원장, 가격 lookup 요약, 오늘 실제 현금, 기준 날짜를 포함해 가격 갱신 재계산도 구분한다.
- `rebuild_and_save_daily_valuation_snapshots()`는 stale row 방지를 위해 계좌의 기존 평가 스냅샷을 삭제한 뒤 전체 series를 다시 저장한다.
- realtime tick마다 재계산하지 않고 거래 UI, CSV import 완료, 수동 가격 refresh, daily rollup에서 계좌별 1회 재계산한다.
- Dashboard는 오늘 평가 스냅샷이 있으면 `보유 평가액`, `입금 원금`, `현재 보유현금`, `입금 대비 손익`, `입금 대비 수익률`을 우선 표시한다.
- 평가액 기록 조회와 화면 표시는 `valuation_date DESC, id DESC` 최신 기준일 우선 순서를 사용한다.
- 평가액 기록 현금값은 오늘은 `account.cash_balance`, 과거일은 같은 날짜 `daily_account_snapshot.cash_balance`가 있으면 실제 현금, 없으면 매수/매도/현금흐름 원장 현금으로 계산한다.
- 평가액 기록의 금액 컬럼과 원화 UI 표시는 소수점 이하를 원 단위로 일반 반올림한다. 수익률은 기존처럼 소수점 표시를 유지한다.
- 같은 날짜/유형/종목/수량/단가에 총액만 1,000배 수준으로 큰 중복 매수/매도가 있으면 큰 총액 행은 평가/실현손익 계산에서 제외한다.
- 국내 종목 코드는 `.KS/.KQ` 접미사를 제거하고 숫자 코드는 6자리로 맞춰 `487240`과 `487240.KS`, `69500`과 `069500`을 같은 종목으로 매칭한다.
- 보유 수량 없이 먼저 들어온 매도 기록은 평가 현금을 부풀리지 않도록 FIFO lot에 매칭된 수량 비율만 현금 유입으로 반영한다.
- 거래 기록 삭제는 개별 행 삭제 버튼 대신 선택 id 목록을 세션에 저장하고, 선택 삭제 dialog에서 기존 `delete_trade_log()`와 평가액 기록 재계산 경로를 반복 호출한다.
- 선택 매수 삭제로 남은 매도 원장이 보유 수량을 음수로 만들 경우 해당 연관 매도 기록을 확인 dialog의 삭제 대상에 자동 포함한다.
- 선택 삭제는 매도/매수 종속성으로 인한 중간 상태 오류를 줄이기 위해 거래일/id 역순으로 삭제한다.
- Dashboard 히어로의 `전일 대비` 값은 입금 대비 손익이 아니라 추이 데이터의 마지막 두 `total_value` 차이로 계산한다.
- 사이드바 계좌 카드에서는 계좌명만 표시하고 `연금(IRP/퇴직연금)` 유형 뱃지는 표시하지 않는다.
- 스냅샷이 없으면 기존 summary와 `daily_account_snapshot` 기반 표시로 fallback한다.
- KIS WebSocket worker는 운영 중 `ping/pong timed out` 후 재연결할 수 있지만, 종료 신호 수신 시에는 WebSocket을 닫고 재연결 루프 대신 `stopped` 상태 저장 경로로 이동한다.
- realtime retention은 시간 범위 count/delete 성능을 우선해 `quote_time, id` 정렬 인덱스를 사용하고, 집계 정확도는 `aggregate_ticks()` 내부 정렬로 유지한다.

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
- 작업 범위: `valuation_snapshots_23.csv`, `trade_logs_23.csv` 기준 평가/실현손익 산식 재점검 및 중복 총액/종목코드 정규화 보정
- 산출 파일: `artifacts/trade_logs_23_reconciled.csv`, `artifacts/valuation_snapshots_23_recalculated.csv`
- `python -m compileall src/valuation.py src/analytics.py src/trade_log_filters.py tests/test_valuation.py tests/test_analytics.py` 성공
- `python -m unittest tests.test_valuation tests.test_analytics` 성공, 35 tests
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 257 tests
- 테스트 중 Streamlit bare mode 경고가 출력됐으나 모든 테스트는 성공했다.

## Git/GitHub 상태
- 기본 브랜치: `main`
- 최근 배포 코드 커밋: `2c1a2ed Round won amounts to units`
- 워크트리에는 이번 요청 전부터 `data/portfolio.db`, 로컬 도구 디렉터리, 산출물 등 여러 변경/미추적 파일이 함께 있었다.
- 커밋 시 요청 관련 파일만 선별하고 `data/portfolio.db`, `.local/`, `.playtools*/`, `.playwright-browsers/`, `.vscode/`, `artifacts/`, `data/kis_cache/` 등 로컬 산출물은 제외한다.

## 운영 시크릿 메모
- 앱용: `SUPABASE_URL`, `SUPABASE_KEY`
- 관리자/배치용: `SUPABASE_SERVICE_ROLE_KEY`
- KIS용: `KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_ENV`
- 배포 검증용: `STREAMLIT_VERIFY_EMAIL`, `STREAMLIT_VERIFY_PASSWORD`
- 실제 값은 `.streamlit/secrets.toml`, Streamlit Cloud secrets, GitHub Actions secrets, OS 환경 변수에만 둔다.

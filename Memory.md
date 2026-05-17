# Memory.md

## 문서 목적
- 현재 프로젝트 상태와 다음 작업에 필요한 최소 정보만 유지한다.
- 상세 검증 이력은 `docs/VALIDATION.md`, 완료 변경 이력은 `docs/CHANGELOG.md`, 설계 결정은 `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-17`

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
- [x] 거래 기록 생성/수정/삭제 후 평가액 기록을 영향 시작일 이후만 부분 재계산하도록 최적화
- [x] 펀드성 코드(`K...`)의 1,000좌 기준가 단위를 보유 평가/거래 UI/저장 경로에 일관 적용
- [x] Dashboard KPI 카드의 입금 대비 손익/수익률 전일 대비 델타 표시
- [x] Dashboard KPI 값 급등 방지를 위해 오늘 평가 스냅샷 현금 산정 fallback 추가
- [x] `?demo=1` URL query parameter 기반 데모 자동 진입 추가
- [x] 로그인/온보딩 화면의 Streamlit 기본 사이드바 컨테이너 숨김
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
- `.streamlit/app.css`: 인증/온보딩 화면에서 `stSidebar`, `stSidebarCollapsedControl`, `stSidebarNav`를 조건부 숨김 처리.
- `tests/test_app_dashboard.py`: 인증/온보딩 화면용 사이드바 숨김 CSS selector 회귀 테스트 추가.
- `docs/VALIDATION.md`, `docs/CHANGELOG.md`, `Memory.md`: 최신 검증 결과와 변경 요약 갱신

## 핵심 설계 결정
- 기존 `account_summary`와 `daily_account_snapshot` 계산은 유지하고, 입금 기준 이력은 별도 `daily_valuation_snapshot`에 저장한다.
- `company_principal` 컬럼은 기존 스키마명을 유지하되 `employer_deposit`, `personal_deposit`, legacy `deposit`, `opening_cash`에서 일반 출금을 차감한 순입금 원금으로 계산한다.
- 매수 lot은 FIFO로 쌓고 매도는 FIFO 기준으로 잔여 수량과 잔여 매입원가를 차감한다.
- 과거 날짜 현금은 같은 날짜 `daily_account_snapshot.cash_balance`가 있으면 실제 현금을 사용하고, 없으면 거래 원장의 `cash_delta`를 누적한 원장 현금으로 fallback한다. 오늘 날짜는 `account.cash_balance`가 원장 현금과 원 단위로 맞을 때만 실제 현금으로 사용하고, 크게 다르면 원장 현금으로 fallback한다.
- 매도 실현손익, 이자, 배당, 수수료, 현금 조정처럼 `cash_delta`가 있는 이벤트는 원금이 아니라 원장 현금에 반영한다.
- UI/배치에서 넘기는 오늘 기준일은 Asia/Seoul 날짜를 사용한다.
- 가격은 해당일 종가, 없으면 직전 종가, 그래도 없으면 lot 단가를 사용한다. `missing_price_symbols`에는 lot 단가 fallback 종목만 기록한다.
- `source_hash`에는 거래 원장, 가격 lookup 요약, 오늘 실제 현금, 기준 날짜를 포함해 가격 갱신 재계산도 구분한다.
- `rebuild_and_save_daily_valuation_snapshots()`는 stale row 방지를 위해 전체 재계산 시 기존 평가 스냅샷을 전부 삭제하고, 거래 UI 등 부분 재계산 시 영향 시작일 이후 스냅샷만 삭제/재저장한다.
- realtime tick마다 재계산하지 않고 거래 UI, CSV import 완료, 수동 가격 refresh, daily rollup에서 계좌별 1회 재계산한다. 거래 UI/CSV import/수동 현금·가격 갱신은 영향 시작일 이후만 부분 재계산하고, daily rollup과 수동 재계산 버튼은 전체 재계산을 유지한다.
- Dashboard는 오늘 평가 스냅샷이 있으면 `보유 평가액`, `입금 원금`, `현재 보유현금`, `입금 대비 손익`, `입금 대비 수익률`을 우선 표시한다.
- 평가액 기록 조회와 화면 표시는 `valuation_date DESC, id DESC` 최신 기준일 우선 순서를 사용한다.
- 평가액 기록 현금값은 오늘은 `account.cash_balance`와 원장 현금이 일치할 때만 실제 현금, 과거일은 같은 날짜 `daily_account_snapshot.cash_balance`가 있으면 실제 현금, 그 외에는 매수/매도/현금흐름 원장 현금으로 계산한다.
- 평가액 기록의 금액 컬럼과 원화 UI 표시는 소수점 이하를 원 단위로 일반 반올림한다. 수익률은 기존처럼 소수점 표시를 유지한다.
- 펀드성 코드(`K...`)는 수량을 좌수로 보고 기준가를 1,000좌당 가격으로 해석해 거래금액과 보유 평가액을 `좌수 * 기준가 / 1000`으로 계산한다.
- 향후 저장되는 펀드 매수/매도 로그는 `total_amount`, `cash_delta`만 1,000좌 기준으로 정규화하고, `avg_cost/current_price`에는 기준가 원값을 유지한다.
- 기존에 저장된 1,000배 총액 데이터는 운영 DB에서 직접 수정하지 않고 표시/계산 경로에서 계속 정규화한다.
- Dashboard treemap intraday 상세 조회는 ECharts 렌더링 가능 경로에서만 수행한다.
- 평가액 부분 재계산은 영향 시작일 이전 계좌 스냅샷 조회를 피하기 위해 `list_account_snapshots(account_id, start_date=...)`를 사용한다.
- 같은 날짜/유형/종목/수량/단가에 총액만 1,000배 수준으로 큰 중복 매수/매도가 있으면 큰 총액 행은 평가/실현손익 계산에서 제외한다.
- 국내 종목 코드는 `.KS/.KQ` 접미사를 제거하고 숫자 코드는 6자리로 맞춰 `487240`과 `487240.KS`, `69500`과 `069500`을 같은 종목으로 매칭한다.
- 보유 수량 없이 먼저 들어온 매도 기록은 평가 현금을 부풀리지 않도록 FIFO lot에 매칭된 수량 비율만 현금 유입으로 반영한다.
- 거래 기록 삭제는 개별 행 삭제 버튼 대신 선택 id 목록을 세션에 저장하고, 선택 삭제 dialog에서 기존 `delete_trade_log()`와 평가액 기록 재계산 경로를 반복 호출한다.
- 선택 매수 삭제로 남은 매도 원장이 보유 수량을 음수로 만들 경우 해당 연관 매도 기록을 확인 dialog의 삭제 대상에 자동 포함한다.
- 선택 삭제는 매도/매수 종속성으로 인한 중간 상태 오류를 줄이기 위해 거래일/id 역순으로 삭제한다.
- Dashboard 히어로의 `전일 대비` 값은 입금 대비 손익이 아니라 추이 데이터의 마지막 두 `total_value` 차이로 계산한다.
- 사이드바 계좌 카드에서는 계좌명만 표시하고 `연금(IRP/퇴직연금)` 유형 뱃지는 표시하지 않는다.
- 스냅샷이 없으면 기존 summary와 `daily_account_snapshot` 기반 표시로 fallback한다.
- `?demo=1`, `?demo=true`, `?demo=yes`, `?demo=demo`는 비로그인 사용자에게만 기존 데모 버튼과 같은 `start_demo_workspace_session()` 흐름을 자동 실행한다. 이미 인증된 사용자는 query parameter로 세션을 바꾸지 않는다.
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
- 작업 범위: 초기 로그인/온보딩 화면의 Streamlit 기본 사이드바 노출 방지
- 변경 파일: `.streamlit/app.css`, `tests/test_app_dashboard.py`, `docs/VALIDATION.md`, `docs/CHANGELOG.md`, `Memory.md`
- 원인: Streamlit 기본 sidebar가 인증 화면에서도 생성되는데 기존 CSS가 `stSidebarNav`만 숨겨 빈 사이드바 컨테이너가 남을 수 있었다.
- CSS 중괄호 균형 확인 성공 (`{` 638개, `}` 638개)
- `python -m unittest tests.test_app_dashboard.ThemeStylesheetTests` 성공, 12 tests
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 281 tests
- 로컬 Streamlit `http://localhost:8508` 로그인 화면 브라우저 확인 성공: 본문 표시, error overlay 없음, `stSidebar` computed display `none`
- 운영 DB 데이터 직접 수정과 migration 추가는 수행하지 않았다.

## Git/GitHub 상태
- 기본 브랜치: `main`
- 최근 배포 코드 커밋: `0f19336 Add demo query auto entry`
- 이번 로그인 사이드바 핫픽스는 `origin/main` 배포 전 로컬 검증까지 완료했다.
- 워크트리에는 이번 요청 전부터 `data/portfolio.db`, 로컬 도구 디렉터리, 산출물 등 여러 변경/미추적 파일이 함께 있었다.
- 커밋 시 요청 관련 파일만 선별하고 `data/portfolio.db`, `.local/`, `.playtools*/`, `.playwright-browsers/`, `.vscode/`, `artifacts/`, `data/kis_cache/` 등 로컬 산출물은 제외한다.

## 운영 시크릿 메모
- 앱용: `SUPABASE_URL`, `SUPABASE_KEY`
- 관리자/배치용: `SUPABASE_SERVICE_ROLE_KEY`
- KIS용: `KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_ENV`
- 배포 검증용: `STREAMLIT_VERIFY_EMAIL`, `STREAMLIT_VERIFY_PASSWORD`
- 실제 값은 `.streamlit/secrets.toml`, Streamlit Cloud secrets, GitHub Actions secrets, OS 환경 변수에만 둔다.

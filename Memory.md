# Memory.md

## 문서 목적
- 현재 프로젝트 상태와 다음 작업에 필요한 최소 정보만 유지한다.
- 상세 검증 이력은 `docs/VALIDATION.md`, 완료 변경 이력은 `docs/CHANGELOG.md`, 설계 결정은 `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-16`

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
- [x] 데모 데이터 `데모 IRP`/`데모 주식` 2계좌 구성, 현재 보유 17개 종목, 5년치 입출금/매매일지 규칙 보강
- [x] 자산 배분 트리맵 예수금 중립색 처리와 타일 수익률 라벨 표시 개선
- [x] Streamlit UI 캡처 자동화와 거래/평가액 기록 페이지 캡처 확장
- [x] 대시보드 UI 개선 로컬 반영 및 요약 카드/트렌드/거래 패널/차트 반응형 보강
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
- `src/ui/app_core.py`: 대시보드/거래/평가액 기록 주요 UI 영역에 캡처용 `capture_*` wrapper 추가, `capture=1` 기준일과 거래 입력 기본 날짜 고정, overview 컬럼 비율 조정, 요약 카드/트렌드 컨트롤/거래 입력 flex wrapper, 차트 높이 metadata, 실현손익 차트 색상 보강
- `.streamlit/app.css`: dashboard max-width, overview hero/card, 기간 버튼, 패널 radius/shadow, treemap legend, 보유종목 테이블 스타일, 요약 카드 120px 높이/라벨, 트렌드 컨트롤, 거래 행 구분선, 거래 입력 2열/1열 responsive, 모바일 적층 레이아웃 보강
- `config/capture_blocks.yaml`: 페이지별 블록 name, selector, PNG 파일명, required, hidden tab 활성화 설정 정의
- `scripts/capture_app.py`: Playwright 기반 전체/블록 캡처, 로컬 Streamlit 자동 실행, page/viewport all, strict, manifest 생성, sidebar 상태 고정, loading 대기, selector 누락 로그, 데모 준비 대기와 visible 탭 클릭 구현
- `requirements-dev.txt`: UI 캡처용 `playwright`, `pyyaml` dev dependency 추가
- `docs/ui_capture.md`, `README.md`: 로컬 설치/실행, 산출물 구조, 보안 주의 문서화
- `.github/workflows/ui-capture.yml`: GitHub Actions에서 캡처 후 artifact 업로드 workflow 추가, checkout/setup-python 안정 버전 고정, job env DB 경로를 `/tmp/portfolio-capture.db`로 변경
- `src/db.py`: 캡처 모드 데모 seed 기준일 고정용 `snapshot_base_date` 인자 추가
- `src/auth.py`: 운영 Supabase URL 하드코딩 제거와 `https://*.supabase.co` URL 검증 복구
- `src/market.py`: KRX 심볼 판별, Naver 가격/이력 fallback, `fetch_price_history_range()` 호환 함수 복구
- `tests/test_app_dashboard.py`, `tests/test_db.py`: capture query, 고정 데모 기준일, 거래/평가액 캡처 wrapper, flex wrapper, 560px 차트 높이, 실현손익 차트 색상/라벨 테스트 추가
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
- Dashboard 자산 배분 트리맵 색상은 보유 종목 수익률 기준으로만 계산하고, 예수금은 수익률이 없는 현금 자산이므로 `visualMap` 값에 `None`을 넣어 회색 중립색으로 표시한다.
- Dashboard 자산 배분 트리맵 leaf 라벨은 보유 종목은 `종목명 + 보유 수익률`, 예수금은 `예수금 + 현금` 2줄 구성을 사용한다.
- 사이드바 계좌 카드에서는 계좌명만 표시하고 `연금(IRP/퇴직연금)` 유형 뱃지는 표시하지 않는다.
- 스냅샷이 없으면 기존 summary와 `daily_account_snapshot` 기반 표시로 fallback한다.
- `?demo=1`, `?demo=true`, `?demo=yes`, `?demo=demo`는 비로그인 사용자에게만 기존 데모 버튼과 같은 `start_demo_workspace_session()` 흐름을 자동 실행한다. 이미 인증된 사용자는 query parameter로 세션을 바꾸지 않는다.
- UI 캡처 기본 URL은 `?demo=1&capture=1`을 사용한다. 캡처 스크립트가 로컬 앱을 직접 실행할 때는 `PORTFOLIO_BACKEND=sqlite`와 캡처 전용 SQLite 파일을 사용해 실제 사용자 데이터 캡처를 피한다.
- `scripts/capture_app.py --page all --viewport all`은 viewport별 같은 브라우저 세션에서 dashboard → trades → valuation 순서로 이동한다. 새 세션마다 데모 seed가 반복되어 선택 계좌 상태가 꼬이는 것을 방지하기 위한 동작이다.
- 캡처 모드는 기본 기준일을 `2026-05-15`로 고정한다. 로컬 자동 실행 시 `PORTFOLIO_CAPTURE_REFERENCE_DATE`를 주입하고, `capture=1` 앱 화면에서는 이 기준일을 사용해 데모 seed, 그래프/테이블, 거래 입력 기본 날짜를 안정화한다.
- 캡처 전 sidebar는 desktop에서 expanded, tablet/mobile에서 collapsed 상태로 고정하고, Playwright는 spinner/progress/skeleton 대기와 animation/transition 비활성화를 적용한다.
- 데모 워크스페이스는 `데모 IRP`(`retirement`)와 `데모 주식`(`brokerage`) 두 계좌만 생성한다. 퇴직연금 계좌는 일반 주식 없이 ETF/채권/금/리츠 ETF 중심으로 구성하고, 일반 주식/해외주식은 주식 계좌에만 배치한다.
- 기존 이름인 `데모 일반계좌`가 남아 있는 워크스페이스는 새 `데모 주식` seed와 중복되지 않도록 데모 재시드 때 함께 삭제한다.
- 데모 seed 후 계좌 현금은 입금, 출금, 매수, 매도 원장을 모두 반영한 값으로 갱신한다. 거래 입력 함수가 계좌 현금을 직접 변경하지 않는 경로와 충돌하지 않도록 seed 전용 계산 helper를 사용한다.
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
- 작업 범위: 대시보드 요약 카드/선택 종목 트렌드 컨트롤/거래 입력 패널/실현손익 차트 반응형 보강, UI Capture GitHub Actions 시작 실패와 거래 탭 캡처 누락 보정
- 변경 파일: `.streamlit/app.css`, `src/ui/app_core.py`, `scripts/capture_app.py`, `tests/test_app_dashboard.py`, `.github/workflows/ui-capture.yml`, `docs/VALIDATION.md`, `docs/CHANGELOG.md`, `Memory.md`
- CSS 중괄호 균형 확인 성공 (`{` 679개, `}` 679개)
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest tests.test_app_dashboard` 성공, 122 tests
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 289 tests
- `.github/workflows/ui-capture.yml` YAML 파싱 및 action version 확인 성공
- `.github/workflows/ui-capture.yml`에서 job-level `env`의 `runner.temp` expression 제거 확인 성공
- `python -m unittest tests.test_app_dashboard` 재실행 성공, 123 tests
- `python scripts/capture_app.py --url "http://localhost:8506/?demo=1&capture=1" --page all --viewport desktop --out-dir /tmp/ui_captures_8506_all_desktop --strict` 성공
- 운영 DB 데이터 직접 수정과 migration 추가는 수행하지 않았다.

## Git/GitHub 상태
- 기본 브랜치: `main`
- 최근 배포 코드 커밋: `0f19336 Add demo query auto entry`
- 기본 UI 캡처 자동화 코드는 `codex/ui-capture-automation` 브랜치에 `89c5e16 Add Streamlit UI capture automation`으로 커밋했고 `origin/codex/ui-capture-automation`에 push했다.
- 이번 최신 변경은 `e9c1b04 Expand UI captures and refine dashboard design` 커밋으로 대시보드 UI 개선과 거래/평가액 기록 캡처 확장을 함께 반영한다.
- 최신 반응형 UI 보강은 `eec7ac1 Refine responsive dashboard UI`, `9828696 Record responsive UI publish` 커밋으로 `codex/ui-capture-automation` 브랜치에 반영했고 `origin/codex/ui-capture-automation`에 push했다.
- UI Capture GitHub Actions 시작 실패 보정은 `fcab67a Fix UI capture workflow actions`, `fb8d51d Fix UI capture workflow env` 커밋으로 반영했다.
- GitHub draft PR은 `https://github.com/jhonkim91/retirement-portfolio-streamlit/pull/1`이다.
- 원격 UI Capture run `25968169216`, `25968290999`는 job 로그 생성 전 실패했고, run `25968358824`는 desktop 거래 탭 selector 누락으로 실패했다. 캡처 스크립트 대기/visible 탭 클릭 보정 후 재실행 대상이다.
- `gh` CLI는 `/home/vscode/.local/bin/gh`에 설치되어 있고 GitHub 계정 `jhonkim91` 인증 상태를 확인했다.
- 워크트리에는 이번 요청 전부터 `data/portfolio.db`, 로컬 도구 디렉터리, 캡처 산출물 등 여러 변경/미추적 파일이 함께 있었다.
- 커밋 시 요청 관련 파일만 선별하고 `data/portfolio.db`, `.local/`, `.playtools*/`, `.playwright-browsers/`, `.vscode/`, `artifacts/`, `data/kis_cache/` 등 로컬 산출물은 제외한다.

## 운영 시크릿 메모
- 앱용: `SUPABASE_URL`, `SUPABASE_KEY`
- 관리자/배치용: `SUPABASE_SERVICE_ROLE_KEY`
- KIS용: `KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_ENV`
- 배포 검증용: `STREAMLIT_VERIFY_EMAIL`, `STREAMLIT_VERIFY_PASSWORD`
- 실제 값은 `.streamlit/secrets.toml`, Streamlit Cloud secrets, GitHub Actions secrets, OS 환경 변수에만 둔다.

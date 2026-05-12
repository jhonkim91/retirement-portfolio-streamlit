# Memory.md

## 작업 상태
- [x] 프로젝트 구조 분석 및 초기화 파일 확인
- [x] Streamlit 로그인 화면 재구성 및 데모 모드 추가
- [x] 대시보드 자산 배분/선택 종목 트렌드 UI 정리
- [x] Supabase 우선 저장소 및 배포 검증 자동화 정리
- [x] KIS REST/WebSocket 기반 실시간 quote worker 추가
- [x] 운영 Supabase realtime 테이블(`realtime_worker_status`, `realtime_price_ticks`) 생성 및 장중 적재 검증
- [x] GitHub Actions 기반 장중 KIS worker 자동 실행 workflow 추가
- [x] `gh` CLI 로컬 설치 및 Actions secrets 등록
- [x] GitHub-hosted runner에서 `KIS Realtime Worker` 수동 실행 성공 검증
- [x] `Memory.md` 장문 로그를 요약형 운영 메모로 정리
- [x] GitHub Actions `Node 24` 전환 경고 제거
- [x] 배포 검증 스크립트에 대시보드 자산 배분 상태 칩 파싱/기대값 검증 추가
- [x] `config.toml` 기반 디자인 토큰 및 전역 CSS 외부 파일 구조 정리
- [x] 보유 종목 수익률 음수 막대 모서리 방향 수정
- [x] 선택 종목 트렌드에 `당일` intraday 구간 추가
- [x] 선택 종목 `당일` 트렌드가 자산 배분 카드의 금일 시세와 같은 마지막 값을 사용하도록 보정
- [x] 현재 보유 종목 표에 가격갱신 초 단위 표시 및 손익/수익률 컬러 스타일 적용
- [x] 현재 보유 종목 박스에 위험/안전/보유현금 비율 막대바 추가
- [x] 현재 보유 종목 비율 막대에서 보유현금을 안전자산에 포함하도록 조정
- [x] 기존 일별 이자 이력이 있는 계좌의 매수 전 현금 재동기화 복구
- [x] 입금액과 무관하게 매수 상품 등록 허용
- [x] Supabase 음수 현금 helper 제약으로 막히던 거래 등록 재수정
- [x] 거래 저장 후 `st.session_state` 직접 초기화 예외 제거
- [x] 운영 배포용 `app.py` 초기 `importlib.reload(src.market)` 제거
- [x] 배포 검증 스크립트에 세션 재사용/디버그 아티팩트 저장 옵션 추가
- [x] `src/market.py` 검색 캐시 추가 및 정규화 질의 회귀 테스트 보강
- [x] 사용자별 DB 조회 캐시 및 이자 조회 제거 반영
- [x] 외부 CDN 폰트 import 제거 및 시스템 폰트 스택 전환
- [x] 거래 페이지 계좌 간 이체 기능 삭제
- [x] 보유현금 수정 로그 비노출 및 거래 흐름 분리
- [ ] 다음 장중 자동 스케줄(`UTC 00:00`, `UTC 02:55`) 1회 추가 확인
- [x] 배포 대시보드에서 자산 배분 상태 칩이 실제로 `실시간 연동 중`으로 보이는지 화면 검증

## 프로젝트 개요
- 유형: `Python + Streamlit`
- 진입점: `app.py`
- 저장소: `Supabase` 우선, 필요 시 `SQLite`
- 시세: `KIS REST/WebSocket` 우선, 일부 fallback `yfinance`
- 배포 앱: `https://retirement-portfolio-app-nh2vq9ferqnpehsslbykbe.streamlit.app/`

## 핵심 파일
- 앱: `app.py`
- DB 추상화: `src/db.py`
- SQLite 구현: `src/sqlite_db.py`
- 인증: `src/auth.py`
- 분석/차트: `src/analytics.py`
- 일별 롤업: `scripts/run_daily_rollup.py`
- KIS worker: `scripts/run_kis_quote_worker.py`
- 배포 검증: `scripts/verify_streamlit_deployment.py`
- 자동 커밋/배포 검증: `scripts/verify_and_push_deploy.py`
- Supabase realtime 핫픽스: `docs/supabase-realtime-schema-hotfix.sql`
- realtime 운영 절차: `docs/supabase-realtime-worker-runbook.md`
- 장중 worker workflow: `.github/workflows/kis-realtime-worker.yml`
- 일별 롤업 workflow: `.github/workflows/daily-rollup.yml`

## 실행 방법
```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

## 운영 시크릿 메모
- 앱용: `SUPABASE_URL`, `SUPABASE_KEY`
- 관리자/배치용: `SUPABASE_SERVICE_ROLE_KEY`
- KIS용: `KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_ENV`
- 배포 검증용: `STREAMLIT_VERIFY_EMAIL`, `STREAMLIT_VERIFY_PASSWORD`
- 실제 값은 로컬 `.streamlit/secrets.toml` 및 GitHub Actions secrets에만 둠

## 현재 운영 상태
- 기준 시각: `2026-05-11`
- 배포 앱은 `Supabase`를 사용 중
- 운영 Supabase realtime 테이블 노출 상태:
  - `accounts`: `200`
  - `realtime_worker_status`: `200`
  - `realtime_price_ticks`: `200`
- 장중 수동 검증 결과:
  - `python3 scripts/run_kis_quote_worker.py --backend supabase --preflight-only` 통과
  - 장중 수동 실행에서 `KIS WebSocket 연결 완료` 확인
  - `realtime_price_ticks` 적재 및 `holdings.current_price` overwrite 확인
- GitHub Actions 수동 검증 결과:
  - 첫 run `25646136285`: 적재는 됐으나 종료 구간 `exit 137`
  - 수정 후 run `25646510735`: `success`
  - 완료 후 `worker_name=kis-quote-worker-github-actions`, `connection_state=stopped` 확인

## 최근 핵심 변경 요약

### 2026-05-09
- 로그인/데모/기본 UI, 카드 정렬, 브라우저 검증 기반 정리
- 로컬 Playwright/브라우저 검증 경로 확보
- README 비정상 텍스트와 예시 시크릿 정리

### 2026-05-10
- 대시보드 자산 배분, 보유 종목 수익률, 선택 종목 트렌드 대폭 정리
- 자산 배분 트리맵을 `자산군 → 섹터 → 보유 종목` 구조로 확장
- KIS 우선 섹터/시세 provider와 realtime quote worker 추가
- Supabase realtime 스키마 핫픽스 SQL과 runbook 추가
- 로그인 카드 레이아웃 개편 및 데모 모드 진입 UX 정리

### 2026-05-11
- `Memory.md`를 장문 실행 로그에서 요약형 운영 메모로 재정리(`1061`줄 -> `133`줄)
- 자산 배분 상태 칩을 실제 worker 상태 기반(`실시간 연동 중`, `지연 데이터 표시 중` 등)으로 변경
- 운영 Supabase realtime 테이블 생성 후 장중 적재 검증 완료
- GitHub Actions 장중 worker 자동화 workflow 추가
- `gh` CLI 설치, GitHub Actions secrets 주입, 수동 dispatch/실행 성공 검증 완료
- 배포 대시보드가 장중에도 `지연 데이터 표시 중`으로 남는 케이스를 재현했고, 최근 quote 시각이 3분 이내면 live 톤으로 승격하는 fallback 및 10초 재확인 로직을 추가
- 커밋 `2ede61d` 배포 후 세 번째 원격 확인에서 자산 배분 상태 칩이 `실시간 연동 중`으로 전환됨을 확인
- `actions/checkout@v6`, `actions/setup-python@v6`, `permissions.contents=read`로 workflow를 올려 `Node.js 20 actions are deprecated` 경고 제거
- `Daily Rollup` 과거 schedule 실패 원인은 `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` 시크릿 누락이었고, 현재는 수동 `dry-run` 성공으로 복구 상태 확인
- `scripts/verify_streamlit_deployment.py`가 대시보드 렌더 완료까지 대기한 뒤 `자산 배분` 상태 칩 텍스트를 파싱하고, `--expect-allocation-status`로 기대값 비교까지 수행하도록 보강
- `app.py` 내부 전역 CSS를 `.streamlit/app.css`로 분리하고, `.streamlit/config.toml`의 `primary/background/secondaryBackground/text`를 기준으로 카드·차트·배경 토큰을 Python 로더에서 파생하도록 정리
- 대시보드 차트 계열의 선택 강조색, 라인 색, 툴팁/캔버스 색을 동일 토큰 체계에 연결하고, `tests/test_app_dashboard.py`에 토큰/외부 CSS 로딩 회귀 테스트를 추가
- `보유 종목 수익률` ECharts 막대가 음수일 때도 상단 라운드가 적용되던 문제를 수정하고, 값 부호에 따라 양수는 상단 라운드, 음수는 하단 라운드가 적용되도록 변경
- Altair fallback 막대차트도 `cornerRadiusEnd`로 맞춰 ECharts 미사용 환경에서 같은 방향성을 유지하도록 정리
- 선택 종목 트렌드 기간에 `당일`을 추가하고, `fetch_intraday_price_snapshot()`의 세션 타임라인을 사용해 장 시작부터 장 마감까지의 intraday 누적 손익 흐름을 그리도록 연결
- KIS/Yahoo intraday 스냅샷 반환값에 `timeline(datetime, close)`를 추가하고, 선택 종목 데이터 보기에서 `당일`일 때 `시간` 컬럼과 `HH:MM` 축 라벨을 함께 노출하도록 정리
- 선택 종목 `당일` 프레임 생성 시 자산 배분 카드가 쓰는 `current_price/as_of`를 마지막 포인트로 덮어써 화면 간 금일 시세 불일치를 줄이고, 타임라인이 비어도 금일 시세 1포인트를 만들도록 fallback 추가
- 현재 보유 종목 표의 `가격갱신`을 `YYYY-MM-DD HH:MM:SS`로 통일하고, `손익`/`수익률`은 양수/음수/0에 따라 컬러와 굵기를 다르게 표시하도록 `Styler` 기반 렌더로 변경
- 현재 보유 종목 박스 상단에 `위험자산/안전자산/보유현금` 스택 막대바와 비중/금액 legend를 추가해 자산 구성을 표 안에서 바로 읽을 수 있게 정리
- 현재 보유 종목 비중 막대는 별도 `보유현금` 세그먼트를 없애고 `안전자산` 금액에 현금을 합산해, `안전자산(보유현금 포함)` 기준으로 보이도록 조정
- `record_trade()` 직전에 기존 `daily_interest`/`interest` 이력이 남은 계좌만 이자 원장을 다시 맞추는 복구 훅을 추가해, 자동 적립 제거 이후 `보유현금 부족` 오탐이 날 수 있는 경로를 보정
- 누적 원금 화면 문구도 `새 이자는 자동 적립하지 않지만 기존 일별 이자 이력은 현금 계산에 반영된다`는 현재 동작에 맞게 수정
- 매수 등록은 보유현금 부족이어도 허용하고, 이후 `현금 조정`으로 실제 통장 잔액을 수동 최신화하는 현재 운영 방식에 맞게 `buy` 현금 부족 차단을 제거
- `app.py` 초기 로딩에서 `src.market` import 직후 다시 호출하던 `importlib.reload()`를 제거해, Streamlit 재실행마다 중복 모듈 초기화 비용이 생기던 경로를 정리
- `src/market.py`의 `search_products()`를 정규화 질의값 기준 내부 캐시(`ttl=3600`, `max_entries=300`)로 감싸, 동일 검색어의 공백/표기 차이로 외부 검색 API를 반복 호출하던 경로를 줄임
- `tests/test_market.py`에 `" 삼성전자 "`와 `"삼성전자"`가 동일 캐시 엔트리를 재사용하는지 검증하는 회귀 테스트를 추가
- 검색 캐시 보강 커밋 `e2dd5fd`를 `origin/main`에 푸시했고, 원격 Streamlit 앱 대시보드 로그인/저장소 검증을 다시 통과함
- `src/db.py`에 사용자별 `scope_key`와 `data_refresh_token`을 포함한 조회 캐시를 추가해 `accounts`, `account`, `holdings`, `trade_logs`, `daily_account_snapshot` 반복 조회를 줄였고, 쓰기 작업 성공 후에는 자동으로 refresh token을 증가시키도록 정리
- Supabase 읽기 경로에서 `holdings`, `trade_logs`, `daily_account_snapshot`, `realtime_*` 조회 전에 `accounts` 존재 확인용 추가 GET을 보내던 경로를 제거해 데이터 페이지/대시보드 렌더 시 중복 호출 수를 낮춤
- `app.py`의 대시보드/데이터 페이지에서 `daily_interest` 조회와 관련 문구를 제거하고, `record_trade()`의 legacy 이자 재동기화 훅도 빼서 이자 제거 방향에 맞게 정리
- 앱 코드 커밋 `8eb14d5`를 `origin/main`에 푸시했고, 원격 Streamlit 앱 `데이터` 페이지에서 로그인/저장소 상태 검증을 다시 통과함
- `.streamlit/app.css`의 Pretendard jsDelivr `@import`를 제거하고 시스템 폰트 스택(`system-ui`, `-apple-system`, `"Segoe UI"`, `"Apple SD Gothic Neo"`, `"Noto Sans KR"`)으로 전환해 첫 렌더 시 외부 폰트 CSS 응답 대기를 없앰
- `tests/test_app_dashboard.py`에 외부 CDN 폰트 import 부재와 시스템 폰트 스택 적용 회귀 테스트를 추가
- 앱 코드 커밋 `569e2f9`를 `origin/main`에 푸시했고, 원격 Streamlit 앱 대시보드 로그인/렌더 검증을 다시 통과함
- 거래 페이지에서 계좌 간 이체 입력 패널과 관련 세션 상태를 제거하고, 대시보드/데이터/데모 문구도 현재 기능 집합에 맞게 정리
- `src/db.py` 데모 블루프린트의 `transfers` 예시와 `seed_demo_workspace()` 이체 생성 루프를 제거해 데모 작업공간도 더 이상 계좌 이체 이벤트를 만들지 않도록 맞춤
- `tests/test_db.py`에서 데모 시드 회귀를 계좌 이체 없는 블루프린트 기준으로 갱신
- 앱 코드 커밋 `83861ad`를 `origin/main`에 푸시했고, 원격 Streamlit 앱 `거래` 페이지에서 로그인/작업공간/`Supabase` 저장소 상태 검증을 다시 통과함
- 대시보드 `보유 현금` 카드 수정이 `trade_logs`에 `cash_adjustment` 행을 남기지 않도록 `src/db.py`/`src/sqlite_db.py` 조정 경로를 바꾸고, 기존 `cash_adjustment` 이력도 거래 화면에서는 숨기도록 정리
- `src/analytics.py`에서는 과거 `cash_adjustment` 로그를 원금/순유입 계산에서 제외해, 보유현금은 현재 잔액으로만 자산배분·평가손익·원금대비 수익률에 반영되도록 정리
- 앱 코드 커밋 `e7a445c`를 `origin/main`에 푸시했고, 원격 Streamlit 앱 `거래`/`데이터` 페이지에서 로그인·작업공간·`Supabase` 저장소 상태 검증을 다시 통과함
- 배포 웹 검증이 불안정하던 원인을 `반복 로그인에 따른 인증 rate limit`과 `실패 시 마지막 화면 증거 부족`으로 분리했고, `scripts/verify_streamlit_deployment.py`에 `--storage-state`, `--debug-dir` 옵션과 `auth_error`/`rate_limited` 진단 필드를 추가
- 검증 실패 시 단계별 `txt/png/url` 아티팩트를 남기도록 보강해, 로그인 실패/페이지 전환 실패/배포 미반영 상태를 이후 세션에서도 바로 재확인할 수 있게 정리

## 최신 검증 결과
- `python3 -m compileall app.py src scripts tests` 성공
- `python3 -m unittest discover -s tests -p "test_*.py"` 성공
- 최신 테스트 수: `108`건 통과
- 배포 검증 산출물:
  - `artifacts/deploy-verify-realtime-data-20260511.txt`
  - `artifacts/deploy-verify-realtime-data-20260511.png`
  - `artifacts/deploy-verify-realtime-dashboard-20260511.txt`
  - `artifacts/deploy-verify-realtime-dashboard-20260511.png`
- 이번 턴 로컬 추가 검증:
  - `python3 -m compileall app.py tests/test_app_dashboard.py` 성공
  - `python3 -m unittest tests.test_app_dashboard` 성공 (`20`건)
  - `python3 -m unittest discover -s tests -p "test_*.py"` 성공 (`78`건)
- 이번 턴 배포 추가 검증:
  - GitHub Actions run `25646982752` 장중 연결 상태에서 계좌 `24`의 `connection_state=connected`, `last_quote_at=2026-05-11T11:30:26` 확인
  - `artifacts/deploy-verify-dashboard-live-chip-postdeploy.txt`에서 `실시간 연동 중` 확인
  - `artifacts/deploy-verify-dashboard-live-chip-postdeploy.png` 스크린샷 저장
- 이번 턴 Actions 추가 검증:
  - `python3 -m compileall app.py src scripts tests` 성공
  - `python3 -m unittest discover -s tests -p "test_*.py"` 성공 (`78`건)
  - `Daily Rollup` 수동 `dry-run` run `25648283262` 성공, 로그에서 `actions/checkout@v6`, `actions/setup-python@v6` 확인
  - `KIS Realtime Worker` 수동 1분 run `25648283181` 성공, 로그에서 `actions/checkout@v6`, `actions/setup-python@v6` 확인
  - 두 run 모두 `Node.js 20 actions are deprecated` 경고 문구 미발견
  - `gh workflow list`, `gh api repos/.../actions/workflows` 기준 `KIS Realtime Worker`, `Daily Rollup` 모두 `active`
  - 다만 `gh run list --workflow "KIS Realtime Worker" --event schedule` 결과는 비어 있어 `schedule` 이벤트 실주행은 다음 자동 사이클에서 추가 확인 필요
- 이번 턴 배포 검증 스크립트 추가 검증:
  - `python3 -m unittest tests.test_verify_streamlit_deployment` 성공 (`7`건)
  - `python3 -m unittest discover -s tests -p "test_*.py"` 재실행 성공 (`81`건)
  - `./.venv/bin/python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase` 성공
  - 위 실행에서 `allocation_status="지연 데이터 표시 중"` 파싱 확인
  - `./.venv/bin/python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase --expect-allocation-status "지연 데이터 표시 중"` 성공
  - 산출물: `artifacts/deploy-verify-dashboard-allocation-status-20260511.txt`, `artifacts/deploy-verify-dashboard-allocation-status-20260511.png`
  - `2026-05-11 03:30 UTC` 기준 `gh run list --workflow "KIS Realtime Worker" --event schedule` 결과는 여전히 비어 있음
- 이번 턴 계좌 간 이체 기능 삭제 검증:
  - `python3 -m compileall app.py src/db.py tests/test_db.py` 성공
  - `python3 -m unittest tests.test_db tests.test_app_dashboard tests.test_analytics` 성공 (`66`건)
  - `python3 -m compileall app.py src scripts tests` 성공
  - `python3 -m unittest discover -s tests -p "test_*.py"` 성공 (`104`건)
  - `./.venv/bin/python scripts/verify_streamlit_deployment.py --page trades --expect-backend supabase --debug-dir artifacts/deploy-verify-remove-transfer-83861ad` 성공
  - 원격 검증 결과: `backend_storage=supabase`, `logged_in=true`, `workspace_visible=true`, `target_page="trades"`
- 이번 턴 보유현금 수정 로그 분리 검증:
  - `python3 -m compileall app.py src tests` 성공
  - `python3 -m unittest tests.test_db tests.test_analytics tests.test_app_dashboard` 성공 (`70`건)
  - `python3 -m unittest discover -s tests -p "test_*.py"` 성공 (`108`건)
  - `./.venv/bin/python scripts/verify_streamlit_deployment.py --page trades --expect-backend supabase --debug-dir artifacts/deploy-verify-cash-adjustment-e7a445c` 성공
  - `./.venv/bin/python scripts/verify_streamlit_deployment.py --page data --expect-backend supabase --debug-dir artifacts/deploy-verify-cash-adjustment-data-e7a445c` 성공
  - 원격 검증 결과: `backend_storage=supabase`, `logged_in=true`, `workspace_visible=true`, `target_page in {"trades","data"}`
- 이번 턴 디자인 토큰/CSS 구조 검증:
  - `python3 -m compileall app.py tests/test_app_dashboard.py` 성공
  - `python3 -m unittest tests.test_app_dashboard` 성공 (`22`건)
  - `python3 -m compileall app.py src scripts tests` 재실행 성공
  - `python3 -m unittest discover -s tests -p "test_*.py"` 성공 (`83`건)
  - `python3 -m streamlit run app.py --server.port 8511 --server.headless true` 로컬 기동 성공
  - `./.local/bin/agent-browser`로 `http://localhost:8511` 확인 시 초기 skeleton 이후 로그인 카드 렌더 스크린샷 확보
  - 로컬 시각 검증 산출물: `artifacts/design-token-local-8511.png`, `artifacts/design-token-local-8511-after-wait.png`
- 이번 턴 보유 종목 수익률 막대 방향 수정 검증:
  - `python3 -m compileall app.py tests/test_app_dashboard.py` 성공
  - `python3 -m unittest tests.test_app_dashboard` 성공 (`22`건)
  - `python3 -m unittest discover -s tests -p "test_*.py"` 성공 (`83`건)
  - `holdings_bar_options()` 테스트에서 양수 막대 `borderRadius=[10, 10, 0, 0]`, 음수 막대 `borderRadius=[0, 0, 10, 10]` 회귀 검증 추가
  - Altair fallback 차트 `mark_bar(cornerRadiusEnd=8)` 스펙 직렬화 확인
  - 로컬 브라우저 기동: `python3 -m streamlit run app.py --server.port 8512 --server.headless true` 성공
  - `agent-browser`로 로그인 화면 렌더 스크린샷 확보: `artifacts/holdings-bar-login-8512-after-double-wait.png`
- 이번 턴 선택 종목 트렌드 `당일` intraday 추가 검증:
  - `python3 -m compileall app.py tests/test_app_dashboard.py` 성공
  - `python3 -m unittest tests.test_app_dashboard` 성공 (`24`건)
  - `python3 -m compileall app.py src scripts tests` 성공
  - `python3 -m unittest discover -s tests -p "test_*.py"` 성공 (`85`건)
  - `python3 -m streamlit run app.py --server.port 8514 --server.headless true` 로컬 기동 성공
  - `agent-browser`로 `http://localhost:8514` 로그인 화면 렌더, 에러 오버레이 없음, 본문 텍스트 존재 확인
  - 로컬 시각 검증 산출물: `artifacts/selected-trend-local-8514-login.png`, `artifacts/selected-trend-local-8514-after-wait.png`
  - `./.venv/bin/python scripts/verify_streamlit_deployment.py --url http://localhost:8514 ...` 는 로컬 앱 프레임 감지 실패로 중단되어, 로컬 브라우저 검증은 `agent-browser` 기준으로 기록
- 이번 턴 선택 종목 `당일` 금일 시세 정합 검증:
  - `python3 -m compileall app.py tests/test_app_dashboard.py` 성공
  - `python3 -m unittest tests.test_app_dashboard` 성공 (`25`건)
  - `./.venv/bin/python -m compileall app.py src scripts tests` 성공
  - `./.venv/bin/python -m unittest discover -s tests -p "test_*.py"` 성공 (`86`건)
  - `build_selected_holding_trend_frame()` 테스트에서 intraday 타임라인 부재 시 `current_price/as_of` fallback으로 1포인트를 만드는 회귀 검증 추가
  - 배포 커밋 `0147543` 푸시 후 `git push origin main` 기준 원격 반영
  - `./.venv/bin/python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase` 성공
  - 원격 검증 결과: `backend_storage=supabase`, `allocation_status="지연 데이터 표시 중"`, 로그인/작업공간 노출 정상
  - 원격 검증 산출물: `artifacts/deploy-verify-selected-trend-0147543.txt`, `artifacts/deploy-verify-selected-trend-0147543.png`
- 이번 턴 현재 보유 종목 표 표시 개선 검증:
  - `python3 -m compileall app.py tests/test_app_dashboard.py` 성공
  - `python3 -m unittest tests.test_app_dashboard` 성공 (`29`건)
  - `build_holdings_table_display()` 테스트에서 `가격갱신=2026-05-11 09:15:27` 초 단위 포맷 확인
  - `style_holdings_table()` 테스트에서 손익/수익률 셀에 상승/하락/중립 색상 스타일이 포함되는지 확인
  - `style_holdings_table()` 테스트에서 `손익="12,000"`처럼 콤마가 들어간 문자열도 상승색으로 인식하는지 확인
  - `build_holdings_mix_bar_html()` 테스트에서 위험/안전/보유현금 `50.0/30.0/20.0%` 비율 렌더 확인
  - `./.venv/bin/python -m compileall app.py src scripts tests` 성공
  - `./.venv/bin/python -m unittest discover -s tests -p "test_*.py"` 성공 (`90`건)
- 이번 턴 현재 보유 종목 비율 막대 보정 검증:
  - `python3 -m compileall app.py tests/test_app_dashboard.py` 성공
  - `python3 -m unittest tests.test_app_dashboard` 성공 (`29`건)
  - `./.venv/bin/python -m compileall app.py src scripts tests` 성공
  - `./.venv/bin/python -m unittest discover -s tests -p "test_*.py"` 성공 (`90`건)
  - `build_holdings_mix_bar_html()` 테스트에서 `보유현금`이 독립 세그먼트로 나오지 않고 `안전자산` 설명에 `보유현금 ₩200,000 포함`으로 합산 표시되는지 확인
  - 배포 커밋 `cb871df` 푸시 후 `git push origin main` 기준 원격 반영
  - `./.venv/bin/python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase` 성공
  - 원격 검증 결과: `backend_storage=supabase`, `allocation_status="실시간 연동 중"`, 로그인/작업공간 노출 정상
  - 원격 검증 산출물: `artifacts/deploy-verify-holdings-safe-cash-cb871df.txt`, `artifacts/deploy-verify-holdings-safe-cash-cb871df.png`
  - 배포 커밋 `1d55a5d` 푸시 후 `git push origin main` 기준 원격 반영
  - `./.venv/bin/python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase` 성공
  - 원격 검증 산출물: `artifacts/deploy-verify-holdings-table-1d55a5d.txt`, `artifacts/deploy-verify-holdings-table-1d55a5d.png`
- 이번 턴 기존 이자 이력 매수 전 재동기화 검증:
  - `python3 -m compileall src/db.py tests/test_db.py` 성공
  - `python3 -m unittest tests.test_db` 성공 (`16`건)
  - `./.venv/bin/python -m compileall app.py src scripts tests` 성공
  - `./.venv/bin/python -m unittest discover -s tests -p "test_*.py"` 성공 (`92`건)
  - `_sync_legacy_interest_history_for_buy()` 테스트에서 기존 `interest`/`daily_interest` 이력이 있으면 `_replace_interest_history()`를 호출하는지 확인
  - 이자 이력이 없는 계좌는 매수 전 재동기화를 건너뛰는지 확인
- 이번 턴 검색 캐시 보강 검증:
  - `python3 -m compileall src/market.py tests/test_market.py` 성공
  - `python3 -m unittest tests.test_market` 성공 (`11`건)
  - `python3 -m compileall app.py src scripts tests` 성공
  - `python3 -m unittest discover -s tests -p "test_*.py"` 성공 (`101`건)
- 이번 턴 검색 캐시 배포 검증:
  - 배포 커밋 `e2dd5fd` 푸시 후 `git push origin main` 기준 원격 반영
  - 로컬 `.streamlit/secrets.toml`의 검증 계정 값을 환경 변수로 주입해 원격 검증 실행
  - `./.venv/bin/python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase --debug-dir artifacts/deploy-verify-search-cache-e2dd5fd` 성공
  - 원격 검증 결과: `backend_storage=supabase`, `allocation_status="데이터 대기"`, 로그인/작업공간 노출 정상
- 이번 턴 DB 캐시/이자 제거 검증:
  - `python3 -m compileall app.py src/db.py tests/test_db.py` 성공
  - `python3 -m unittest tests.test_db tests.test_app_dashboard tests.test_analytics` 성공 (`65`건)
  - `python3 -m compileall app.py src scripts tests` 성공
  - `python3 -m unittest discover -s tests -p "test_*.py"` 성공 (`103`건)
  - 배포 커밋 `8eb14d5` 푸시 후 `git push origin main` 기준 원격 반영
  - 로컬 `.streamlit/secrets.toml`의 검증 계정 값을 환경 변수로 주입해 원격 검증 실행
  - `./.venv/bin/python scripts/verify_streamlit_deployment.py --page data --expect-backend supabase --debug-dir artifacts/deploy-verify-db-cache-8eb14d5` 성공
  - 원격 검증 결과: `backend_storage=supabase`, `status_panel_visible=true`, `snapshot_count="1건"`, 로그인/작업공간 노출 정상
- 이번 턴 CSS 초기 로딩 개선 검증:
  - `python3 -m compileall app.py tests/test_app_dashboard.py` 성공
  - `python3 -m unittest tests.test_app_dashboard` 성공 (`32`건)
  - `python3 -m compileall app.py src scripts tests` 성공
  - `python3 -m unittest discover -s tests -p "test_*.py"` 성공 (`104`건)
  - 배포 커밋 `569e2f9` 푸시 후 `git push origin main` 기준 원격 반영
  - 로컬 `.streamlit/secrets.toml`의 검증 계정 값을 환경 변수로 주입해 원격 검증 실행
  - `./.venv/bin/python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase --debug-dir artifacts/deploy-verify-system-font-569e2f9` 성공
  - 원격 검증 결과: `backend_storage=supabase`, `allocation_status="지연 데이터 표시 중"`, 로그인/작업공간 노출 정상
- 이번 턴 매수 현금 부족 차단 해제 검증:
  - `python3 -m compileall src/db.py src/sqlite_db.py tests/test_db.py` 성공
  - `python3 -m unittest tests.test_db` 성공 (`17`건)
  - `./.venv/bin/python -m compileall app.py src scripts tests` 성공
  - `./.venv/bin/python -m unittest discover -s tests -p "test_*.py"` 성공 (`93`건)
  - SQLite 통합 테스트에서 `opening_cash=100000` 계좌가 `140000` 매수 후에도 저장되고 `cash_balance=-40000`으로 남는지 확인
  - 배포 커밋 `d44a3b3` 푸시 후 `git push origin main` 기준 원격 반영
  - `./.venv/bin/python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase` 성공
  - 원격 검증 결과: `backend_storage=supabase`, `allocation_status="실시간 연동 중"`, 로그인/작업공간 노출 정상
  - 원격 검증 산출물: `artifacts/deploy-verify-buy-cash-rule-d44a3b3.txt`, `artifacts/deploy-verify-buy-cash-rule-d44a3b3.png`
- 이번 턴 거래 등록 재수정 검증:
  - 실제 배포 UI 재현에서 임시 계좌 `codex-tmp-qbvcsv` 매수 저장 시 `매수하기에 현금이 부족합니다.` 문구가 다시 노출되는 것을 확인
  - 원인: `record_trade()`의 현금 부족 검사는 제거됐지만 `_supabase_update_cash_balance()` helper가 여전히 음수 잔액을 금지하고 있었음
  - 조치: `src/db.py`에서 `_supabase_update_cash_balance(..., allow_negative=False)` 플래그를 추가하고, `buy`/기존 이자 재동기화 경로에서만 `allow_negative=True`를 사용하도록 수정
  - `python3 -m compileall src/db.py tests/test_db.py` 성공
  - `python3 -m unittest tests.test_db` 성공 (`19`건)
  - `./.venv/bin/python -m compileall app.py src scripts tests` 성공
  - `./.venv/bin/python -m unittest discover -s tests -p "test_*.py"` 성공 (`95`건)
  - 로컬 `streamlit run app.py --server.port 8520 --server.headless true` 재현에서 기존 `매수하기에 현금이 부족합니다.` / `현금은 0 이상이어야 합니다.` 문구가 더 이상 나타나지 않음을 확인
  - 로컬 재현 산출물: `artifacts/trade-register-local-8520-fixed.txt`, `artifacts/trade-register-local-8520-fixed.png`
  - 후속 확인에서 저장 직후 `st.session_state.trade_symbol cannot be modified after the widget ... is instantiated` 예외가 발생하는 것을 발견
  - 조치: `app.py` 거래 페이지를 `pending reset + rerun` 구조로 바꿔 거래/현금 흐름/계좌 이체 폼을 다음 실행에서만 초기화하도록 수정
  - `python3 -m compileall app.py src/db.py tests/test_db.py tests/test_app_dashboard.py` 성공
  - `python3 -m unittest tests.test_db tests.test_app_dashboard` 성공 (`50`건)
  - `./.venv/bin/python -m compileall app.py src scripts tests` 성공
  - `./.venv/bin/python -m unittest discover -s tests -p "test_*.py"` 성공 (`97`건)
  - 로컬 `streamlit run app.py --server.port 8520 --server.headless true` 재현 후 서버 종료 시 더 이상 `StreamlitAPIException` traceback이 발생하지 않음을 확인
  - 최신 로컬 재현 산출물: `artifacts/trade-register-local-8520-fixed-2.txt`, `artifacts/trade-register-local-8520-fixed-2.png`
  - 기능 커밋 `2cb8006`, `dbef65a`를 `origin/main`에 푸시 완료
  - 원격 일반 배포 검증: `./.venv/bin/python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase` 성공
  - 원격 거래 저장 재현은 `2026-05-11 09:39~09:45 UTC` 시점에도 여전히 예전 문구 `매수하기에 현금이 부족합니다.`를 반환해, Streamlit Cloud가 새 커밋을 아직 반영하지 않은 상태로 기록
- 이번 턴 `src.market reload` 제거 검증:
  - `python3 -m compileall app.py tests/test_app_dashboard.py` 성공
  - `python3 -m unittest tests.test_app_dashboard` 성공 (`29`건)
  - `./.venv/bin/python -m compileall app.py src scripts tests` 성공
  - `./.venv/bin/python -m unittest discover -s tests -p "test_*.py"` 성공 (`93`건)
  - 운영 배포 기준 `app.py`에서 `importlib.reload(src.market)` 제거 후 대시보드/차트 테스트 회귀 없음 확인
  - 배포 커밋 `89038db` 푸시 후 `git push origin main` 기준 원격 반영
  - `./.venv/bin/python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase` 성공
  - 원격 검증 결과: `backend_storage=supabase`, `allocation_status="실시간 연동 중"`, 로그인/작업공간 노출 정상
  - 원격 검증 산출물: `artifacts/deploy-verify-remove-reload-89038db.txt`, `artifacts/deploy-verify-remove-reload-89038db.png`
- 이번 턴 배포 검증 디버그성 보강 검증:
  - `python3 -m compileall scripts/verify_streamlit_deployment.py tests/test_verify_streamlit_deployment.py` 성공
  - `python3 -m unittest tests.test_verify_streamlit_deployment` 성공 (`10`건)
  - `python3 -m compileall app.py src scripts tests` 성공
  - `python3 -m unittest discover -s tests -p "test_*.py"` 성공 (`100`건)
  - `scripts/verify_streamlit_deployment.py`에 `--storage-state` 재사용 옵션 추가
  - `scripts/verify_streamlit_deployment.py`에 `--debug-dir` 단계별 `txt/png/url` 저장 옵션 추가
  - 로그인 실패 시 `Request rate limit reached` 같은 인증 제한 문구를 `auth_error`, `rate_limited`로 분리 노출하도록 보강

## Git/GitHub 상태
- 기본 브랜치: `main`
- 최근 기능 커밋:
  - `89038db` `Remove market module reload on app startup`
  - `d44a3b3` `Allow buys regardless of current cash`
  - `b57ab5a` `Restore legacy interest cash sync before buys`
  - `cb871df` `Fold holdings cash into safe allocation`
  - `7337b17` `Improve holdings table visual cues`
  - `1d55a5d` `Polish holdings table quote timestamps`
  - `0147543` `Align today's selected trend with live allocation quotes`
  - `13a98c7` `Refine dashboard theme and selected intraday trend`
  - `72f0f41` `Refresh auth UI and allocation status chip`
  - `12748fd` `Add scheduled KIS realtime worker workflow`
  - `7ee4d45` `Fix GitHub worker shutdown handling`
  - `2ede61d` `Improve dashboard live status fallback`
  - `c07e7d7` `Upgrade GitHub Actions to Node 24 runtimes`
- 최근 기록 커밋:
  - `0f53406` `Record Node 24 workflow verification`
  - `2654620` `Record realtime table activation verification`
  - `00aa563` `Record GitHub worker validation`
- 로컬 도구:
  - `./.local/bin/agent-browser`
  - `./.local/bin/gh`
- 현재 워크트리 주의:
  - `data/portfolio.db`는 로컬 변경 상태
  - `.local/`, `artifacts/`, `.playwright-browsers/`, `data/kis_cache/` 등은 커밋 제외 대상

## 운영 runbook 요약
- realtime 테이블 수정은 `docs/supabase-realtime-schema-hotfix.sql`
- worker 수동 실행:
```powershell
python scripts/run_kis_quote_worker.py --backend supabase
```
- 배포 상태 검증:
```powershell
python scripts/verify_streamlit_deployment.py --page data --expect-backend supabase
```
- GitHub Actions 장중 자동 실행:
  - workflow: `KIS Realtime Worker`
  - 스케줄 1: `UTC 00:00` (`KST 09:00`)
  - 스케줄 2: `UTC 02:55` (`KST 11:55`)

## 남은 작업
1. `KIS Realtime Worker`의 다음 자동 스케줄(`UTC 00:00` 또는 `UTC 02:55`)이 실제 `schedule` 이벤트로 생성되고 `success`로 끝나는지 확인
2. `2026-05-11 03:30 UTC` 기준 자동 `schedule` run이 없으므로, 다음 확인 시각은 `2026-05-12 00:00 UTC` 이후가 우선

## 2026-05-11 현금/데이터 정합성 읽기 전용 점검
- [x] 저장소 구조, 핵심 문서, `Memory.md`, 현금/거래/스냅샷 관련 코드 경로 확인
- [x] 로컬 SQLite `data/portfolio.db` 읽기 전용 무결성 점검
- [x] Supabase 서버 데이터를 service role 및 인증 사용자 기준으로 읽기 전용 점검
- [x] `python3 -m compileall app.py src scripts tests` 성공
- [x] `python3 -m unittest discover -s tests -p "test_*.py"` 성공 (`108`건)
- [ ] 승인 후 보유현금/스냅샷/레거시 현금조정 데이터 수정

### 발견 사항
- 현재 설계 의도는 `매수는 현금 부족이어도 허용`, `보유현금 수동 수정은 trade_logs에 남기지 않음`, `cash_adjustment는 원금/순유입 계산에서 제외`, `보유현금은 안전자산 비중에 합산`으로 확인됨.
- 로컬 SQLite는 외래키 깨짐, 중복 보유종목, 음수 수량/단가, `cash_delta` 부호 오류는 발견되지 않음.
- 로컬 SQLite에는 레거시 `cash_adjustment` 로그 2건이 남아 있음.
- 운영 Supabase에는 계좌 4개, 보유종목 14개, 거래 71건, 스냅샷 9건이 조회됐고 외래키 깨짐, 중복 보유종목, 음수 수량/단가, `cash_delta` 부호 오류는 발견되지 않음.
- 운영 Supabase에는 레거시 `cash_adjustment` 로그 3건이 남아 있음: 계좌 23 1건, 계좌 24 2건.
- 운영 Supabase의 과거 스냅샷 중 계좌 23의 `2026-05-09`, `2026-05-10` 현금이 현재 원장 흐름과 크게 어긋나 보임.
- `src/db.py`의 과거 스냅샷 현금 재계산 경로는 현재 현금에서 모든 거래 델타를 뺀 뒤 과거 날짜 델타를 다시 누적하는 구조라, 오늘/미래 거래 또는 계좌 생성일보다 과거인 거래일이 있으면 과거 현금이 왜곡될 수 있음.
- `setup_supabase.sql`에는 `CREATE POLICY holdings_update_own` 중복 구문처럼 보이는 부분과 `daily_interest_update_own` 부근 괄호 불일치처럼 보이는 부분이 있어 재적용 전 수정 검토 필요.

### 다음 수정 계획
- `src/db.py` 과거 현금 스냅샷 재계산 로직을 현재 현금에서 스냅샷일 이후 거래 델타를 역산하는 방식으로 보정하고, 계좌 생성일보다 과거인 거래일/당일 거래가 있는 회귀 테스트를 추가한다.
- 레거시 `cash_adjustment` 로그는 현재 설계와 맞지 않으므로 서버/로컬 정리 SQL을 별도 스크립트 또는 일회성 절차로 준비하되, `accounts.cash_balance`는 변경하지 않는다.
- 운영 Supabase의 잘못된 과거 스냅샷은 수정 로직 적용 후 대상 계좌만 재계산하거나 명시 SQL로 보정한다.
- `setup_supabase.sql` 정책 구문 오류 후보를 수정하고 SQL 적용 전 문법 검증을 수행한다.
- 수정 후 `compileall`, 전체 unittest, 배포 데이터 페이지 검증, Supabase 읽기 전용 재점검을 수행한다.

## 2026-05-11 현금 스냅샷 계산 수정
- [x] 과거 현금 스냅샷 계산에서 기준일 이후 거래가 과거 현금에 섞이던 문제 수정
- [x] 계좌 생성일보다 과거로 backdate된 거래가 과거 현금 스냅샷에서 누락되던 문제 수정
- [x] 회귀 테스트 2건 추가
- [x] 로컬 SQLite 스냅샷 재검산 후 추가 보정 필요 없음 확인
- [x] 운영 Supabase 스냅샷 재대조 후 추가 보정 필요 없음 확인

### 변경 내용
- `src/db.py`
  - `_daily_interest_row_amount_by_date()`, `_trade_interest_amount_by_date()`, `_cash_delta_by_date()`가 `target_date=None`인 전체 기간 계산을 지원하도록 확장
  - `_historical_cash_balance_by_date()`가 현재 현금에서 전체 원장/고아 이자 합계를 기준으로 opening cash를 잡고, `snapshot_date`뿐 아니라 실제 가장 이른 거래일/이자일도 iteration 시작점으로 사용하도록 수정
- `tests/test_db.py`
  - 기준일 이후 거래가 과거 스냅샷 현금을 오염시키지 않는 회귀 테스트 추가
  - 계좌 생성 후 입력했지만 거래일이 더 과거인 backdate 거래를 과거 스냅샷 계산에 포함하는 회귀 테스트 추가

### 검증 결과
- `python3 -m compileall src/db.py tests/test_db.py` 성공
- `python3 -m unittest tests.test_db` 성공 (`25`건)
- `python3 -m compileall app.py src scripts tests` 성공
- `python3 -m unittest discover -s tests -p "test_*.py"` 성공 (`110`건)
- 로컬 SQLite 재대조 결과: `sqlite_pending_snapshot_changes=0`
- 운영 Supabase 재대조 결과:
  - 계좌 `23` `미래에셋증권`: historical snapshot 추가 보정 필요 없음
  - 계좌 `24` `IRP (신한)`: historical snapshot 추가 보정 필요 없음

### 비고
- 운영 Supabase의 레거시 `cash_adjustment` 거래 로그 3건은 현재도 남아 있지만, 현재 계산 로직/스냅샷 재대조 기준으로는 별도 강제 삭제보다 보존이 안전하다고 판단해 이번 턴에는 삭제하지 않음
- 로컬 `data/portfolio.db`는 재검산 과정에서 다시 저장되어 워크트리에 변경으로 남아 있음

## 2026-05-11 보유현금 수동값 유지 배포
- [x] 상품 매수/매도 저장이 `보유현금`을 자동으로 깎거나 더하지 않도록 수정
- [x] 거래 페이지 안내 문구에 현금 규칙 반영
- [x] 관련 테스트 갱신 및 전체 검증
- [x] `main` 배포 및 운영 페이지 검증

### 변경 내용
- `src/sqlite_db.py`
  - `record_trade()`가 `accounts.cash_balance`를 갱신하지 않고 보유 종목과 거래 로그만 반영하도록 수정
- `src/db.py`
  - `_supabase_record_trade()`가 Supabase 계좌 `cash_balance`를 자동 변경하지 않도록 수정
- `app.py`
  - 거래 페이지 캡션에 `보유현금은 거래와 연동하지 않고 직접 수정한 값만 유지` 문구 추가
- `tests/test_db.py`
  - 매수 저장 후 현금이 자동 음수로 바뀌지 않는 규칙으로 테스트 기대값 갱신

### 검증 결과
- `python3 -m compileall app.py src/db.py src/sqlite_db.py tests/test_db.py` 성공
- `python3 -m unittest tests.test_db` 성공 (`25`건)
- `python3 -m compileall app.py src scripts tests` 성공
- `python3 -m unittest discover -s tests -p "test_*.py"` 성공 (`110`건)
- 배포 검증:
  - 명령: `./.venv/bin/python scripts/verify_streamlit_deployment.py --page trades --expect-backend supabase --text-output artifacts/deploy-trades.txt --screenshot artifacts/deploy-trades.png --debug-dir artifacts/deploy-trades-debug`
  - 결과: `logged_in=true`, `workspace_visible=true`, `backend_storage=supabase`, `ok=true`
  - 배포 페이지 본문에서 새 안내 문구 노출 확인

### 배포/커밋
- 기능 커밋: `ea2fd37` `Keep cash balance manual on trade entry`
- 배포 방법: `git push origin main`

### 메모
- 이번 변경은 `매수/매도`와 `보유현금`의 자동 연동만 끊었고, `거래기록 수정/삭제` 기능은 아직 구현하지 않음

## 2026-05-11 거래기록 수정/삭제 배포
- [x] 거래 페이지에서 보이는 거래기록을 선택해 수정/삭제하는 UI 추가
- [x] SQLite/Supabase 공통 거래기록 수정/삭제 백엔드 구현
- [x] 매수/매도 수정/삭제 시 보유 종목 재계산 반영
- [x] 현금 흐름 수정/삭제 시 현재 보유현금 재계산 반영
- [x] 관련 테스트 추가 및 `main` 배포 확인

### 지원 범위
- 수정/삭제 지원:
  - `buy`
  - `sell`
  - `personal_deposit`
  - `employer_deposit`
  - `withdraw`
- 현재 미지원:
  - `transfer_in`
  - `transfer_out`
  - `interest`
  - `cash_adjustment`

### 변경 내용
- `src/db.py`
  - `update_trade_log()`, `delete_trade_log()` 공개 wrapper 추가
  - Supabase/SQLite 각각의 거래기록 수정/삭제 구현 추가
  - 매수/매도 로그를 기준으로 holdings를 다시 계산하는 helper 추가
  - 현금 흐름 로그 수정/삭제 시 `cash_balance`를 다시 계산하는 helper 추가
- `app.py`
  - 거래 기록 표 아래에 `수정/삭제할 기록` 선택 UI 추가
  - 선택한 기록 유형에 따라 매수/매도 편집 폼 또는 현금 흐름 편집 폼을 표시
  - 삭제 확인 체크 후 삭제 실행 버튼 추가
  - 이체/이자/레거시 현금조정은 현재 미지원 안내 추가
- `tests/test_db.py`
  - SQLite 거래 수정/삭제 통합 테스트 4건 추가
  - Supabase 거래 수정/삭제 경로 unit test 2건 추가
- `tests/test_app_dashboard.py`
  - 거래기록 편집 가능 유형과 선택 라벨 표시 helper 테스트 추가

### 검증 결과
- `python3 -m compileall app.py src/db.py tests/test_db.py tests/test_app_dashboard.py` 성공
- `python3 -m unittest tests.test_db tests.test_app_dashboard` 성공 (`66`건)
- `python3 -m compileall app.py src scripts tests` 성공
- `python3 -m unittest discover -s tests -p "test_*.py"` 성공 (`118`건)
- 배포 검증:
  - 명령: `./.venv/bin/python scripts/verify_streamlit_deployment.py --page trades --expect-backend supabase --text-output artifacts/deploy-trade-edit.txt --screenshot artifacts/deploy-trade-edit.png --debug-dir artifacts/deploy-trade-edit-debug`
  - 결과: `logged_in=true`, `workspace_visible=true`, `backend_storage=supabase`, `ok=true`
  - 본문 텍스트 확인:
    - `수정/삭제할 기록`
    - `선택한 거래 기록 수정 / 삭제`
    - `수정 저장`
    - `삭제 실행`

### 배포/커밋
- 기능 커밋: `bec3f67` `Add trade log edit and delete flows`
- 배포 방법: `git push origin main`

### 메모
- 거래기록 수정/삭제는 현재 `거래` 페이지에서 보이는 사용자 입력 로그 중심으로 지원한다.
- 이체/이자/레거시 현금조정까지 편집 대상으로 넓히려면 paired event 정합성과 다계좌 재계산을 추가로 설계해야 한다.

## 2026-05-11 16:17 거래기록 수정 UI 업데이트

### 변경 내용
- 매수/매도 컬러 배지 스타일 추가
- 거래유형 컬러 배지 HTML 함수 추가
- 거래유형 셀 표시를 컬러 배지로 변경
- 거래기록 셀 HTML 렌더링 적용

### 검증 방법
- `streamlit run app.py` 실행
- 거래 화면에서 매수/매도 배지가 색상으로 표시되는지 확인
- 거래기록의 `수정` 버튼 클릭 시 해당 행 바로 아래에 수정 입력 박스가 표시되는지 확인
- 저장 후 거래기록, 보유 종목, 대시보드 금액이 갱신되는지 확인

## 2026-05-11 16:35 거래기록 삭제 후 대시보드 잔상 수정

- `src/sqlite_db.py`
  - 거래기록 삭제 시 남아 있는 `buy`/`sell` 원장을 기준으로 `holdings`를 재계산하도록 수정.
  - 매수/매도 삭제 시 `cash_balance`는 변경하지 않도록 처리.
  - 개인 입금, 회사 납입금, 출금, 이자, 이체, 현금조정 등 현금성 이벤트 삭제 시에만 `cash_delta`를 반대로 반영.
- `src/db.py`
  - `delete_trade_log()` 실행 후 `mark_data_dirty()`를 호출해 Streamlit 데이터 캐시 잔상 방지.
- 검증 필요
  - 거래기록에서 매수 기록 삭제 후 대시보드/보유종목에서 해당 종목이 사라지는지 확인.
  - 개인 입금/회사 납입금/출금 삭제 시 현금 잔액이 정상 보정되는지 확인.

## 2026-05-11 19:06 대시보드 카드/트렌드 컨트롤 스타일 조정

### 변경 파일
- `app.py`
- `.streamlit/app.css`
- `tests/test_app_dashboard.py`

### 변경 내용
- 상단 5개 요약 카드와 `현재 보유 종목` 패널 내부 배경을 흰색 기준으로 정리.
- `원금 대비 평가손익`, `원금 대비 수익률` 카드 tone을 값 부호 기준 초록/빨강으로 복원.
- `현재 보유 종목` 비중 막대는 `위험자산=빨강`, `안전자산=초록`, 트랙 배경은 흰색으로 조정.
- 선택 종목 트렌드 컨트롤에서 `기간`, `지표`, `선택 해제`를 한 행에 배치하고 `선택 해제` 버튼을 동일한 박스 스타일로 통일.
- 대시보드 상단/패널 관련 CSS 회귀를 반영하고 테스트 expectation을 갱신.

### 검증 결과
- `python -m compileall app.py src tests` 성공
- `python -m unittest discover -s tests -p "test_*.py"` 성공 (`124`건)
- 추가 확인:
  - `python -m compileall app.py` 성공
  - `python -m unittest tests.test_app_dashboard` 성공 (`40`건)

### 로컬 실행 메모
- Streamlit 로컬 서버: `python -m streamlit run app.py --server.port 8522 --server.headless true`
- 확인 URL: `http://localhost:8522`
- Playwright 기반 로컬 자동 확인은 Streamlit 초기 렌더 프레임을 안정적으로 잡지 못해 스크린샷이 빈 흰 화면으로 남았고, 이 한계는 `artifacts/local-dashboard-manual.png` 및 `artifacts/local-dashboard-debug/`에 기록함.

## 2026-05-11 19:08 자산 배분 차트 세로 비율 확대

### 변경 내용
- `app.py`에 자산 배분 전용 높이 상수 `DASHBOARD_ALLOCATION_PANEL_HEIGHT=720`, `DASHBOARD_ALLOCATION_CHART_HEIGHT=520`를 추가.
- 자산 배분 패널만 더 길게 보이도록 컨테이너 높이와 트리맵 렌더 높이를 전용 상수로 분리.
- Altair fallback 자산 배분 차트도 동일 전용 높이를 사용하도록 맞춤.

### 검증 결과
- `python -m compileall app.py` 성공
- `python -m unittest tests.test_app_dashboard` 성공 (`40`건)

## 2026-05-11 19:29 대시보드 레이아웃/모바일/트리맵 경계 재조정

### 변경 파일
- `app.py`
- `.streamlit/app.css`
- `.streamlit/config.toml`
- `tests/test_app_dashboard.py`

### 변경 내용
- 상단 5개 요약 카드 아래에 `기준시각`을 `YYYY-MM-DD HH:MM:SS` 형식으로 우측 정렬 배치.
- 자산 배분/선택 종목 트렌드/보유 종목 수익률 패널의 고정 높이를 풀고 내부 gap을 줄여, 하단 공백이 과도하게 남지 않도록 정리.
- `현재 보유 종목` 패널과 표 영역을 흰색 기준으로 맞추고, 자산 비중 막대 트랙도 흰색으로 정리.
- 선택 종목 트렌드와 보유 종목 수익률 2열 영역에 모바일 전용 nowrap/축소 레이아웃을 적용해, 모바일에서도 PC와 같은 배치를 유지하고 필요 시 확대해서 볼 수 있게 조정.
- 트리맵 상위/하위 레벨 `gapWidth`, `borderWidth`, `upperLabel` 높이, 외곽 margin을 줄여 경계선 어긋남과 과한 흰 여백을 완화.
- 상단 카드 중 `입금 원금`, `원금 대비 평가손익`, `원금 대비 수익률`도 `보유 현금`, `현재 평가액` 카드와 같은 높이 기준으로 재정렬.

### 검증 결과
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest discover -s tests -p "test_*.py"` 성공 (`125`건)
- 추가 확인:
  - `python -m unittest tests.test_app_dashboard` 성공 (`41`건)
  - `python -m unittest tests.test_app_dashboard.ThemeStylesheetTests` 성공 (`3`건)

### 로컬 확인 메모
- Streamlit 로컬 서버: `python -m streamlit run app.py --server.port 8524 --server.headless true`
- Playwright 로컬 확인에서는 Streamlit skeleton 단계 스크린샷까지만 안정적으로 캡처됐고, 산출물은 `artifacts/local-dashboard-8524.png`에 남김.

## 2026-05-11 19:42 현재 보유 종목 표 테마 조정

### 변경 파일
- `app.py`
- `.streamlit/app.css`
- `tests/test_app_dashboard.py`

### 변경 내용
- `현재 보유 종목` 표만 `st.dataframe` 기본 캔버스 렌더 대신 커스텀 HTML 테이블 스킨으로 전환.
- 헤더 배경, 셀 보더, 숫자 정렬, hover 배경, 손익/수익률 양수·음수 컬러를 첨부 스크린샷 톤에 맞게 정리.
- 표 스킨 회귀 테스트와 CSS 클래스 존재 검증을 추가.

### 검증 결과
- `python -m compileall app.py tests/test_app_dashboard.py` 성공
- `python -m unittest tests.test_app_dashboard.HoldingsTableDisplayTests tests.test_app_dashboard.ThemeStylesheetTests` 성공 (`8`건)
- `python -m unittest discover -s tests -p "test_*.py"` 성공 (`126`건)

## 2026-05-12 02:20 거래/대시보드 레이아웃 및 실현손익 차트 정리

### 변경 파일
- `app.py`
- `.streamlit/app.css`
- `tests/test_app_dashboard.py`

### 변경 내용
- 상단 요약 카드 5개에 동일한 최소 높이 기준을 적용해 `입금 원금`, `원금 대비 평가손익`, `원금 대비 수익률` 카드 하단 라인을 `보유 현금`, `현재 평가액`과 맞춤.
- 선택 종목 트렌드 기간 옵션에서 대시보드 전용 `당일`을 제거하고, `기간`/`지표`/`선택 해제` 컨트롤 폭과 높이를 줄여 한 줄 배치가 더 타이트하게 보이도록 정리.
- 거래 페이지에서 `상품 등록`과 `현금입금/출금` 패널을 2열로 병렬 배치.
- `실현손익` 차트를 대시보드 `보유 종목 수익률`과 같은 막대 톤으로 맞춘 ECharts/Altair helper로 교체.
- 대시보드 기간 옵션 제외와 실현손익 막대 라벨/모서리 회귀 테스트를 추가.

### 검증 결과
- `python -m compileall app.py tests/test_app_dashboard.py` 성공
- `python -m unittest tests.test_app_dashboard.TradeFormResetTests tests.test_app_dashboard.HoldingsBarLabelTests tests.test_app_dashboard.RealizedProfitBarTests` 성공 (`14`건)
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest discover -s tests -p "test_*.py"` 성공 (`128`건)
- `python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase --wait-ms 15000` 성공
- `python scripts/verify_streamlit_deployment.py --page trades --expect-backend supabase --wait-ms 15000` 성공

### 배포 메모
- 커밋: `5de102e` (`Adjust dashboard and trade layouts`)
- `origin/main` 푸시 완료
- 원격 검증 결과:
  - dashboard: `logged_in=true`, `workspace_visible=true`, `backend_storage=Supabase`, `allocation_status="지연 데이터 표시 중"`
  - trades: `logged_in=true`, `workspace_visible=true`, `backend_storage=Supabase`

## 2026-05-12 03:48 거래 실현손익 오류 및 선택 종목 트렌드 컨트롤 재조정

### 변경 파일
- `app.py`
- `.streamlit/app.css`

### 변경 내용
- `trade_entry_page()`에서 `echarts_available` 지역 변수를 먼저 계산하도록 보강해, 실현손익 차트 렌더 분기에서 발생하던 `NameError`를 제거.
- 상단 5개 카드 높이 정렬이 실제 Streamlit DOM에도 적용되도록 `dashboard-summary-strip` 하위 `stVerticalBlockBorderWrapper` 기준 최소 높이/스트레치 셀렉터를 강화.
- 선택 종목 트렌드 컨트롤은 기간 영역 폭을 더 넓히고, 라벨/버튼/segmented control 높이와 padding을 추가로 줄여 `1개월·3개월·6개월·1년`이 같은 행에 유지되도록 재조정.

### 검증 결과
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest tests.test_app_dashboard` 성공 (`44`건)
- `python -m unittest discover -s tests -p "test_*.py"` 성공 (`128`건)
- `python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase --wait-ms 15000` 성공
- `python scripts/verify_streamlit_deployment.py --page trades --expect-backend supabase --wait-ms 15000` 성공

### 배포 메모
- 커밋: `0cb1796` (`Fix trade chart error and compact trend controls`)
- `origin/main` 푸시 완료
- 원격 검증 결과:
  - dashboard: `logged_in=true`, `workspace_visible=true`, `backend_storage=Supabase`, `allocation_status="실시간 연동 중"`
  - trades: `logged_in=true`, `workspace_visible=true`, `backend_storage=Supabase`

## 2026-05-12 03:56 대시보드 카드 헤더 정렬 및 실현손익 요약 컬러 보강

### 변경 파일
- `app.py`
- `.streamlit/app.css`

### 변경 내용
- 요약 카드 본문을 항상 동일한 `header(label + ghost action slot)` 구조로 렌더링해 상단 카드들의 시각적 정렬 기준을 통일.
- 선택 종목 트렌드 컨트롤은 바깥 `border=True` 래퍼를 제거하고, 내부 행 정렬/segmented control/button 간격을 더 줄여 박스 높이를 낮춤.
- `실현 손익 요약` 표에 `실현손익`, `실현수익률(%)` 컬러 스타일을 추가해 양수/음수 톤이 보이도록 변경.

### 검증 결과
- `python -m compileall app.py` 성공
- `python -m unittest tests.test_app_dashboard` 성공 (`44`건)
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest discover -s tests -p "test_*.py"` 성공 (`128`건)

## 2026-05-12 04:06 대시보드 상단 카드/선택 종목 트렌드 추가 압축

### 변경 파일
- `app.py`
- `.streamlit/app.css`

### 변경 내용
- 선택 종목 트렌드 컨트롤을 `기간 / 지표 / 선택 해제` 3블록만 남기도록 단순화해, 라벨 칸 때문에 생기던 세로 높이와 줄바꿈을 제거.
- 상단 요약 카드 라벨은 `nowrap`과 더 작은 글자 크기로 조정하고, ghost action slot에 고정 최소 폭을 줘 카드별 헤더 줄수 차이를 줄임.
- 선택 종목 트렌드 segmented control / 버튼 높이, padding, gap을 한 단계 더 줄여 한 줄형 밀도를 높임.

### 검증 결과
- `python -m compileall app.py` 성공
- `python -m unittest tests.test_app_dashboard` 성공 (`44`건)
- `python -m unittest discover -s tests -p "test_*.py"` 성공 (`128`건)

### 배포 메모
- 커밋: `1152639` (`Compress dashboard summary and trend controls`)
- `origin/main` 푸시 완료
- 원격 검증:
  - `python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase --wait-ms 15000 --screenshot artifacts/dashboard-top-after-1152639.png --text-output artifacts/dashboard-top-after-1152639.txt` 성공
  - 상단 카드 원격 스크린샷에서 라벨 줄바꿈 제거 확인

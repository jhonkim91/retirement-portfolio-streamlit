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
- 배포 웹 검증이 불안정하던 원인을 `반복 로그인에 따른 인증 rate limit`과 `실패 시 마지막 화면 증거 부족`으로 분리했고, `scripts/verify_streamlit_deployment.py`에 `--storage-state`, `--debug-dir` 옵션과 `auth_error`/`rate_limited` 진단 필드를 추가
- 검증 실패 시 단계별 `txt/png/url` 아티팩트를 남기도록 보강해, 로그인 실패/페이지 전환 실패/배포 미반영 상태를 이후 세션에서도 바로 재확인할 수 있게 정리

## 최신 검증 결과
- `python3 -m compileall app.py src scripts tests` 성공
- `python3 -m unittest discover -s tests -p "test_*.py"` 성공
- 최신 테스트 수: `85`건 통과
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

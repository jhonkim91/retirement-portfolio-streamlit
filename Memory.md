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

## Git/GitHub 상태
- 기본 브랜치: `main`
- 최근 기능 커밋:
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

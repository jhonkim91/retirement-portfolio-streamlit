# Memory.md

## 문서 목적
- 이 파일은 현재 프로젝트 상태와 다음 작업에 필요한 최소 정보만 유지한다.
- 날짜별 상세 작업 로그는 `docs/archive/memory-YYYY-MM-DD.md`로 분리했다.
- 검증 상세 이력은 `docs/VALIDATION.md`에 모았다.
- 완료된 변경 이력은 `docs/CHANGELOG.md`에 모았다.
- 중요한 설계 결정은 `docs/DECISIONS.md`에 모았다.
- 정리 기준일은 `2026-05-13`이다.
- 원본의 `2026-05-15` 섹션은 현재 기준일보다 뒤라 날짜 오류 가능성으로 별도 표시했다.

## 작업 상태
- [x] 프로젝트 구조 분석, 문서 분리, `app.py` 지연 로더와 `src/ui/app_core.py` 중심 구조 반영
- [x] `pages/dashboard.py`, `pages/trades.py`, `pages/data.py` 기반 `st.navigation` 전환 반영
- [x] Supabase 우선 저장소, SQLite fallback, KIS REST/WebSocket worker, daily rollup 유지
- [x] 보유현금 수동 관리, 거래/현금 흐름 분리, 삭제 후 DB 조회 캐시 무효화 반영
- [x] realtime worker `last_quote_at` 보존과 `realtime_price_ticks` 보존/집계 정책 반영
- [x] 대시보드/거래/데이터 페이지 UI 정리와 모바일 거래 입력 overflow 보강
- [x] CSS radius/shadow 토큰, KPI 카드 위계/반응형 grid, 차트 패널 카드감, 팔레트 보강
- [x] `setup_supabase.sql` RLS 정책 재실행 안정화 반영
- [x] UG-01 CSS 파일 누락 시 `render_app_stylesheet()` 안전 반환 처리
- [x] BUG-02 우선 surface 배경의 흰색 하드코딩 토큰화
- [ ] KIS WebSocket worker 장시간 실행 중 재연결/상태 복구를 장중 운영 로그 기준으로 추가 점검
- [ ] 모바일 viewport에서 대시보드 트리맵/보유 종목 표/거래 입력 폼 가독성 확인
- [ ] 스냅샷 저장, CSV export, 운영 정리 작업의 로딩 상태 표시 누락 여부 점검
- [ ] `scripts/verify_streamlit_deployment.py`의 거래/데이터 요약 추출값 정밀화
- [ ] Supabase SQL Editor에서 `setup_supabase.sql` 전체 또는 문제 정책 블록 재실행 확인

## 프로젝트 개요
- 유형: `Python + Streamlit`
- 진입점: `app.py`
- 앱 코어: `src/ui/app_core.py`
- 페이지: `pages/dashboard.py`, `pages/trades.py`, `pages/data.py`
- 저장소: `Supabase` 우선, 필요 시 `SQLite`
- 로컬 SQLite DB: `data/portfolio.db`
- 시세: `KIS REST/WebSocket` 우선, KRX/Naver fallback, 일부 `yfinance` fallback
- 배포 앱: `https://retirement-portfolio-app-nh2vq9ferqnpehsslbykbe.streamlit.app/`
- UI 설정: `.streamlit/config.toml`과 `.streamlit/app.css` 기준 유지

## 핵심 파일
- `app.py`: 얇은 Streamlit 엔트리포인트와 기존 공개 API 호환 지연 로더
- `src/ui/app_core.py`: 앱 라우터, 페이지 공통 상태, UI helper의 중심 구현
- `src/ui/charts.py`, `src/ui/forms.py`, `src/ui/layout.py`: 앱 코어 helper re-export 호환 모듈
- `pages/dashboard.py`: 대시보드 페이지 진입점
- `pages/trades.py`: 거래 페이지 진입점
- `pages/data.py`: 데이터/운영 상태 페이지 진입점
- `src/db.py`: Supabase 중심 DB 추상화 및 조회 캐시
- `src/sqlite_db.py`: SQLite fallback 구현
- `src/auth.py`: 인증 및 Supabase client 지연 초기화
- `src/analytics.py`: 포트폴리오 계산 및 차트 데이터
- `src/market.py`: KIS/Naver/yfinance 시세 조회와 캐시
- `scripts/run_daily_rollup.py`: 일별 롤업 배치
- `scripts/run_kis_quote_worker.py`: KIS realtime quote worker
- `scripts/run_realtime_tick_retention.py`: realtime tick 1분/5분/일봉 집계와 raw tick 보존 정책 실행
- `scripts/verify_streamlit_deployment.py`: Streamlit Cloud 운영 검증
- `setup_supabase.sql`: Supabase schema/RLS 정책 기준 스크립트
- `.github/workflows/kis-realtime-worker.yml`: 장중 worker 자동 실행
- `.github/workflows/daily-rollup.yml`: 일별 롤업 자동 실행

## 실행 명령
```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

## 권장 검증 명령
```powershell
python -m compileall app.py src scripts tests pages
python -m unittest discover -s tests -p "test_*.py"
python scripts/run_kis_quote_worker.py --backend sqlite --preflight-only
python scripts/verify_streamlit_deployment.py --page data --expect-backend supabase --wait-ms 12000
```

## 운영 시크릿 메모
- 앱용: `SUPABASE_URL`, `SUPABASE_KEY`
- 관리자/배치용: `SUPABASE_SERVICE_ROLE_KEY`
- KIS용: `KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_ENV`
- 배포 검증용: `STREAMLIT_VERIFY_EMAIL`, `STREAMLIT_VERIFY_PASSWORD`
- 실제 값은 `.streamlit/secrets.toml`, Streamlit Cloud secrets, GitHub Actions secrets, OS 환경 변수에만 둔다.
- `SUPABASE_SERVICE_ROLE_KEY` 같은 관리자 키는 UI, 문서, 커밋에 노출하지 않는다.

## 현재 운영 상태
- 기준일: `2026-05-13`
- 배포 앱은 `Supabase` backend를 사용 중인 것으로 최근 검증에 기록됨.
- 운영 Supabase realtime 테이블 노출 상태는 최근 기록 기준 `accounts`, `realtime_worker_status`, `realtime_price_ticks` 모두 HTTP `200`.
- GitHub Actions `KIS Realtime Worker` manual run `25771266167`은 job `success`로 기록됨.
- run 중 `ping/pong timed out` 후 재연결이 발생했고, 종료 시 `exit 137`이 있었으나 workflow 결과는 성공으로 기록됨.
- 계좌 `24`, `25`는 최신 tick과 같은 `last_quote_at=2026-05-13T09:54:33` 기록.
- 계좌 `26`은 quote 미수신 상태에서도 기존 `last_quote_at=2026-05-12T15:48:44` 유지.
- 계좌 `23`은 tick 이력이 없어 `last_quote_at=null` 유지.
- `setup_supabase.sql` 정책 재실행 안정화는 로컬 문법/테스트/배포 데이터 페이지 검증까지 완료.
- 원격 SQL Editor에서 정책 블록 직접 재실행 검증은 아직 남아 있음.

## 핵심 설계 결정 요약
- Supabase를 기본 저장소로 사용하고, 로컬/개발 fallback은 SQLite로 유지한다.
- `app.py`는 얇은 엔트리포인트로 두고 실제 구현은 `src/ui/app_core.py`와 `pages/`에 둔다.
- 기존 테스트와 monkey patch 호환을 위해 `app.py` 공개 함수/상수 접근은 앱 코어로 위임한다.
- 보유현금은 거래 저장과 자동 연동하지 않고 사용자가 직접 수정한 현재 잔액으로 관리한다.
- 매수는 현재 보유현금 부족 여부와 무관하게 저장을 허용한다.
- 레거시 `cash_adjustment` 거래는 거래 화면과 원금/순유입 계산에서 제외한다.
- 보유현금은 자산 비중 표시에서 안전자산에 포함한다.
- 계좌 간 이체 UI와 데모 seed 이체 예시는 제거된 상태다.
- realtime worker 상태 갱신 시 새 quote 시각이 없으면 기존 `last_quote_at`를 보존한다.
- KIS 가능한 종목은 KIS를 우선하고, KRX 알파뉴메릭 종목은 Naver chart fallback을 사용한다.
- `altair`는 Streamlit Cloud Python 3.14 호환 문제 때문에 `altair>=5.3,<5.4`로 제한한다.
- Supabase hotfix 상세 절차는 기본 비노출이며 `PORTFOLIO_SHOW_HOTFIX_GUIDE=true`일 때만 표시한다.
- 전역 차트 색상은 `ChartColors`/`CHART_COLORS` 네임스페이스를 기준으로 관리한다.
- `.streamlit/config.toml`의 테마/서버 설정은 요청이 없으면 변경하지 않는다.

## 최신 검증 결과
- 상세 검증 이력은 `docs/VALIDATION.md`에 정리했다.
- BUG-02 CSS surface 토큰 교체: `python -m unittest tests.test_app_dashboard.ThemeStylesheetTests` 성공, 8 tests.
- UG-01 CSS 누락 안전장치: `python -m compileall src/ui/app_core.py tests/test_app_dashboard.py` 성공.
- UG-01 CSS 누락 안전장치: `python -m unittest tests.test_app_dashboard.ThemeStylesheetTests` 성공, 7 tests.
- 최신 전체 검증: `python -m compileall app.py src scripts tests pages` 성공.
- 최신 전체 검증: `python -m unittest discover -s tests -p "test_*.py"` 성공, 157 tests.
- 대표 배포 검증 기록:
  - `2026-05-13` DESIGN-04 KPI 반응형 배포 검증 성공: 운영 앱 dashboard, backend `Supabase`, allocation status `실시간 반영 중`, `ok=true`
  - `python3 scripts/verify_streamlit_deployment.py --page data --expect-backend supabase --wait-ms 12000` 성공
  - Streamlit Cloud 대시보드/거래/데이터 페이지 검증 성공 기록 존재
- 이번 UG-01/BUG-02 패치는 로컬 코드/단위 테스트/전체 테스트로 검증했고 BUG-02 요청에 따라 배포를 진행한다.

## 문서 분리 결과
- 날짜별 상세 로그:
  - `docs/archive/memory-2026-05-11.md`
  - `docs/archive/memory-2026-05-12.md`
  - `docs/archive/memory-2026-05-13.md`
  - `docs/archive/memory-2026-05-15.md`
- `2026-05-15` archive는 현재 기준일보다 뒤라 날짜 오류 가능성을 파일 상단에 표시했다.
- 검증 상세 이력: `docs/VALIDATION.md`
- 완료 변경 이력: `docs/CHANGELOG.md`
- 설계 결정: `docs/DECISIONS.md`

## Git/GitHub 상태
- 기본 브랜치: `main`
- 최근 커밋 기록에는 `437c4db`, `b293d0a`, `aab9d67`, `5e2584b`, `a3d9285`, `32fe43a`, `33e754f` 등이 있음.
- `2026-05-15`로 기록된 `33e754f`, `32fe43a` 관련 내용은 현재 파일/커밋에는 존재하지만 날짜는 오류 가능성으로 취급한다.
- 기존 워크트리에는 `data/portfolio.db` 수정과 여러 untracked 로컬 산출물이 남아 있다.
- 최근 주요 변경 파일은 `.streamlit/app.css`, `.streamlit/config.toml`, `src/ui/app_core.py`, `tests/test_app_dashboard.py`, `docs/VALIDATION.md`, `docs/CHANGELOG.md`, `Memory.md` 중심이다.
- 이번 UG-01/BUG-02 배포 대상 파일은 `.streamlit/app.css`, `.streamlit/config.toml`, `src/ui/app_core.py`, `tests/test_app_dashboard.py`, `docs/VALIDATION.md`, `docs/CHANGELOG.md`, `Memory.md`다.
- 배포 커밋: `5ad9936` `Improve dashboard KPI responsive cards` (`origin/main` push 완료)
- 커밋 시 이번 요청 관련 파일만 선별하고 `data/portfolio.db`, `.local/`, `artifacts/`, `.playtools*/`, `.playwright-browsers/`, `.vscode/`, `data/kis_cache/` 등은 제외한다.

## 운영 runbook 요약
- realtime schema hotfix: `docs/supabase-realtime-schema-hotfix.sql`
- realtime worker runbook: `docs/supabase-realtime-worker-runbook.md`
- realtime tick retention runbook: `docs/realtime-tick-retention-runbook.md`
- Supabase hotfix runbook: `docs/supabase-hotfix-runbook.md`
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
  - schedule 1: `UTC 00:00` (`KST 09:00`)
  - schedule 2: `UTC 02:55` (`KST 11:55`)

## 남은 작업
1. KIS WebSocket worker 장시간 실행 중 재연결/상태 복구 로직을 장중 운영 로그로 추가 확인한다.
2. 계좌 `23`처럼 tick 이력이 없는 계좌의 `last_quote_at=null` 유지가 운영 요구와 맞는지 확인한다.
3. 모바일 viewport에서 대시보드 트리맵, 보유 종목 표, 거래 입력 폼 가독성을 실제 스크린샷으로 확인한다.
4. 장시간 작업의 `st.spinner`/`st.status` 적용 누락 여부를 점검한다.
5. `scripts/verify_streamlit_deployment.py`의 거래/데이터 페이지 요약 추출값을 새 화면 구조에 맞게 정밀화한다.
6. Supabase SQL Editor에서 `setup_supabase.sql` 전체 또는 문제 정책 블록 재실행 결과를 확인한다.

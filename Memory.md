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
- [ ] 다음 장중 자동 스케줄(`UTC 00:00`, `UTC 02:55`) 1회 추가 확인
- [ ] 배포 대시보드에서 자산 배분 상태 칩이 실제로 `실시간 연동 중`으로 보이는지 화면 검증
- [ ] GitHub Actions Node 24 전환 전 액션 버전 점검

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
- 자산 배분 상태 칩을 실제 worker 상태 기반(`실시간 연동 중`, `지연 데이터 표시 중` 등)으로 변경
- 운영 Supabase realtime 테이블 생성 후 장중 적재 검증 완료
- GitHub Actions 장중 worker 자동화 workflow 추가
- `gh` CLI 설치, GitHub Actions secrets 주입, 수동 dispatch/실행 성공 검증 완료

## 최신 검증 결과
- `python3 -m compileall app.py src scripts tests` 성공
- `python3 -m unittest discover -s tests -p "test_*.py"` 성공
- 최신 테스트 수: `73`건 통과
- 배포 검증 산출물:
  - `artifacts/deploy-verify-realtime-data-20260511.txt`
  - `artifacts/deploy-verify-realtime-data-20260511.png`
  - `artifacts/deploy-verify-realtime-dashboard-20260511.txt`
  - `artifacts/deploy-verify-realtime-dashboard-20260511.png`

## Git/GitHub 상태
- 기본 브랜치: `main`
- 최근 기능 커밋:
  - `72f0f41` `Refresh auth UI and allocation status chip`
  - `12748fd` `Add scheduled KIS realtime worker workflow`
  - `7ee4d45` `Fix GitHub worker shutdown handling`
- 최근 기록 커밋:
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
1. 다음 장중 자동 스케줄이 `success`로 끝나는지 1회 더 확인
2. 배포 대시보드에서 자산 배분 상태 칩이 `실시간 연동 중`으로 보이는지 화면 검증
3. 필요 시 `verify_streamlit_deployment.py`에 자산 배분 상태 칩 텍스트 검증 추가
4. GitHub Actions의 Node 24 전환 경고 대응 검토

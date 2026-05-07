# 진행 메모

기준 시각: 2026-05-08 Asia/Seoul

## 목적

딥 리서치 문서 이후 단계별 개선 작업의 진행 현황, 산출물, 현재 운영 이슈를 한 곳에서 추적한다.

## 단계별 상태

### 1단계. 원장/이자 규칙 설계

- 상태: 완료
- 산출물: [phase-1-ledger-interest-spec.md](/C:/Users/JKKIM/retirement-portfolio-streamlit/docs/phase-1-ledger-interest-spec.md)
- 핵심 내용:
  - `trade_logs`를 단일 이벤트 원장으로 확장하는 방향 확정
  - `cash_delta`, `event_group_id`, `counterparty_account_id`, `metadata_json` 규칙 정의
  - `personal_deposit`, `employer_deposit`, `interest`, `transfer`, `cash_adjustment` 이벤트 정의
  - 일별 이자 적립 규칙과 계좌 스냅샷 방향 확정

### 2단계. 스키마 정비

- 상태: 완료
- 반영 파일:
  - [setup_supabase.sql](/C:/Users/JKKIM/retirement-portfolio-streamlit/setup_supabase.sql)
  - [src/sqlite_db.py](/C:/Users/JKKIM/retirement-portfolio-streamlit/src/sqlite_db.py)
  - [src/db.py](/C:/Users/JKKIM/retirement-portfolio-streamlit/src/db.py)
- 핵심 내용:
  - `trade_logs` 확장 컬럼 추가
  - `daily_interest`, `daily_account_snapshot` 테이블 추가
  - SQLite 자동 마이그레이션과 Supabase 스키마 SQL 정리

### 3단계. 현금 원장화와 계좌 이체

- 상태: 완료
- 반영 파일:
  - [app.py](/C:/Users/JKKIM/retirement-portfolio-streamlit/app.py)
  - [src/db.py](/C:/Users/JKKIM/retirement-portfolio-streamlit/src/db.py)
  - [src/sqlite_db.py](/C:/Users/JKKIM/retirement-portfolio-streamlit/src/sqlite_db.py)
- 핵심 내용:
  - `현금 잔액 직접 수정` 제거 후 `현금 조정` 기록 방식으로 변경
  - `개인 입금`, `회사 납입금`, `일반 출금` 이벤트 저장 통일
  - 계좌 간 이체 UI 및 `event_group_id` 기반 입출금 2건 기록 구현

### 4단계. 일별 이자/스냅샷 롤업

- 상태: 완료
- 반영 파일:
  - [scripts/run_daily_rollup.py](/C:/Users/JKKIM/retirement-portfolio-streamlit/scripts/run_daily_rollup.py)
  - [.github/workflows/daily-rollup.yml](/C:/Users/JKKIM/retirement-portfolio-streamlit/.github/workflows/daily-rollup.yml)
  - [docs/daily-rollup-ops-checklist.md](/C:/Users/JKKIM/retirement-portfolio-streamlit/docs/daily-rollup-ops-checklist.md)
- 핵심 내용:
  - 전일 기준 일별 이자 적립 배치 구현
  - `daily_account_snapshot` 저장 구현
  - GitHub Actions 자동 실행 추가

### 5단계. 성과/추이 계산 고도화

- 상태: 부분 완료
- 현재 반영:
  - [src/analytics.py](/C:/Users/JKKIM/retirement-portfolio-streamlit/src/analytics.py)
  - [app.py](/C:/Users/JKKIM/retirement-portfolio-streamlit/app.py)
- 완료된 내용:
  - 스냅샷이 있으면 대시보드 추이에 우선 사용
  - `누적 이자` 메트릭 추가
- 남은 내용:
  - 총투입원금, 순유입, 누적 이자, 실제 성과를 원장/스냅샷 기준으로 완전히 재정의
  - `account_summary`와 `build_portfolio_trend`의 잔여 구간 정리

### 6단계. UI/운영 진단 개선

- 상태: 부분 완료
- 완료된 내용:
  - 거래/데이터 화면 용어 통일
  - 데이터 화면에 `운영 상태` 패널 추가
  - 현재 저장소, 누적 이자, 롤업 건수, 스냅샷 건수 노출
  - 배포 백엔드 선택 로직을 `auto` 기본값으로 수정하고 Supabase 우선 사용으로 변경
  - 사이드바를 `로그인 계정 / 선택 계좌 / 페이지 이동 / 새 계좌 만들기` 구조로 재정리
  - 본문 상단에 계좌/페이지/저장소를 보여주는 컨텍스트 배너 추가
  - 대시보드 상단을 `헤더 / 우선순위 메트릭 / 시각화 / 관리 작업 / 분석 섹션` 흐름으로 재배치
  - 메트릭 카드를 `총자산·평가손익` 우선, `투입원금·현금·누적이자` 보조 구조로 분리
  - `자산 배분`, `보유 종목 수익률`, `시장 업데이트`, `현금 조정`, `보유 종목`, `추이`를 카드형 섹션으로 정리
- 남은 내용:
  - 거래 화면 카드화 여부와 밀도 재조정
  - 데이터 화면 운영자 액션 링크 보강
  - 상태 패널의 운영자 액션 링크 보강

### 7단계. 테스트/운영 검증

- 상태: 부분 완료
- 완료된 내용:
  - `py_compile` 검증
  - 로컬 SQLite 마이그레이션/이체/롤업 수동 검증
  - 웹 로그인 검증
  - 데이터 화면의 실제 렌더링 확인
- 남은 내용:
  - 자동 회귀 테스트 추가
  - Streamlit Cloud 최신 커밋 재배포 확인
  - Supabase 운영 전환 후 재검증

## 원격 반영 이력

- `e4cdfd9`: 원장/롤업/이체/운영 자동화 1차 반영
- `2b839b7`: 데이터 화면 `운영 상태` 패널 추가
- `09814cc`: 배포 환경에서 `Supabase`를 우선 사용하도록 백엔드 선택 로직 수정

## 현재 운영 상태

- 원격 `main`에는 `09814cc`까지 반영됨
- 웹 앱 로그인은 검증됨
- 다만 2026-05-08 기준 배포 웹은 아직 이전 빌드를 보고 있어 `로컬 SQLite`로 표시됨
- 따라서 다음 실제 운영 체크포인트는 `Streamlit Cloud 재배포 반영 여부` 확인이다

## 현재 작업 트리 메모

- 커밋되지 않은 진행 중 작업:
  - [app.py](/C:/Users/JKKIM/retirement-portfolio-streamlit/app.py)
  - [docs/progress-memory.md](/C:/Users/JKKIM/retirement-portfolio-streamlit/docs/progress-memory.md)
  - [scripts/verify_streamlit_deployment.py](/C:/Users/JKKIM/retirement-portfolio-streamlit/scripts/verify_streamlit_deployment.py)
  - [README.md](/C:/Users/JKKIM/retirement-portfolio-streamlit/README.md)
- 용도:
  - 대시보드 우선 UI 정리와 진행 메모 업데이트 반영
  - 배포된 웹 앱에 로그인해서 `데이터 > 운영 상태`를 자동 점검하는 스크립트 추가 중
  - 앞으로 배포 후 검증을 반복 가능하게 만들기 위한 작업

## 다음 권장 순서

1. `verify_streamlit_deployment.py` 마무리 및 커밋
2. Streamlit Cloud 최신 커밋 반영 여부 재확인
3. 반영 후에도 `SQLite`면 Streamlit secrets와 Supabase 스키마/RLS/Data API 노출 상태 점검
4. 운영 전환이 끝나면 5단계 잔여 분석 계산 고도화 진행

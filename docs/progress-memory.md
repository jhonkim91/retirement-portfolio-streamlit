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
  - `운영 상태` 패널에 `SUPABASE_URL/SUPABASE_KEY` 존재 여부, 설정 출처(secret/env/default/missing), 프로젝트 호스트, 누락 설정 안내 추가
- 남은 내용:
  - 거래 화면 카드화 여부와 밀도 재조정
  - 데이터 화면 운영자 액션 링크 보강

### 7단계. 테스트/운영 검증

- 상태: 부분 완료
- 완료된 내용:
  - `py_compile` 검증
  - 로컬 SQLite 마이그레이션/이체/롤업 수동 검증
  - 웹 로그인 검증
  - 데이터 화면의 실제 렌더링 확인
  - `scripts/verify_streamlit_deployment.py`로 로그인 후 `데이터 > 운영 상태` 자동 점검 가능 상태까지 안정화
- 남은 내용:
  - 자동 회귀 테스트 추가
  - Streamlit Cloud 최신 커밋 재배포 확인
  - Supabase 운영 전환 후 재검증

## 원격 반영 이력

- `e4cdfd9`: 원장/롤업/이체/운영 자동화 1차 반영
- `2b839b7`: 데이터 화면 `운영 상태` 패널 추가
- `09814cc`: 배포 환경에서 `Supabase`를 우선 사용하도록 백엔드 선택 로직 수정
- `4cb0a9a`: 사이드바와 대시보드 레이아웃 정리, 컨텍스트 배너 추가
- `83af6df`: 배포 웹 자동 점검 스크립트 추가 및 진행 메모 갱신
- 작업 중: 운영 상태 진단 세분화와 auth/db 설정 읽기 동적화
- 작업 중: Supabase 전환 후 온보딩 화면까지 인식하는 배포 검증 보강
- 작업 중: 로컬 SQLite -> Supabase dry-run 마이그레이션 스크립트 정리와 기존 이관 스크립트 보안 정리
- 작업 중: 초기 온보딩 화면용 데모 모드 버튼과 샘플 데이터 시드 기능 추가

## 현재 운영 상태

- 원격 `main`에는 `83af6df`까지 반영됨
- 웹 앱 로그인은 검증됨
- 2026-05-08 초기 자동 검증 결과 `데이터 저장소=로컬 SQLite`, `Supabase 설정 감지=아니오`, `이자 롤업=0건`, `자산 스냅샷=0건`
- 2026-05-08 재검증에서 새 사이드바/컨텍스트 배너/UI 문구가 배포 웹에 반영된 것까지 확인됨
- 이후 재검증에서 배포 웹이 `현재 저장소: Supabase` 온보딩 화면으로 전환된 것까지 확인됨
- 따라서 `Streamlit secrets/Supabase 연결` 자체는 반영된 것으로 보이며, 기존 `SQLite` 병목은 해소된 상태다
- 현재 실제 상태는 `Supabase 연결 완료 + 아직 첫 계좌가 없는 신규 온보딩 화면`이다
- 로컬 코드 기준 진단은 `SUPABASE_URL=default`, `SUPABASE_KEY=missing`일 때 이유를 별도 표기하도록 보강 완료
- 로컬 SQLite dry-run 기준 이관 대상은 `계좌 4개 / 보유종목 6개 / 거래기록 58개 / 일별 이자 0개 / 스냅샷 0개`다
- 데모 모드는 `데모 IRP`, `데모 일반계좌`와 입금/매수/이자/이체/스냅샷 예시를 한 번에 생성하도록 구현 중이다
- 데모 버튼 실검증 중 `Supabase 쓰기 403` 뒤 `SQLite fallback`이 발생해, 인증 토큰 재확인과 `401/403 fallback 금지` 수정까지 추가 진행 중이다
- 계좌 이름 접두사도 `session user_id` 대신 JWT `sub` 우선 기준으로 맞추도록 보강 중이다
- 따라서 다음 실제 운영 체크포인트는 `첫 계좌 생성 또는 초기 데이터 이관 여부 결정`과 `그 이후 데이터/롤업 재검증`이다

## 현재 작업 트리 메모

- 커밋되지 않은 진행 중 작업:
  - [README.md](/C:/Users/JKKIM/retirement-portfolio-streamlit/README.md)
  - 로컬 검증 산출물 PNG/TXT 파일들
- 용도:
  - `verify_streamlit_deployment.py`는 커밋 및 원격 반영 완료
  - 현재는 운영 secrets 정리 전까지 검증 기록과 보조 문서를 로컬에 유지하는 단계
  - `migrate_sqlite_to_supabase.py`는 dry-run 검증까지 완료했고, 실제 쓰기는 아직 실행하지 않음

## 다음 권장 순서

1. 운영 계정에 첫 계좌를 생성할지, 기존 데이터를 이관할지 결정
2. 쓰기 작업 승인 후 `migrate_sqlite_to_supabase.py --write` 또는 계좌 생성 진행
3. 그다음 `verify_streamlit_deployment.py --page data --expect-backend supabase`와 롤업 화면 재검증
4. 운영 전환이 끝나면 5단계 잔여 분석 계산 고도화 진행
## 2026-05-08 RLS hotfix memo

- Commit `70e281f`: reduced Supabase write response coupling by using `return=minimal` on writes and resolving account id with a follow-up read.
- Deployment check after that change: demo button still fails with `Supabase POST accounts ... 403 ... row-level security policy for table "accounts"`.
- Conclusion: the blocker is the production `accounts INSERT` RLS policy, not the write response format.
- Prepared SQL hotfix in `setup_supabase.sql`:
  - add `accounts.owner_user_id uuid references auth.users(id)`
  - backfill `owner_user_id` from existing `name` prefixes where possible
  - set `owner_user_id default auth.uid()`
  - add index on `owner_user_id`
  - switch all RLS policies from `split_part(name, '::', 1)` checks to `owner_user_id = auth.uid()`
- App-side error handling now maps this specific 403 to an actionable message that points to the `owner_user_id` hotfix.
- Next required action: apply the updated `setup_supabase.sql` in the production Supabase SQL editor, then rerun the demo/onboarding verification.

## 2026-05-08 verification tooling follow-up

- Added [supabase-owner-user-id-hotfix.sql](/C:/Users/JKKIM/retirement-portfolio-streamlit/docs/supabase-owner-user-id-hotfix.sql) as a focused production SQL patch for the current RLS blocker.
- Added [supabase-hotfix-runbook.md](/C:/Users/JKKIM/retirement-portfolio-streamlit/docs/supabase-hotfix-runbook.md) with the exact SQL Editor + redeploy verification sequence.
- Extended [verify_streamlit_deployment.py](/C:/Users/JKKIM/retirement-portfolio-streamlit/scripts/verify_streamlit_deployment.py) with `--click-demo` and output fields:
  - `onboarding_visible`
  - `onboarding_error`
  - `hotfix_required`
  - `demo_button_clicked`
  - `demo_seeded`
- This lets the next verification run distinguish between:
  - onboarding still blocked by RLS
  - onboarding screen visible but demo click not triggered
  - demo data seeded successfully and dashboard opened

## 2026-05-08 analytics step 5 follow-up

- Continued the pending stage 5 analytics work while the production Supabase RLS fix remains blocked.
- Updated [analytics.py](/C:/Users/JKKIM/retirement-portfolio-streamlit/src/analytics.py) so `account_summary()` now separates:
  - `total_principal`
  - `net_flow`
  - `total_interest`
  - `actual_profit_loss`
  - existing market-only holding P/L
- Updated snapshot trend enrichment so [snapshot_trend_frame](/C:/Users/JKKIM/retirement-portfolio-streamlit/src/analytics.py) derives cumulative principal / net flow / interest and actual performance from `trade_logs + daily_interest`.
- Updated the dashboard in [app.py](/C:/Users/JKKIM/retirement-portfolio-streamlit/app.py) to show:
  - `실제 성과`
  - `투입 원금`
  - `순유입`
  - snapshot trend tooltip support for `순유입` and `실제 성과`
- Local verification completed:
  - `python -m py_compile src/analytics.py app.py`
  - sample-data analytic check for account summary and snapshot trend cumulative flow behavior
- Commit `f4aa705` pushed to `origin/main`: `Refine performance and flow analytics`

## 2026-05-08 analytics regression tests

- Added [tests/test_analytics.py](/C:/Users/JKKIM/retirement-portfolio-streamlit/tests/test_analytics.py) with built-in `unittest` coverage for:
  - principal / net flow / interest / actual profit separation in `account_summary()`
  - fallback behavior when capital-flow history is missing
  - cumulative snapshot trend enrichment in `snapshot_trend_frame()`
- Verification completed:
  - `python -m unittest discover -s tests -p "test_*.py"`
  - `python -m py_compile src/analytics.py app.py tests/test_analytics.py`
- This closes the local regression gap for the phase 5 analytics changes.

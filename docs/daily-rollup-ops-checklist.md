# 일별 롤업 운영 체크리스트

## 목적

이 문서는 웹 반영 후 일별 이자 적립과 자산 스냅샷 배치를 안전하게 운영하기 위한 체크리스트다.

## 1. Supabase 스키마 반영

운영자가 Supabase SQL Editor에서 [setup_supabase.sql](/C:/Users/JKKIM/retirement-portfolio-streamlit/setup_supabase.sql)을 적용한다.

확인 포인트:

- `daily_interest` 테이블 생성
- `daily_account_snapshot` 테이블 생성
- `trade_logs`의 `cash_delta`, `event_group_id`, `counterparty_account_id`, `metadata_json` 컬럼 반영
- `GRANT`와 RLS 정책 반영

## 2. GitHub Actions 시크릿 설정

GitHub 저장소의 **Settings > Secrets and variables > Actions** 에 아래 값을 등록한다.

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

주의:

- `SUPABASE_SERVICE_ROLE_KEY`는 배치 전용이다.
- Streamlit 앱 시크릿에는 계속 `SUPABASE_KEY`만 둔다.

## 3. 수동 드라이런 점검

GitHub Actions의 `Daily Rollup` 워크플로를 수동 실행한다.

권장 입력:

- `backend = supabase`
- `dry_run = true`
- `target_date = 비움` 또는 점검할 날짜 입력
- `annual_rate = 0.05`

확인 포인트:

- 계좌 수가 정상 출력되는지
- 에러 없이 종료되는지
- 각 계좌별 `interest_added`, `cash_balance`, `market_value`, `total_value`가 출력되는지

## 4. 실제 반영 실행

드라이런이 정상이라면 같은 워크플로를 다시 실행한다.

권장 입력:

- `backend = supabase`
- `dry_run = false`
- `target_date = 비움` 또는 재처리 날짜 입력

확인 포인트:

- `mode=apply` 로그 확인
- 대상 날짜가 중복 적립되지 않는지 확인

## 5. 웹 앱 확인

웹 앱에서 아래 항목을 확인한다.

- 로그인 가능 여부
- 대시보드의 `누적 이자` 노출 여부
- `일별 자산 스냅샷 기준 추이를 표시하고 있습니다.` 문구 노출 여부
- 거래 화면의 계좌 간 이체 기록 저장 여부
- 데이터 화면에서 `daily_interest`, `daily_account_snapshot` 다운로드 가능 여부

## 6. 장애 시 우선 점검

- GitHub Actions 로그에서 `SUPABASE_SERVICE_ROLE_KEY` 누락 여부 확인
- Supabase에서 새 테이블이 Data API에 노출되는지 확인
- `daily_interest`, `daily_account_snapshot` RLS 정책 적용 여부 확인
- 같은 날짜에 이미 적립된 데이터가 있는지 확인

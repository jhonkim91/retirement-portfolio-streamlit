# Supabase Realtime Worker Runbook

이 문서는 운영 Supabase에서 `public.realtime_worker_status`, `public.realtime_price_ticks`가 없어 KIS live worker가 시작 직후 재연결만 반복할 때 적용하는 절차입니다.

## 1. SQL 적용

Supabase SQL Editor에서 아래 파일 내용을 그대로 실행합니다.

- [supabase-realtime-schema-hotfix.sql](/workspaces/retirement-portfolio-streamlit/docs/supabase-realtime-schema-hotfix.sql)

핵심 변경:

- `public.realtime_price_ticks` 테이블 생성
- `public.realtime_worker_status` 테이블 생성
- 두 테이블의 인덱스, `authenticated/service_role` 권한, RLS 정책 적용
- 마지막 줄에서 `NOTIFY pgrst, 'reload schema';` 실행

## 2. REST 재확인

SQL 적용 직후 아래 두 REST 경로가 `404 PGRST205`가 아닌 `200`으로 돌아오는지 확인합니다.

- `/rest/v1/realtime_worker_status?select=*&limit=1`
- `/rest/v1/realtime_price_ticks?select=*&limit=1`

만약 여전히 `404`면 Supabase SQL Editor에서 아래 SQL을 한 번 더 실행합니다.

```sql
select pg_notification_queue_usage();
notify pgrst, 'reload schema';
```

참고:

- Supabase 문서상 새 테이블/함수 반영이 PostgREST schema cache에 즉시 보이지 않을 때는 `NOTIFY pgrst, 'reload schema';`로 refresh 할 수 있습니다.
- notification queue 이슈가 있을 때는 `select pg_notification_queue_usage();` 실행으로 cache refresh를 유도할 수 있습니다.

## 3. live worker 실행

로컬 셸에 관리자 시크릿을 로드한 뒤 아래 명령을 실행합니다.

```powershell
$env:SUPABASE_URL = "https://your-project.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"
$env:KIS_APP_KEY = "your-kis-app-key"
$env:KIS_APP_SECRET = "your-kis-app-secret"
$env:KIS_ENV = "prod"
python scripts/run_kis_quote_worker.py --backend supabase
```

정상 기대값:

- 시작 로그에 `backend=supabase`
- 재연결 반복 없이 `KIS WebSocket 연결 완료: <N>개 종목 구독`
- 장중이면 `realtime_worker_status.last_quote_at`과 `realtime_price_ticks` 행이 증가

## 4. 앱/REST 후속 검증

1. `데이터 > 운영 상태`에서 `KIS WebSocket worker=connected` 확인
2. `마지막 quote 반영` 시각이 갱신되는지 확인
3. 필요하면 아래 명령으로 배포 화면을 재검증합니다.

```powershell
python scripts/verify_streamlit_deployment.py --page data --expect-backend supabase
```

주의:

- 장 시작 전, 장 종료 후, 휴장일에는 worker가 `connected`여도 quote tick이 `0`일 수 있습니다.
- 이 앱은 `public.accounts.owner_user_id` 기반 RLS를 전제로 하므로, 계좌 생성이 여전히 막히면 realtime 패치가 아니라 기존 accounts RLS 핫픽스를 먼저 봐야 합니다.

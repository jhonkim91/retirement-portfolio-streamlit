# Realtime Tick Retention Runbook

## 목적
- `realtime_price_ticks` 원본 tick 증가로 인한 Supabase DB 용량, 조회 속도, 대시보드 렌더링 저하를 방지한다.
- 기본 정책은 최근 7일 원본 tick 보관, 7~90일 1분/5분봉 보관, 90일 초과 일봉 보관이다.
- 실제 삭제는 `scripts/run_realtime_tick_retention.py --apply`를 명시한 경우에만 수행한다.

## 보존 정책
| 구간 | 보관 형태 | 기본값 |
| --- | --- | --- |
| 최근 원본 구간 | `realtime_price_ticks` 원본 tick | 7일 |
| 중기 구간 | `realtime_price_bars` 1분봉/5분봉 | 90일 |
| 장기 구간 | `realtime_price_bars` 일봉 | 삭제하지 않음 |

## 사전 조건
- `setup_supabase.sql`에 포함된 `public.realtime_price_bars` 테이블과 RLS 정책이 적용되어 있어야 한다.
- Supabase 운영 실행은 `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`가 필요하다.
- 서비스 롤 키는 배치/관리자 작업에만 사용하고 앱 UI나 문서에 실제 값을 기록하지 않는다.

## 로컬 점검
```powershell
python scripts/run_realtime_tick_retention.py --backend sqlite --as-of 2026-05-13T00:00:00
```

## 운영 dry-run
```powershell
$env:SUPABASE_URL = "https://your-project.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"
python scripts/run_realtime_tick_retention.py --backend supabase --timezone Asia/Seoul
```

## 운영 적용
```powershell
$env:SUPABASE_URL = "https://your-project.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"
python scripts/run_realtime_tick_retention.py --backend supabase --timezone Asia/Seoul --apply
```

## 조정 옵션
```powershell
python scripts/run_realtime_tick_retention.py `
  --backend supabase `
  --raw-retention-days 7 `
  --intraday-retention-days 90 `
  --daily-retention-days 365 `
  --timezone Asia/Seoul `
  --apply
```

- `--raw-retention-days`: 원본 tick 보관 기간이다. 기본값은 7일이다.
- `--intraday-retention-days`: 1분/5분봉 보관 기간이다. 기본값은 90일이다.
- `--daily-retention-days`: 일봉 삭제 기준이다. `0`이면 일봉은 삭제하지 않는다.
- `--intervals`: 기본값은 `1m,5m`이다.

## 운영 주기
- 권장 실행 시점은 한국 장 종료 후 또는 일별 스냅샷 이후다.
- 처음 운영 적용 전에는 반드시 dry-run 결과의 `raw_ticks_deleted` 대상 수와 생성될 `bars_*` 수를 확인한다.
- 자동화를 붙일 때도 최초 며칠은 dry-run 로그를 먼저 확인한 뒤 `--apply` 전환 여부를 결정한다.

# Supabase RLS Hotfix Runbook

이 문서는 운영 Supabase에서 `첫 계좌 만들기`와 `데모 데이터 불러오기`가 `accounts INSERT RLS 403`으로 막힐 때 적용하는 절차입니다.

## 1. SQL 적용

Supabase SQL Editor에서 아래 파일 내용을 그대로 실행합니다.

- [supabase-owner-user-id-hotfix.sql](/C:/Users/JKKIM/retirement-portfolio-streamlit/docs/supabase-owner-user-id-hotfix.sql)

핵심 변경:

- `public.accounts.owner_user_id` 추가
- 기존 `name` prefix에서 `owner_user_id` 백필
- `owner_user_id default auth.uid()` 설정
- 관련 RLS 정책을 `owner_user_id = auth.uid()` 기준으로 교체

## 2. 배포 재검증

핫픽스 적용 후 아래 명령으로 웹 배포본을 다시 검증합니다.

```powershell
python scripts/verify_streamlit_deployment.py `
  --email "jhonkim2025@gmail.com" `
  --password "854854" `
  --page dashboard `
  --expect-backend supabase `
  --click-demo `
  --screenshot playwright-demo-after-hotfix.png `
  --text-output playwright-demo-after-hotfix.txt
```

정상 기대값:

- `backend_storage_code = "supabase"`
- `demo_button_clicked = true`
- `demo_seeded = true`
- `hotfix_required = false`
- `onboarding_visible = false`

## 3. 후속 단계

데모 시드가 정상 동작하면 그다음 순서는 아래와 같습니다.

1. 필요하면 기존 SQLite 데이터 이관 실행
2. 데이터 화면에서 롤업/스냅샷 상태 재확인
3. 5단계 잔여 성과 계산 고도화 작업 재개

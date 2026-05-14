# Retirement Portfolio Streamlit

완전히 분리된 독립형 Streamlit 포트폴리오 앱입니다.

## 포함 기능

- 다중 계좌 생성
- 현금 입출금 기록
- 계좌 간 현금 이체 기록
- 매수/매도 기록과 자동 보유수량 반영
- 현재가 갱신과 수익률 계산
- 자산 배분 대시보드
- 실현손익 요약
- 일별 자산 스냅샷 저장
- 입금액 기준 일별 평가액 기록
- 로컬 SQLite 데이터 CSV 내보내기

## 기술 구조

- UI: `Streamlit`
- 저장소: `Supabase` 우선, 필요 시 로컬 `SQLite` fallback
- 시세: `KIS REST/WebSocket` 우선, 미지원 자산은 `yfinance` fallback
- 로컬 앱 데이터 파일: `data/portfolio.db`

## 로컬 실행

```powershell
cd <프로젝트_루트>
python -m pip install -r requirements.txt
streamlit run app.py
```

## 배포 메모

### Supabase 연동 (권장)

이 앱은 **Supabase PostgreSQL**을 사용하도록 수정되었습니다. 데이터를 영구 저장할 수 있습니다.

#### 1단계: Supabase 테이블 생성

1. https://app.supabase.com 에서 프로젝트 선택
2. **SQL Editor** > **New query** 클릭
3. `setup_supabase.sql` 파일의 모든 코드 복사 & 실행
4. 실행 완료 확인

#### 2단계: 시크릿 설정

Streamlit Community Cloud 배포 시 아래 값을 준비합니다.

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-public-key"
```

- 배포 화면의 **Advanced settings** > **Secrets** 에 바로 붙여넣을 수 있습니다.
- 이미 배포한 앱이라면 `Settings > Secrets` 에서 같은 값을 추가하면 됩니다.

#### 3단계: Streamlit Community Cloud에 배포

1. GitHub에 코드 업로드
2. https://share.streamlit.io 접속
3. 우측 상단 **Create app** 클릭
4. Repository: `jhonkim91/retirement-portfolio-streamlit`
5. Branch: `main`
6. Main file path: `app.py`
7. 필요하면 **Advanced settings** 에서 Python 버전과 Secrets 설정
8. **Deploy** 클릭

배포 URL은 기본적으로 `*.streamlit.app` 형식으로 생성됩니다.

---

### 배포 후 시크릿 추가 방법

이미 앱이 올라간 뒤라면 아래 순서로 시크릿을 추가할 수 있습니다.

1. https://share.streamlit.io 에서 대상 앱 열기
2. **Settings** > **Secrets** 이동
3. 다음 값 추가:
```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-public-key"
```
4. 저장 후 필요 시 **Reboot app** 또는 재배포

---

### 로컬 테스트 (Supabase 사용)

```powershell
# 환경 변수 설정
$env:SUPABASE_URL = "https://your-project.supabase.co"
$env:SUPABASE_KEY = "your-anon-public-key"

# 앱 실행
streamlit run app.py
```

### KIS 시세/실시간 설정

국내 종목 현재가와 섹터는 KIS Open API를 우선 사용하고, 자산배분 당일 추세는 full-day 분봉 확보를 위해 Naver 차트를 우선 사용합니다.

```powershell
$env:KIS_APP_KEY = "your-kis-app-key"
$env:KIS_APP_SECRET = "your-kis-app-secret"
$env:KIS_ENV = "prod"   # 또는 paper
streamlit run app.py
```

- `KIS_APP_KEY`, `KIS_APP_SECRET`이 있으면 국내주식/국내ETF 현재가는 KIS REST로 우선 조회합니다. 당일 추세는 Naver 차트가 비어 있을 때 KIS REST로 fallback 합니다.
- 대시보드 `실시간` 버튼은 KIS REST 우선으로 `holdings.current_price`, `price_updated_at`을 갱신합니다.
- 국내 개별주 섹터는 KIS 종목 마스터와 업종 코드 캐시를 기준으로 우선 분류하고, ETF/해외 자산은 기존 규칙을 fallback으로 유지합니다.

### KIS WebSocket worker

장중 자동 반영은 별도 worker 프로세스로 처리합니다.

```powershell
# Supabase service role 기준
$env:SUPABASE_URL = "https://your-project.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"
$env:KIS_APP_KEY = "your-kis-app-key"
$env:KIS_APP_SECRET = "your-kis-app-secret"
$env:KIS_ENV = "prod"
python scripts/run_kis_quote_worker.py --backend supabase
```

- worker는 현재 보유 중인 국내 종목 전체를 KIS WebSocket으로 구독합니다.
- 수신한 quote마다 `holdings.current_price`를 overwrite하고 `realtime_price_ticks` 이력 테이블에도 append 합니다.
- 현재 UI에서 데이터 탭은 제거되어 있습니다. worker 상태는 `realtime_worker_status` 저장소 값과 배포 검증 스크립트의 backend 결과로 확인합니다.

### 실시간 tick 보존 정책

`realtime_price_ticks`는 장중 worker 실행 시간에 비례해 빠르게 증가하므로, 운영 환경에서는 집계 후 원본을 정리합니다.

| 구간 | 보관 형태 | 기본 정책 |
| --- | --- | --- |
| 최근 원본 구간 | tick 원본 | 7일 |
| 중기 구간 | 1분봉/5분봉 | 90일 |
| 장기 구간 | 일봉 | 유지 또는 별도 보존 기간 지정 |

```powershell
# 기본은 dry-run
python scripts/run_realtime_tick_retention.py --backend supabase --timezone Asia/Seoul

# 검토 후 실제 집계/삭제 적용
python scripts/run_realtime_tick_retention.py --backend supabase --timezone Asia/Seoul --apply
```

상세 절차는 [docs/realtime-tick-retention-runbook.md](docs/realtime-tick-retention-runbook.md)를 기준으로 합니다.

### GitHub Actions로 장중 worker 자동 실행

별도 유료 worker를 두지 않을 경우, 저장소의 [`.github/workflows/kis-realtime-worker.yml`](.github/workflows/kis-realtime-worker.yml)로 한국 장중 세션을 둘로 나눠 자동 실행할 수 있습니다.

- 스케줄 1: `KST 09:00` 시작, 약 `175분`
- 스케줄 2: `KST 11:55` 시작, 약 `225분`
- 두 실행 모두 `timeout --signal=SIGINT`로 종료되어 worker 상태를 `stopped`로 남기도록 구성했습니다.

GitHub 저장소의 **Settings > Secrets and variables > Actions** 에 아래 시크릿을 추가하세요.

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
KIS_APP_KEY
KIS_APP_SECRET
KIS_ENV
```

- `KIS_ENV`를 비워두면 workflow는 기본값 `prod`로 실행합니다.
- 수동 실행은 **Actions > KIS Realtime Worker > Run workflow** 에서 `manual / morning / afternoon` 세그먼트를 선택해 바로 점검할 수 있습니다.
- 실행 후 workflow 로그 마지막 `post-check 요약 출력` 단계에서 `worker_status`, `realtime_price_ticks_count`를 확인할 수 있습니다.

### 일별 스냅샷 자동 실행

일별 자산 스냅샷과 입금액 기준 평가액 기록 저장은 GitHub Actions 워크플로 [`.github/workflows/daily-rollup.yml`](.github/workflows/daily-rollup.yml)로 자동 실행할 수 있습니다.

- 기본 스케줄: 한국 시간 기준 매일 00:10
- 실행 스크립트: `scripts/run_daily_rollup.py`
- 기본 처리 대상일: 실행 시점의 한국 시간 기준 전일
- `daily_account_snapshot`은 기존 총자산 스냅샷을 유지하고, `daily_valuation_snapshot`은 개인 입금과 회사 납입금을 합산한 입금 원금 기준 평가 이력을 별도로 저장합니다.
- 수동 실행 시 `dry_run=true`로 쓰기 없이 점검 가능

GitHub 저장소의 **Settings > Secrets and variables > Actions** 에 아래 시크릿을 추가하세요.

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
```

주의:

- `SUPABASE_KEY`는 앱 사용자용 키입니다.
- `SUPABASE_SERVICE_ROLE_KEY`는 배치/관리자 작업용 키이며 브라우저나 Streamlit 프론트엔드에 노출하면 안 됩니다.

수동 실행 예시는 아래와 같습니다.

```powershell
# SQLite 로컬 테스트
python scripts/run_daily_rollup.py --backend sqlite --date 2026-05-10 --timezone Asia/Seoul --dry-run

# Supabase 관리자 실행
$env:SUPABASE_URL = "https://your-project.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"
python scripts/run_daily_rollup.py --backend supabase --date 2026-05-10 --timezone Asia/Seoul --dry-run
```

---

### 구성 요소

- **UI**: Streamlit
- **데이터베이스**: Supabase (PostgreSQL)
- **시세**: KIS REST/WebSocket 우선, yfinance fallback
- **배포**: Streamlit Community Cloud

## 주의

- 한국 6자리 숫자 코드는 자동으로 `.KS`를 붙여 조회합니다.
- 코스닥/ETF/해외 종목은 Yahoo Finance 심볼을 직접 입력하는 편이 더 정확할 수 있습니다.
- `data/portfolio.db`는 `.gitignore`에 포함되어 있습니다.

## 배포 백엔드 참고

- 기본 백엔드 선택값은 `PORTFOLIO_BACKEND=auto`입니다.
- 코드에는 기본 Supabase 프로젝트 URL을 두지 않습니다. 환경별 `SUPABASE_URL`과 `SUPABASE_KEY`가 모두 있고 URL이 `https://*.supabase.co` 형식이면 앱은 기본적으로 `Supabase`를 우선 사용합니다.
- `PORTFOLIO_BACKEND=sqlite`가 설정되어 있으면 배포 환경에서도 로컬 SQLite를 강제로 사용하므로 운영 배포에서는 권장하지 않습니다.
- 현재 운영 UI는 대시보드, 거래, 평가액 기록 페이지를 노출합니다. 저장소 상태는 배포 검증 스크립트의 `backend_storage` 결과로 확인합니다.

## 웹 배포 검증

배포된 앱 로그인과 저장소 상태는 `scripts/verify_streamlit_deployment.py`로 자동 점검할 수 있습니다.

```powershell
python -m pip install playwright
python -m playwright install chromium

$env:STREAMLIT_VERIFY_EMAIL = "you@example.com"
$env:STREAMLIT_VERIFY_PASSWORD = "your-password"
python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase
```

- `--screenshot`을 주면 전체 화면 이미지를 저장합니다.
- `--text-output`을 주면 화면 본문 텍스트를 UTF-8로 저장합니다.
- 기대 저장소와 실제 저장소가 다르면 종료 코드 `2`를 반환합니다.
- 로그인 자격 증명이 없으면 종료 코드 `1`과 함께 `--email/--password ... 가 필요합니다.` 오류를 반환합니다.

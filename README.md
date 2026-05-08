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
- 일별 이자 적립 및 자산 스냅샷 저장
- 로컬 SQLite 데이터 CSV 내보내기

## 기술 구조

- UI: `Streamlit`
- 저장소: `Supabase` 우선, 필요 시 로컬 `SQLite` fallback
- 시세: `yfinance`
- 로컬 앱 데이터 파일: `data/portfolio.db`

## 로컬 실행

```powershell
cd C:\Users\JKKIM\retirement-portfolio-streamlit
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

### 일별 롤업 자동 실행

일별 이자 적립과 일별 자산 스냅샷 저장은 GitHub Actions 워크플로 [`.github/workflows/daily-rollup.yml`](.github/workflows/daily-rollup.yml)로 자동 실행할 수 있습니다.

- 기본 스케줄: 한국 시간 기준 매일 00:10
- 실행 스크립트: `scripts/run_daily_rollup.py`
- 기본 처리 대상일: 실행 시점의 한국 시간 기준 전일
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
python scripts/run_daily_rollup.py --backend sqlite --date 2026-05-10 --annual-rate 0.05 --timezone Asia/Seoul --dry-run

# Supabase 관리자 실행
$env:SUPABASE_URL = "https://your-project.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"
python scripts/run_daily_rollup.py --backend supabase --date 2026-05-10 --annual-rate 0.05 --timezone Asia/Seoul --dry-run
```

---

### 구성 요소

- **UI**: Streamlit
- **데이터베이스**: Supabase (PostgreSQL)
- **시세**: yfinance
- **배포**: Streamlit Community Cloud

## 주의

- 한국 6자리 숫자 코드는 자동으로 `.KS`를 붙여 조회합니다.
- 코스닥/ETF/해외 종목은 Yahoo Finance 심볼을 직접 입력하는 편이 더 정확할 수 있습니다.
- `data/portfolio.db`는 `.gitignore`에 포함되어 있습니다.

## 배포 백엔드 참고

- 기본 백엔드 선택값은 `PORTFOLIO_BACKEND=auto`입니다.
- `SUPABASE_URL`과 `SUPABASE_KEY`가 있으면 앱은 기본적으로 `Supabase`를 우선 사용합니다.
- `PORTFOLIO_BACKEND=sqlite`가 설정되어 있으면 배포 환경에서도 로컬 SQLite를 강제로 사용하므로 운영 배포에서는 권장하지 않습니다.
- 웹 앱의 `데이터 > 운영 상태` 패널에서 현재 저장소, Supabase 설정 감지 여부, 강제 백엔드 설정 여부를 바로 확인할 수 있습니다.

## 웹 배포 검증

배포된 앱 로그인과 저장소 상태는 `scripts/verify_streamlit_deployment.py`로 자동 점검할 수 있습니다.

```powershell
python -m pip install playwright
python -m playwright install chromium

$env:STREAMLIT_VERIFY_EMAIL = "you@example.com"
$env:STREAMLIT_VERIFY_PASSWORD = "your-password"
python scripts/verify_streamlit_deployment.py --page data --expect-backend supabase
```

- `--screenshot`을 주면 전체 화면 이미지를 저장합니다.
- `--text-output`을 주면 화면 본문 텍스트를 UTF-8로 저장합니다.
- 기대 저장소와 실제 저장소가 다르면 종료 코드 `2`를 반환합니다.
- 로그인 자격 증명이 없으면 종료 코드 `1`과 함께 `--email/--password ... 가 필요합니다.` 오류를 반환합니다.

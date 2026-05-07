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
- 저장소: 로컬 `SQLite`
- 시세: `yfinance`
- 앱 데이터 파일: `data/portfolio.db`

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

#### 2단계: 환경 변수 설정

Streamlit Cloud에 배포할 때:

1. https://share.streamlit.io 에서 앱 배포 후
2. **Settings** > **Secrets** 에서 다음 추가:
```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-public-key"
```

3. **Redeploy** 클릭

#### 3단계: Streamlit Cloud에 배포

1. GitHub에 코드 업로드 (위 방법 참고)
2. https://share.streamlit.io 접속
3. **New app** 클릭
4. Repository: `YOUR_USERNAME/retirement-portfolio-streamlit`
   Branch: `main`
   Main file path: `app.py`
5. **Deploy!** 클릭

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

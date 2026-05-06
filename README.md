# Retirement Portfolio Streamlit

완전히 분리된 독립형 Streamlit 포트폴리오 앱입니다.

## 포함 기능

- 다중 계좌 생성
- 현금 입출금 기록
- 매수/매도 기록과 자동 보유수량 반영
- 현재가 갱신과 수익률 계산
- 자산 배분 대시보드
- 실현손익 요약
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

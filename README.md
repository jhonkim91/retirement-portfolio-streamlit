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

이 앱은 기본적으로 로컬 SQLite를 사용합니다. 따라서 수정 데이터가 계속 유지되어야 한다면 영구 스토리지를 제공하는 환경이 더 적합합니다.

- 데모/개인 테스트용: Streamlit Community Cloud
- 데이터 유지가 필요한 운영용: Railway, Render, VM, Docker 호스팅

Streamlit Community Cloud 공식 문서:

- [Community Cloud overview](https://docs.streamlit.io/deploy/streamlit-community-cloud)
- [Deploy your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [App dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)

## 주의

- 한국 6자리 숫자 코드는 자동으로 `.KS`를 붙여 조회합니다.
- 코스닥/ETF/해외 종목은 Yahoo Finance 심볼을 직접 입력하는 편이 더 정확할 수 있습니다.
- `data/portfolio.db`는 `.gitignore`에 포함되어 있습니다.

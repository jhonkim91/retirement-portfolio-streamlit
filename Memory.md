# Memory.md

## 문서 목적
- 현재 프로젝트 상태와 다음 작업에 필요한 최소 정보만 유지한다.
- 상세 검증 이력은 `docs/VALIDATION.md`, 완료 변경 이력은 `docs/CHANGELOG.md`, 설계 결정은 `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-17`

## 작업 상태
- [x] 입금액 기준 평가액 기록, 거래 UI, Dashboard 스냅샷 우선 표시 기능 반영
- [x] 데모 자동 진입(`?demo=1`)과 데모 데이터 2계좌 구성을 보강
- [x] Dashboard 자산 배분 트리맵 예수금 중립색/수익률 라벨 개선 및 운영 배포
- [x] Streamlit UI 캡처 자동화와 거래/평가액 기록 페이지 캡처 확장
- [x] 대시보드 UI 개선 및 요약 카드/트렌드/거래 패널/차트 반응형 보강
- [x] 로그인/온보딩 화면의 Streamlit 기본 사이드바 컨테이너 숨김
- [x] 거래 상품 검색 결과 compact dropdown 및 자산 구분/거래일자 항상 표시 반영
- [ ] temporal normalize migration 실제 적용 전 운영 `realtime_price_bars` 테이블 생성/노출 여부 결정

## 프로젝트 개요
- 유형: `Python + Streamlit`
- 진입점: `app.py`
- 앱 코어: `src/ui/app_core.py`
- 공개 페이지: `pages/dashboard.py`, `pages/trades.py`, `pages/valuation.py`
- 저장소: `Supabase` 우선, 필요 시 `SQLite`
- 로컬 SQLite DB: `data/portfolio.db`
- 시세: `KIS REST/WebSocket` 우선, KRX/Naver fallback, 일부 `yfinance` fallback
- UI 설정: `.streamlit/config.toml`, `.streamlit/app.css`
- 배포 앱: `https://retirement-portfolio-app-nh2vq9ferqnpehsslbykbe.streamlit.app/`

## 최근 변경 파일
- `src/ui/app_core.py`: 상품 검색 결과 컨테이너의 border/height 박스를 제거하고 compact dropdown wrapper 및 자산 구분/거래일자/메모 3열 meta 영역을 적용.
- `.streamlit/app.css`: 상품 검색 결과 dropdown absolute 배치, 모바일 relative fallback, 자산 구분/거래일자/메모 compact 반응형 스타일 추가.
- `tests/test_app_dashboard.py`: 검색 dropdown 구조와 필수 입력 노출, CSS selector/속성 회귀 테스트 추가.
- `docs/VALIDATION.md`, `docs/CHANGELOG.md`, `Memory.md`: 이번 UI 변경 검증 결과와 `origin/main` 병합 상태를 반영.

## 핵심 설계 결정
- 기존 `account_summary`와 `daily_account_snapshot` 계산은 유지하고, 입금 기준 이력은 별도 `daily_valuation_snapshot`에 저장한다.
- `company_principal` 컬럼은 기존 스키마명을 유지하되 `employer_deposit`, `personal_deposit`, legacy `deposit`, `opening_cash`에서 일반 출금을 차감한 순입금 원금으로 계산한다.
- 매수 lot은 FIFO로 쌓고 매도는 FIFO 기준으로 잔여 수량과 잔여 매입원가를 차감한다.
- 과거 날짜 현금은 같은 날짜 `daily_account_snapshot.cash_balance`가 있으면 실제 현금을 사용하고, 없으면 거래 원장의 `cash_delta`를 누적한 원장 현금으로 fallback한다.
- 오늘 날짜는 `account.cash_balance`가 원장 현금과 원 단위로 맞을 때만 실제 현금으로 사용하고, 크게 다르면 원장 현금으로 fallback한다.
- 펀드성 코드(`K...`)는 수량을 좌수로 보고 기준가를 1,000좌당 가격으로 해석해 거래금액과 보유 평가액을 `좌수 * 기준가 / 1000`으로 계산한다.
- 거래 기록 삭제는 선택 id 목록을 세션에 저장하고, 선택 삭제 dialog에서 기존 `delete_trade_log()`와 평가액 기록 재계산 경로를 반복 호출한다.
- 선택 매수 삭제로 남은 매도 원장이 보유 수량을 음수로 만들 경우 해당 연관 매도 기록을 확인 dialog의 삭제 대상에 자동 포함한다.
- Dashboard 히어로의 `전일 대비` 값은 입금 대비 손익이 아니라 추이 데이터의 마지막 두 `total_value` 차이로 계산한다.
- Dashboard 자산 배분 트리맵에서 예수금은 투자 수익률이 없는 현금 자산으로 보고, `profit_rate=None`, `node_kind="cash"`, `FEARGREED_FLAT_COLOR` 회색 중립색으로 표시한다.
- 사이드바 계좌 카드에서는 계좌명만 표시하고 `연금(IRP/퇴직연금)` 유형 뱃지는 표시하지 않는다.
- `?demo=1`, `?demo=true`, `?demo=yes`, `?demo=demo`는 비로그인 사용자에게만 기존 데모 버튼과 같은 `start_demo_workspace_session()` 흐름을 자동 실행한다.
- UI 캡처 기본 URL은 `?demo=1&capture=1`을 사용한다. 캡처 스크립트가 로컬 앱을 직접 실행할 때는 `PORTFOLIO_BACKEND=sqlite`와 캡처 전용 SQLite 파일을 사용해 실제 사용자 데이터 캡처를 피한다.
- `scripts/capture_app.py --page all --viewport all`은 viewport별 같은 브라우저 세션에서 dashboard → trades → valuation 순서로 이동한다.
- 캡처 모드는 기본 기준일을 `2026-05-15`로 고정한다.
- 데모 워크스페이스는 `데모 IRP`(`retirement`)와 `데모 주식`(`brokerage`) 두 계좌만 생성한다.
- KIS WebSocket worker는 운영 중 `ping/pong timed out` 후 재연결할 수 있지만, 종료 신호 수신 시에는 WebSocket을 닫고 재연결 루프 대신 `stopped` 상태 저장 경로로 이동한다.
- realtime retention은 시간 범위 count/delete 성능을 우선해 `quote_time, id` 정렬 인덱스를 사용하고, 집계 정확도는 `aggregate_ticks()` 내부 정렬로 유지한다.

## 실행 명령
```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```
- 로컬호스트가 응답하지 않거나 파일 감시자 이슈가 있으면 다음처럼 실행한다.
```powershell
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.fileWatcherType none
```

## 최신 검증 결과
- 작업 범위: 거래 입력 > 상품 등록 검색 결과를 compact dropdown으로 변경하고 자산 구분/거래일자/메모를 항상 노출.
- 코드 검증: `python -m compileall app.py src scripts tests` 성공.
- 단위 검증: `python -m pytest tests/test_app_dashboard.py` 성공, 125 passed.
- 전체 검증: `python -m unittest discover -s tests -p "test_*.py"` 성공, 291 tests.
- UI 캡처 검증: `python scripts/capture_app.py --page trades --viewport desktop --strict`, `tablet --strict`, `mobile --strict` 모두 성공.
- 원격 PR 체크: GitHub Actions run `25991712602`의 `capture-ui` 성공.
- 확인 산출물: `artifacts/ui_captures/2026-05-17_125933/trades/desktop/blocks/03_trade_product_entry.png`, `artifacts/ui_captures/2026-05-17_130031/trades/tablet/blocks/03_trade_product_entry.png`, `artifacts/ui_captures/2026-05-17_130127/trades/mobile/blocks/03_trade_product_entry.png`.
- 운영 DB 데이터 수정은 수행하지 않았다.

## Git/GitHub 상태
- 기본 브랜치: `main`
- 작업 브랜치: `codex/ui-capture-automation`
- 이번 작업 커밋: `7c88a55 Refine trade product entry layout`
- PR: `https://github.com/jhonkim91/retirement-portfolio-streamlit/pull/1`
- 배포 방법: `main` 병합 후 `git push origin main` 또는 PR merge로 Streamlit Cloud 자동 재배포 트리거.
- `origin/main` 병합 충돌은 문서(`Memory.md`, `docs/CHANGELOG.md`, `docs/VALIDATION.md`) 중심으로 해결 중이며, 병합 완료 후 재검증과 push가 필요하다.
- 워크트리에는 이번 요청 전부터 `data/portfolio.db`, 로컬 도구 디렉터리, 캡처 산출물 등 여러 변경/미추적 파일이 함께 있었다.
- 커밋 시 요청 관련 파일만 선별하고 `data/portfolio.db`, `.local/`, `.playtools*/`, `.playwright-browsers/`, `.vscode/`, `artifacts/`, `data/kis_cache/` 등 로컬 산출물은 제외한다.

## 운영 시크릿 메모
- 앱용: `SUPABASE_URL`, `SUPABASE_KEY`
- 관리자/배치용: `SUPABASE_SERVICE_ROLE_KEY`
- KIS용: `KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_ENV`
- 배포 검증용: `STREAMLIT_VERIFY_EMAIL`, `STREAMLIT_VERIFY_PASSWORD`
- 실제 값은 `.streamlit/secrets.toml`, Streamlit Cloud secrets, GitHub Actions secrets, OS 환경 변수에만 둔다.

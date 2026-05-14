# Memory.md

## 문서 목적
- 현재 프로젝트 상태와 다음 작업에 필요한 최소 정보만 유지한다.
- 상세 검증 이력은 `docs/VALIDATION.md`, 완료 변경 이력은 `docs/CHANGELOG.md`, 설계 결정은 `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-14`

## 작업 상태
- [x] Streamlit 앱을 RetirementPort Soft Wealth 라이트 디자인으로 전환
- [x] Data 페이지 파일/기본 multipage/커스텀 사이드바/라우팅 노출 제거
- [x] Dashboard Hero, KPI 카드, Trades 3탭 구조 유지 및 밝은 핀테크 스타일 적용
- [x] `returns_chart.html` 목업 기준 Dashboard 보유 종목 수익률 차트, 전체/수익/손실 탭, 수익률순/금액순 정렬, 막대 overflow 방지 반영
- [x] `premium_ui.html` 목업 기준 거래 기록 카드, 필터, 흰색 테이블 내부, 흰색 CSV 버튼, 색상 매수/매도 배지, 수정/삭제 액션 배지, 민트 페이지네이션 스타일 반영
- [x] 거래/현금 입력, 저장, 조회, 분석, Supabase/SQLite fallback, CSV export helper 로직 보존
- [x] 로컬 테스트와 브라우저 검증 완료
- [x] `main` 배포 커밋 푸시 및 Streamlit Cloud dashboard/trades 원격 검증 완료
- [ ] KIS WebSocket worker 장시간 실행 중 재연결/상태 복구를 장중 운영 로그 기준으로 추가 점검
- [ ] 모바일 viewport에서 대시보드 트리맵/보유 종목 표 가독성 추가 확인
- [ ] 스냅샷 저장, CSV export, 운영 정리 작업의 로딩 상태 표시 누락 여부 점검
- [ ] Supabase SQL Editor에서 `setup_supabase.sql` 전체 또는 문제 정책 블록 재실행 확인

## 프로젝트 개요
- 유형: `Python + Streamlit`
- 진입점: `app.py`
- 앱 코어: `src/ui/app_core.py`
- 공개 페이지: `pages/dashboard.py`, `pages/trades.py`
- 저장소: `Supabase` 우선, 필요 시 `SQLite`
- 로컬 SQLite DB: `data/portfolio.db`
- 시세: `KIS REST/WebSocket` 우선, KRX/Naver fallback, 일부 `yfinance` fallback
- UI 설정: `.streamlit/config.toml`, `.streamlit/app.css`
- 배포 앱: `https://retirement-portfolio-app-nh2vq9ferqnpehsslbykbe.streamlit.app/`

## 최근 변경 파일
- `.streamlit/config.toml`: Soft Wealth 라이트 테마 색상 적용
- `.streamlit/app.css`: 화이트 사이드바, 아이보리 배경, 민트 활성 메뉴, Hero/KPI/거래 카드/거래 기록 프리미엄 테이블, 보유 종목 수익률 차트 wrapper 스타일 적용
- `src/ui/app_core.py`: Data 라우팅 제거, Soft Wealth 디자인 토큰, Dashboard Hero, returns_chart 기반 인터랙티브 수익률 차트, Trades 입력 순서, 거래 기록 필터/테이블/아이콘 액션/페이지네이션 helper 반영
- `pages/data.py`: 삭제 상태 유지
- `pages/dashboard.py`, `pages/trades.py`: Streamlit multipage 진입점 유지
- `tests/test_app_dashboard.py`: Soft Wealth 테마, Data 제거, 거래 기록 프리미엄 UI helper와 아이콘 액션 버튼 회귀 테스트 갱신
- `docs/VALIDATION.md`: 최신 검증 결과 갱신

## 핵심 설계 결정
- `PAGES == ("Dashboard", "Trades")`만 유지하고, `"Data"` 또는 알 수 없는 page name은 Dashboard로 fallback한다.
- Data UI는 제거했지만 `TABLE_LABELS`, `backend_status`, `export_dataframe_rows`, `build_data_export_table_html` 등 내부 helper는 보존한다.
- 거래 기록 화면 테이블은 목업 기준 `매입일`, `종목명`, `유형`, `단가`, `수량`, `총금액`, `수익률`, `액션` 순서를 사용한다.
- 거래 기록 페이지 크기는 목업과 맞춰 5건으로 유지한다.
- 거래 기록 필터의 자산 구분은 유지하되 화면 테이블 컬럼에서는 제외한다.
- Dashboard 보유 종목 수익률 차트는 `streamlit.components.v1.html`로 렌더링해 `전체/수익/손실` 필터와 `수익률순/금액순` 정렬을 클라이언트에서 즉시 전환한다.
- 수익률 차트 막대 좌표는 양수/음수 최대값을 별도 span으로 계산하고 `Math.min(width, 100 - left)`로 clamp해 차트 track 밖으로 벗어나지 않게 한다.
- 매수/매도/현금 흐름 저장 로직, 계좌 로직, DB fallback, 시세 조회, CSV export 로직은 변경하지 않는다.
- 전체 앱은 항상 밝은 Soft Wealth 테마를 유지하고 다크 자동 전환 CSS는 사용하지 않는다.

## 실행 명령
```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```
- 로컬호스트가 응답하지 않거나 파일 감시자 이슈가 있으면 다음처럼 실행한다.
```powershell
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.fileWatcherType none
```

## 권장 검증 명령
```powershell
python -m compileall app.py src scripts tests pages
python -m pytest tests/test_app_dashboard.py
python -m unittest discover -s tests -p "test_*.py"
```

## 최신 검증 결과
- `python -m compileall app.py src scripts tests pages` 성공
- `python -m pytest tests/test_app_dashboard.py` 성공, 77 tests
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 190 tests
- `git diff --check -- .streamlit/app.css src/ui/app_core.py tests/test_app_dashboard.py Memory.md docs/VALIDATION.md` 성공
- Streamlit 로컬 실행 검증: SQLite backend로 `127.0.0.1:8501` 실행 중이며 health `ok`
- 브라우저 검증: 수익률 차트 독립 컴포넌트에서 `손실` 탭 클릭 시 손실 종목만 표시, `금액순` 클릭 시 평가금액 내림차순 전환, 막대 overflow 없음, browser error 없음
- Playwright 검증: Data 메뉴 없음, 거래 기록 프리미엄 패널/CSV 버튼/날짜 범위/목업 헤더/5건 페이지네이션/매수·매도 배지/390px 모바일 overflow 없음/browser error 없음
- 최근 사용자 브라우저 확인 후 거래 기록 행 배경을 흰색으로 고정하고, CSV 버튼도 흰색으로 고정했다. 매수/매도 배지는 색상 유지.
- 거래 기록 패널 내부 Streamlit wrapper 배경을 흰색으로 강제해 행 사이에 연한 배경이 비치지 않도록 했다.
- 액션 셀 내부 `st.columns(2)` 구조를 제거하고 단일 flex 액션 컨테이너로 변경해 `수정`/`삭제` pill 배지가 한 줄로 보이도록 조정했다.
- Streamlit key class가 `stVerticalBlock` 자체에 붙는 경우까지 잡도록 self selector를 추가해 액션 컨테이너를 확실히 row 배치한다.
- 거래 기록 행 padding은 `6px 10px`로 줄여 목업에 가깝게 행간을 낮췄다.
- 페이지네이션 active 버튼은 검은색 대신 `#5DBB92` 민트로 표시한다.
- 브라우저 산출물: `artifacts/premium-trade-log-desktop.png`, `artifacts/premium-trade-log-mobile.png`, `artifacts/returns-chart-interactive-standalone.png`
- 현재 8501 Streamlit 서버는 사용자 확인을 위해 실행 상태로 유지 중
- 배포 커밋: `1a3d951` (`Apply Soft Wealth design and remove Data page`)
- 원격 배포 검증: Streamlit Cloud `dashboard`/`trades` 모두 로그인 성공, workspace 표시, Supabase backend 확인, `ok=true`
- 원격 검증 산출물: `artifacts/deploy-dashboard-latest.txt`, `artifacts/deploy-dashboard-latest.png`, `artifacts/deploy-trades-latest.txt`, `artifacts/deploy-trades-latest.png`

## Git/GitHub 상태
- 기본 브랜치: `main`
- `origin/main`에 배포 커밋 `1a3d951`을 push했다.
- 실제 PR 생성은 하지 않았다.
- 워크트리에는 이번 요청 전부터 `data/portfolio.db`, 문서, 산출물, 로컬 도구 디렉터리 등 여러 변경/미추적 파일이 있었다.
- 커밋 시 요청 관련 파일만 선별하고 `data/portfolio.db`, `.local/`, `.playtools*/`, `.playwright-browsers/`, `.vscode/`, `artifacts/`, `data/kis_cache/` 등 로컬 산출물은 제외한다.

## 운영 시크릿 메모
- 앱용: `SUPABASE_URL`, `SUPABASE_KEY`
- 관리자/배치용: `SUPABASE_SERVICE_ROLE_KEY`
- KIS용: `KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_ENV`
- 배포 검증용: `STREAMLIT_VERIFY_EMAIL`, `STREAMLIT_VERIFY_PASSWORD`
- 실제 값은 `.streamlit/secrets.toml`, Streamlit Cloud secrets, GitHub Actions secrets, OS 환경 변수에만 둔다.

## 남은 작업
1. 배포 후 실제 사용자 브라우저에서 Dashboard 수익률 차트 탭/정렬과 Trades 거래 기록 UI를 최종 육안 확인한다.
2. PR을 별도로 만들 경우 제목은 `Apply Soft Wealth design and remove Data page`를 사용한다.
3. PR 설명에는 Data 페이지 제거, Soft Wealth 테마 적용, 저장/분석/시세/거래 로직 보존, 테스트 갱신을 명시한다.

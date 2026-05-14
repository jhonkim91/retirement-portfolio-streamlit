# VALIDATION

## 문서 목적
- 최신 대표 검증 결과 1세트를 기록한다.
- 과거 상세 이력은 `docs/archive/`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-14`

## 최신 대표 검증 결과
- 작업 범위: RetirementPort Soft Wealth 라이트 디자인 적용, Data 페이지 제거, `premium_ui.html` 기준 거래 기록 프리미엄 UI 반영, `returns_chart.html` 기준 보유 종목 수익률 차트 반영
- 환경: 로컬 Python 3.11, Streamlit, SQLite backend 검증
- 서버 실행:
```bash
env -u SUPABASE_URL -u SUPABASE_KEY -u SUPABASE_SERVICE_ROLE_KEY \
  PORTFOLIO_BACKEND=sqlite \
  RETIREMENT_DB_PATH=/tmp/retirement-portfolio-trade-log-premium.db \
  streamlit run app.py \
  --server.port 8553 \
  --server.address 127.0.0.1 \
  --server.headless true \
  --server.fileWatcherType none
```
- 브라우저 검증 후 8501 포트를 같은 포트로 재시작해 최신 CSS를 반영했다.

## 명령 검증
- `python -m compileall app.py src scripts tests pages` 성공
- `python -m pytest tests/test_app_dashboard.py` 성공, 77 tests
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 190 tests
- `git diff --check -- .streamlit/app.css src/ui/app_core.py tests/test_app_dashboard.py Memory.md docs/VALIDATION.md` 성공
- `curl -sS --max-time 5 http://127.0.0.1:8501/_stcore/health` 결과 `ok`

## 브라우저 검증
- 사이드바와 Streamlit 기본 multipage에 Data 메뉴 없음
- Dashboard Soft Wealth Hero/KPI 렌더링 유지
- Dashboard 보유 종목 수익률 차트는 `returns_chart.html` 스타일의 카드/필터/요약/막대/범례 구조로 렌더링
- 수익률 차트 `전체`, `수익`, `손실` 필터 버튼 클릭 전환 확인
- 수익률 차트 `수익률순`, `금액순` 정렬 버튼 클릭 전환 확인
- 수익률 차트 양수/음수 막대가 track 영역 밖으로 벗어나지 않음
- Trades 탭 `거래 입력`, `거래 기록`, `실현 손익` 유지
- 거래 기록 카드에 `거래 기록` 제목과 `↓ CSV 내보내기` 버튼 표시
- 검색, 유형 필터, 자산 필터, 시작일, 종료일, `~` 날짜 범위 UI 표시
- 테이블 헤더가 `매입일`, `종목명`, `유형`, `단가`, `수량`, `총금액`, `수익률`, `액션` 순서로 표시
- 페이지당 5건 표시 및 `5 / ...건 표시 중` 페이지 요약 표시
- 매수/매도 배지와 양수/음수 수익률 색상 표시
- 거래 기록 카드 내부 행 배경은 흰색으로 고정
- 거래 기록 패널 내부 Streamlit wrapper 배경은 흰색으로 고정
- CSV 내보내기 버튼은 흰색 배경으로 고정
- 액션 버튼은 단일 flex 액션 컨테이너 안에서 `수정`/`삭제` pill 배지로 표시하고 한 줄 유지
- 액션 컨테이너 selector는 key class가 wrapper 또는 `stVerticalBlock` 자체에 붙는 경우를 모두 처리
- 거래 기록 행 padding은 `6px 10px`로 조정
- 페이지네이션 active 버튼은 검은색 대신 `#5DBB92` 민트로 표시
- 페이지네이션 컨트롤 표시
- 390px 모바일 viewport에서 가로 overflow 없음
- browser console error와 page error 없음

## 산출물
- `artifacts/premium-trade-log-desktop.png`
- `artifacts/premium-trade-log-mobile.png`
- `artifacts/returns-chart-interactive-standalone.png`

## 미수행 항목
- 원격 Streamlit Cloud 배포 검증은 수행하지 않았다.
- 커밋, push, 실제 PR 생성은 수행하지 않았다.

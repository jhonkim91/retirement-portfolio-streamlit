# CHANGELOG

## 기준
- 이 문서는 `Memory.md`에서 분리한 완료 변경 이력 요약이다.
- 날짜별 상세 로그 원문은 `docs/archive/memory-YYYY-MM-DD.md`에 보존했다.
- 정리 기준일은 `2026-05-15`이다.

## 최근 완료 변경 요약

### 2026-05-15
- temporal normalize migration 사전 점검.
  - 운영 Supabase project `iyszkybxostbjfzbbymq`에서 `migrations/2026-05-14_normalize_temporal_columns.sql` 대상 temporal 컬럼을 `pg_input_is_valid()` read-only SQL로 점검.
  - `accounts`, `holdings`, `trade_logs`, `daily_interest`, `daily_account_snapshot`, `realtime_price_ticks`, `realtime_worker_status` 대상 컬럼의 cast 실패 행이 없는 것을 확인.
  - 운영 DB에 `public.realtime_price_bars`가 아직 없어 migration 전체 적용 전 테이블 선행 적용 여부를 별도 주의 사항으로 기록.
- KIS WebSocket worker 장중 운영 로그 점검 및 종료 복구 보강.
  - 최신 GitHub Actions `KIS Realtime Worker` run `25845045857` 성공과 운영 Supabase tick 12,449건 저장을 확인.
  - 운영 로그에서 `ping/pong timed out` 후 5초 재연결과 구독 복구가 반복되는 것을 확인.
  - timeout 종료 신호가 WebSocket 오류 콜백으로 흡수된 뒤 재연결하다 `137`로 kill되는 흐름을 막기 위해 worker shutdown flag와 WebSocket close 처리를 추가.
  - GitHub Actions workflow의 timeout 신호를 `--signal=SIGINT`로 명시하고 worker 회귀 테스트를 추가.

### 2026-05-14
- RetirementPort Soft Wealth 라이트 디자인 적용.
  - Streamlit theme와 디자인 토큰을 아이보리 배경, 화이트 카드, 민트/블루/라벤더 포인트 중심으로 전환.
  - 다크 모드 자동 전환 CSS를 제거하고 `.soft-wealth-hero` 민트-블루 그라디언트 Hero를 대시보드 상단에 추가.
  - 대시보드 KPI를 입금 원금/보유 현금/평가 손익/목표 달성률 중심의 화이트 카드로 정리.
  - 거래 화면은 `거래 입력`, `거래 기록`, `실현 손익` 3탭 구조를 유지하면서 밝은 카드/테이블/미리보기 스타일로 재정리.
  - 저장소, 분석, 시세, 거래 저장/조회, CSV export helper 로직은 유지.
  - `python -m pytest tests/test_app_dashboard.py`, 전체 compileall/unittest, 로컬 Streamlit dashboard/trades, agent-browser 390px 검증 완료.
- 데이터 탭 제거.
  - `st.navigation`과 커스텀 사이드바에서 데이터 페이지 링크를 제거하고 대시보드/거래 2탭 구조로 전환.
  - `pages/data.py` 진입점 파일을 삭제해 직접 페이지 노출 경로도 제거.
  - 배포 검증 스크립트와 자동 검증 래퍼의 기본 대상/선택지를 dashboard/trades로 조정.

### 2026-05-13
- `ui 개선/report2.md` 기반 UI 개선.
  - 대시보드 KPI를 `현재 평가액` 와이드 카드 중심의 2행 계층형 구조로 변경하고 보유현금 비중 delta를 추가.
  - 실현손익 요약에 기간 필터, 총 실현손익/포지션 수/총 매도금액/실현 수익률 KPI, 월별 손익 차트, 상품별 Top 5 기여 목록을 추가.
  - 거래 기록에 상품 검색, 거래 유형, 자산군, 날짜 범위 필터와 필터 기준 CSV 다운로드, 결과 요약, `실현수익률` 컬럼, 10건 페이지네이션을 추가.
  - `realized_summary()`가 매도 거래와 수익률 표시를 연결할 수 있도록 `sell_log_id`를 반환.
  - `agent-browser` CLI `0.27.0`을 설치하고 로컬 데모 대시보드/거래 페이지를 1440px/820px/390px에서 검증.
  - 커밋 `9571ea9`를 `origin/main`에 push하고 Streamlit Cloud 운영 dashboard/trades 검증을 완료.
- 거래 페이지 UI/UX 단계별 패치.
  - 상품 등록 폼 흐름을 검색/코드/가격/수량 중심으로 정리하고 예상 매입금액 미리보기와 0원 저장 방지를 추가.
  - 현금 흐름 입력을 `st.tabs()`로 전환하고 빠른 금액 선택, 예상 원금 잔액 미리보기, 유형별 위젯 key 분리를 반영.
  - 사이드바 계좌 영역을 `내 계좌` 섹션으로 압축하고 새 계좌 popover와 계좌 삭제 확인 dialog를 추가.
  - 화면 목업 기준으로 사이드바 브랜드/페이지 링크, 상품 자동완성 라벨, 상품 코드 상태, `+ 상품 추가`, `✓ 입금 기록` 문구를 보정.
  - 거래 페이지 배포 검증 marker, 로컬 Streamlit frame fallback, 새 사이드바/온보딩 저장소 문구 파서를 보강.
  - 전체 compileall/unittest discover와 로컬 Streamlit 거래 페이지 1440px/700px/390px 브라우저 검증 완료.
- PC 보유 종목 모바일 카드 노출 hotfix.
  - 모바일 카드 wrapper를 inline `display:none`으로 기본 숨김 처리하고, `640px` 이하에서만 CSS `display:grid !important`로 표시.
  - PC 화면에서 기존 보유 종목 테이블 아래에 모바일 카드 텍스트가 노출되는 문제를 수정.
  - 대상 테스트, 전체 테스트, 로컬 Streamlit 1280px/390px 브라우저 검증 완료.
  - 커밋 `199c853` `Hide mobile holdings cards on desktop`를 `origin/main`에 push하고 Streamlit Cloud 운영 dashboard 검증 완료.
- 검증 완료 패치 묶음 배포.
  - 커밋 `d4e9813` `Improve realtime workflows and mobile holdings`를 `origin/main`에 push.
  - Streamlit Cloud 운영 dashboard 검증 성공: backend `Supabase`, `allocation_status=지연 데이터 표시 중`, `ok=true`.
- 모바일 보유 종목 카드 표시 보강.
  - 대시보드 현재 보유 종목 패널에서 데스크톱 11컬럼 테이블은 유지하고, `640px` 이하 모바일에서는 카드 리스트를 표시.
  - 카드 필드는 상품명, 코드, 자산군, 평가금액, 손익, 수익률, 수량, 현재가, 평단가로 제한하고 손익/수익률 색상은 기존 positive/negative class를 재사용.
  - 모바일 카드 HTML 테스트와 로컬 Streamlit 1280px/390px 브라우저 검증 완료.
- 자산배분 당일 추세 provider 보강.
  - 숫자 6자리 KRX 종목도 Naver full-day 분봉을 우선 사용해 알파뉴메릭 ETF/ETN과 동일한 당일 추세 경로를 타도록 조정.
  - Naver 차트가 비어 있을 때만 KIS/yfinance로 fallback하고, KIS fallback의 분봉 조회 시각은 현재 KST 정규장 범위로 제한.
  - provider 선택/KIS 시간 보정 회귀 테스트를 추가하고 전체 compileall/unittest discover 검증 완료.
- BUG-02 CSS surface 토큰 교체.
  - 우선 교체 대상 selector의 흰색 배경 하드코딩을 `var(--surface-strong)`과 `color-mix(...)` 기반으로 전환.
  - 인증 카드, 대시보드 패널, KPI 카드, holdings table, 주요 버튼/탭 surface 배경도 토큰 기반으로 정리.
  - 회귀 테스트와 전체 compileall/unittest discover 검증 완료.
- UG-01 CSS 파일 누락 안전장치.
  - `render_app_stylesheet()`가 `.streamlit/app.css` 읽기 실패 시 빈 문자열을 반환하도록 보강.
  - CSS 템플릿 누락 회귀 테스트를 추가하고 전체 compileall/unittest discover 검증 완료.
- DESIGN-05 은퇴/포트폴리오 팔레트 고급화.
  - Streamlit theme를 indigo/navy 기반 `#3B5BDB`, `#F6F8FB`, `#EEF2F7`, `#0F172A`로 변경.
  - `load_design_tokens()`의 brand/hero/status/chart 색상을 새 팔레트 기준으로 조정하고 fallback theme도 동기화.
  - 디자인 토큰/스타일시트 회귀 테스트와 전체 unittest discover 검증 완료.
- DESIGN-03 차트 패널 카드감 보강.
  - 자산 배분/선택 종목 트렌드/보유 종목/보유 종목 표 패널에 gradient surface, `--radius-xl`, `--shadow-card`, hidden overflow를 적용.
  - 각 패널 내부 Streamlit border wrapper는 transparent/no-border/no-shadow로 초기화해 카드 안 차트 느낌을 강화.
  - 대시보드 섹션 헤더 padding, title weight/size, caption size를 조정.
- DESIGN-04 KPI 카드 반응형 grid 보강.
  - `.dashboard-metric-strip`를 `1180px` 이하 3열, `820px` 이하 2열, `560px` 이하 1열로 전환.
  - 좁은 화면에서 대시보드 섹션 헤더 상태 영역을 세로 정렬하고, 모바일 카드 높이와 본문 좌우 padding을 보정.
  - 로컬 단위 테스트와 Streamlit 데모 대시보드 1180/820/560px 브라우저 검증 완료.
- DESIGN-02 KPI 카드 시각적 위계 보강.
  - 대시보드 요약/metric 카드에 gradient surface, `--radius-xl`, `--shadow-card`, hover shadow, 상단 accent bar를 적용.
  - 카드 렌더러가 `dashboard-*-card--positive/negative/accent`와 `dashboard-*-card__delta`를 출력할 수 있도록 확장.
  - 수익률/손익 상태별 delta chip 색상 CSS를 분리하고 데모 대시보드 브라우저 검증 완료.
- CSS radius/shadow 디자인 토큰 교체.
  - `.streamlit/app.css` 상단 `:root`에 `--radius-*`, `--shadow-*` 토큰을 추가하고 `--panel-radius`를 `--radius-lg` 기준으로 변경.
  - 기존 `--card-shadow` CSS 변수 의존을 제거하고 공통 카드/패널 shadow를 `--shadow-soft`/`--shadow-card`로 전환.
  - 대시보드 요약 카드 기준 높이를 `128px`로 조정하고 스타일시트 회귀 테스트 갱신.
- realtime tick 보존/집계 정책 추가.
  - `realtime_price_bars` 스키마와 RLS 정책을 추가해 raw tick을 1분/5분/일봉으로 집계할 수 있게 함.
  - `scripts/run_realtime_tick_retention.py` 추가: 기본 dry-run, `--apply` 명시 시에만 집계 저장과 raw tick 삭제 수행.
  - SQLite/Supabase 공통 retention runbook과 회귀 테스트 추가.
- 실시간 worker/quote 상태 영역 fragment 갱신 보강.
  - 대시보드 기준시각, 자산 배분 상태 칩, 데이터 페이지 worker/마지막 quote metric을 `st.fragment(run_every="10s")`로 분리.
  - 대시보드 전체 자동 rerun fragment는 제거하고 상태 표시 조각만 독립 갱신하도록 범위 축소.
  - fragment 적용 범위 회귀 테스트와 전체 unittest discover 검증 완료.
- DESIGN-07 모바일 거래 페이지 2열 입력 영역 overflow 보강.
  - 거래/현금흐름 상위 2열을 `trade-form-cols` key 컨테이너로 감싸 CSS 적용 범위를 고정.
  - `max-width: 768px`에서 거래 입력 영역의 Streamlit horizontal block/column을 단일 컬럼으로 전환.
  - 스타일시트 회귀 테스트, 전체 unittest discover, 375px 로컬 브라우저 검증 완료.
- DESIGN-04 데이터 페이지 보유종목/거래기록 테이블 테마 통일.
  - `holdings`, `trade_logs` export preview를 `.holdings-table` HTML 테이블로 렌더링.
  - `accounts`, `daily_account_snapshot`, 원금 누적 기록은 기존 `st.dataframe` 표시 유지.
  - 로컬 Streamlit 데모 데이터 페이지 브라우저 검증과 전체 unittest discover 검증 완료.
- DESIGN-02 선택 종목 트렌드 컨트롤 1행 유지 보강.
  - 대시보드 기간 selectbox 라벨을 `1M`, `3M`, `6M`, `1Y`로 단축.
  - trend-controls column/select `min-width: 0` 규칙을 추가해 좁은 PC 화면폭에서 wrapping 가능성을 낮춤.
  - 스타일/라벨 회귀 테스트와 전체 unittest discover 검증 완료.
- DESIGN-01 상단 요약 카드 높이 정렬 보강.
  - `dashboard-summary-strip` 내부 horizontal block 직계 column을 Flexbox column으로 만들고 하위 wrapper를 `flex: 1`로 stretch.
  - 요약 카드 전용 `stVerticalBlockBorderWrapper` 높이 의존 규칙을 제거해 Streamlit DOM 계층 변화 영향을 줄임.
  - 스타일시트 회귀 테스트와 전체 unittest discover 검증 완료.
- DESIGN-05 거래유형 배지 스타일 보강.
  - `personal_deposit`, `employer_deposit`, `withdraw` 배지 색상 정의 추가.
  - 현금흐름 거래유형도 거래 기록 표에서 raw label이 아니라 컬러 배지 HTML로 렌더링.
  - 배지 스타일 회귀 테스트와 전체 unittest discover 검증 완료.
- DESIGN-03 자산 배분 트리맵 경계선/여백 정렬.
  - ECharts treemap `upperLabel` 높이와 글자 크기를 고정.
  - series/level/leaf `gapWidth=0`, `borderWidth=1`로 통일해 흰 여백을 줄이고 border로 경계를 표현.
  - 트리맵 옵션 회귀 테스트와 전체 unittest discover 검증 완료.
- BUG-03 거래기록 삭제 후 캐시 잔상 방지.
  - `delete_trade_log()` 성공 후 세션 refresh token과 Streamlit DB 조회 캐시를 함께 무효화.
  - 삭제 성공/실패 경로 단위 테스트 추가.
  - 로컬 compileall과 전체 unittest discover 검증 완료.
- `setup_supabase.sql` RLS 정책 재실행 안정화.
  - `holdings_update_own`, `daily_interest_update_own` 직전 `DROP POLICY IF EXISTS` 보강.
  - 정책 점검용 `pg_policies` 조회 주석 추가.
  - `tests/test_setup_supabase_sql.py` 회귀 테스트 추가.
  - 커밋: `5e2584b` `Harden Supabase policy setup reruns`.
- realtime worker `last_quote_at` 보존 패치.
  - `scripts/run_kis_quote_worker.py`, `src/db.py`, `src/sqlite_db.py`에서 quote 시각이 없을 때 기존 값을 보존.
  - 운영 Supabase 계좌 `24`, `25`, `26`의 `last_quote_at`를 최신 tick 기준으로 1회 복구.
  - 커밋: `aab9d67` `Preserve realtime worker last quote timestamps`.
- GitHub Actions `KIS Realtime Worker` manual run 검증 기록.
  - run `25771266167`, job `success`.
  - `ping/pong timed out` 후 재연결, 종료코드 `137`, workflow 결과 성공.
  - 커밋 기록: `437c4db`, `b293d0a`.

### 2026-05-12
- KRX 알파뉴메릭 ETF/ETN 종목의 당일/일봉 차트 fallback 보강.
  - `src/market.py`에 Naver `siseJson.naver` 기반 fallback 추가.
  - `0162Z0`, `0113D0` 분봉/일봉 fallback 테스트 추가.
  - 커밋: `a3d9285` `Fix KRX intraday chart fallback`.
- `review_report.md` 반영 상태 정리.
  - `st.navigation` 전환, DB/시세 TTL 캐시, `altair` 제한, KIS 재연결, hotfix 안내 비노출, 색상 상수 네임스페이스화 등 완료 상태 기록.
  - 모바일 레이아웃과 로딩 상태 표시는 추가 확인 필요 항목으로 남김.
- 대시보드/거래 UI 정리.
  - 거래/대시보드 2열 레이아웃, 실현손익 차트, 카드/트렌드 컨트롤 압축, 좌우 패널 높이 정렬 반영.
  - 주요 커밋: `5de102e`, `0cb1796`, `1152639`.

### 2026-05-11
- 현금/데이터 정합성 점검 및 스냅샷 계산 수정.
  - 과거 현금 스냅샷 계산에서 기준일 이후 거래가 섞이는 문제 수정.
  - 계좌 생성일보다 과거로 입력된 거래도 스냅샷 계산에 반영.
- 보유현금 정책 변경.
  - 매수/매도 저장이 `cash_balance`를 자동 변경하지 않도록 수정.
  - 매수는 현금 부족과 무관하게 허용.
  - Supabase 음수 현금 helper 예외 경로 수정.
- 거래기록 수정/삭제 기능 추가.
  - `buy`, `sell`, `personal_deposit`, `employer_deposit`, `withdraw` 수정/삭제 지원.
  - paired event 성격의 이체/이자/레거시 현금조정은 미지원으로 남김.
- 대시보드 UI 개선.
  - 자산 배분 상태 칩, 보유 종목 표, 보유 종목 비율 막대, 선택 종목 당일 트렌드, 가격갱신 초 단위 표시 보강.
- 운영/배포 검증 스크립트 보강.
  - `scripts/verify_streamlit_deployment.py`에 `--storage-state`, `--debug-dir`, allocation status expectation 추가.
  - Actions `Node 24` 전환 경고 제거.

### 2026-05-10
- 자산 배분 트리맵을 `자산군 -> 섹터 -> 보유 종목` 구조로 확장.
- KIS 우선 섹터/시세 provider와 realtime quote worker 추가.
- Supabase realtime schema hotfix SQL과 worker runbook 추가.
- 로그인 카드 레이아웃과 데모 모드 진입 UX 정리.

### 2026-05-09
- Streamlit 로그인/데모/기본 UI 정리.
- 대시보드 카드 정렬과 브라우저 검증 경로 확보.
- README 비정상 텍스트와 예시 시크릿 정리.

## 날짜 오류 가능성 표시 항목
- 원본 `Memory.md`에는 `2026-05-15` 섹션이 있었다.
- 현재 기준일은 `2026-05-14`이므로 실제 작업일 오기 또는 시스템 날짜 오류 가능성이 있다.
- 해당 섹션의 주요 내용은 현재 git log와 파일 상태에는 존재한다.
- 상세 원문은 `docs/archive/memory-2026-05-15.md`에 별도 주의 문구와 함께 보존했다.

## 상세 원문 위치
- `docs/archive/memory-2026-05-11.md`
- `docs/archive/memory-2026-05-12.md`
- `docs/archive/memory-2026-05-13.md`
- `docs/archive/memory-2026-05-15.md`

# CHANGELOG

## 기준
- 이 문서는 `Memory.md`에서 분리한 완료 변경 이력 요약이다.
- 날짜별 상세 로그 원문은 `docs/archive/memory-YYYY-MM-DD.md`에 보존했다.
- 정리 기준일은 `2026-05-13`이다.
- `2026-05-15`로 기록된 섹션은 현재 기준일보다 뒤라 날짜 오류 가능성으로 표시한다.

## 최근 완료 변경 요약

### 2026-05-13
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
- 현재 기준일은 `2026-05-13`이므로 실제 작업일 오기 또는 시스템 날짜 오류 가능성이 있다.
- 해당 섹션의 주요 내용은 현재 git log와 파일 상태에는 존재한다.
- 상세 원문은 `docs/archive/memory-2026-05-15.md`에 별도 주의 문구와 함께 보존했다.

## 상세 원문 위치
- `docs/archive/memory-2026-05-11.md`
- `docs/archive/memory-2026-05-12.md`
- `docs/archive/memory-2026-05-13.md`
- `docs/archive/memory-2026-05-15.md`

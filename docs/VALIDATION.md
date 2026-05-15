# VALIDATION

## 문서 목적
- 최신 대표 검증 결과 1세트를 기록한다.
- 과거 상세 이력은 `docs/archive/`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-15`

## 최신 대표 검증 결과
- 작업 범위: 펀드성 코드(`K...`)의 1,000좌 기준가 정규화와 Dashboard/거래 UI 부분 조회 성능 개선
- 원인: 일부 보유 평가/거래 표시/저장 경로가 펀드 기준가를 일반 주식 단가처럼 `수량 * 가격`으로 계산해 금액이 1,000배 커질 수 있었다.
- 수정: 보유 평가액, 거래 총액 preview, 거래 기록 표시/CSV/delete preview, 선택 종목 당일 트렌드, Supabase/SQLite 거래 저장/수정 경로를 `좌수 * 기준가 / 1000` 기준으로 통일했다.
- 수정: 평가액 부분 재계산 시 계좌 스냅샷 조회도 영향 시작일 이후로 제한하고, ECharts 비활성 경로에서는 treemap intraday 상세 조회를 건너뛰도록 했다.
- 유지: 기존 운영 DB 데이터와 CSV/artifacts 파일은 직접 수정하지 않았다. 스키마 변경과 migration 추가도 없다.
- 환경: 로컬 Python 3.11, Streamlit bare mode 테스트 실행.

## 명령 검증
- `python -m unittest tests.test_analytics tests.test_app_dashboard tests.test_db` 성공, 181 tests
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 273 tests

## 검증 범위
- `holdings_frame()`/`account_summary()` 펀드 보유 평가액과 매입원가가 1,000좌 기준으로 계산되는지 검증
- 거래 총액 preview, 거래 기록 표기, CSV export, 삭제/수정 선택 label이 펀드 총액을 정규화하는지 검증
- 선택 종목 당일 트렌드의 `market_value`, `cost_basis`, `profit_loss`가 펀드 기준가 단위를 반영하는지 검증
- Supabase/SQLite 매수 및 수정 저장 경로에서 `total_amount`, `cash_delta`만 정규화하고 `avg_cost/current_price` 기준가는 유지하는지 검증
- 평가액 부분 재계산의 `list_account_snapshots(..., start_date=...)` 호출과 ECharts 비활성 시 treemap intraday 조회 생략을 검증

## 미수행 항목
- 운영 DB 데이터 직접 수정, 커밋, 푸시, 원격 배포 검증은 수행하지 않았다.

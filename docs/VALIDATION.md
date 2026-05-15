# VALIDATION

## 문서 목적
- 최신 대표 검증 결과 1세트를 기록한다.
- 과거 상세 이력은 `docs/archive/`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-15`

## 최신 대표 검증 결과
- 작업 범위: `valuation_snapshots_23.csv`, `trade_logs_23.csv` 기준 평가/실현손익 산식 재점검 및 중복 총액/종목코드 정규화 보정
- 원인: 같은 날짜/유형/종목/수량/단가의 거래가 원 단위 총액과 1,000배 수준 총액으로 중복 저장되어 교보악사파워인덱스, 신한퇴직연금TopsValue40 매수/매도 금액이 계산에 중복 반영될 수 있었다.
- 추가 원인: 국내 종목 코드가 `487240`과 `487240.KS`처럼 접미사 유무가 다르면 FIFO lot 매칭에서 다른 종목으로 처리될 수 있었다.
- 수정: 총액만 1,000배 수준으로 큰 중복 매수/매도 행은 평가 스냅샷과 실현손익 계산 입력에서 제외한다.
- 수정: 국내 종목 코드는 `.KS/.KQ` 접미사를 제거하고 숫자 코드는 6자리로 정규화해 같은 종목으로 매칭한다.
- 산출 파일: `artifacts/trade_logs_23_reconciled.csv`, `artifacts/valuation_snapshots_23_recalculated.csv`
- 환경: 로컬 Python 3.11, Streamlit bare mode 테스트 실행.

## 명령 검증
- `python -m compileall src/valuation.py src/analytics.py src/trade_log_filters.py tests/test_valuation.py tests/test_analytics.py` 성공
- `python -m unittest tests.test_valuation tests.test_analytics` 성공, 35 tests
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 257 tests

## 검증 범위
- 총액만 1,000배 수준으로 큰 중복 매수/매도 행이 평가 스냅샷의 원장 현금, 잔여 매입원가, 실현손익 계산에서 제외되는지 검증
- 국내 종목 코드의 `.KS/.KQ` 접미사 유무와 앞자리 0 차이가 FIFO 매칭을 깨지 않는지 검증
- `trade_logs_23.csv` 기준 제외 행과 교보악사파워인덱스 정정 실현손익을 산출 파일에 기록했는지 검증
- `valuation_snapshots_23.csv` 기준 현재 실제 보유현금 `17,449`원을 사용한 최신 보유 평가액을 산출 파일에 기록했는지 검증
- 전체 unittest suite가 기존 기능 회귀 없이 통과하는지 검증

## 미수행 항목
- 운영 거래 원장의 중복/비정상 거래 id 삭제 또는 수정은 destructive 작업이므로 수행하지 않았다.
- 운영 `daily_valuation_snapshot` 재작성은 운영 DB 파생 데이터 변경이므로 수행하지 않았다.
- 배포 후 원격 Streamlit 평가액 기록 페이지 검증은 아직 수행하지 않았다.

# VALIDATION

## 문서 목적
- 최신 대표 검증 결과 1세트를 기록한다.
- 과거 상세 이력은 `docs/archive/`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-15`

## 최신 대표 검증 결과
- 작업 범위: 거래 기록 생성/수정/삭제 후 평가액 기록 로딩 최적화
- 원인: 거래 1건 변경 후에도 전체 기간 가격 히스토리 조회와 전체 `daily_valuation_snapshot` 삭제/재저장이 동기 실행되어 Streamlit UI 로딩이 길어질 수 있었다.
- 수정: 평가 스냅샷 계산에 `output_start_date`를 추가해 원장 상태는 최초 입금일부터 누적하고, 반환/저장 스냅샷은 영향 시작일 이후로 제한한다.
- 수정: Supabase/SQLite `delete_valuation_snapshots(account_id, start_date=None)`를 지원해 시작일 이후 평가 스냅샷만 삭제한다.
- 수정: 거래 생성/수정/삭제/CSV import는 거래일 기준, 현금/가격 갱신은 오늘 기준으로 부분 재계산한다.
- 유지: 평가액 기록 페이지 수동 재계산과 daily rollup은 기존 전체 재계산을 유지한다.
- 환경: 로컬 Python 3.11, Streamlit bare mode 테스트 실행.

## 명령 검증
- `python -m compileall src/valuation.py src/db.py src/sqlite_db.py src/ui/app_core.py tests/test_valuation.py tests/test_db.py tests/test_app_dashboard.py` 성공
- `python -m unittest tests.test_valuation tests.test_db tests.test_app_dashboard` 성공, 175 tests
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 264 tests

## 검증 범위
- `output_start_date` 이전 거래가 원금/현금/FIFO lot 누적에는 반영되고 반환 스냅샷에서는 제외되는지 검증
- 과거 매수 lot이 부분 재계산 시작일 이후 매도 계산에 계속 반영되는지 검증
- SQLite 평가 스냅샷 부분 삭제가 시작일 이전 행을 보존하는지 검증
- Supabase 평가 스냅샷 부분 삭제가 `valuation_date=gte.<date>` 필터를 전달하는지 검증
- 거래 생성/수정/삭제/CSV import/현금/가격 갱신 UI 호출부가 영향 시작일을 전달하는지 검증
- 전체 unittest suite가 기존 기능 회귀 없이 통과하는지 검증

## 미수행 항목
- 커밋, 원격 push, Streamlit 운영 배포 검증은 명시 요청이 없어 수행하지 않았다.

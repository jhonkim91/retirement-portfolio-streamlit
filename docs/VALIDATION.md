# VALIDATION

## 문서 목적
- 최신 대표 검증 결과 1세트를 기록한다.
- 과거 상세 이력은 `docs/archive/`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-15`

## 최신 대표 검증 결과
- 작업 범위: 거래 기록 선택 삭제 UI/로직 추가
- 요구 사항: 거래 기록을 한 건씩 삭제하지 않고, 사용자가 선택한 여러 건을 한 번에 확인 후 삭제할 수 있게 한다.
- 수정: `src/ui/app_core.py` 거래 기록 표에 행 선택 체크박스, `현재 페이지 선택`, `선택 해제`, `선택 삭제` 액션을 추가했다.
- 삭제 처리: 선택 삭제 확인 dialog에서 선택 목록을 표시한 뒤 기존 `delete_trade_log()`와 평가액 기록 재계산 경로를 반복 호출한다.
- 삭제 순서: 매도/매수 종속성으로 인한 중간 상태 오류를 줄이기 위해 선택 거래를 `trade_date`, `id` 역순으로 삭제한다.
- 회귀 테스트: 선택 id 정규화, 체크박스 callback, 선택 삭제 dialog/source 연결을 `tests/test_app_dashboard.py`에 추가했다.
- 환경: 로컬 Python 3.11, Streamlit bare mode 테스트 실행.

## 명령 검증
- `python -m compileall src/ui/app_core.py tests/test_app_dashboard.py` 성공
- `python -m unittest tests.test_app_dashboard` 성공, 102 tests
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 247 tests

## 검증 범위
- 거래 기록 선택 id가 정수/중복/비정상 값이 섞여도 안전하게 정규화되는지 검증
- 행 체크박스 callback이 선택 삭제 id 목록을 추가/제거하는지 검증
- 거래 기록 화면 source에 행 선택, 선택 삭제 버튼, 선택 삭제 dialog 호출 경로가 포함되는지 검증
- 선택 삭제 dialog가 기존 `delete_trade_log()`와 `rebuild_valuation_snapshots_for_account(..., "trade_deleted")` 경로를 사용하는지 검증
- 전체 unittest suite가 기존 기능 회귀 없이 통과하는지 검증

## 미수행 항목
- 브라우저 수동 UI 검증과 원격 배포 검증은 이번 로컬 패치 범위에서 수행하지 않았다.

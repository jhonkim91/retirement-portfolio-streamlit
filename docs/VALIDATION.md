# VALIDATION

## 문서 목적
- 최신 대표 검증 결과 1세트를 기록한다.
- 과거 상세 이력은 `docs/archive/`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-15`

## 최신 대표 검증 결과
- 작업 범위: 거래 기록 선택 삭제 연관 매도 자동 포함 보강
- 원인: 선택한 매수 기록만 먼저 삭제하면 남아 있는 매도 기록 재계산 중 보유 수량이 음수가 되어 기존 단건 삭제 경로가 실패했다.
- 수정: 선택 삭제 실행 전 남은 매수/매도 원장을 replay해 음수 보유수량을 만드는 연관 매도 기록을 삭제 확인 대상에 자동 포함한다.
- 안전 장치: 기존 원장 자체가 이미 음수 보유수량을 만드는 상태면 선택 삭제 실행 버튼을 비활성화하고 오류를 안내한다.
- 삭제 처리: 확인 dialog에서 선택 항목과 자동 포함된 `연관 매도` 항목을 함께 표시한 뒤 기존 `delete_trade_log()`와 평가액 기록 재계산 경로를 사용한다.
- 삭제 순서: 매도/매수 종속성으로 인한 중간 상태 오류를 줄이기 위해 선택 거래를 `trade_date`, `id` 역순으로 삭제한다.
- 회귀 테스트: 연관 매도 자동 포함, 기존 불일치 원장 차단, 선택 삭제 dialog/source 연결을 `tests/test_app_dashboard.py`에 추가했다.
- 환경: 로컬 Python 3.11, Streamlit bare mode 테스트 실행.

## 명령 검증
- `python -m compileall src/ui/app_core.py tests/test_app_dashboard.py` 성공
- `python -m unittest tests.test_app_dashboard` 성공, 104 tests
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 249 tests
- `git push origin main` 성공, 배포 코드 커밋 `ddf61a2f939ae140f6c9da7ac7f52ea3e4f2f462`
- `python scripts/verify_streamlit_deployment.py --page trades --expect-backend supabase --wait-ms 30000 --text-output artifacts/deploy-verify-trades-dependent-sells-20260515-0328.txt --screenshot artifacts/deploy-verify-trades-dependent-sells-20260515-0328.png --debug-dir artifacts/deploy-verify-trades-dependent-sells-20260515-0328-debug` 성공

## 검증 범위
- 거래 기록 선택 id가 정수/중복/비정상 값이 섞여도 안전하게 정규화되는지 검증
- 행 체크박스 callback이 선택 삭제 id 목록을 추가/제거하는지 검증
- 선택 매수 삭제 시 남은 매도 원장이 음수 보유수량을 만들면 해당 매도 id가 삭제 대상에 포함되는지 검증
- 기존 원장 자체가 이미 불일치하면 선택 삭제 실행을 차단할 수 있는 plan을 반환하는지 검증
- 거래 기록 화면 source에 행 선택, 선택 삭제 버튼, 선택 삭제 dialog 호출 경로가 포함되는지 검증
- 선택 삭제 dialog가 기존 `delete_trade_log()`와 `rebuild_valuation_snapshots_for_account(..., "trade_deleted")` 경로를 사용하는지 검증
- 전체 unittest suite가 기존 기능 회귀 없이 통과하는지 검증
- 원격 Streamlit 거래 페이지가 로그인 후 Supabase backend로 로드되는지 검증

## 미수행 항목
- 브라우저에서 선택 삭제 버튼을 직접 클릭하는 수동 destructive 검증은 수행하지 않았다.

# VALIDATION

## 문서 목적
- 최신 대표 검증 결과 1세트를 기록한다.
- 과거 상세 이력은 `docs/archive/`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-15`

## 최신 대표 검증 결과
- 작업 범위: `?demo=1` URL query parameter 기반 데모 자동 진입
- 원인: 버튼 클릭과 Streamlit `session_state` 유지가 어려운 AI/자동 접근 도구는 기존 데모 버튼 흐름을 안정적으로 통과하지 못할 수 있었다.
- 수정: `src/ui/app_core.py`에 `maybe_enter_demo_from_query_param()`을 추가해 `?demo=1`, `true`, `yes`, `demo` 요청 시 비로그인 사용자만 기존 데모 진입 흐름을 실행한다.
- 수정: 자동 진입은 `start_demo_workspace_session()`을 재사용해 데모 로그인, 데모 데이터 seed, 선택 계좌 설정이 버튼 클릭과 동일하게 처리되도록 했다.
- 보안: 이미 인증된 사용자는 query parameter가 있어도 세션을 바꾸지 않는다. 새 시크릿, RLS, DB 스키마 변경은 없다.
- 확인: Supabase changelog에서 이번 작업과 직접 충돌하는 Auth breaking change는 확인되지 않았다.
- 환경: 로컬 Python 3.11, Streamlit bare mode 테스트 실행.

## 명령 검증
- `python -m unittest tests.test_app_dashboard` 성공, 116 tests
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 280 tests

## 검증 범위
- `is_demo_query_requested()`가 허용값과 거부값을 올바르게 판별하는지 검증
- 비로그인 상태에서 `?demo=1`이면 기존 데모 진입 흐름을 호출하는지 검증
- 이미 로그인한 사용자는 `?demo=1`이 있어도 데모 세션으로 전환하지 않는지 검증
- `main()`이 로그인 화면 렌더링 전에 query parameter를 처리하는지 검증

## 미수행 항목
- 로컬/운영 Streamlit 브라우저 화면 검증, 커밋, 배포는 수행하지 않았다.

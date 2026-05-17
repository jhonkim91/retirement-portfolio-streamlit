# VALIDATION

## 문서 목적
- 최신 대표 검증 결과 1세트를 기록한다.
- 과거 상세 이력은 `docs/archive/`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-17`

## 최신 대표 검증 결과
- 작업 범위: 초기 로그인/온보딩 화면의 Streamlit 기본 사이드바 노출 방지.
- 원인: `pages/` 기반 Streamlit 기본 사이드바가 인증 화면에서도 생성되는데, 기존 CSS는 `[data-testid="stSidebarNav"]`만 숨겨 사이드바 컨테이너가 남을 수 있었다.
- 수정: `.auth-page-shell` 또는 `.empty-state-shell`이 있는 화면에서 `[data-testid="stSidebar"]`, `[data-testid="stSidebarCollapsedControl"]`, `[data-testid="stSidebarNav"]`를 `display: none !important`로 숨긴다.
- 회귀 테스트: 인증/온보딩 화면용 사이드바 숨김 selector가 CSS 결과물에 포함되는지 `tests/test_app_dashboard.py`에서 고정했다.
- 환경: Python 3.11, Streamlit 로컬 서버 `http://localhost:8508`.

## 명령 검증
- CSS 중괄호 균형 확인 성공 (`{` 638개, `}` 638개)
- `python -m unittest tests.test_app_dashboard.ThemeStylesheetTests` 성공, 12 tests
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 281 tests
- 로컬 브라우저 확인 성공: 로그인 화면 본문 표시, error overlay 없음, `stSidebar` computed display `none`.
- 로컬 로그인 화면 확인 스크린샷: `/tmp/retirement-login-sidebar-hidden-main.png`

## 검증 범위
- 인증/온보딩 marker가 있는 화면에서 기본 사이드바 컨테이너와 접힘 컨트롤을 숨기는 CSS selector 검증.
- 로컬 Streamlit 로그인 화면에서 사이드바 DOM은 존재하더라도 computed display가 `none`인지 검증.

## 미수행 항목
- 운영 DB 데이터 직접 수정은 수행하지 않았다.
- 원격 Streamlit 배포 검증은 커밋/푸시 후 최신 결과로 갱신한다.

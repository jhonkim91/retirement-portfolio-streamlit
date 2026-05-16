# VALIDATION

## 문서 목적
- 최신 대표 검증 결과 1세트를 기록한다.
- 과거 상세 이력은 `docs/archive/`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-16`

## 최신 대표 검증 결과
- 작업 범위: Streamlit UI 캡처 자동화 추가
- 수정: 대시보드 주요 블록에 `capture_*` wrapper를 추가하고 `config/capture_blocks.yaml` 기준으로 Playwright PNG 캡처를 생성하도록 구현.
- 수정: `scripts/capture_app.py`는 로컬 Streamlit 자동 실행, 외부 URL 접속, desktop/tablet/mobile/all viewport, strict 모드, manifest 생성을 지원.
- 수정: 캡처 전 sidebar 기본 상태 고정, loading/spinner 대기, animation/transition 비활성화, 캡처 기준일 고정, selector 누락 상세 로그를 추가.
- 수정: `capture=1`에서는 데모 seed 기준일을 고정해 그래프 데이터와 테이블 행 구성이 반복 실행마다 흔들리지 않도록 보강.
- 수정: 캡처 모드 검증 중 발견된 기존 회귀(`src.auth` 기본 Supabase URL, `src.market` 누락 호환 함수)를 보정해 데모 화면 경고와 전체 테스트 실패를 제거.
- 확인: desktop/tablet/mobile 전체 viewport에서 full page와 7개 block PNG 및 manifest 생성 성공.
- 환경: Python 3.11, 로컬 Streamlit `http://127.0.0.1:8522`, 캡처 전용 SQLite `/tmp/retirement-ui-capture-8522.db`.

## 명령 검증
- `python -m pip install -r requirements-dev.txt` 성공
- `python -m playwright install chromium` 성공
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest tests.test_app_dashboard.DemoQueryParamTests tests.test_db.DemoWorkspaceSeedTests` 성공, 10 tests
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 285 tests
- `python scripts/capture_app.py --url "http://127.0.0.1:8522/?demo=1&capture=1" --viewport all --strict --out-dir artifacts/ui_captures --wait-ms 30000` 성공

## 산출물 확인
- 최신 대표 캡처: `artifacts/ui_captures/2026-05-16_144429/`
- `desktop`, `tablet`, `mobile` 각각 `full_page.png`, `blocks/01_header.png`~`07_recommendation_panel.png`, `manifest.json` 생성 확인.
- 각 manifest status는 `success`, `missing_selectors`는 빈 목록.
- 캡처 로그에서 sidebar 상태는 `desktop=expanded`, `tablet/mobile=collapsed`로 고정 확인.
- full page PNG를 육안 확인해 기준일 `2026.05.15 00:00` 표시와 주요 차트 렌더링을 확인.

## 미수행 항목
- 운영 Streamlit 배포, 운영 DB 데이터 직접 수정, GitHub Actions 원격 실행은 수행하지 않았다.

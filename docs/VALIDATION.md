# VALIDATION

## 문서 목적
- 최신 대표 검증 결과 1세트를 기록한다.
- 과거 상세 이력은 `docs/archive/`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-16`

## 최신 대표 검증 결과
- 작업 범위: 대시보드 요약 카드/선택 종목 트렌드 컨트롤/거래 입력 패널/실현손익 차트 반응형 보강
- 수정: Streamlit 1.55의 `class_name` 미지원에 맞춰 `key` + `horizontal=True` 기반 flex wrapper를 `dashboard-summary-strip`, `dashboard-trend-controls`, `trade-form-cols`에 적용.
- 수정: 상단 요약 카드 높이를 120px로 고정하고 flex wrapping, 라벨 ellipsis, ghost action slot 폭 고정을 보강.
- 수정: 선택 종목 트렌드 컨트롤은 desktop 한 줄 compact 배치, 860px 이하 세로 적층으로 정리.
- 수정: 거래 입력의 상품 등록/현금 흐름 패널은 desktop 2열, mobile 1열로 wrapping되도록 보강.
- 수정: 대시보드/거래 차트 높이를 560px 기준으로 통일하고 ECharts option에 높이 metadata를 부여해 렌더링 높이를 같은 값에서 읽도록 변경.
- 수정: 실현손익 막대 차트 양수/음수 색상을 `#2e7d32`/`#c62828`로 고정하고 bar label을 상단에 표시.
- 수정: UI Capture GitHub Actions가 job 로그 생성 전 실패한 상태를 확인하고 `actions/checkout@v4`, `actions/setup-python@v5` 안정 버전으로 고정.
- 수정: workflow job-level `env`에서 `${{ runner.temp }}` expression을 제거하고 `/tmp/portfolio-capture.db` 고정 경로로 변경.
- 환경: Python 3.11.

## 명령 검증
- CSS 중괄호 균형 확인 성공 (`{` 679개, `}` 679개)
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest tests.test_app_dashboard` 성공, 122 tests
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 288 tests
- `.github/workflows/ui-capture.yml` YAML 파싱 및 action version 확인 성공
- `.github/workflows/ui-capture.yml`에서 job-level `env`의 `runner.temp` expression 제거 확인 성공

## 산출물 확인
- 이번 변경은 레이아웃/CSS/차트 option/test 보강으로 신규 PNG 캡처 산출물은 생성하지 않았다.
- 직전 대표 캡처는 `artifacts/ui_captures/2026-05-16_162900/desktop/`이며, manifest status `success`, 누락 selector 없음.

## 미수행 항목
- 운영 Streamlit 배포와 운영 DB 데이터 직접 수정은 수행하지 않았다.
- 원격 GitHub Actions run `25968169216`, `25968290999`는 job 생성 전 실패했고, workflow action version과 job env expression 보정 후 재실행 대상이다.

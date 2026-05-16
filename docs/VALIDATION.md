# VALIDATION

## 문서 목적
- 최신 대표 검증 결과 1세트를 기록한다.
- 과거 상세 이력은 `docs/archive/`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-16`

## 최신 대표 검증 결과
- 작업 범위: 대시보드 UI 개선 로컬 반영 및 Streamlit UI 캡처 자동화 확장
- 확인: GitHub 원격에는 별도 디자인 패치 PR/커밋이 없어 참고안을 로컬에 직접 반영.
- 수정: 대시보드 전체 max-width, overview hero/card 높이, 기간 버튼, 카드 hover, 자산 배분/보유종목 패널 radius/shadow, treemap legend, 보유종목 테이블 대비/패딩을 조정.
- 수정: overview hero와 metric grid 컬럼 비율을 `(0.42, 0.58)`, `gap="medium"`으로 변경.
- 수정: 대시보드, 거래, 평가액 기록 페이지를 `--page dashboard|trades|valuation|all`로 선택 캡처하도록 확장.
- 수정: 거래 페이지 header와 평가액 기록 header/요약/차트/테이블에 캡처용 wrapper를 추가하고, 거래 탭 내부 블록은 `activate` 설정으로 탭 전환 후 캡처한다.
- 수정: 한 viewport 안에서는 같은 브라우저 세션으로 dashboard → trades → valuation 순서로 이동해 데모 seed 반복으로 선택 계좌 상태가 흔들리지 않도록 했다.
- 수정: tablet/mobile sidebar 링크와 Streamlit tab 전환은 force/DOM click fallback을 적용해 viewport 밖 판정과 tab underline overlay로 인한 실패를 방지했다.
- 수정: `capture=1` 거래 입력/현금 흐름 기본 날짜는 `PORTFOLIO_CAPTURE_REFERENCE_DATE` 기준일을 사용해 현재 날짜 변동을 제거했다.
- 확인: desktop/tablet/mobile 전체 viewport에서 dashboard/trades/valuation full page와 블록 PNG 및 manifest 생성 성공.
- 환경: Python 3.11, 로컬 Streamlit `http://127.0.0.1:8526`, 캡처 전용 SQLite `/tmp/retirement-ui-design-8526.db`.

## 명령 검증
- `python -m pip install -r requirements-dev.txt` 성공
- `python -m playwright install chromium` 성공
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest tests.test_app_dashboard` 성공, 121 tests
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 287 tests
- `python scripts/capture_app.py --url "http://127.0.0.1:8525/?demo=1&capture=1" --page all --viewport all --strict --out-dir artifacts/ui_captures --wait-ms 30000` 성공
- `python scripts/capture_app.py --url "http://127.0.0.1:8526/?demo=1&capture=1" --page dashboard --viewport desktop --strict --out-dir artifacts/ui_captures --wait-ms 30000` 성공

## 산출물 확인
- 최신 대표 캡처: `artifacts/ui_captures/2026-05-16_161602/`
- `dashboard`, `trades`, `valuation` 각각 `desktop`, `tablet`, `mobile` 아래 `full_page.png`, `blocks/*.png`, `manifest.json` 생성 확인.
- 9개 manifest status는 모두 `success`, `missing_selectors`는 모두 빈 목록.
- 대시보드 UI 개선 확인 캡처: `artifacts/ui_captures/2026-05-16_162900/desktop/`, manifest status `success`, 누락 selector 없음.
- 캡처 로그에서 sidebar 상태는 `desktop=expanded`, `tablet/mobile=collapsed`로 고정 확인.
- full page PNG를 육안 확인해 기준일 `2026.05.15 00:00`, 거래 입력일 `2026/05/15`, 주요 차트/테이블 렌더링을 확인.

## 미수행 항목
- 운영 Streamlit 배포, 운영 DB 데이터 직접 수정, GitHub Actions 원격 실행은 수행하지 않았다.

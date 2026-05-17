# VALIDATION

## 문서 목적
- 최신 대표 검증 결과 1세트를 기록한다.
- 과거 상세 이력은 `docs/archive/`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-17`

## 최신 대표 검증 결과
- 작업 범위: Dashboard Overview 상단 기간 버튼/KPI 카드 정렬 회귀 보정.
- 수정: Streamlit Cloud DOM 차이로 기간 버튼 래퍼가 히어로 밖 레이아웃 흐름을 차지하지 않도록 `.st-key-dashboard-overview-hero-shell` 하위 wrapper를 absolute overlay로 고정했다.
- CSS: KPI 카드 영역은 `.st-key-dashboard-overview-option2`로 scope를 제한해 4열 grid, 220px 높이, sparkline 표시를 후순위 override로 보정하고 tablet/mobile breakpoints를 추가했다.
- 회귀 테스트: `tests/test_app_dashboard.py`에서 기간 버튼 overlay selector, KPI 카드 height/grid/sparkline selector를 고정했다.
- 환경: Python 3.11, 로컬 Streamlit 서버 `http://localhost:8510`, GitHub Actions, Streamlit Cloud 운영 앱.

## 명령 검증
- `python -m compileall app.py src scripts tests` 성공
- `python -m pytest tests/test_app_dashboard.py` 성공, 125 passed
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 291 tests
- `python scripts/capture_app.py --url "http://localhost:8510/?demo=1&capture=1" --page dashboard --viewport desktop --strict --out-dir /tmp/dashboard-overview-final-desktop` 성공
- `python scripts/capture_app.py --url "http://localhost:8510/?demo=1&capture=1" --page dashboard --viewport tablet --strict --out-dir /tmp/dashboard-overview-final-check` 성공
- commit `83c3463` push 후 GitHub Actions run `25992989168`의 `UI Capture` 성공
- `python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase --screenshot /tmp/prod-dashboard-overview-after-fix.png --text-output /tmp/prod-dashboard-overview-after-fix.txt --debug-dir /tmp/prod-dashboard-overview-after-fix --click-demo --wait-ms 90000` 성공, `ok=true`, backend `Supabase`

## 산출물 확인
- desktop 대시보드 캡처: `/tmp/dashboard-overview-final-desktop/2026-05-17_140054/desktop/full_page.png`
- tablet 대시보드 캡처: `/tmp/dashboard-overview-final-check/2026-05-17_135933/tablet/full_page.png`
- 운영 대시보드 검증 스크린샷: `/tmp/prod-dashboard-overview-after-fix.png`
- 운영 대시보드 본문 텍스트: `/tmp/prod-dashboard-overview-after-fix.txt`
- 사용자 제공 운영 스크린샷에서 기간 버튼 히어로 내부 배치와 KPI 카드 정렬 정상화를 확인했다.

## 이전 운영 검증 유지 사항
- 거래 상품 검색 dropdown 및 자산 구분/거래일자/메모 항상 표시 변경은 `main`에서 운영 배포 검증 완료 상태다.
- Dashboard 자산 배분 트리맵 예수금 중립색은 `main`에서 운영 배포 검증 완료 상태다.
- 운영 Streamlit Cloud `?demo=1&capture=1` 대시보드에서 예수금 회색 표시를 확인했다.

## 참고 실패
- 운영 공개 데모 URL 대상 `python scripts/capture_app.py --url "https://retirement-portfolio-app-nh2vq9ferqnpehsslbykbe.streamlit.app/?demo=1&capture=1" --page trades --viewport desktop --strict`는 Streamlit Cloud shell 링크만 감지하고 앱 내부 `거래` 링크를 찾지 못해 실패했다.
- 같은 운영 앱은 로그인 기반 배포 검증에서 거래 페이지 본문과 Supabase backend가 정상 확인됐다.
- 로컬 dashboard mobile strict 캡처는 선택 계좌 불일치 안내 화면으로 진입해 selector 확인 전에 중단했다. 이번 수정 대상인 desktop/tablet 상단 Overview 정렬은 strict 캡처와 운영 스크린샷으로 확인했다.

## 미수행 항목
- 운영 DB 데이터 직접 수정은 수행하지 않았다.
- 운영 DB migration은 수행하지 않았다.

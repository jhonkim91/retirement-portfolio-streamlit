# VALIDATION

## 문서 목적
- 최신 대표 검증 결과 1세트를 기록한다.
- 과거 상세 이력은 `docs/archive/`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-17`

## 최신 대표 검증 결과
- 작업 범위: 거래 입력 > 상품 등록 검색 결과 compact dropdown 전환 및 자산 구분/거래일자/메모 항상 표시.
- 수정: `st.container(border=True, height=260, key="trade-search-suggestions")`를 제거하고 `trade-product-search-box`, `trade-search-suggestions`, `trade-product-meta` key 기반 구조로 정리했다.
- CSS: 검색 결과는 desktop에서 absolute dropdown, mobile에서 relative list로 표시하며, 자산 구분/거래일자/메모는 desktop 3열, mobile 1열로 배치한다.
- 회귀 테스트: `tests/test_app_dashboard.py`에서 compact dropdown source 구조와 관련 CSS selector/속성을 고정했다.
- 환경: Python 3.11, 로컬 Streamlit 서버 `http://localhost:8501`, GitHub Actions.

## 명령 검증
- `python -m compileall app.py src scripts tests` 성공
- `python -m pytest tests/test_app_dashboard.py` 성공, 125 passed
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 291 tests
- `python scripts/capture_app.py --page trades --viewport desktop --strict` 성공
- `python scripts/capture_app.py --page trades --viewport tablet --strict` 성공
- `python scripts/capture_app.py --page trades --viewport mobile --strict` 성공
- GitHub Actions run `25991712602`, `25991878887`, `25991879672`의 PR/branch `capture-ui` 성공
- PR #1 merge 후 `main` GitHub Actions run `25991986493`의 `UI Capture` 성공
- `python scripts/verify_streamlit_deployment.py --page trades --expect-backend supabase --screenshot /tmp/prod-trades-after-deploy.png --text-output /tmp/prod-trades-after-deploy.txt --debug-dir /tmp/prod-verify-trades --click-demo --wait-ms 60000` 성공, `ok=true`, backend `Supabase`

## 산출물 확인
- desktop 상품 등록 캡처: `artifacts/ui_captures/2026-05-17_125933/trades/desktop/blocks/03_trade_product_entry.png`
- tablet 상품 등록 캡처: `artifacts/ui_captures/2026-05-17_130031/trades/tablet/blocks/03_trade_product_entry.png`
- mobile 상품 등록 캡처: `artifacts/ui_captures/2026-05-17_130127/trades/mobile/blocks/03_trade_product_entry.png`
- 운영 거래 페이지 검증 스크린샷: `/tmp/prod-trades-after-deploy.png`
- 운영 거래 페이지 본문 텍스트: `/tmp/prod-trades-after-deploy.txt`

## 이전 운영 검증 유지 사항
- Dashboard 자산 배분 트리맵 예수금 중립색은 `main`에서 운영 배포 검증 완료 상태다.
- 운영 Streamlit Cloud `?demo=1&capture=1` 대시보드에서 예수금 회색 표시를 확인했다.

## 참고 실패
- 운영 공개 데모 URL 대상 `python scripts/capture_app.py --url "https://retirement-portfolio-app-nh2vq9ferqnpehsslbykbe.streamlit.app/?demo=1&capture=1" --page trades --viewport desktop --strict`는 Streamlit Cloud shell 링크만 감지하고 앱 내부 `거래` 링크를 찾지 못해 실패했다.
- 같은 운영 앱은 로그인 기반 배포 검증에서 거래 페이지 본문과 Supabase backend가 정상 확인됐다.

## 미수행 항목
- 운영 DB 데이터 직접 수정은 수행하지 않았다.
- 운영 DB migration은 수행하지 않았다.

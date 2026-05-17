# VALIDATION

## 문서 목적
- 최신 대표 검증 결과 1세트를 기록한다.
- 과거 상세 이력은 `docs/archive/`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`를 기준으로 확인한다.
- 기준일: `2026-05-17`

## 최신 대표 검증 결과
- 작업 범위: `preview.html` 기준 상품 등록 카드 스타일 동기화.
- 수정: 상품 등록 카드를 680px compact 카드로 정리하고, 검색 영역/선택 상품/상품 코드/금액 입력/예상 금액/저장 버튼을 preview 목업에 맞춰 재배치했다.
- 거래 유형: 기존 radio를 카드 우상단 segmented control로 이동했으며, 매수 활성은 파랑, 매도 활성은 빨강으로 표시한다.
- 수량 단위: `주` select 박스를 제거하고 수량 입력 박스 내부 우측에 inline 단위로 표시한다.
- 반응형: 768px 이하에서 상품 등록 헤더와 가격/수량 입력 줄이 모바일 폭에 맞게 재배치된다.
- 회귀 테스트: `tests/test_app_dashboard.py`에서 compact card/search dropdown/segmented control/inline unit CSS와 소스 구조를 고정했다.
- 환경: Python 3.11, 로컬 Streamlit 서버 `http://localhost:8510`.

## 명령 검증
- `python -m compileall app.py src scripts tests` 성공
- `python -m pytest tests/test_app_dashboard.py` 성공, 125 passed
- `python -m unittest discover -s tests -p "test_*.py"` 성공, 291 tests
- `python scripts/capture_app.py --url "http://localhost:8510/?demo=1&capture=1" --page trades --viewport desktop --strict --out-dir /tmp/trade-preview-final-8` 성공
- `python scripts/capture_app.py --url "http://localhost:8510/?demo=1&capture=1" --page trades --viewport tablet --strict --out-dir /tmp/trade-preview-final-8` 성공
- `python scripts/capture_app.py --url "http://localhost:8510/?demo=1&capture=1" --page trades --viewport mobile --strict --out-dir /tmp/trade-preview-final-8` 성공
- Playwright로 매도 segmented control 클릭 후 매도 활성 버튼이 흰 배경/빨간 글자로 렌더링되는 것을 확인.

## 산출물 확인
- desktop 상품 등록 블록: `/tmp/trade-preview-final-8/2026-05-17_153948/trades/desktop/blocks/03_trade_product_entry.png`
- tablet 상품 등록 블록: `/tmp/trade-preview-final-8/2026-05-17_153734/trades/tablet/blocks/03_trade_product_entry.png`
- mobile 상품 등록 블록: `/tmp/trade-preview-final-8/2026-05-17_153948/trades/mobile/blocks/03_trade_product_entry.png`
- 매도 segmented control 클릭 확인: `/tmp/trade-preview-sell-segment.png`

## 이전 운영 검증 유지 사항
- Dashboard Overview 상단 기간 버튼/KPI 카드 정렬 핫픽스는 `main`에서 운영 배포 검증 완료 상태다.
- 거래 상품 검색 dropdown 및 자산 구분/거래일자/메모 항상 표시 변경은 `main`에서 운영 배포 검증 완료 상태다.
- Dashboard 자산 배분 트리맵 예수금 중립색은 `main`에서 운영 배포 검증 완료 상태다.

## 참고 실패
- desktop/tablet/mobile 캡처를 동시에 3개 실행했을 때 desktop 1회가 초기 selector 대기 중 중단됐다. 같은 명령을 단독 재실행해 성공했다.
- 상품 등록 블록이 mobile viewport보다 길면 블록 PNG 상단 일부가 잘릴 수 있으나, full page 캡처와 실제 렌더링에서는 헤더/segmented control이 정상 표시된다.

## 미수행 항목
- 운영 DB 데이터 직접 수정은 수행하지 않았다.
- 운영 DB migration은 수행하지 않았다.

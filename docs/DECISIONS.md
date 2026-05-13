# DECISIONS

## 기준
- 이 문서는 `Memory.md`에서 분리한 중요한 설계 결정 요약이다.
- 정리 기준일은 `2026-05-13`이다.
- 상세 배경은 `docs/archive/memory-YYYY-MM-DD.md`와 `docs/CHANGELOG.md`를 참조한다.

## 앱 구조
- `app.py`는 얇은 엔트리포인트와 호환 레이어로 유지한다.
- 실제 앱 구현은 `src/ui/app_core.py`가 담당한다.
- `pages/dashboard.py`, `pages/trades.py`, `pages/data.py`는 `st.navigation` 기반 페이지 진입점으로 유지한다.
- 기존 테스트와 monkey patch 호환을 위해 `app.py` 공개 함수/상수 접근은 앱 코어로 위임한다.
- 무거운 의존성은 인증 화면 첫 렌더를 늦추지 않도록 가능한 지연 로드한다.

## 저장소와 데이터 정책
- 기본 저장소는 Supabase다.
- SQLite는 로컬 개발과 fallback 용도로 유지한다.
- `PORTFOLIO_BACKEND`, `SUPABASE_URL`, `SUPABASE_KEY` 설정에 따라 backend가 결정된다.
- 사용자별 DB 조회 캐시는 scope와 data refresh token을 포함해 쓰기 후 자동 무효화한다.
- 운영 DB 파괴적 변경과 데이터 삭제는 명시 요청 없이는 수행하지 않는다.

## 현금/거래 정책
- 보유현금은 거래 저장과 자동 연동하지 않는다.
- 보유현금은 사용자가 직접 최신화한 현재 잔액으로 취급한다.
- 매수는 현재 보유현금 부족 여부와 무관하게 저장을 허용한다.
- `cash_adjustment` 레거시 로그는 거래 화면에서 숨기고 원금/순유입 계산에서 제외한다.
- 보유현금은 자산 비중 표시에서 안전자산에 포함한다.
- 계좌 간 이체 UI와 데모 seed 이체 이벤트는 제거된 상태다.
- 거래기록 수정/삭제는 사용자 입력 로그 중심으로 지원한다.
- `transfer_in`, `transfer_out`, `interest`, `cash_adjustment` 편집은 paired event 정합성 때문에 현재 미지원이다.

## 시세와 realtime worker
- KIS REST/WebSocket을 우선 시세 공급원으로 사용한다.
- KIS 조회가 어려운 KRX 알파뉴메릭 ETF/ETN은 Naver chart fallback을 사용한다.
- 그 외 일부 경로는 `yfinance` fallback을 유지한다.
- realtime worker 상태 갱신 시 새 quote 시각이 없으면 기존 `last_quote_at`를 보존한다.
- quote 이력이 없는 계좌는 `last_quote_at=null`을 유지한다.
- GitHub Actions `KIS Realtime Worker`는 장중 `UTC 00:00`, `UTC 02:55` schedule을 기준으로 관리한다.

## UI와 디자인
- `.streamlit/config.toml`의 테마/서버 기본 설정은 요청이 없으면 변경하지 않는다.
- 전역 CSS는 `.streamlit/app.css`를 기준으로 관리한다.
- 외부 CDN 폰트 import는 제거하고 시스템 폰트 스택을 사용한다.
- 전역 차트 색상은 `ChartColors` dataclass와 `CHART_COLORS` 네임스페이스를 기준으로 관리한다.
- 자산 배분 트리맵은 `자산군 -> 섹터 -> 보유 종목` 구조를 유지한다.
- 대시보드 보유 종목 표는 손익/수익률 양수·음수·중립 스타일을 구분한다.
- 선택 종목 `당일` 트렌드는 자산 배분 카드의 금일 시세 마지막 값과 맞춘다.

## 의존성과 배포
- Streamlit Cloud Python 3.14에서 `altair>=5.4` import 문제가 확인되어 `altair>=5.3,<5.4`로 제한한다.
- `streamlit-keyup`, `streamlit-echarts`는 선택 fallback 없이 필수 의존성으로 취급한다.
- Supabase hotfix 상세 절차는 기본 비노출이며 `PORTFOLIO_SHOW_HOTFIX_GUIDE=true`일 때만 표시한다.
- `scripts/verify_streamlit_deployment.py`는 배포 검증의 우선 도구로 사용한다.
- 검증 실패 시 `--debug-dir` 산출물을 남겨 로그인 실패, 페이지 전환 실패, 배포 미반영을 구분한다.

## 문서 관리
- `Memory.md`는 현재 상태 요약 파일로 유지하고 장문 날짜별 로그를 누적하지 않는다.
- 날짜별 상세 로그는 `docs/archive/memory-YYYY-MM-DD.md`에 보존한다.
- 검증 상세는 `docs/VALIDATION.md`, 완료 변경 이력은 `docs/CHANGELOG.md`, 설계 결정은 `docs/DECISIONS.md`에 둔다.
- 원본 `2026-05-15` 섹션은 현재 기준일보다 뒤라 날짜 오류 가능성으로 별도 표시한다.

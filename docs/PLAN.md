# review_report.md 전체 반영 패치 계획

## 요약
- 사용자가 선택한 “전체 일괄” 범위로 진행한다.
- 현재 코드 기준으로 `DB/시세 TTL 캐시`와 `KIS WebSocket 재연결`은 이미 구현되어 있으므로 회귀 테스트와 상태 기록을 보강한다.
- `app.py`는 Streamlit 공식 권장 방식인 `st.Page` + `st.navigation` 구조로 분리한다. 참고: [Streamlit multipage docs](https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation).
- Altair는 보고서 권장값인 `altair>=5.4,<6`로 올린다. PyPI 기준 최신은 6.x지만, 이번 패치는 호환성 리스크를 줄이기 위해 5.x 범위에 머문다. 참고: [Altair PyPI](https://pypi.org/project/altair/).

## 주요 변경
- `app.py`를 라우터/공통 초기화 중심으로 줄이고, 화면 렌더링은 `pages/dashboard.py`, `pages/trades.py`, `pages/data.py`로 이동한다.
- 공통 UI/차트/폼 헬퍼는 `src/ui/` 하위 모듈로 분리한다.
- 기존 `active_page` 라디오 기반 페이지 전환을 제거하고 `st.navigation`으로 전환하되, 계좌 선택/로그인/데모 세션 상태는 기존 `st.session_state` 키를 유지한다.
- `requirements.txt`의 `altair==5.0.1`을 `altair>=5.4,<6`으로 변경한다.
- `render_operation_error()`의 Supabase hotfix 상세 절차는 기본적으로 숨기고, `PORTFOLIO_SHOW_HOTFIX_GUIDE=true`일 때만 표시한다.
- `TRADE_LOG_TABLE_COLUMN_WEIGHTS`는 컬럼명 기반 dict에서 파생되도록 바꾼다.
- 차트 색상 전역 상수는 `ChartColors` dataclass 또는 namespace로 묶고, 기존 테스트/호환성을 위해 필요한 기존 상수명은 alias로 유지한다.
- `st_keyup`, `st_echarts`는 필수 의존성으로 명확히 import하고, 누락 시 설치 안내가 포함된 명시적 오류를 발생시킨다.
- `.streamlit/app.css`에 시스템 다크모드 CSS 변수와 모바일 세로 스택 보강을 추가한다.
- `page_icon`은 앱 성격에 맞게 `💼`로 교체한다.
- 현재가 갱신, 스냅샷 저장, orphan cleanup 등 수 초 걸릴 수 있는 작업에 `st.status` 또는 `st.spinner`를 일관되게 적용한다.

## 검증 계획
- `python -m compileall app.py src scripts tests`
- `python -m unittest discover -s tests -p "test_*.py"`
- `python scripts/run_kis_quote_worker.py --backend sqlite --preflight-only`
- `streamlit run app.py` 로컬 기동 후 대시보드/거래/데이터 페이지 전환 확인
- 가능하면 `scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase`와 `--page trades`를 실행한다.
- `Memory.md`에 변경 파일, 검증 결과, 미완료 항목, 배포 여부를 기록한다.

## 가정
- 이번 패치는 보고서 12개 항목을 한 번에 반영하되, Supabase 스키마나 운영 DB 데이터는 변경하지 않는다.
- 기존 API와 테스트가 직접 참조하는 상수/함수명은 호환 alias를 두어 회귀를 줄인다.
- 현재 작업트리의 기존 변경 사항(`Memory.md`, `data/portfolio.db`, untracked 파일들)은 사용자 작업으로 간주하고 요청 범위 밖이면 건드리지 않는다.

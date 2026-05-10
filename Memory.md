# Memory.md

## 작업 기록
- [x] 프로젝트 구조 분석
- [x] 초기화 대상 파일 존재 여부 확인
- [x] 프로젝트 유형 판별
- [x] 기본 검증 수행
- [x] Memory.md 신규 생성
- [x] 대시보드 보유 현금 카드 높이 정렬
- [x] 보유 현금 카드 수정/취소 반응 개선
- [x] 상단 요약 카드 hover 색상 제거 및 높이 재정렬
- [x] 접속 화면 상단 제거 및 실시간 버튼 재배치
- [x] 상단 요약 카드 값 위치 정렬
- [x] Pylance import 경고 원인 확인 및 인터프리터 설정 정리
- [x] 로컬 Streamlit 브라우저 검증 및 Playwright 설치
- [x] README 시크릿/비정상 텍스트 정리
- [x] 데모 5년 거래 시드 확장 및 이자 적립 제거
- [x] Memory.md 기준 변경분 리뷰
- [x] 데모 계정 `test` 고정 및 데모 내부 계좌 리셋 재시드
- [x] 과거 스냅샷 재동기화와 레거시 이자 반영 복구

## 프로젝트 유형
- Python 프로젝트
- Streamlit 프로젝트
- Node.js 프로젝트 아님 (루트 `package.json` 미확인)
- 임베디드/펌웨어 프로젝트 아님 (루트 `Makefile`, `CMakeLists.txt`, `*.ioc`, `*.uvprojx` 미확인)
- 판별 근거: `requirements.txt`에 `streamlit` 존재, `.streamlit/config.toml` 존재

## 현재 확인된 주요 파일
- `AGENTS.md`
- `README.md`
- `requirements.txt`
- `.gitignore`
- `.env.example`
- `.streamlit/config.toml`
- `app.py`
- `src/db.py`
- `src/auth.py`
- `src/analytics.py`
- `src/sqlite_db.py`
- `scripts/run_daily_rollup.py`
- `scripts/verify_streamlit_deployment.py`
- `tests/test_db.py`
- `tests/test_auth.py`
- `tests/test_analytics.py`
- `tests/test_market.py`
- `tests/test_migrate_sqlite_to_supabase.py`
- `tests/test_verify_streamlit_deployment.py`

## 실행 방법
```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

## 생성한 파일 목록
- `Memory.md`

## 기존에 존재하던 파일 목록
- `AGENTS.md`
- `.gitignore`
- `README.md`
- `.env.example`

## 검증 가능 여부
- 가능
- `python -m compileall app.py src scripts tests` 성공
- `python -m unittest discover -s tests -p "test_*.py"` 성공
- 단위 테스트 `41`건 통과
- `.env` 파일은 생성하지 않음

## 현재 프로젝트 상태
- 상태 미확인
- 이유: 코드와 문서, 기본 검증 결과는 확인했지만 운영 상태나 사용자 의도 기준 완료 여부는 단정하지 않음

## 2026-05-09 대시보드 보유 현금 카드 높이 정렬
- 변경 파일: `app.py`, `Memory.md`
- 변경 내용:
  - `보유 현금` 카드의 표시용 `수정` 배지를 카드 마크업으로 옮기고, 실제 버튼은 절대 위치 오버레이로 분리
  - 오버레이 부모 `stLayoutWrapper`와 내부 `stElementContainer`가 카드 높이를 밀어 올리지 않도록 CSS 조정
  - `dashboard-summary-card__header` 높이와 여백을 줄여 다른 카드 라벨 높이와 맞춤
- 검증:
  - `python -m compileall app.py src scripts tests`
  - `python -m unittest discover -s tests -p "test_*.py"`
  - 로컬 SQLite 데모 모드 서버: `PORTFOLIO_BACKEND=sqlite` + 데모 자격 증명 비활성화 상태로 `8512` 포트 기동
  - Playwright headless로 데모 체험 진입 후 상단 카드 높이 측정
  - 결과: `입금 원금`, `보유 현금`, `현재 평가액`, `원금 대비 평가손익`, `원금 대비 수익률` 카드 높이 모두 `97.59375px`로 동일
  - 콘솔 오류 0건, 페이지 오류 0건
- 산출물:
  - `artifacts/dashboard-cash-card-height-local-demo-fixed-2.png`
  - `artifacts/dashboard-cash-card-height-local-demo-fixed-2.json`

## 2026-05-09 Pylance import 경고 확인
- 변경 파일: `.vscode/settings.json`, `.venv/pyvenv.cfg`, `Memory.md`
- 재현 조건:
  - VS Code Pylance가 `app.py` 상단 import에서 `altair`, `pandas`, `streamlit`, `dateutil.relativedelta`를 찾지 못한다고 표시
- 원인:
  - 시스템 Python(`/usr/local/bin/python`)에는 의존성이 설치되어 있었지만, 프로젝트 로컬 `.venv`에는 핵심 패키지가 비어 있거나 설치가 중간 상태였음
  - `.vscode/settings.json`에 Python 인터프리터 경로가 없어 Pylance가 올바른 환경을 보지 못할 수 있는 상태였음
- 수정 내용:
  - 중단된 `.venv` 패키지 설치 프로세스를 정리
  - `.venv/pyvenv.cfg`의 `include-system-site-packages`를 `true`로 변경해 로컬 가상환경이 시스템에 이미 설치된 패키지를 참조하도록 조정
  - `.vscode/settings.json`의 `python.defaultInterpreterPath`를 `/workspaces/retirement-portfolio-streamlit/.venv/bin/python`으로 설정
- 검증:
  - `.venv/bin/python` 기준 import 확인
  - `python -m compileall app.py src scripts tests`
  - `python -m unittest discover -s tests -p "test_*.py"`
  - 결과: `altair`, `pandas`, `streamlit`, `dateutil` import 성공, 단위 테스트 41건 통과
- 미완료:
  - VS Code 창에서 Pylance 진단 갱신 여부 직접 확인 필요

## 2026-05-09 로컬 Streamlit 브라우저 검증
- 변경 파일: `Memory.md`
- 설치:
  - `.venv`에 `playwright` 설치
  - `PLAYWRIGHT_BROWSERS_PATH=/workspaces/retirement-portfolio-streamlit/.playwright-browsers` 기준 `chromium` 설치
- 검증 내용:
  - `.venv/bin/python -m streamlit run app.py --server.port 8511 --server.headless true`로 로컬 서버 기동
  - `http://127.0.0.1:8511/_stcore/health` 응답 `ok` 확인
  - Playwright headless로 `http://127.0.0.1:8511/` 접속 후 8초 대기
  - 본문 텍스트에 `RETIREMENT PORTFOLIO`, `로그인`, `데모 작업공간` 포함 여부 확인
  - 콘솔 오류 0건, 페이지 오류 0건 확인
- 산출물:
  - `artifacts/local-streamlit-8511-ready.png`
  - `artifacts/local-streamlit-8511-ready.txt`
- 비고:
  - 초기 1차 캡처는 Streamlit 스켈레톤만 잡혀 `Deploy`만 보였고, 추가 대기 후 정상 렌더링을 확인함
  - 검증 종료 후 8511 포트 서버 세션 정리 완료

## 2026-05-09 보유 현금 카드 수정/취소 반응 개선
- 변경 파일: `app.py`, `Memory.md`
- 변경 내용:
  - `보유 현금` 카드의 실제 클릭 요소를 카드 전체 오버레이가 아닌 우측 상단의 실제 `수정` 버튼으로 분리
  - 카드 hover는 전체 카드에 유지하고, `수정` 열기와 `취소`는 `@st.fragment` 부분 리런으로 처리
  - `저장`은 현금 조정 기록과 롤업 갱신이 필요하므로 전체 리런을 유지
- 검증:
  - `python -m compileall app.py`
  - `python -m unittest discover -s tests -p "test_*.py"`
  - 로컬 SQLite 데모 모드 서버 `8512` 포트에서 Playwright headless 재검증
  - 결과:
    - 카드 hover 배경 변경 확인: `rgba(0, 0, 0, 0)` -> `rgba(15, 118, 110, 0.05)`
    - `수정` 열기: `0.423s`
    - `취소`: `0.475s`
    - `저장`: `3.461s`
    - 추가 검증에서 `수정` 버튼 DOM이 실제 `button` 요소로 렌더링되고, 클릭 후 숫자 입력과 `저장`/`취소` 버튼 표시 확인
    - 콘솔 오류 0건, 페이지 오류 0건
- 산출물:
  - `artifacts/dashboard-cash-card-hover-and-latency-fixed.png`
  - `artifacts/dashboard-cash-card-hover-and-latency-fixed.json`
  - `artifacts/dashboard-cash-card-before-click.png`
  - `artifacts/dashboard-cash-card-after-click.png`

## 2026-05-09 README 점검 및 정리
- 변경 파일: `README.md`, `Memory.md`
- 확인 내용:
  - 실제처럼 보이는 Supabase URL/키 예시와 배포 검증 계정 예시가 섞여 있던 구간을 placeholder 값으로 정리
  - 롤업 예시 블록에 섞여 있던 무관한 프롬프트 텍스트 제거
  - 로컬 실행 예시의 사용자 개인 절대 경로를 `cd <프로젝트_루트>`로 일반화
- 비고:
  - 현재 README 기준으로 위 이상 텍스트와 민감해 보이는 예시는 제거된 상태
  - 배포 명령과 검증 명령은 유지

## 2026-05-09 상단 요약 카드 hover 색상 제거 및 높이 재정렬
- 변경 파일: `app.py`, `Memory.md`
- 변경 내용:
  - `보유 현금` 카드의 hover 시 카드 본문에 뜨던 초록 배경 강조를 제거
  - `수정` 버튼 hover 색상도 초록 계열 대신 중립 톤으로 조정
  - `입금 원금`, `현재 평가액`, `원금 대비 평가손익`, `원금 대비 수익률` 4개 카드 높이를 `보유 현금` 카드와 같은 높이로 확장
- 검증:
  - `.venv/bin/python -m compileall app.py`
  - 로컬 SQLite 데모 모드 서버 `8512` 포트에서 Playwright headless 재검증
  - 결과:
    - `수정` 버튼 hover 전후 `보유 현금` 카드 본문 배경 모두 `rgba(0, 0, 0, 0)` 유지
    - `수정` 버튼 hover 배경은 `rgba(248, 250, 252, 0.98)`의 중립 톤으로 변경
    - 상단 5개 요약 카드 높이 모두 `123.188px`로 동일
    - 콘솔 오류 0건, 페이지 오류 0건
- 산출물:
  - `artifacts/dashboard-summary-cards-neutral-hover.png`

## 2026-05-09 접속 화면 상단 제거 및 실시간 버튼 재배치
- 변경 파일: `app.py`, `Memory.md`
- 변경 내용:
  - 접속 화면 상단의 기존 히어로/설명 영역을 제거하고 제목을 `자산관리 대장`만 남기도록 단순화
  - `로그인`, `계정 만들기`, `데모 체험` 탭 구조는 유지하고 상단 장식 영역만 삭제
  - 대시보드의 `시장 업데이트` 패널을 제거
  - `현재가 새로고침` 버튼을 `실시간`으로 변경하고 `현재 평가액` 카드 우상단으로 이동
  - 상단 5개 요약 카드 높이를 다시 맞춰 `보유 현금`과 같은 행 카드가 모두 동일 높이로 유지되게 조정
- 검증:
  - `.venv/bin/python -m compileall app.py src scripts tests`
  - `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`
  - 로컬 SQLite 데모 모드 서버 `8512` 포트에서 Playwright headless 재검증
  - 결과:
    - 접속 화면 제목 `자산관리 대장` 확인
    - 접속 화면에서 `Retirement Portfolio` 텍스트 미노출 확인
    - `로그인`/`계정 만들기`/`데모 체험` 탭 유지 확인
    - 대시보드에서 `시장 업데이트` 텍스트 미노출 확인
    - `실시간` 버튼이 `현재 평가액` 카드 우상단에 표시 확인
    - 상단 5개 요약 카드 높이 모두 `123.188px`로 동일
    - 콘솔 오류 0건, 페이지 오류 0건
- 산출물:
  - `artifacts/auth-page-simple-title.png`
  - `artifacts/dashboard-live-button-top-card.png`

## 2026-05-09 상단 요약 카드 값 위치 정렬
- 변경 파일: `app.py`, `Memory.md`
- 변경 내용:
  - `입금 원금`, `원금 대비 평가손익`, `원금 대비 수익률` 카드의 값 영역을 상단 정렬로 조정
  - 카드 전체 높이는 유지하면서 값 시작 위치를 `보유 현금` 카드와 맞춤
- 검증:
  - `.venv/bin/python -m compileall app.py`
  - 사용자 실화면 확인 완료
- 비고:
  - 로컬 브라우저 자동 검증은 실행 중 사용자가 실화면 확인 완료를 알려 중단
  - 상단 카드 높이 동일화 조정은 유지

## 2026-05-09 데모 5년 거래 시드 확장 및 이자 적립 제거
- 변경 파일: `src/db.py`, `src/sqlite_db.py`, `src/analytics.py`, `src/auth.py`, `app.py`, `scripts/run_daily_rollup.py`, `.github/workflows/daily-rollup.yml`, `scripts/verify_streamlit_deployment.py`, `tests/test_db.py`, `tests/test_analytics.py`, `tests/test_verify_streamlit_deployment.py`, `README.md`, `Memory.md`
- 변경 내용:
  - 데모 워크스페이스 블루프린트를 약 5년치 투자 일지 형태로 확장하고 반도체, 원자력, 방산, 2차전지, 배당, 채권, 미국 기술주 등 다양한 테마와 수익/손실 사례를 섞어 재구성
  - 로컬 데모 세션 표시 주소를 `demo@local`에서 `test`로 변경
  - 자동 일별 이자 적립 로직을 비활성화하고, 공개 이자 조회/기록 함수는 더 이상 데이터를 만들지 않도록 차단
  - 일별 롤업 배치는 스냅샷 저장 전용으로 단순화하고, 데이터 내보내기/배포 검증 파서/문서를 현재 동작에 맞게 정리
- 검증:
  - `python -m compileall app.py src scripts tests`
  - `python -m unittest discover -s tests -p "test_*.py"`
  - 결과: 컴파일 성공, 단위 테스트 `39`건 통과
- 남은 작업:
  - 필요 시 실제 Streamlit 데모 진입 후 새 5년 시드가 화면에서 의도대로 보이는지 브라우저 실검증 추가 가능

## 2026-05-10 Memory.md 기준 변경분 리뷰
- 검토 범위:
  - `Memory.md`에 기록된 최근 변경 중 `데모 5년 거래 시드 확장 및 이자 적립 제거` 관련 코드/테스트/문서
  - 확인 파일: `src/db.py`, `src/sqlite_db.py`, `src/analytics.py`, `src/auth.py`, `app.py`, `scripts/run_daily_rollup.py`, `scripts/verify_streamlit_deployment.py`, `tests/test_db.py`, `tests/test_analytics.py`, `tests/test_verify_streamlit_deployment.py`, `README.md`
- 검토 결과:
  - 코드 리뷰 관점에서 기능 회귀 가능성이 있는 이슈 2건 확인
  - 1) 백데이트 입력 후 과거 스냅샷 재계산 부재
  - 2) 레거시 `daily_interest`/`interest` 데이터가 분석값에서 0으로 고정되어 과거 이자 반영이 사라질 가능성
- 검증:
  - `python -m unittest discover -s tests -p "test_*.py"` 성공
  - 결과: 39건 통과
- 비고:
  - 이번 작업에서는 리뷰만 수행했고 코드 수정은 하지 않음

## 2026-05-10 데모 계정/리셋 및 스냅샷 보정 반영
- 변경 파일: `src/auth.py`, `src/db.py`, `src/sqlite_db.py`, `src/analytics.py`, `app.py`, `scripts/verify_streamlit_deployment.py`, `tests/test_auth.py`, `tests/test_db.py`, `tests/test_analytics.py`, `tests/test_verify_streamlit_deployment.py`, `Memory.md`
- 변경 내용:
  - 초기 화면 데모 진입이 `STREAMLIT_VERIFY_EMAIL` 같은 운영 검증 계정으로 자동 로그인하지 않도록 분리하고, 전용 `DEMO_LOGIN_*`이 없으면 로컬 데모 세션 `test`로 고정
  - `seed_demo_workspace()`가 기존 `데모 IRP`/`데모 일반계좌`를 재사용하지 않고 항상 삭제 후 다시 만들어 내부 계좌를 전부 리셋하도록 변경
  - `list_daily_interest()`를 읽기 전용으로 복구해 기존 `daily_interest` 데이터를 다시 조회하도록 조정하고, 신규 이자 적립은 계속 차단 유지
  - `account_summary()`, `snapshot_trend_frame()`, `cumulative_contribution_frame()`가 레거시 이자 데이터를 다시 누적 반영하도록 수정
  - 메인 화면 롤업이 당일 스냅샷만 쓰는 대신, 기존 과거 스냅샷도 가능한 범위에서 다시 맞춘 뒤 당일 스냅샷을 저장하도록 `sync_account_rollup()` 연결
  - 배포 검증 스크립트가 `SUPABASE_URL 설정: 예 (secret)` 형식에서도 `secret` 출처를 안정적으로 파싱하도록 보정
- 검증:
  - `python -m compileall app.py src scripts tests` 성공
  - `python -m unittest discover -s tests -p "test_*.py"` 성공
  - 결과: 단위 테스트 `39`건 통과
- 남은 작업:
  - 필요 시 실제 Streamlit 화면에서 데모 진입 시 사이드바 로그인 계정이 `test`로 보이는지 브라우저 실검증 가능
  - 필요 시 백데이트 매매/입금 입력 후 과거 추이 화면이 기대 범위로 갱신되는지 수동 점검 가능

## 다음 작업 후보
- 로컬 `streamlit run app.py` 실사용 흐름에서 현금 조정 저장 후 데이터 반영 체감 속도 재확인
- 배포 점검 스크립트 실행 여부 검토
- `docs/progress-memory.md`와 필요 시 내용 동기화 검토

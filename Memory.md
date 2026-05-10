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
- [x] 계좌 삭제 기능 추가
- [x] 서버 일별 이자 거래 기록 점검 및 제거
- [x] 저장소 기준 검증/자동 푸시 배포 스크립트 추가
- [x] 대시보드 자산 배분/보유 종목 수익률 재배치 및 선택 종목 트렌드 추가
- [x] 대시보드 수익률 바 원복 및 설치 원칙 기록
- [x] 보유 종목 수익률 라벨 표시 및 선택 종목 트렌드 선택 payload 수정
- [x] 자산 배분 수익률 바 실제 최대값 기준 및 범위 밖 투명 처리
- [x] 선택 종목 트렌드 ECharts 디자인 전환 및 기능 확장
- [x] 웹 배포 실행 및 원격 대시보드 검증
- [x] 보유 종목 수익률 차트 양수 전용 Y축 범위 보정
- [x] 선택 종목 트렌드 상단 설명 제거 및 차트 위 데이터 정렬
- [x] 보유 종목 수익률 차트 mixed 구간 Y축 자동 스케일 복원
- [x] 선택 종목 트렌드 상단 데이터 텍스트 제거 및 컨트롤 박스 정리
- [x] 선택 종목 트렌드 제목/종목코드 표기 및 컨트롤 일열 정리

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

## 2026-05-10 배포 반영
- 배포 원칙:
  - `jhonkim2025@gmail.com` 관련 서버/운영 계정 데이터는 삭제하거나 변경하지 않음
  - 로컬 `data/portfolio.db` 변경분과 로컬 산출물은 배포 커밋에서 제외
- 배포 커밋:
  - `a853be1` `Reset demo workspace and restore rollup integrity`
- 배포 방법:
  - `main` 브랜치에서 GitHub 원격 `origin`으로 `git push origin main`
- 배포 검증:
  - `PLAYWRIGHT_BROWSERS_PATH=/workspaces/retirement-portfolio-streamlit/.playwright-browsers .venv/bin/python scripts/verify_streamlit_deployment.py --page data --expect-backend supabase --wait-ms 12000 --text-output artifacts/deploy-verify-current-2.txt --screenshot artifacts/deploy-verify-current-2.png`
  - 결과: 배포 앱 접속 성공, 로그인 성공, 작업공간 표시 확인, `status_panel_visible=true`, `backend_storage_code=supabase`
- 비고:
  - 검증 산출물: `artifacts/deploy-verify-current-2.txt`, `artifacts/deploy-verify-current-2.png`

## 2026-05-10 계좌 삭제 기능 및 서버 이자 기록 정리
- 변경 파일: `app.py`, `src/db.py`, `tests/test_db.py`, `Memory.md`
- 변경 내용:
  - 사이드바의 현재 선택 계좌 영역에 `현재 계좌 삭제` 확장 섹션을 추가하고, 삭제 확인 체크박스를 켠 뒤에만 선택 계좌 삭제 버튼이 활성화되도록 구성
  - 선택 계좌 삭제 버튼에서 계좌/보유종목/거래기록/스냅샷 삭제를 실행하도록 연결
  - 공개 DB wrapper `delete_account()`를 추가해 Supabase/SQLite 공통 삭제 경로를 UI에서 직접 호출할 수 있게 정리
  - 계좌 삭제 후 사이드바 선택 계좌를 남아 있는 첫 계좌로 재설정하고, 계좌가 더 없으면 `None`으로 비운 뒤 롤업 dirty 플래그를 세우도록 처리
  - `tests/test_db.py`에 공개 `delete_account()`가 내부 fallback 경로를 타는지 검증하는 단위 테스트 추가
- 서버 정리:
  - Supabase 실서버에서 현재 사용자 작업공간의 `trade_logs.trade_type='interest'`와 `daily_interest` 잔존 레코드를 조회 후 제거
  - 삭제 전 확인:
    - 계좌 `미래에셋증권`(`id=23`): `interest` 거래 `233`건, `daily_interest` `234`건
    - 계좌 `IRP (신한)`(`id=24`): `interest` 거래 `66`건, `daily_interest` `66`건
    - 계좌 `카카오증권`(`id=26`): `interest` 거래 `57`건, `daily_interest` `57`건
    - 합계: `interest` 거래 `356`건, `daily_interest` `357`건
  - 삭제 후 확인:
    - `trade_logs.trade_type='interest'` `0`건
    - `daily_interest` `0`건
- 검증:
  - `python -m compileall app.py src scripts tests` 성공
  - `python -m unittest discover -s tests -p "test_*.py"` 성공
  - 결과: 단위 테스트 `40`건 통과
- 비고:
  - 이번 서버 정리는 계좌 자체나 다른 거래 유형은 건드리지 않고, 잔존 이자 기록만 제거
  - `jhonkim2025@gmail.com` 운영 계정 전체 삭제나 계좌 삭제는 수행하지 않음

## 2026-05-10 저장소 검증/자동 푸시 배포 스크립트 추가
- 변경 파일: `scripts/verify_and_push_deploy.py`, `tests/test_verify_and_push_deploy.py`, `Memory.md`
- 변경 내용:
  - 저장소 기준 로컬 검증(`compileall`, `unittest`) 통과 후 `git add`, `git commit`, `git push`, 배포 검증 스크립트 실행까지 한 번에 처리하는 `scripts/verify_and_push_deploy.py` 추가
  - 로컬 DB, 배포 산출물, Playwright 캐시, 임시 이미지 등 자동 커밋에서 제외할 기본 패턴을 스크립트 내부에 반영
  - 비추적 파일은 `--include-untracked`로 명시한 경우에만 자동 스테이징하도록 막아, 검토 없이 예상 밖 파일이 푸시되지 않도록 안전장치 추가
  - `tests/test_verify_and_push_deploy.py`에서 Git 상태 파싱, 제외 경로 판별, 비추적 파일 분류 로직을 단위 테스트로 추가
- 검증:
  - `python -m compileall app.py src scripts tests` 성공
  - `python -m unittest discover -s tests -p "test_*.py"` 성공
  - 결과: 단위 테스트 `45`건 통과
  - `python scripts/verify_and_push_deploy.py --dry-run --commit-message "Add deployment helper" --include-untracked scripts/verify_and_push_deploy.py tests/test_verify_and_push_deploy.py` 성공
- 비고:
  - 이번 요청에서는 스크립트만 추가했고 실제 커밋/푸시/배포는 실행하지 않음
  - 사용자가 다음 대화에서 배포 문제를 별도로 언급하지 않으면 배포 성공으로 간주하기로 합의

## 2026-05-10 대시보드 자산 배분/선택 종목 트렌드 정리
- 변경 파일: `app.py`, `Memory.md`
- 변경 내용:
  - `자산 배분` 패널을 전체 폭으로 확장하고, `보유 종목 수익률` 패널을 그 아래 전체 폭 섹션으로 재배치
  - 기존 하단 `추이` 섹션을 제거하고, 대신 `선택 종목 트렌드` 박스를 추가해 자산 배분과 같은 화면 흐름에서 개별 종목 가격/수익률 추이를 확인하도록 정리
  - `선택 종목 트렌드` 박스 상단에 기간 선택과 지표 선택을 배치하고, 선택 해제 버튼으로 현재 선택 종목 상태를 지울 수 있도록 추가
  - 트리맵 선택 결과를 대시보드 세션 상태에 반영하는 선택 보조 함수를 추가하고, 현재 보유 종목 표 설명을 새 레이아웃에 맞게 수정
  - 후속 조정으로 `선택 종목 트렌드`와 `보유 종목 수익률`을 같은 행의 2열 50:50 레이아웃으로 변경
  - `자산 배분` 수익률 바를 현재 보유 종목의 실제 수익률 최소/최대 기준으로 다시 계산하고, `select_slider`를 이용해 종목별 수익률 포인트 단위로 드래그되도록 변경
  - 내부 ECharts `visualMap`은 표시를 숨긴 상태로 현재 선택 범위만 반영하고, 패널 하단에 실제 드래그용 수익률 바와 최소/최대 안내 캡션을 노출
- 검증:
  - `python -m compileall app.py src scripts tests` 성공
  - `python -m unittest discover -s tests -p "test_*.py"` 성공
  - 결과: 단위 테스트 `45`건 통과
  - 로컬 SQLite 데모 모드 서버 `8513` 포트에서 Playwright headless 검증
  - 결과:
    - `자산 배분`, `선택 종목 트렌드`, `보유 종목 수익률` 섹션 노출 확인
    - 기존 하단 `추이` 섹션 문구 미노출 확인
  - 로컬 SQLite 데모 모드 서버 `8514` 포트에서 Playwright headless 재검증
  - 결과:
    - `수익률 바` 레이블 노출 확인
    - `현재 보유 종목 기준 최소 ... 최대 ...` 캡션 노출 확인
    - Streamlit 세션 상태 경고 문구 미노출 확인
- 산출물:
  - `artifacts/dashboard-allocation-selected-trend-layout.png`
- 비고:
  - 캔버스 기반 트리맵 클릭은 좌표 자동화로 선택 상태를 안정적으로 재현하기 어려워, 실제 타일 클릭 상호작용은 실화면 수동 확인이 한 번 더 필요할 수 있음

## 2026-05-10 대시보드 수익률 바 원복 및 설치 원칙 기록
- 변경 파일: `app.py`, `AGENTS.md`, `Memory.md`
- 변경 내용:
  - `자산 배분` 패널 하단의 외부 `select_slider` 수익률 바를 제거
  - 트리맵 내부 ECharts `visualMap` 수익률 바가 다시 직접 보이도록 `calculable`, `realtime`, `dimension`, `visualDimension`, 하단 여백 계산을 이전 방식으로 복원
  - 프로젝트 `AGENTS.md`에 "필요한 패키지/도구가 없으면 프로젝트 로컬 환경에 설치하면서 진행하고, 설치 내역과 이유를 `Memory.md`에 기록" 규칙 추가
- 설치:
  - 추가 설치 없음
  - 브라우저 검증은 기존 프로젝트 로컬 `.venv`의 `playwright` 환경을 재사용
- 검증:
  - `python -m compileall app.py src scripts tests` 성공
  - `python -m unittest discover -s tests -p "test_*.py"` 성공
  - 결과: 단위 테스트 `45`건 통과
  - 로컬 Streamlit 서버 `8516` 포트 기동 및 `/_stcore/health` 응답 `ok` 확인
  - 코드 확인 결과 `app.py`에서 `select_slider("수익률 바", ...)` 제거, `visualMap.calculable=True`, `visualMap.realtime=True`, `visualMap.dimension=2`, `series.visualDimension=2` 상태 복원 확인
- 미완료:
  - Streamlit 리런 특성 때문에 Playwright 기반 실화면 자동 캡처는 이번 턴에서 안정적으로 끝내지 못함
  - 사용자가 실화면에서 트리맵 하단 수익률 바 표시를 한 번 확인하면 최종 체감 검증이 완료됨

## 2026-05-10 보유 종목 수익률 라벨 표시 및 선택 종목 트렌드 선택 payload 수정
- 변경 파일: `app.py`, `tests/test_app_dashboard.py`, `Memory.md`
- 변경 내용:
  - `보유 종목 수익률` ECharts 막대차트의 모든 막대에 수익률 라벨이 항상 보이도록 수정
  - 선택 종목이 있을 때만 라벨 강조도가 올라가고, 나머지 라벨은 약하게 유지되도록 조정
  - Altair fallback 차트에도 수익률 텍스트 라벨을 함께 그리도록 보완
  - `선택 종목 트렌드`가 안 뜨던 원인을 확인했고, `streamlit_echarts`가 selection state를 최상위가 아니라 `selection` 키 내부에 넣어 반환하는데 `app.py`가 이를 직접 해석하지 못하던 문제를 수정
  - 회귀 방지를 위해 중첩 selection payload 해석과 막대 라벨 표시를 검증하는 테스트 추가
- 설치:
  - 추가 설치 없음
- 검증:
  - `python -m compileall app.py src scripts tests` 성공
  - `python -m unittest discover -s tests -p "test_*.py"` 성공
  - 결과: 단위 테스트 `48`건 통과
- 비고:
  - 선택 종목 트렌드의 차트 데이터 자체는 여전히 선택 종목의 시세 이력 조회 결과에 따라 비어 있을 수 있음
  - 이번 수정으로는 "선택 이벤트가 세션 상태로 전달되지 않던 문제"를 우선 복구함

## 2026-05-10 자산 배분 수익률 바 실제 최대값 기준 및 범위 밖 투명 처리
- 변경 파일: `app.py`, `tests/test_app_dashboard.py`, `Memory.md`
- 변경 내용:
  - `자산 배분` 트리맵 `visualMap`의 고정 `-100 ~ 100` 스케일을 제거하고, 현재 보유 종목의 실제 최소/최대 수익률을 기준값으로 사용하도록 변경
  - 트리맵 색상 필터 차원을 실제 `profit_rate` 값으로 맞춰, 막대바 드래그 범위와 타일 색상 판정 기준이 동일하게 동작하도록 정리
  - 막대바 범위 밖 타일은 반투명이 아니라 fill이 완전히 사라지도록 `outOfRange.colorAlpha = 0.0`으로 조정
  - 회귀 방지를 위해 `visualMap` 최소/최대가 실제 수익률을 따르는지, 범위 밖 타일이 투명 처리되는지 테스트 추가
- 설치:
  - 추가 설치 없음
- 검증:
  - `python -m compileall app.py src scripts tests` 성공
  - `python -m unittest discover -s tests -p "test_*.py"` 성공
  - 결과: 단위 테스트 `50`건 통과
- 비고:
  - 현재 구현은 수익률 바의 좌우 끝값을 현재 화면 보유 종목의 실제 최소/최대 수익률로 직접 사용함
  - 수익률 범위 밖 타일은 배경 fill만 투명해지고, 트리맵 경계선 구조는 유지됨

## 2026-05-10 선택 종목 트렌드 ECharts 디자인 전환 및 기능 확장
- 변경 파일: `app.py`, `tests/test_app_dashboard.py`, `Memory.md`
- 변경 내용:
  - 기존 Altair 중심 `선택 종목 트렌드`를 ECharts 옵션 기반으로 확장하고, ECharts 사용 가능 시 스무스 라인 + area fill + 하단 dataZoom slider + toolbox UI로 렌더링하도록 변경
  - 차트 제목은 현재 화면 제목인 `선택 종목 트렌드`로 유지하고, 부제에는 선택 종목명·현재 지표·기간을 표시하도록 구성
  - tooltip에서 현재 지표뿐 아니라 평가금액, 수익률, 종가를 함께 확인할 수 있도록 보강
  - toolbox에 `saveAsImage`, `dataView`, `dataZoom`, `restore`, `magicType(line/bar)` 기능 추가
  - 수익률 지표 선택 시 0% 기준선을 함께 보여 주도록 `markLine` 추가
  - ECharts 미사용 환경에서는 기존 Altair fallback을 유지
- 설치:
  - 추가 설치 없음
- 검증:
  - `python -m compileall app.py src scripts tests` 성공
  - `python -m unittest discover -s tests -p "test_*.py"` 성공
  - 결과: 단위 테스트 `52`건 통과
- 비고:
  - 구현 참고 방향은 사용자가 전달한 Streamlit ECharts 예시 스타일과 Apache ECharts의 smooth line, area chart, dataZoom/toolbox 상호작용 구성
  - 실브라우저 시각 확인은 이번 턴에서 자동화하지 않았고, 현재는 옵션/회귀 테스트 기준으로 검증 완료

## 2026-05-10 웹 배포 실행 및 원격 대시보드 검증
- 변경 파일: `Memory.md`
- 배포 방법:
  - `python scripts/verify_and_push_deploy.py --page dashboard --commit-message "Update dashboard trend and treemap visuals" --include-untracked scripts/verify_and_push_deploy.py tests/test_verify_and_push_deploy.py tests/test_app_dashboard.py`
  - 위 실행으로 커밋 `a950908078d8e9b9bff3840c47d53eb8418a3606` 생성 및 `origin/main` 푸시 완료
  - 원격 검증 단계는 시스템 Python에 `playwright`가 없어 실패했고, 규칙에 따라 프로젝트 로컬 `.venv` 환경을 사용해 수동 재검증
  - `PLAYWRIGHT_BROWSERS_PATH=/workspaces/retirement-portfolio-streamlit/.playwright-browsers ./.venv/bin/python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase --wait-ms 20000 --text-output artifacts/deploy-verify-manual-dashboard.txt --screenshot artifacts/deploy-verify-manual-dashboard.png`
- 검증:
  - 자동 배포 스크립트 실행 전 로컬 검증 성공
  - `python -m compileall app.py src scripts tests` 성공
  - `python -m unittest discover -s tests -p "test_*.py"` 성공
  - 결과: 단위 테스트 `52`건 통과
  - 원격 대시보드 검증 결과:
    - 앱 URL: `https://retirement-portfolio-app-nh2vq9ferqnpehsslbykbe.streamlit.app/`
    - 로그인 성공
    - 작업공간 표시 확인
    - 저장소: `Supabase`
    - 대상 페이지: `dashboard`
    - 원격 검증 산출물:
      - `artifacts/deploy-verify-manual-dashboard.txt`
      - `artifacts/deploy-verify-manual-dashboard.png`
- 설치:
  - 추가 글로벌 설치 없음
  - 원격 검증은 기존 프로젝트 로컬 `.venv`의 `playwright`와 `.playwright-browsers`를 사용
- 비고:
  - 자동 배포 스크립트의 원격 검증은 실행 Python 환경에 `playwright`가 없으면 실패하므로, 이후 배포 자동화를 안정화하려면 `.venv` 기준으로 스크립트를 실행하는 편이 안전함

## 2026-05-10 보유 종목 수익률 차트 양수 전용 Y축 범위 보정
- 변경 파일: `app.py`, `tests/test_app_dashboard.py`, `Memory.md`
- 변경 내용:
  - `보유 종목 수익률` 차트의 Y축 범위 계산을 분기 처리로 수정
  - 모든 종목 수익률이 양수인 경우 Y축 최소값을 `0`으로 고정하고 상단 여백만 추가하도록 변경
  - 모든 종목 수익률이 음수인 경우 Y축 최대값을 `0`으로 고정하고 하단 여백만 추가하도록 정리
  - 혼합 구간일 때만 기존처럼 상하 padding을 함께 적용
  - 회귀 방지를 위해 양수 종목만 있을 때 Y축 최소값이 음수로 내려가지 않는 테스트 추가
- 설치:
  - 추가 설치 없음
- 검증:
  - `python -m compileall app.py src scripts tests` 성공
  - `python -m unittest discover -s tests -p "test_*.py"` 성공
  - 결과: 단위 테스트 `53`건 통과

## 2026-05-10 선택 종목 트렌드 상단 설명 제거 및 차트 위 데이터 정렬
- 변경 파일: `app.py`, `Memory.md`
- 변경 내용:
  - `선택 종목 트렌드` 패널의 좌측 설명형 헤더 블록을 제거
  - 선택 종목명, 기간, 표시 지표, 선택 해제 버튼을 차트 바로 위 상단 행으로 재배치
  - 기존 `선택 종목: ... · 기준 기간: ...` 캡션은 차트 데이터 기준 한 줄 메타 정보로 정리
  - 차트 내부 제목은 기존 `선택 종목 트렌드`를 그대로 유지
- 설치:
  - 추가 설치 없음
- 검증:
  - `python -m compileall app.py src scripts tests` 성공
  - `python -m unittest discover -s tests -p "test_*.py"` 성공
  - 결과: 단위 테스트 `53`건 통과

## 2026-05-10 보유 종목 수익률 차트 mixed 구간 Y축 자동 스케일 복원
- 변경 파일: `app.py`, `tests/test_app_dashboard.py`, `Memory.md`
- 변경 내용:
  - `보유 종목 수익률` 차트에서 양수/음수가 섞인 경우 Y축 `min/max`를 직접 계산해 넣던 로직 제거
  - mixed 구간은 ECharts 자동 스케일에 맡겨 자연스러운 축 값(예: `-10`, `40`)이 나오도록 정리
  - 양수 전용일 때만 `min=0`, 음수 전용일 때만 `max=0`을 고정하도록 유지
  - 회귀 방지를 위해 mixed 구간에서는 `yAxis.min/max`를 넘기지 않는 테스트 추가
- 설치:
  - 추가 설치 없음
- 검증:
  - `python -m compileall app.py src scripts tests` 성공
  - `python -m unittest discover -s tests -p "test_*.py"` 성공
  - 결과: 단위 테스트 `54`건 통과

## 2026-05-10 선택 종목 트렌드 상단 데이터 텍스트 제거 및 컨트롤 박스 정리
- 변경 파일: `app.py`, `Memory.md`
- 변경 내용:
  - 선택 종목 트렌드 패널 상단의 `선택 데이터`, `차트 데이터` 텍스트 제거
  - 기간/표시 지표/선택 해제 영역을 별도 내부 컨트롤 박스로 묶어 상단 배치 정리
  - `선택 해제` 버튼이 좁은 열에서 세로로 깨지지 않도록 열 비율과 버튼 CSS 보정
  - 차트 식별 정보는 차트 자체 부제에서만 확인하도록 단순화
- 설치:
  - 추가 설치 없음
- 검증:
  - `python -m compileall app.py src scripts tests` 성공
  - `python -m unittest discover -s tests -p "test_*.py"` 성공
  - 결과: 단위 테스트 `54`건 통과

## 2026-05-10 선택 종목 트렌드 제목/종목코드 표기 및 컨트롤 일열 정리
- 변경 파일: `app.py`, `tests/test_app_dashboard.py`, `Memory.md`
- 변경 내용:
  - 선택 종목 트렌드 ECharts 제목을 고정 문구 대신 현재 선택 종목명으로 변경
  - 차트 부제는 종목명 대신 실제 종목코드와 표시 지표, 기간을 표시하도록 정리
  - Altair fallback 차트도 같은 제목/부제 규칙을 따르도록 맞춤
  - 상단 컨트롤 박스의 기간/표시 지표 segmented control이 줄바꿈되지 않도록 열 비율과 CSS를 조정
- 설치:
  - 추가 설치 없음
- 검증:
  - `python -m compileall app.py src scripts tests` 성공
  - `python -m unittest discover -s tests -p "test_*.py"` 성공
  - 결과: 단위 테스트 `54`건 통과
- 배포:
  - `PLAYWRIGHT_BROWSERS_PATH=/workspaces/retirement-portfolio-streamlit/.playwright-browsers ./.venv/bin/python scripts/verify_and_push_deploy.py --page dashboard --expect-backend supabase --wait-ms 20000 --commit-message "Refine selected holding trend header"`
  - 코드 커밋: `1ac0b008e4f8c51003f7d67a576c82c0451b0e6d`
  - 원격 앱 URL: `https://retirement-portfolio-app-nh2vq9ferqnpehsslbykbe.streamlit.app/`
  - 원격 검증 산출물:
    - `artifacts/deploy-verify-20260510-062641.txt`
    - `artifacts/deploy-verify-20260510-062641.png`
- 비고:
  - 원격 대시보드 검증은 로그인 성공, 작업공간 표시 확인, 저장소 `Supabase`, 대상 페이지 `dashboard` 기준으로 통과

## 다음 작업 후보
- 로컬 `streamlit run app.py` 실사용 흐름에서 현금 조정 저장 후 데이터 반영 체감 속도 재확인
- 배포 점검 스크립트 실행 여부 검토
- `docs/progress-memory.md`와 필요 시 내용 동기화 검토

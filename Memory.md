# Memory.md

## 작업 기록
- [x] 프로젝트 구조 분석
- [x] 초기화 대상 파일 존재 여부 확인
- [x] 프로젝트 유형 판별
- [x] 기본 검증 수행
- [x] 2026-05-08 초기화 재확인
- [x] 2026-05-08 권장 검증 재실행
- [x] 회사 납입/매매/일별 이자 기준 자동 반영 로직 보강
- [x] 데이터 탭 누적 원금 기록 추가
- [x] 로컬 Streamlit 서버 기동 확인
- [x] 데이터 탭/대시보드 렌더링 검증
- [x] Streamlit width deprecation 경고 정리
- [x] KRX 영문 혼합 ETF 코드 시세 조회 보강
- [x] 영문 혼합 KRX ETF 코드 표본 점검
- [x] 과거 백데이트 거래 이자 재계산 보강
- [x] README 배포 안내 최신화
- [x] historical snapshot 원장 기준 보정
- [x] SQLite -> Supabase dry-run 재확인
- [x] Supabase 401/403 fallback 회귀 테스트 추가
- [ ] 실제 로그인 후 브라우저 내부 화면 확인
- [ ] 배포 환경 시크릿/운영 점검 재검증

## 프로젝트 유형
- Python 프로젝트
- Streamlit 프로젝트
- Node.js 프로젝트 아님 (`package.json` 미확인)
- 임베디드/펌웨어 프로젝트 아님 (관련 빌드 파일 미확인)
- 판별 근거: `requirements.txt`에 `streamlit` 존재, `.streamlit/config.toml` 존재

## 현재 확인된 주요 파일
- `app.py`
- `requirements.txt`
- `README.md`
- `.gitignore`
- `.streamlit/config.toml`
- `.streamlit/secrets.example.toml`
- `.streamlit/secrets.toml`
- `.streamlit/secrets.toml.example`
- `setup_supabase.sql`
- `src/auth.py`
- `src/db.py`
- `src/sqlite_db.py`
- `src/analytics.py`
- `scripts/run_daily_rollup.py`
- `scripts/verify_streamlit_deployment.py`
- `tests/test_analytics.py`
- `tests/test_db.py`
- `tests/test_verify_streamlit_deployment.py`
- `docs/progress-memory.md`

## 실행 방법
```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

추가 검증 명령:

```powershell
python -m compileall app.py src scripts tests
python -m unittest discover -s tests -p "test_*.py"
```

## 생성한 파일 목록
- 없음
- 초기화 대상 파일 5종(`AGENTS.md`, `Memory.md`, `.gitignore`, `README.md`, `.env.example`)이 모두 기존에 존재하여 이번 작업에서는 생성하지 않음

## 기존에 존재하던 파일 목록
- `AGENTS.md`
- `Memory.md`
- `.gitignore`
- `README.md`
- `.env.example`
- `requirements.txt`
- `app.py`
- `Procfile`
- `setup_supabase.sql`
- `.streamlit/config.toml`
- `.streamlit/secrets.example.toml`
- `.streamlit/secrets.toml`
- `.streamlit/secrets.toml.example`
- `docs/progress-memory.md`
- `src/auth.py`
- `src/db.py`
- `src/sqlite_db.py`
- `src/analytics.py`
- `scripts/run_daily_rollup.py`
- `scripts/verify_streamlit_deployment.py`
- `tests/test_analytics.py`
- `tests/test_db.py`
- `tests/test_verify_streamlit_deployment.py`

## 검증 가능 여부
- 가능
- 이번 초기화에서 수행한 검증:
  - `python -m compileall app.py src scripts tests`
  - `python -m unittest discover -s tests -p "test_*.py"`
  - `.env` 미생성 확인
- 검증 결과:
  - 문법/바이트코드 컴파일 성공
  - 단위 테스트 16건 성공
  - 프로젝트 루트에 `.env` 파일 없음
  - Streamlit 서버 실제 기동 여부는 이번 초기화 범위에서 미실행

## 현재 프로젝트 상태
- 상태 미확인
- 근거: 로컬 서버 기동과 테스트 런타임 기준 내부 화면 렌더링은 확인했지만, 실제 로그인 후 브라우저 내부 화면과 배포 환경 동작은 아직 미확인임

## 2026-05-08 초기화 재확인
- 작업 범위:
  - 프로젝트 구조 분석
  - 초기화 대상 파일 존재 여부 확인
  - 권장 검증 재실행
  - `Memory.md` 최신화
- 프로젝트 유형:
  - Python 프로젝트
  - Streamlit 프로젝트
  - Node.js 프로젝트 아님 (`package.json` 미확인)
  - 임베디드/펌웨어 프로젝트 아님 (`Makefile`, `CMakeLists.txt`, `*.ioc`, `*.uvprojx` 미확인)
- 현재 확인된 주요 파일:
  - `AGENTS.md`
  - `Memory.md`
  - `.gitignore`
  - `README.md`
  - `.env.example`
  - `requirements.txt`
  - `.streamlit/config.toml`
  - `app.py`
  - `src/db.py`
  - `src/auth.py`
  - `src/analytics.py`
  - `src/sqlite_db.py`
  - `scripts/run_daily_rollup.py`
  - `scripts/verify_streamlit_deployment.py`
- 실행 방법:
  - `python -m pip install -r requirements.txt`
  - `streamlit run app.py`
- 생성한 파일 목록:
  - 없음
- 기존에 존재하던 파일 목록:
  - `AGENTS.md`
  - `Memory.md`
  - `.gitignore`
  - `README.md`
  - `.env.example`
- 검증 가능 여부:
  - 가능
  - 수행 결과: `compileall` 성공, `unittest` 16건 성공, `.env` 미생성 확인
- 현재 프로젝트 상태:
  - 상태 미확인
- 다음 작업 후보:
  - `streamlit run app.py`로 로컬 기동 확인
  - 필요 시 `python scripts/verify_streamlit_deployment.py --page data --expect-backend supabase`로 배포 점검
  - Supabase 또는 SQLite 실제 저장 동작 확인

## 2026-05-08 자동 반영 보강
- 변경 파일:
  - `app.py`
  - `src/db.py`
  - `src/analytics.py`
  - `tests/test_analytics.py`
  - `tests/test_db.py`
- 변경 내용:
  - 전일까지 누락된 일별 이자를 원장(`trade_logs`, `daily_interest`) 기준으로 자동 보정하는 `sync_account_rollup()` 추가
  - 오늘 날짜 기준 예상 현금 이자를 대시보드/데이터 화면에 즉시 반영하도록 보강
  - 대시보드 `실제 성과` 메트릭에 누적 수익률(%) 표시 추가
  - 회사 납입 누계가 있으면 원금 기준 설명을 함께 표시
- 검증:
  - `python -m compileall app.py src tests`
  - `python -m unittest discover -s tests -p "test_*.py"`
  - 결과: 테스트 16건 통과
- 비고:
  - 자동 보정은 전일까지의 확정 이자를 기록하고, 오늘 이자는 화면에서 예상치로 반영한다.
  - Streamlit 실제 화면 동작은 아직 미확인이다.

## 2026-05-08 원금 기준 성과 정리
- 변경 파일:
  - `app.py`
  - `src/analytics.py`
  - `tests/test_analytics.py`
- 변경 내용:
  - `회사 납입 누계`, `누적 납입 원금`, `원금 대비 추정 수익`, `보유상품 추정 수익률`을 분리 계산
  - 매수/매도는 원금을 바꾸지 않고 현금/보유상품 구성만 바꾸는 규칙을 테스트로 고정
  - 추이 차트 tooltip에 원금 대비 손익/수익률 추가
- 검증:
  - `python -m compileall app.py src tests`
  - `python -m unittest discover -s tests -p "test_*.py"`
  - 결과: 테스트 16건 통과

## 2026-05-08 데이터 탭 누적 원금 기록
- 변경 파일:
  - `app.py`
  - `src/analytics.py`
  - `tests/test_analytics.py`
- 변경 내용:
  - 데이터 탭에 최초 입금일부터 현재까지의 누적 원금 기록 표 추가
  - `연금(IRP/퇴직연금)` 계좌 라벨을 명시하고 회사 납입 누계를 별도 컬럼으로 표시
  - 현재 평가액과 원금 대비 손익/수익률을 누적 기록의 최신 행에서 함께 확인하도록 보강
  - `cumulative_contribution_frame()` 테스트로 현재 시점 평가액 행이 누적 원금과 올바르게 연결되는지 고정
- 검증:
  - `python -m compileall app.py src scripts tests`
  - `python -m unittest discover -s tests -p "test_*.py"`
  - 결과: 테스트 17건 통과
- 비고:
  - 현재 구현은 `retirement` 계좌를 `연금(IRP/퇴직연금)`으로 묶어 표시한다.
  - `IRP`와 `퇴직연금`을 서로 다른 저장 속성으로 분리하는 스키마 변경은 아직 미구현이다.

## 2026-05-08 로컬 실행 및 화면 검증
- 변경 파일:
  - `Memory.md`
- 변경 내용:
  - `python -m streamlit run app.py --server.port 8510 --server.headless true`로 로컬 서버 기동 확인
  - Playwright headless로 로컬 첫 화면을 열어 로그인/계정 만들기 탭과 입력 필드가 렌더링되는지 확인
  - `Streamlit AppTest`에서 인증 모듈을 테스트용으로 패치하고 `PORTFOLIO_BACKEND=sqlite`로 강제해 데이터 탭/대시보드 내부 화면 렌더링 확인
- 검증:
  - `http://127.0.0.1:8510/_stcore/health` 응답 `ok`
  - Playwright DOM 확인: 로그인, 계정 만들기, 이메일/비밀번호 입력 필드 표시
  - AppTest 데이터 탭 확인:
    - `원금 누적 기록` 섹션 렌더링
    - `누적 투자원금`, `현재 평가액`, `원금 대비 현재 수익률` 메트릭 렌더링
  - AppTest 대시보드 확인:
    - `원금 대비 추정 수익`, `누적 납입 원금`, `회사 납입 누계`, `누적 이자` 메트릭 렌더링
    - `2026-05-08 예상 현금 이자` 캡션 렌더링
- 비고:
  - 실제 Supabase 로그인 자격 증명이 없어 브라우저에서 로그인 후 내부 화면까지의 완전한 E2E 검증은 이번 작업 범위에서 미실행
  - 테스트 런타임에서 `use_container_width` deprecation 경고가 반복 출력됨
  - 대시보드 시세 조회 중 Yahoo Finance 심볼 `0113D0` 404 경고가 있었지만 AppTest 렌더링 자체는 성공

## 2026-05-08 Streamlit width deprecation 정리
- 변경 파일:
  - `app.py`
  - `Memory.md`
- 변경 내용:
  - `st.button()`, `st.form_submit_button()`, `st.download_button()`의 `use_container_width=True`를 `width="stretch"`로 치환
  - `st.dataframe()`과 `st.altair_chart()`의 `use_container_width=True`를 `width="stretch"`로 치환
  - 화면 레이아웃 폭 동작은 유지하면서 Streamlit deprecation 경고만 제거
- 검증:
  - `rg -n "use_container_width" app.py src tests scripts` 결과 없음
  - `python -m compileall app.py src scripts tests`
  - `python -m unittest discover -s tests -p "test_*.py"`
  - AppTest 재검증:
    - 데이터 탭 메트릭 `데이터 저장소`, `누적 이자`, `누적 투자원금`, `현재 평가액`, `원금 대비 현재 수익률` 렌더링 확인
    - 대시보드 메트릭 `포트폴리오 평가액`, `원금 대비 추정 수익`, `누적 납입 원금`, `회사 납입 누계`, `누적 이자` 렌더링 확인
- 비고:
  - AppTest 실행 시 `use_container_width` 경고는 더 이상 출력되지 않음
  - 테스트 런타임의 `ScriptRunContext` 경고와 Yahoo Finance 심볼 `0113D0` 조회 404 경고는 별도 이슈로 남아 있음
  - SQLite 강제 모드 AppTest가 `sync_account_rollup()`를 통과하면서 로컬 `data/portfolio.db`에 일별 이자/스냅샷 쓰기가 발생했을 수 있으므로 후속 검토 시 데이터 변경 여부를 함께 확인할 것

## 2026-05-08 KRX 영문 혼합 ETF 코드 시세 조회 보강
- 변경 파일:
  - `src/market.py`
  - `tests/test_market.py`
  - `Memory.md`
- 변경 내용:
  - KRX 상장 코드 판별 규칙에 `9999A9` 형태의 영문 혼합 ETF 코드를 추가
  - `0113D0` 같은 코드가 `normalize_symbol()`에서 `0113D0.KS`로 정규화되도록 수정
  - Yahoo 검색 결과 파싱에서도 영문 혼합 KRX 코드를 인식하도록 정규식 보강
  - `tests/test_market.py`로 `is_krx_code()`, `normalize_symbol()`, `clean_code()` 회귀 테스트 추가
- 검증:
  - `python -m compileall app.py src scripts tests`
  - `python -m unittest discover -s tests -p "test_*.py"`
  - 결과: 테스트 22건 통과
  - 실조회:
    - `normalize_symbol('0113D0') == '0113D0.KS'`
    - `fetch_latest_price('0113D0')` 결과 `12260.0`, 기준일 `2026-05-08`
    - `fetch_price_history('0113D0', '1mo')` 결과 21행
  - AppTest 대시보드 재확인:
    - 예외 0건
    - 이전의 `0113D0` Yahoo 404 경고 미재현
- 비고:
  - 라이브 확인 기준 Naver ETF 목록과 Naver 차트 API 모두 `0113D0`를 `TIME 글로벌탑픽액티브`로 반환했고, Yahoo Finance도 `0113D0.KS`에는 응답함

## 2026-05-08 영문 혼합 KRX ETF 코드 표본 점검
- 변경 파일:
  - `Memory.md`
- 변경 내용:
  - Naver ETF 목록 API에서 영문 혼합 KRX ETF 코드 표본 15건을 추출해 정규화 및 Yahoo 시세 응답 여부를 점검
  - 표본 코드: `0043B0`, `0162Z0`, `0117V0`, `0072R0`, `0117L0`, `0167A0`, `0139F0`, `0091P0`, `0163Y0`, `0061Z0`, `0148J0`, `0048J0`, `0105E0`, `0127P0`, `0101N0`
- 검증:
  - 모든 표본이 `normalize_symbol()`에서 `*.KS`로 정규화됨
  - 모든 표본이 `yfinance.Ticker(<code>.KS).history(period='5d')` 기준 5행 응답
- 비고:
  - 현재 수집한 Naver ETF 영문 혼합 코드 225건은 모두 `9999A9` 패턴이었음
  - 이번 표본 범위에서는 추가 fallback 로직 없이 현재 정규화 수정만으로 충분했음

## 2026-05-08 과거 백데이트 거래 이자 재계산 보강
- 변경 파일:
  - `src/db.py`
  - `app.py`
  - `tests/test_db.py`
  - `Memory.md`
- 변경 내용:
  - `sync_account_rollup()`가 누락 이자만 채우는 방식에서, 원장과 기존 이자 이력이 어긋난 경우 자동 이자 기간 전체를 재구성하도록 보강
  - 기대 이자 일정과 실제 `trade_logs`/`daily_interest` 상태를 비교하는 diff 집계 및 추가/수정/삭제 건수 계산 로직 추가
  - SQLite/Supabase 모두 전일까지의 자동 이자 레코드를 삭제 후 기대 일정으로 다시 쓰는 `_replace_interest_history()` 경로 추가
  - 대시보드 상단 자동 반영 안내가 `추가/재계산/제거` 건수와 순변동 금액을 함께 보여주도록 보강
- 검증:
  - `python -m compileall app.py src scripts tests`
  - `python -m unittest discover -s tests -p "test_*.py"`
  - 결과: 테스트 23건 통과
- 비고:
  - 이번 재계산은 자동 생성된 일별 이자 이력만 재구성하며, 과거 날짜의 `daily_account_snapshot` 이력은 재생성하지 않음
  - 실데이터 쓰기 검증은 로컬 DB 변형 가능성이 있어 이번 단계에서는 단위 테스트로만 확인

## 2026-05-08 README 배포 안내 최신화
- 변경 파일:
  - `README.md`
  - `Memory.md`
- 변경 내용:
  - Streamlit Community Cloud 배포 절차를 현재 공식 용어에 맞춰 `Create app`, `Advanced settings > Secrets` 기준으로 정리
  - `Repository` 예시를 현재 git remote 기준 `jhonkim91/retirement-portfolio-streamlit`로 구체화
  - 배포 후 `Settings > Secrets` 로 시크릿을 추가하는 보조 절차를 분리해 문서화
  - `scripts/verify_streamlit_deployment.py` 사용 시 로그인 자격 증명이 없으면 종료 코드 `1`로 실패한다는 조건을 README에 명시
- 검증:
  - `python scripts/verify_streamlit_deployment.py --page data --expect-backend supabase`
  - 결과: `STREAMLIT_VERIFY_EMAIL`/`STREAMLIT_VERIFY_PASSWORD` 미설정으로 종료 코드 `1`, 예상 오류 메시지 확인
- 비고:
  - 실제 배포 환경 로그인 검증은 자격 증명이 준비된 뒤 재실행 필요

## 2026-05-08 historical snapshot 원장 기준 보정
- 변경 파일:
  - `src/db.py`
  - `app.py`
  - `tests/test_db.py`
  - `Memory.md`
- 변경 내용:
  - `sync_account_rollup()`에서 과거 이자 보정이 발생하면 해당 시작일 이후의 기존 historical snapshot을 함께 재계산하도록 보강
  - historical snapshot 보정 시 `cash_balance`와 `total_cost`는 원장 기준으로 다시 계산하고, 기존 snapshot에 저장돼 있던 `market_value`는 유지한 채 `total_value`만 다시 맞춤
  - 대시보드 자동 반영 안내에 `과거 스냅샷 보정` 건수를 추가
  - 테스트로 누락 이자 3일 보정 후 `2026-05-06`~`2026-05-08` snapshot 3건이 함께 수정되는 시나리오를 고정
- 검증:
  - `python -m compileall app.py src scripts tests`
  - `python -m unittest discover -s tests -p "test_*.py"`
  - 결과: 테스트 24건 통과
- 비고:
  - 시점별 가격 이력이 저장돼 있지 않아 historical snapshot의 `market_value`는 새로 추정하지 않고 기존 저장값을 유지함
  - 따라서 이번 보정은 historical snapshot의 현금/원가/총액 정합성을 높이는 목적이며, 과거 시점 시장가격 재현까지 포함하지 않음

## 2026-05-08 SQLite -> Supabase dry-run 재확인
- 변경 파일:
  - `docs/progress-memory.md`
  - `Memory.md`
- 변경 내용:
  - `scripts/migrate_sqlite_to_supabase.py`를 기본 dry-run 모드로 다시 실행해 현재 로컬 SQLite 이관 대상 규모를 최신 값으로 재확인
  - 예전 메모에 남아 있던 `거래기록 58 / 이자 0 / 스냅샷 0` 수치를 최신 dry-run 결과로 갱신
  - 현재 source namespace와 계좌별 이관 계획을 `docs/progress-memory.md`에 반영
- 검증:
  - `python scripts/migrate_sqlite_to_supabase.py`
  - 결과:
    - source namespace: `6e4d857d-b654-40c9-b458-a0b084449fce`
    - 계좌 4개 / 보유종목 6개 / 거래기록 122개 / 일별 이자 64개 / 스냅샷 1개
    - `--write` 미지정 상태라 실제 Supabase 쓰기는 수행하지 않음
- 비고:
  - 운영 쓰기를 진행하려면 대상 사용자 이메일, 대상 사용자 비밀번호 환경변수, `SUPABASE_KEY`가 추가로 필요함
## 다음 작업 후보
- 실제 로그인 자격 증명으로 브라우저에서 데이터 탭의 누적 원금 기록 표와 현재 평가액 기준 수익률 표시 확인
- 실제 로그인 자격 증명으로 브라우저에서 대시보드의 자동 이자 반영 메시지와 누적 수익률 표시 확인
- historical snapshot `market_value`를 시점별 가격 이력과 연결해 더 정확히 재생성할지 검토
- `docs/progress-memory.md` 기준 운영 계정에서 첫 계좌 생성과 기존 데이터 이관 중 우선순위 결정
- 대상 사용자 이메일/비밀번호와 `SUPABASE_KEY` 준비 후 `scripts/migrate_sqlite_to_supabase.py --write` 실행 검토
- `scripts/verify_streamlit_deployment.py --page data --expect-backend supabase`로 배포 환경 재검증
- Streamlit 실제 실행(`streamlit run app.py`) 후 로컬 UI 동작 확인

## 2026-05-08 구조 및 Memory 점검 요약
- 변경 파일:
  - `Memory.md`
- 변경 내용:
  - 프로젝트 루트 구조, `requirements.txt`, `README.md`, `.streamlit/config.toml`, `Memory.md`를 다시 확인
  - `Memory.md` 기준 최근 완료/미완료 항목, 실행 방법, 검증 결과, 다음 작업 후보를 재정리
  - 현재 git working tree가 dirty 상태이며 기존 미커밋 변경이 다수 존재함을 확인
- 현재 파일 상태:
  - 수정 추적 파일: `.gitignore`, `README.md`, `app.py`, `data/portfolio.db`, `docs/progress-memory.md`, `src/analytics.py`, `src/db.py`, `src/market.py`, `tests/test_analytics.py`, `tests/test_db.py`
  - 미추적 파일: `.env.example`, `.vscode/`, `AGENTS.md`, `Memory.md`, `tests/test_market.py`, `tmp_source.png`
  - 이번 점검에서는 위 파일들에 추가 변경을 가하지 않고 `Memory.md`만 갱신
- 실행/설정 기준:
  - 실행 명령은 기존 문서와 동일하게 `python -m pip install -r requirements.txt`, `streamlit run app.py`
  - `.streamlit/config.toml`은 `theme` 설정 유지, `[server] headless = true` 유지
- 검증:
  - 이번 점검에서는 구조/문서/메모리 확인만 수행했고 추가 테스트는 재실행하지 않음
  - 최신 기록 기준 마지막 검증 결과는 `python -m compileall app.py src scripts tests`, `python -m unittest discover -s tests -p "test_*.py"` 성공, dry-run 마이그레이션 재확인까지 완료
- 현재 상태 판단:
  - 코드와 문서는 최근 작업 내용이 `Memory.md`와 대체로 일치함
  - 다만 실제 로그인 후 내부 화면 확인과 배포 환경 시크릿/운영 점검은 아직 미완료 상태로 유지

## 2026-05-08 Supabase fallback 회귀 테스트 보강
- 변경 파일:
  - `tests/test_db.py`
  - `Memory.md`
- 변경 내용:
  - `src/db.py`의 `_should_fallback()` / `_run_with_fallback()` 정책을 직접 고정하는 회귀 테스트 3건 추가
  - `401`, `403` 인증/권한 오류에서는 `SQLite fallback`으로 우회하지 않고 예외를 그대로 재전파하는지 확인
  - `500` 서버 오류에서는 기존처럼 `SQLite fallback`이 동작하는지 확인
  - 배포 검증 자격 증명(`STREAMLIT_VERIFY_EMAIL`, `STREAMLIT_VERIFY_PASSWORD`)은 현재 환경과 `.streamlit/secrets.toml`에 없어 실제 로그인 기반 검증은 이번 턴에서 계속 보류
- 검증:
  - `python -m compileall app.py src scripts tests`
  - `python -m unittest discover -s tests -p "test_*.py"`
  - 결과: 테스트 27건 통과
- 비고:
  - 운영 Supabase 온보딩/데모 버튼 실검증을 재개하려면 로그인 자격 증명이 추가로 필요
  - 현재 `.streamlit/secrets.toml`에는 `SUPABASE_URL`, `SUPABASE_KEY`만 있고 검증용 이메일/비밀번호는 없음

## 2026-05-08 배포 로그인 자격 증명 재검증 실패
- 변경 파일:
  - `Memory.md`
- 변경 내용:
  - 제공된 자격 증명으로 `scripts/verify_streamlit_deployment.py` 기본 검증과 `--click-demo` 검증을 각각 재실행
  - 두 실행 모두 로그인 화면에서 `Invalid login credentials`가 반환되어 앱 내부 화면 진입 실패
- 검증:
  - `python scripts/verify_streamlit_deployment.py --page data --expect-backend supabase`
  - `python scripts/verify_streamlit_deployment.py --page data --expect-backend supabase --click-demo`
  - 결과: 두 명령 모두 종료 코드 `1`, 동일한 로그인 실패 메시지 재현
- 비고:
  - 현재 차단 원인은 배포 앱 계정 자격 증명 불일치로 보임
  - 다음 진행을 위해서는 비밀번호 재확인 또는 해당 이메일로 비밀번호 재설정 후 새 자격 증명이 필요

## 2026-05-08 배포 로그인 검증 성공
- 변경 파일:
  - `Memory.md`
- 변경 내용:
  - 새로 확인한 배포 앱 자격 증명으로 `scripts/verify_streamlit_deployment.py` 기본 검증과 `--click-demo` 검증을 다시 실행
  - 두 실행 모두 로그인 성공, 작업공간 진입 성공, `데이터 > 운영 상태` 패널 확인 성공
  - 현재 배포 앱 저장소가 `Supabase`로 보고되고, 온보딩/RLS hotfix 차단 상태는 재현되지 않음
- 검증:
  - `python scripts/verify_streamlit_deployment.py --page data --expect-backend supabase`
  - `python scripts/verify_streamlit_deployment.py --page data --expect-backend supabase --click-demo`
  - 결과:
    - `logged_in=true`
    - `workspace_visible=true`
    - `status_panel_visible=true`
    - `backend_storage=Supabase`
    - `hotfix_required=false`
    - `ok=true`
- 비고:
  - 이번 응답에서는 `demo_button_clicked=false`, `demo_seeded=true`로 반환되어 이미 작업공간 상태에서 검증된 것으로 해석됨
  - 현재 계정은 온보딩이 아닌 기존 작업공간 계정으로 보인다

## 2026-05-08 운영 데이터 상태 우선순위 점검
- 변경 파일:
  - `Memory.md`
- 변경 내용:
  - 배포 `데이터` 페이지 본문을 텍스트로 저장해 실제 작업공간 상태를 확인
  - 현재 배포 계정 `jhonkim2025@gmail.com`은 온보딩이 아니라 기존 작업공간 상태이며, 선택 계좌 `IRP (신한)` / 포트폴리오 평가액 `₩919,352` / 실제 성과 `₩117,032` / 투입 원금 `₩802,320` / 현금 `₩253,717` / 누적 이자 `₩0` 이 표시됨
  - `scripts/migrate_sqlite_to_supabase.py` dry-run을 재실행해 로컬 SQLite 이관 대상 4계좌가 아직 그대로 남아 있음을 재확인
- 검증:
  - `python scripts/verify_streamlit_deployment.py --page data --expect-backend supabase --text-output artifacts\\verify-data-page.txt`
  - `python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase --text-output artifacts\\verify-dashboard-page.txt`
  - `python scripts/migrate_sqlite_to_supabase.py`
- 결과:
  - 배포 작업공간: 기존 데이터가 있는 Supabase 계정
  - 로컬 SQLite dry-run: 계좌 4개 / 보유종목 6개 / 거래기록 122개 / 일별 이자 64개 / 스냅샷 1개
- 비고:
  - 다음 단계는 읽기 검증이 아니라 원격 Supabase 쓰기(`--write`) 여부 결정이다
  - 현재 배포 계정에 이미 데이터가 있으므로, 이관 실행 전 덮어쓰기 의도를 확인해야 한다

## 2026-05-08 회사 납입 기준 보정 후 Supabase 이관
- 변경 파일:
  - `src/analytics.py`
  - `scripts/migrate_sqlite_to_supabase.py`
  - `tests/test_analytics.py`
  - `tests/test_migrate_sqlite_to_supabase.py`
  - `Memory.md`
- 변경 내용:
  - 레거시 원장에 `trade_type='personal_deposit'`로 저장돼 있어도 `product_name='회사 현금입금'` 또는 `회사 납입금`이면 `employer_deposit`로 재해석하도록 보강
  - 같은 정규화 규칙을 `account_summary()` 계산과 `migrate_sqlite_to_supabase.py` 이관 경로에 모두 적용
  - 로컬 `IRP (신한)` 계좌(`id=6`) 원장을 재점검한 결과 회사 성격 입금은 `2026-02-05`, `2026-03-05`, `2026-04-03`, `2026-04-30` 각 `₩200,000`으로 총 `₩800,000`
  - 그 기준으로 로컬 요약값이 `company_principal=800000`, `total_principal=800000`, `net_flow=800000`, `total_interest=581.2625`, `total_value=916508.2625`로 재계산됨을 확인
  - 이후 `scripts/migrate_sqlite_to_supabase.py --write --target-email jhonkim2025@gmail.com`를 실행해 Supabase로 실제 이관 완료
- 검증:
  - `python -m compileall app.py src scripts tests`
  - `python -m unittest discover -s tests -p "test_*.py"`
  - `python scripts/migrate_sqlite_to_supabase.py`
  - `python scripts/migrate_sqlite_to_supabase.py --write --target-email jhonkim2025@gmail.com`
  - `python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase --text-output artifacts\\post-migration-dashboard.txt`
- 결과:
  - 테스트 30건 통과
  - 실제 이관 건수: 계좌 4 / 보유종목 6 / 거래기록 122 / 일별 이자 64 / 스냅샷 1
  - 배포 대시보드 재검증:
    - 저장소 `Supabase`
    - 계좌 `IRP (신한)`
    - 순유입 `₩800,000`
    - 투입 원금 `₩800,000`
    - 누적 이자 `₩581`
    - 포트폴리오 평가액 `₩916,508`
- 비고:
  - 현재 배포 대시보드 문구는 `회사 납입 누계`를 별도 노출하지 않고 `순유입`/`투입 원금` 위주로 표시되고 있음
  - 하지만 이관된 원장 레코드 기준으로 `회사 성격 입금 총액 = 80만원`이 맞는 상태다

## 2026-05-08 대시보드 핵심 지표 카드형 레이아웃 조정
- 변경 파일:
  - `app.py`
  - `Memory.md`
- 변경 내용:
  - 대시보드 상단 핵심 지표 영역을 기본 `st.metric` 나열 대신 커스텀 HTML/CSS 카드 스트립으로 변경
  - 카드 구성은 `입금 원금`, `보유 현금`, `현재 평가액`, `원금 대비 평가손익`, `원금 대비 수익률` 5개로 정리
  - `보유 현금` 카드에는 상단 `수정` 배지와 `아래 현금 조정 카드에서 바로 수정` 안내 문구 추가
  - 반응형 CSS를 넣어 좁은 화면에서는 2열, 더 좁은 화면에서는 1열로 줄어들도록 조정
- 검증:
  - `python -m compileall app.py src scripts tests`
  - `python -m unittest discover -s tests -p "test_*.py"`
  - 결과: 테스트 30건 통과
- 비고:
  - 이번 턴은 대시보드 상단 카드 레이아웃만 바꿨고, 계산 로직과 아래 차트/폼 영역은 유지
  - 실제 배포 화면 반영은 배포/재실행 후 브라우저에서 최종 시각 확인이 필요

## 2026-05-08 배포 웹 미반영 원인 확인
- 변경 파일:
  - `Memory.md`
- 변경 내용:
  - 배포 웹 대시보드를 다시 검증해 현재 표시 텍스트를 확인
  - 웹은 아직 기존 `포트폴리오 평가액 / 실제 성과 / 투입 원금 / 현금 / 누적 이자` 레이아웃을 보여주고 있어 새 카드형 메트릭 UI는 반영되지 않음
  - 로컬 git 상태 확인 결과 `app.py` 포함 다수 변경이 미커밋 상태이며, `HEAD`와 `origin/main`은 둘 다 `a583b10`으로 같아 원격에는 새 UI 변경이 아직 올라가지 않았음
- 검증:
  - `git status --short`
  - `git log --oneline --decorate -n 8`
  - `python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase --text-output artifacts\\web-dashboard-current.txt`
- 결과:
  - 배포 웹은 기존 레이아웃 유지
  - 로컬 변경은 아직 커밋/푸시 전 상태
- 비고:
  - 웹 반영을 위해서는 관련 변경을 커밋하고 원격으로 푸시한 뒤 Streamlit 배포가 다시 돌아야 함

## 2026-05-08 대시보드 카드 HTML 렌더링 보정
- 변경 파일:
  - `app.py`
  - `Memory.md`
- 변경 내용:
  - 첫 배포 후 대시보드 카드 일부가 HTML 문자열 그대로 노출되는 현상 확인
  - 원인: 카드 5개를 하나의 큰 HTML 블록으로 이어 붙이는 방식이 배포 환경에서 안정적으로 렌더링되지 않음
  - 조치: `render_dashboard_metric_strip()`를 `st.columns()` 기반으로 바꾸고, 카드마다 개별 `st.markdown(..., unsafe_allow_html=True)`를 호출하도록 수정
- 검증:
  - `python -m compileall app.py src scripts tests`
  - `python -m unittest discover -s tests -p "test_*.py"`
  - 결과: 테스트 30건 통과
- 비고:
  - 이 수정은 카드 스타일/라벨은 유지하면서 렌더 방식만 안전하게 바꾸는 최소 패치다

## 2026-05-08 커밋 푸시 및 배포 확인
- 변경 파일:
  - `Memory.md`
- 변경 내용:
  - `6d34396` `Refine Supabase rollup metrics and dashboard cards` 커밋을 `origin/main`에 푸시
  - 첫 배포 반영 후 대시보드 카드 라벨(`입금 원금`, `보유 현금`, `현재 평가액`, `원금 대비 평가손익`, `원금 대비 수익률`)은 웹에 나타났지만 일부 카드 HTML이 그대로 노출되는 현상 확인
  - `92a86d3` `Fix dashboard metric card rendering` 커밋으로 카드 렌더 방식을 개별 `st.markdown` 호출로 보정 후 다시 푸시
- 검증:
  - `git push origin main`
  - `python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase --text-output artifacts\\web-dashboard-current.txt`
  - `python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase --screenshot artifacts\\deploy-dashboard-current.png`
  - `python scripts/verify_streamlit_deployment.py --page dashboard --expect-backend supabase --text-output artifacts\\deploy-final-check.txt --screenshot artifacts\\deploy-final-check.png`
- 결과:
  - 배포 텍스트 기준 새 카드 라벨은 웹에 반영됨
  - `dashboard-metric-card__label`, `</div>` 같은 raw HTML 텍스트 노출은 보정 후 재현되지 않음
  - 다만 배포 검증 스크린샷은 시점에 따라 대시보드 대신 로그인 폼이 본문에 잠시 보이는 등 세션/재렌더 타이밍 편차가 있어, 브라우저 수동 확인까지 하면 더 안전함
- 비고:
  - 현재 원격 최신 커밋은 `92a86d3`

## 2026-05-08 대시보드 카드 문자열 렌더링 2차 보정
- 변경 파일:
  - `app.py`
  - `Memory.md`
- 변경 내용:
  - 배포 웹에서 카드 HTML 일부가 여전히 조각 문자열처럼 보이는 현상을 재확인
  - `render_dashboard_metric_strip()` 내부 카드 마크업을 들여쓰기 포함 멀티라인 f-string에서 단일 연결 문자열로 바꿔 Markdown 파서 간섭 여지를 제거
- 검증:
  - `python -m compileall app.py src scripts tests`
  - `python -m unittest discover -s tests -p "test_*.py"`
  - 결과: 테스트 30건 통과

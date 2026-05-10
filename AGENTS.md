# AGENTS.md

## 프로젝트 개요
- 이 저장소는 `Python + Streamlit` 기반 은퇴 포트폴리오 관리 앱이다.
- 앱 진입점은 `app.py`다.
- 저장소는 `Supabase`를 우선 사용하고, 필요 시 `SQLite`(`data/portfolio.db`)로 fallback 한다.
- Streamlit UI 테마와 서버 기본 설정은 `.streamlit/config.toml`을 기준으로 유지한다.

## 우선 확인 파일
- `requirements.txt`
- `README.md`
- `.streamlit/config.toml`
- `app.py`
- `src/db.py`
- `src/auth.py`
- `src/analytics.py`
- `src/sqlite_db.py`
- `scripts/run_daily_rollup.py`
- `scripts/verify_streamlit_deployment.py`

## 작업 순서
1. `Get-ChildItem -Force` 또는 `tree /F /A`로 구조를 먼저 확인한다.
2. 작업 범위와 관련된 파일만 읽고 수정 범위를 제한한다.
3. 구현 전 `Memory.md`와 기존 문서를 보고 현재 진행 상황을 확인한다.
4. 수정 후 가능한 범위에서 검증을 수행한다.
5. 작업 종료 시 `Memory.md`를 업데이트한다.

## 변경 원칙
- 요청 범위를 벗어나는 구조 변경이나 대규모 리팩토링은 하지 않는다.
- 기존 파일이 있으면 덮어쓰지 않는다.
- `.streamlit/config.toml`의 테마/서버 설정은 요청이 없는 한 변경하지 않는다.
- `setup_supabase.sql`, `src/db.py`, `src/sqlite_db.py`는 저장소 동작에 직접 영향을 주므로 관련 작업 외에는 건드리지 않는다.

## 환경 변수 및 시크릿
- `.env` 파일은 자동 생성하지 않는다.
- 예시 값은 `.env.example`에만 기록한다.
- 실제 시크릿은 `.streamlit/secrets.toml`, Streamlit Cloud secrets, 또는 OS 환경 변수에 둔다.
- `SUPABASE_SERVICE_ROLE_KEY`와 같은 관리자 키는 브라우저 UI나 커밋에 노출하지 않는다.

## 실행 명령
```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

## 설치 원칙
- 작업 중 필요한 패키지나 도구가 없으면 중단하지 말고 프로젝트 로컬 환경에 설치하면서 진행한다.
- 설치는 글로벌이 아닌 현재 저장소 기준으로 수행하고, 설치한 항목과 이유는 `Memory.md`에 기록한다.

## 권장 검증 명령
```powershell
python -m compileall app.py src scripts tests
python -m unittest discover -s tests -p "test_*.py"
```

## 커밋 및 배포 규칙
- 사용자가 별도 중단 지시를 하지 않은 상태에서, 현재 요청 범위의 검증이 `100% 완료`되면 Codex가 같은 턴에서 커밋과 원격 배포까지 마무리한다.
- 이 저장소에서 `100% 완료`는 최소한 다음을 모두 만족하는 상태로 본다.
  - 요청 범위 코드 수정 반영 완료
  - `python -m compileall app.py src scripts tests` 성공
  - `python -m unittest discover -s tests -p "test_*.py"` 성공
  - 배포가 필요한 작업이면 `scripts/verify_streamlit_deployment.py` 또는 동등한 운영 검증까지 성공
- 커밋/배포 시에는 요청 범위와 무관한 로컬 산출물, 캐시, 개인 DB 파일은 제외한다.
- 커밋 해시, 배포 방법, 검증 결과는 반드시 `Memory.md`에 기록한다.

## 운영 관련 메모
- 배포/운영 점검 스크립트는 `scripts/verify_streamlit_deployment.py`를 우선 사용한다.
- 일별 롤업 배치는 `scripts/run_daily_rollup.py`와 `.github/workflows/daily-rollup.yml` 기준으로 관리한다.
- 배포 백엔드 선택 동작은 `PORTFOLIO_BACKEND`, `SUPABASE_URL`, `SUPABASE_KEY` 설정에 의존한다.

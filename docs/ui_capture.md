# Streamlit UI 캡처 자동화

## 목적

Streamlit 앱의 현재 화면을 디자인 리뷰용 PNG 산출물로 저장한다. 기본 실행은 `?demo=1&capture=1` URL을 사용해 샘플 데이터 화면을 캡처하며, 실제 사용자 데이터나 시크릿이 캡처되지 않도록 데모 모드를 우선 사용한다.

## 설치

```powershell
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
```

Linux GitHub Actions 환경에서 브라우저 시스템 의존성까지 함께 설치해야 하면 아래 명령을 사용한다.

```powershell
python -m playwright install --with-deps chromium
```

## 로컬 실행

기본 명령은 로컬 Streamlit 앱이 없으면 자동으로 `streamlit run app.py`를 실행하고, `http://localhost:8501/?demo=1&capture=1`에 접속한다.

```powershell
python scripts/capture_app.py --viewport desktop
```

로컬 자동 실행 시 캡처 기준일은 기본 `2026-05-15`로 고정된다. 다른 기준일이 필요하면 `PORTFOLIO_CAPTURE_REFERENCE_DATE=YYYY-MM-DD`를 지정한다.

이미 실행 중인 앱을 캡처하려면 URL을 직접 지정한다.

```powershell
python scripts/capture_app.py `
  --url "http://localhost:8501/?demo=1&capture=1" `
  --viewport all `
  --out-dir artifacts/ui_captures
```

환경 변수로도 대상 URL을 지정할 수 있다.

```powershell
$env:CAPTURE_BASE_URL = "http://localhost:8501/?demo=1&capture=1"
python scripts/capture_app.py --viewport desktop
```

## CLI 옵션

| 옵션 | 설명 |
| --- | --- |
| `--url` | 접속할 앱 URL. 없으면 `CAPTURE_BASE_URL`, 그다음 로컬 자동 실행을 사용 |
| `--out-dir` | 캡처 산출물 루트. 기본값은 `artifacts/ui_captures` |
| `--viewport` | `desktop`, `tablet`, `mobile`, `all` 중 선택 |
| `--strict` | `required: false` 블록 누락도 실패 처리 |
| `--config` | 캡처 블록 YAML 경로. 기본값은 `config/capture_blocks.yaml` |
| `--wait-ms` | 페이지, selector, loading 안정화 대기 시간. 기본값은 `30000` |

## 캡처 안정화

- 캡처 URL은 `?demo=1&capture=1`을 사용한다.
- `capture=1`에서는 화면에 직접 영향을 주는 기준일을 고정해 데모 seed, 그래프 데이터, 테이블 행 수가 반복 실행마다 흔들리지 않게 한다.
- Playwright 캡처 전 Streamlit sidebar는 desktop에서 expanded, tablet/mobile에서 collapsed 기본 상태로 맞춘다.
- 캡처 전후로 Streamlit spinner/progress/skeleton이 사라질 때까지 대기하고, animation/transition CSS를 비활성화한다.
- selector 누락 시 로그에 `viewport`, `name`, `selector`, `required` 여부를 출력하고, 같은 내용은 `manifest.json`의 `missing_selectors`에도 기록한다.

## 산출물 구조

```text
artifacts/ui_captures/
└── 2026-05-15_153000/
    └── desktop/
        ├── full_page.png
        ├── blocks/
        │   ├── 01_header.png
        │   ├── 02_input_panel.png
        │   ├── 03_summary_cards.png
        │   ├── 04_asset_allocation_chart.png
        │   ├── 05_retirement_projection_chart.png
        │   ├── 06_holdings_table.png
        │   └── 07_recommendation_panel.png
        └── manifest.json
```

`manifest.json`에는 캡처 시각, git commit, 브랜치, 앱 URL, viewport, 블록별 selector, output path, 성공/실패 상태, 누락 selector가 기록된다.

## 캡처 블록 설정

기본 설정은 `config/capture_blocks.yaml`에 있다. Streamlit `st.container(key="capture_xxx")`는 DOM에서 `.st-key-capture_xxx` CSS class로 노출되므로 Playwright selector는 해당 class를 사용한다.

## 보안 주의

- 기본 URL은 `?demo=1&capture=1`을 포함한다.
- 로컬 자동 실행 시 `PORTFOLIO_BACKEND=sqlite`와 캡처 전용 임시 SQLite 파일을 사용한다.
- 실제 운영 URL을 직접 지정할 경우 PR 첨부 전에 `manifest.json`의 `app_url`과 PNG에 개인정보, 계좌번호, 토큰, 시크릿이 포함되지 않았는지 확인한다.

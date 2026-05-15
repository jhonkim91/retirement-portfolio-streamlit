# 은퇴 포트폴리오 앱 개선 리뷰

> 분석 기준: `app.py` (4,560줄 / 194 KB), `requirements.txt`, `src/` 구조, GitHub Actions 워크플로

---

## 🔴 우선순위 HIGH — 성능 / 안정성

### 1. `app.py` 단일 파일 4,560줄 — 분리 필수

Streamlit은 **사용자 인터랙션(버튼 클릭, 슬라이더 이동)마다 스크립트 전체를 재실행**합니다.  
4,560줄이 한 파일에 있으면 매 rerun마다 파싱·임포트 오버헤드가 발생합니다.

**권장 구조**
```
pages/
  dashboard.py   # render_dashboard() 이동
  trades.py      # render_trades() 이동
  data.py        # render_data() 이동
src/
  ui/
    charts.py    # 차트 렌더 함수 모음
    forms.py     # 폼 렌더 함수 모음
    layout.py    # 공통 레이아웃 헬퍼
app.py           # set_page_config + st.navigation 만 남김 (~50줄)
```

Streamlit의 `st.Page` + `st.navigation` (v1.36+)을 쓰면 현재 세션 상태로 수동 관리하는
`active_page` 로직도 제거할 수 있습니다.

---

### 2. DB / 시세 호출에 `@st.cache_data` TTL 미적용

현재 `@st.cache_data`는 디자인 토큰 로드에만 사용됩니다.  
`list_holdings`, `list_trade_logs`, `fetch_latest_price` 등 **무거운 I/O 함수에 TTL이 없으면**
버튼 한 번 누를 때마다 Supabase / yfinance 를 반복 호출합니다.

```python
# 예시
@st.cache_data(ttl=60, show_spinner=False)
def cached_list_holdings(account_id: int):
    return list_holdings(account_id)

@st.cache_data(ttl=180, show_spinner=False)   # 3분 캐시
def cached_fetch_price(symbol: str):
    return fetch_latest_price(symbol)
```

특히 **yfinance**는 외부 HTTP 요청이라 응답이 느리고 rate-limit에 걸릴 수 있어
TTL 캐시가 없으면 앱 체감 속도에 큰 영향을 줍니다.

---

### 3. `altair==5.0.1` 버전 핀 — 업데이트 필요

`altair==5.0.1`은 2023년 릴리스입니다. 현재(2026.05) 최신은 **5.5.x** 입니다.  
Streamlit 1.55.0이 내부적으로 Altair 최신을 지원하는데 구버전을 핀하면
렌더링 불일치 · 경고 메시지가 발생할 수 있습니다.

```txt
# 수정 전
altair==5.0.1

# 수정 후
altair>=5.4,<6
```

---

### 4. GitHub Actions KIS WebSocket worker — 안정성

현재 구성은 장중 2세션(175분 + 225분)을 **Actions 단일 Job으로 실행**합니다.  
무료 티어 제한(월 2,000분)이 있고, 네트워크 단절·타임아웃 시 재시도 로직 없이 그냥 종료됩니다.

- `timeout --signal=SIGINT` 방식은 graceful shutdown은 되지만,  
  중간 연결 끊김 → worker_status가 `running`에서 멈추는 경우가 있을 수 있음
- **개선안**: `scripts/run_kis_quote_worker.py` 내부에 WebSocket 재연결 로직 추가  
  (`websocket-client`의 `on_close` 핸들러에서 일정 횟수 재연결 시도)

---

### 5. Supabase hotfix 코드가 프로덕션에 노출

`render_operation_error()` 내부에 **운영 DB hotfix 절차**가 UI에 직접 노출됩니다.  
일반 사용자에게 불필요한 정보이고, `is_accounts_hotfix_error`가 항상 `False`를 반환하도록 개선하거나
관리자 모드(환경변수 플래그)에서만 노출하는 것이 좋습니다.

---

## 🟡 우선순위 MEDIUM — 코드 품질

### 6. 전역 상수 남용

`FEARGREED_*`, `TREEMAP_*`, `CHART_*` 등 30개 이상의 전역 변수가 모듈 레벨에 선언됩니다.  
이 값들은 `DESIGN_TOKENS`에서 파생되므로 **`dataclass` 또는 `SimpleNamespace`로 묶는 것**이 가독성·유지보수에 좋습니다.

```python
from types import SimpleNamespace

@st.cache_data(show_spinner=False)
def build_chart_colors(tokens: dict) -> SimpleNamespace:
    return SimpleNamespace(
        line=tokens["chart_line_color"],
        up=tokens["chart_up_color"],
        down=tokens["chart_down_color"],
        ...
    )

C = build_chart_colors(DESIGN_TOKENS)
# 사용: C.line, C.up, C.down
```

---

### 7. `TRADE_LOG_TABLE_COLUMN_WEIGHTS` 하드코딩

컬럼 9개의 비율을 `[1.05, 1.45, 1.0, 0.9, 0.95, 0.9, 0.9, 1.0, 1.3]` 으로
하드코딩하면 컬럼 순서 변경 시 버그가 생깁니다.  
`dict` 형태로 컬럼명과 비율을 묶어 관리하는 것을 권장합니다.

---

### 8. `st_keyup` / `st_echarts` ImportError fallback

현재 `st_keyup = None`, `st_echarts = None` 으로 fallback하고  
실제 사용 코드에서 `if st_keyup is not None:` 분기를 해야 합니다.  
의존성이 핵심 기능이라면 fallback 대신 `requirements.txt`에서 필수화하고  
배포 시 설치 확인 단계를 넣는 편이 더 안전합니다.

---

## 🟢 우선순위 LOW — 디자인 / UX

### 9. 다크모드 미지원

`.streamlit/config.toml`의 테마가 라이트 전용입니다.  
Streamlit은 `[theme] base = "dark"` 또는 `base = "light"`를 지원하며,  
CSS 변수를 `prefers-color-scheme` 미디어쿼리로 전환하면 시스템 다크모드를 존중할 수 있습니다.

```css
/* app.css */
@media (prefers-color-scheme: dark) {
  :root {
    --panel-color: #1e2736;
    --text-color: #f0f4f8;
    /* ... */
  }
}
```

---

### 10. 모바일 레이아웃

`layout="wide"` 고정이므로 모바일에서는 컬럼이 매우 좁아집니다.  
`st.columns`에서 `[1, 2]` 비율을 쓸 때 모바일 viewport를 고려해  
핵심 지표 카드(`metric`) 위주로 세로 스택을 우선 배치하는 것을 검토해 보세요.

---

### 11. `page_icon` 업그레이드

현재 `:material/account_balance_wallet:` Material 아이콘을 쓰고 있는데,  
앱 특성을 더 잘 표현하는 `💼` 이모지나 실제 `.ico` 파일로 교체하면  
브라우저 탭·공유 미리보기 품질이 올라갑니다.

---

### 12. 로딩 스피너 / 스켈레톤 UI 부재

시세 갱신·스냅샷 저장처럼 수 초가 걸리는 작업에  
`st.spinner` 또는 `st.status`로 진행 상태를 보여주면  
사용자가 앱이 멈췄다고 오인하는 것을 방지할 수 있습니다.

```python
with st.status("현재가 갱신 중...", expanded=True) as status:
    results = refresh_prices(holdings)
    status.update(label="갱신 완료", state="complete")
```

---

## 📋 요약표

| # | 영역 | 항목 | 우선순위 | 예상 난이도 |
|---|------|------|----------|-------------|
| 1 | 성능 | app.py 분리 + st.navigation | 🔴 HIGH | 높음 |
| 2 | 성능 | DB·시세 캐시 TTL 추가 | 🔴 HIGH | 낮음 |
| 3 | 안정성 | altair 버전 핀 해제 | 🔴 HIGH | 매우 낮음 |
| 4 | 안정성 | KIS WebSocket 재연결 로직 | 🔴 HIGH | 중간 |
| 5 | 보안 | hotfix 메시지 관리자 전용화 | 🔴 HIGH | 낮음 |
| 6 | 품질 | 전역 색상 상수 네임스페이스화 | 🟡 MEDIUM | 낮음 |
| 7 | 품질 | 컬럼 비율 dict화 | 🟡 MEDIUM | 낮음 |
| 8 | 품질 | 선택적 의존성 처리 방식 정리 | 🟡 MEDIUM | 낮음 |
| 9 | 디자인 | 다크모드 CSS 변수 추가 | 🟢 LOW | 중간 |
| 10 | UX | 모바일 레이아웃 개선 | 🟢 LOW | 중간 |
| 11 | UX | page_icon 교체 | 🟢 LOW | 매우 낮음 |
| 12 | UX | 스피너/스켈레톤 추가 | 🟢 LOW | 낮음 |

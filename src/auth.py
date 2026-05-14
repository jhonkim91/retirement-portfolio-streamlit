from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import streamlit as st

if TYPE_CHECKING:
    from supabase import Client


DEFAULT_SUPABASE_URL = ""
DEFAULT_EMAIL_REDIRECT_TO = "https://retirement-portfolio-app-nh2vq9ferqnpehsslbykbe.streamlit.app/"
SESSION_STATE_KEY = "auth_session"
BACKEND_STATE_KEY = "db_backend_state"
CLIENT_STATE_KEY = "supabase_client_state"
DEMO_SESSION_MODE = "local_demo"
DEMO_USER_ID = "local-demo-user"
DEMO_USER_EMAIL = "test"
SESSION_REFRESH_SKEW_SECONDS = 60
_FALLBACK_STATE: dict[str, Any] = {}


def _state_store() -> dict[str, Any]:
    try:
        return st.session_state
    except Exception:
        return _FALLBACK_STATE


def _get_config_value(name: str, default: str = "") -> str:
    try:
        secret_value = st.secrets.get(name)
    except Exception:
        secret_value = None
    if secret_value not in (None, ""):
        return str(secret_value).strip()
    return str(os.getenv(name, default)).strip()


def _supabase_url() -> str:
    """현재 세션에서 사용할 Supabase URL을 반환한다."""

    return _get_config_value("SUPABASE_URL", DEFAULT_SUPABASE_URL)


def _is_valid_supabase_url(url: str) -> bool:
    """Supabase hosted 프로젝트 URL 형식인지 확인한다."""

    parsed = urlparse(str(url or "").strip())
    return parsed.scheme == "https" and parsed.netloc.endswith(".supabase.co")


def _supabase_key() -> str:
    """현재 세션에서 사용할 Supabase 키를 반환한다."""

    return _get_config_value("SUPABASE_KEY")


def _email_redirect_to() -> str:
    """회원가입 메일 링크에 사용할 리다이렉트 URL을 반환한다."""

    return _get_config_value("SUPABASE_EMAIL_REDIRECT_TO", DEFAULT_EMAIL_REDIRECT_TO)


def get_demo_credentials() -> tuple[str, str]:
    """초기 화면 데모 접속에 사용할 이메일과 비밀번호를 반환한다."""

    email = _get_config_value("DEMO_LOGIN_EMAIL")
    password = _get_config_value("DEMO_LOGIN_PASSWORD")
    return str(email).strip(), str(password)


def has_demo_credentials() -> bool:
    """데모 자동 로그인 자격 증명 존재 여부를 반환한다."""

    email, password = get_demo_credentials()
    return bool(email and password)


def is_enabled() -> bool:
    """현재 실행 환경에 Supabase 인증 설정이 있는지 확인한다."""

    return _is_valid_supabase_url(_supabase_url()) and bool(_supabase_key())


def _serialize_session(session: Any) -> dict[str, Any]:
    user = getattr(session, "user", None)
    return {
        "access_token": getattr(session, "access_token", ""),
        "refresh_token": getattr(session, "refresh_token", ""),
        "expires_at": getattr(session, "expires_at", None),
        "user_id": getattr(user, "id", None),
        "email": getattr(user, "email", None),
        "mode": "supabase",
    }


def _save_session(session: Any) -> None:
    if not session:
        return
    store = _state_store()
    store[SESSION_STATE_KEY] = _serialize_session(session)
    store.pop(BACKEND_STATE_KEY, None)


def _save_demo_session() -> None:
    """로컬 SQLite 기반 데모 세션을 저장한다."""

    store = _state_store()
    store[SESSION_STATE_KEY] = {
        "access_token": "",
        "refresh_token": "",
        "expires_at": None,
        "user_id": DEMO_USER_ID,
        "email": DEMO_USER_EMAIL,
        "mode": DEMO_SESSION_MODE,
    }
    store.pop(BACKEND_STATE_KEY, None)


def _client_state() -> dict[str, Any]:
    """클라이언트와 세션 서명을 캐시하는 상태를 반환한다."""
    store = _state_store()
    state = store.get(CLIENT_STATE_KEY)
    if isinstance(state, dict):
        return state

    state = {
        "client": None,
        "session_signature": "",
    }
    store[CLIENT_STATE_KEY] = state
    return state


def _session_signature(session: dict[str, Any] | None) -> str:
    """세션의 unique signature를 생성한다."""
    if not session:
        return ""
    return "|".join(
        [
            str(session.get("access_token") or ""),
            str(session.get("refresh_token") or ""),
            str(session.get("expires_at") or ""),
        ]
    )


def _session_expires_soon(session: dict[str, Any] | None, *, skew_seconds: int = SESSION_REFRESH_SKEW_SECONDS) -> bool:
    """세션이 곧 만료될 예정인지 확인한다."""
    if not session:
        return False
    expires_at = session.get("expires_at")
    if expires_at in (None, ""):
        return False
    try:
        return int(expires_at) <= int(time.time()) + int(skew_seconds)
    except Exception:
        return False


def clear_session() -> None:
    store = _state_store()
    store.pop(SESSION_STATE_KEY, None)
    store.pop(BACKEND_STATE_KEY, None)
    store.pop(CLIENT_STATE_KEY, None)


def _raw_session() -> dict[str, Any] | None:
    session = _state_store().get(SESSION_STATE_KEY)
    return session if isinstance(session, dict) else None


def _create_client() -> Client:
    """Supabase 클라이언트를 실제 네트워크 인증 작업 직전에 로드해 생성한다."""

    from supabase import create_client

    return create_client(_supabase_url(), _supabase_key())


def get_client(*, refresh_if_needed: bool = False) -> Client:
    """현재 세션 기준 Supabase 클라이언트를 반환한다.
    
    세션 signature와 만료 시간을 캐시해 불필요한 set_session() 호출을 줄인다.
    """
    if not is_enabled():
        raise RuntimeError("Supabase 인증이 설정되지 않았습니다.")

    state = _client_state()
    client = state.get("client")
    if client is None:
        client = _create_client()
        state["client"] = client
        state["session_signature"] = ""

    session = _raw_session()
    if not session or is_demo_user():
        return client

    access_token = str(session.get("access_token") or "")
    refresh_token = str(session.get("refresh_token") or "")
    if not access_token or not refresh_token:
        clear_session()
        return client

    current_signature = _session_signature(session)
    needs_refresh = refresh_if_needed or _session_expires_soon(session)

    # 세션이 동일하고 만료 임박도 아니면 set_session을 다시 호출하지 않는다.
    if state.get("session_signature") == current_signature and not needs_refresh:
        return client

    try:
        response = client.auth.set_session(access_token, refresh_token)
    except Exception:
        clear_session()
        return _create_client()

    if response.session:
        _save_session(response.session)
        state["session_signature"] = _session_signature(_raw_session())
    else:
        state["session_signature"] = current_signature

    return client


def refresh_session_state() -> None:
    """명시적으로 세션을 점검하고 필요 시 refresh한다."""
    if is_demo_user():
        return
    if not is_enabled():
        clear_session()
        return
    # 명시적으로 세션 점검이 필요할 때만 refresh 경로를 탄다.
    get_client(refresh_if_needed=True)


def sign_in(email: str, password: str) -> Any:
    client = get_client()
    response = client.auth.sign_in_with_password(
        {
            "email": str(email or "").strip(),
            "password": str(password or ""),
        }
    )
    if response.session:
        _save_session(response.session)
    return response


def sign_in_demo_user() -> dict[str, str]:
    """초기 화면의 데모 접속 버튼용 자동 로그인 또는 로컬 데모 진입을 수행한다."""

    email, password = get_demo_credentials()
    if email and password:
        sign_in(email=email, password=password)
        return {"email": email, "mode": "supabase"}

    _save_demo_session()
    return {"email": DEMO_USER_EMAIL, "mode": DEMO_SESSION_MODE}


def sign_up(email: str, password: str) -> Any:
    """이메일과 비밀번호로 회원가입을 시도한다."""

    client = get_client()
    options: dict[str, Any] = {}
    redirect_url = _email_redirect_to()
    if redirect_url:
        options["email_redirect_to"] = redirect_url
    response = client.auth.sign_up(
        {
            "email": str(email or "").strip(),
            "password": str(password or ""),
            "options": options,
        }
    )
    if response.session:
        _save_session(response.session)
    return response


def resend_signup(email: str) -> Any:
    """가입 확인 메일을 다시 발송한다."""

    client = get_client()
    payload: dict[str, Any] = {
        "type": "signup",
        "email": str(email or "").strip(),
    }
    redirect_url = _email_redirect_to()
    if redirect_url:
        payload["options"] = {"email_redirect_to": redirect_url}
    return client.auth.resend(payload)


def exchange_code_for_session(auth_code: str) -> Any:
    client = get_client()
    response = client.auth.exchange_code_for_session({"auth_code": str(auth_code or "").strip()})
    if response.session:
        _save_session(response.session)
    return response


def verify_otp(token_hash: str, otp_type: str) -> Any:
    client = get_client()
    response = client.auth.verify_otp(
        {
            "token_hash": str(token_hash or "").strip(),
            "type": str(otp_type or "email").strip(),
        }
    )
    if response.session:
        _save_session(response.session)
    return response


def sign_out() -> None:
    if is_enabled() and not is_demo_user():
        try:
            client = get_client()
            client.auth.sign_out()
        except Exception:
            pass
    clear_session()


def is_authenticated() -> bool:
    return bool(get_user_id())


def is_demo_user() -> bool:
    """현재 세션이 로컬 데모 세션인지 반환한다."""

    session = _raw_session()
    if not session:
        return False
    return str(session.get("mode") or "").strip() == DEMO_SESSION_MODE


def get_user() -> dict[str, Any] | None:
    session = _raw_session()
    if not session:
        return None
    user_id = session.get("user_id")
    if not user_id:
        return None
    return {
        "id": user_id,
        "email": session.get("email"),
        "mode": session.get("mode"),
    }


def get_user_id() -> str | None:
    user = get_user()
    return str(user["id"]) if user and user.get("id") else None


def get_user_email() -> str | None:
    user = get_user()
    return str(user["email"]) if user and user.get("email") else None


def get_access_token() -> str | None:
    session = _raw_session()
    if not session:
        return None
    return str(session.get("access_token") or "") or None

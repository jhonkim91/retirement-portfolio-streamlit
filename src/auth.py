from __future__ import annotations

import os
from typing import Any

import streamlit as st
from supabase import Client, create_client


DEFAULT_SUPABASE_URL = "https://iyszkybxostbjfzbbymq.supabase.co"
DEFAULT_EMAIL_REDIRECT_TO = "https://retirement-portfolio-app-nh2vq9ferqnpehsslbykbe.streamlit.app/"
SESSION_STATE_KEY = "auth_session"
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


def _supabase_key() -> str:
    """현재 세션에서 사용할 Supabase 키를 반환한다."""

    return _get_config_value("SUPABASE_KEY")


def _email_redirect_to() -> str:
    """회원가입 메일 링크에 사용할 리다이렉트 URL을 반환한다."""

    return _get_config_value("SUPABASE_EMAIL_REDIRECT_TO", DEFAULT_EMAIL_REDIRECT_TO)


def is_enabled() -> bool:
    """현재 실행 환경에 Supabase 인증 설정이 있는지 확인한다."""

    return bool(_supabase_url() and _supabase_key())


def _serialize_session(session: Any) -> dict[str, Any]:
    user = getattr(session, "user", None)
    return {
        "access_token": getattr(session, "access_token", ""),
        "refresh_token": getattr(session, "refresh_token", ""),
        "expires_at": getattr(session, "expires_at", None),
        "user_id": getattr(user, "id", None),
        "email": getattr(user, "email", None),
    }


def _save_session(session: Any) -> None:
    if not session:
        return
    _state_store()[SESSION_STATE_KEY] = _serialize_session(session)


def clear_session() -> None:
    _state_store().pop(SESSION_STATE_KEY, None)


def _raw_session() -> dict[str, Any] | None:
    session = _state_store().get(SESSION_STATE_KEY)
    return session if isinstance(session, dict) else None


def get_client() -> Client:
    """현재 세션 기준 Supabase 클라이언트를 반환한다."""

    if not is_enabled():
        raise RuntimeError("Supabase 인증이 설정되지 않았습니다.")

    client = create_client(_supabase_url(), _supabase_key())
    session = _raw_session()
    if not session:
        return client

    access_token = str(session.get("access_token") or "")
    refresh_token = str(session.get("refresh_token") or "")
    if not access_token or not refresh_token:
        clear_session()
        return client

    try:
        response = client.auth.set_session(access_token, refresh_token)
    except Exception:
        clear_session()
        return client

    if response.session:
        _save_session(response.session)
    return client


def refresh_session_state() -> None:
    if not is_enabled():
        clear_session()
        return
    get_client()


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
    if is_enabled():
        try:
            client = get_client()
            client.auth.sign_out()
        except Exception:
            pass
    clear_session()


def is_authenticated() -> bool:
    return bool(get_user_id())


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

import hmac
import hashlib
import time
from typing import Optional
from fastapi import Request, Response
from .openrosa import AUTH_USER, AUTH_PASS, check_credentials

COOKIE_NAME = "kobo_session"
COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days in seconds (2,592,000s)

def get_secret_key() -> bytes:
    """Key dynamically derived from username and current password.

    Changing the password instantly invalidates all issued session tokens.
    """
    return hashlib.sha256(f"kobo_cookie_secret:{AUTH_USER}:{AUTH_PASS}".encode("utf-8")).digest()

def create_session_token(username: Optional[str] = None) -> str:
    user = username or AUTH_USER
    expires_at = int(time.time()) + COOKIE_MAX_AGE
    payload = f"{user}:{expires_at}"
    sig = hmac.new(get_secret_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"

def verify_session_token(token: Optional[str]) -> bool:
    if not token or not isinstance(token, str):
        return False
    parts = token.split(":")
    if len(parts) != 3:
        return False
    user, expires_at_str, sig = parts
    if user != AUTH_USER:
        return False
    try:
        expires_at = int(expires_at_str)
    except ValueError:
        return False
    if time.time() > expires_at:
        return False
    payload = f"{user}:{expires_at}"
    expected_sig = hmac.new(get_secret_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected_sig)

def is_authenticated(
    authorization: Optional[str] = None,
    session_cookie: Optional[str] = None,
    request: Optional[Request] = None
) -> bool:
    # 1. Check persistent 30-day cookie
    token = session_cookie
    if not token and request is not None:
        token = request.cookies.get(COOKIE_NAME)
    if token and verify_session_token(token):
        return True

    # 2. Check HTTP Basic Auth header
    auth_header = authorization
    if not auth_header and request is not None:
        auth_header = request.headers.get("authorization")
    if auth_header and check_credentials(auth_header):
        return True

    return False

def set_session_cookie(response: Response, username: Optional[str] = None) -> Response:
    token = create_session_token(username)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        expires=COOKIE_MAX_AGE,
        path="/",
        httponly=True,
        samesite="lax",
        secure=False
    )
    return response

def check_auth_or_401(
    authorization: Optional[str] = None,
    session_cookie: Optional[str] = None,
    request: Optional[Request] = None
) -> Optional[Response]:
    if is_authenticated(authorization=authorization, session_cookie=session_cookie, request=request):
        return None
    return Response(
        content="Autenticação necessária. O acesso direto e aberto à API foi desativado por segurança dos dados.",
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="KoBo Renova-me Dados Protegidos"'}
    )

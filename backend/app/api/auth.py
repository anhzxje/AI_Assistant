"""Local authentication API."""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from backend.app.config import get_backend_settings
from backend.app.schemas.auth_schema import (
    GoogleLoginStatusResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    MeResponse,
    UserPublic,
)
from backend.app.services.auth.auth_service import (
    authenticate_user,
    get_current_user_optional,
    get_user_store,
    issue_token,
)
from backend.app.services.auth.google_oauth import GOOGLE_LOGIN_SCOPES, GoogleOAuthService
from backend.app.services.auth.user_store import UserRecord

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest) -> LoginResponse:
    user = authenticate_user(email=request.email, password=request.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email hoặc mật khẩu không đúng.")
    return LoginResponse(access_token=issue_token(user), user=to_public_user(user))


@router.post("/logout", response_model=LogoutResponse)
def logout() -> LogoutResponse:
    return LogoutResponse(ok=True)


@router.get("/me", response_model=MeResponse)
def me(user: UserRecord | None = Depends(get_current_user_optional)) -> MeResponse:
    if user is None:
        return MeResponse(authenticated=False, user=None)
    return MeResponse(authenticated=True, user=to_public_user(user))


@router.get("/google/status", response_model=GoogleLoginStatusResponse)
def google_login_status() -> GoogleLoginStatusResponse:
    service = GoogleOAuthService()
    return GoogleLoginStatusResponse(
        configured=service.configured,
        scopes=GOOGLE_LOGIN_SCOPES,
        redirect_uri=get_backend_settings().google_redirect_uri,
        message=(
            "Google Login đã được cấu hình."
            if service.configured
            else "Google Login chưa được cấu hình trên máy này."
        ),
    )


@router.get("/google/start")
def google_login_start():
    service = GoogleOAuthService()
    if not service.configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Login chưa được cấu hình trên máy này.",
        )
    return RedirectResponse(service.authorization_url(service.create_state()), status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/google/callback")
def google_login_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    frontend_url = get_backend_settings().frontend_url.rstrip("/")
    if error:
        return RedirectResponse(f"{frontend_url}/login?{urlencode({'error': error})}")
    if not code or not state:
        return redirect_auth_error(frontend_url, "Thiếu mã xác thực Google.")

    service = GoogleOAuthService()
    if not service.configured:
        return redirect_auth_error(frontend_url, "Google Login chưa được cấu hình trên máy này.")
    if not service.validate_state(state):
        return redirect_auth_error(frontend_url, "Phiên đăng nhập Google đã hết hạn hoặc không hợp lệ.")

    try:
        tokens = service.exchange_code(code)
        profile = service.profile_from_tokens(tokens)
        user = get_user_store().upsert_google_user(
            email=profile.email,
            display_name=profile.display_name,
            google_sub=profile.sub,
        )
    except ValueError as exc:
        if str(exc) == "google_login_cannot_grant_admin":
            return redirect_auth_error(frontend_url, "Tài khoản quản lý cần đăng nhập bằng tài khoản nội bộ.")
        return redirect_auth_error(frontend_url, "Không đọc được hồ sơ Google.")
    except Exception:
        return redirect_auth_error(frontend_url, "Không hoàn tất được đăng nhập Google.")

    query = urlencode({"token": issue_token(user)})
    return RedirectResponse(f"{frontend_url}/auth/callback?{query}")


def to_public_user(user: UserRecord) -> UserPublic:
    return UserPublic(**user.public())


def redirect_auth_error(frontend_url: str, message: str) -> RedirectResponse:
    return RedirectResponse(f"{frontend_url}/login?{urlencode({'error': message})}")

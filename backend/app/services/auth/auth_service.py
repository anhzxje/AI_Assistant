"""FastAPI authentication dependencies."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.services.auth.token_service import TokenService
from backend.app.services.auth.user_store import UserRecord, UserStore


security = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def get_user_store() -> UserStore:
    return UserStore()


@lru_cache(maxsize=1)
def get_token_service() -> TokenService:
    return TokenService()


def authenticate_user(email: str, password: str) -> UserRecord | None:
    return get_user_store().verify_credentials(email=email, password=password)


def issue_token(user: UserRecord) -> str:
    return get_token_service().create_token(
        {
            "sub": user.user_id,
            "email": user.email,
            "role": user.role,
        }
    )


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> UserRecord | None:
    if credentials is None:
        return None
    payload = get_token_service().verify_token(credentials.credentials)
    if not payload:
        return None
    user_id = str(payload.get("sub") or "")
    user = get_user_store().get_by_id(user_id)
    if user is None or user.disabled:
        return None
    return user


def get_current_user(
    user: UserRecord | None = Depends(get_current_user_optional),
) -> UserRecord:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin_user(user: UserRecord = Depends(get_current_user)) -> UserRecord:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn cần đăng nhập với vai trò Người quản lý để truy cập trang này.",
        )
    return user

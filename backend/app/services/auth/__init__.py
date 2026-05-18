"""Local authentication services for OmniAssistant."""

from backend.app.services.auth.auth_service import (
    get_current_user,
    get_current_user_optional,
    require_admin_user,
)

__all__ = ["get_current_user", "get_current_user_optional", "require_admin_user"]

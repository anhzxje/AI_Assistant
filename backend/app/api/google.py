"""Read-only Google personal connector APIs."""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from backend.app.schemas.google_schema import (
    CalendarSyncRequest,
    CalendarListResponse,
    CalendarTodayResponse,
    DailyBriefingResponse,
    GoogleIntegrationStatusResponse,
    GmailSummaryResponse,
    GmailSyncRequest,
    GoogleStatusResponse,
    SyncResponse,
)
from backend.app.services.auth.google_oauth import GOOGLE_LOGIN_SCOPES, GoogleOAuthService
from backend.app.services.connectors.google_auth import GoogleAuthManager
from backend.app.services.connectors.google_auth import CALENDAR_READONLY_SCOPE, GMAIL_READONLY_SCOPE
from backend.app.services.connectors.personal_ingestion import PersonalIngestionService
from backend.app.services.auth.auth_service import get_current_user, get_current_user_optional
from backend.app.services.auth.user_store import UserRecord
from backend.app.config import get_backend_settings
from backend.app.services.integrations.google_integration_service import GoogleIntegrationService
from backend.app.services.integrations.google_oauth_service import GoogleIntegrationOAuthService
from backend.app.services.integrations.google_token_store import GoogleTokenStore

router = APIRouter(tags=["google-connectors"])


def resolve_user_id(requested_user_id: str, user: UserRecord | None) -> str:
    return user.user_id if user is not None else requested_user_id


@router.get("/api/google/status", response_model=GoogleStatusResponse)
def google_status() -> GoogleStatusResponse:
    status = GoogleAuthManager().status()
    return GoogleStatusResponse(
        credentials_available=status.credentials_available,
        google_libraries_available=status.google_libraries_available,
        mode=status.mode,
        client_secret_path=status.client_secret_path,
        scopes=status.scopes,
    )


@router.get("/api/integrations/google/status", response_model=GoogleIntegrationStatusResponse)
def google_integration_status(user: UserRecord = Depends(get_current_user)) -> GoogleIntegrationStatusResponse:
    return GoogleIntegrationStatusResponse(**GoogleIntegrationService().status(user.user_id, google_login_email=expected_google_email(user)))


@router.get("/api/integrations/google/gmail/start")
def gmail_connect_start(user: UserRecord = Depends(get_current_user)):
    return integration_connect_start("gmail", user)


@router.get("/api/integrations/google/calendar/start")
def calendar_connect_start(user: UserRecord = Depends(get_current_user)):
    return integration_connect_start("calendar", user)


@router.get("/api/integrations/google/gmail/start-url")
def gmail_connect_start_url(user: UserRecord = Depends(get_current_user)) -> dict[str, str]:
    return integration_connect_start_url("gmail", user)


@router.get("/api/integrations/google/calendar/start-url")
def calendar_connect_start_url(user: UserRecord = Depends(get_current_user)) -> dict[str, str]:
    return integration_connect_start_url("calendar", user)


@router.get("/api/integrations/google/gmail/callback")
def gmail_connect_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    return integration_connect_callback("gmail", code=code, state=state, error=error)


@router.get("/api/integrations/google/calendar/callback")
def calendar_connect_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    return integration_connect_callback("calendar", code=code, state=state, error=error)


@router.post("/api/integrations/google/gmail/disconnect")
def gmail_disconnect(user: UserRecord = Depends(get_current_user)) -> dict:
    return GoogleIntegrationService().disconnect(user.user_id, "gmail")


@router.post("/api/integrations/google/calendar/disconnect")
def calendar_disconnect(user: UserRecord = Depends(get_current_user)) -> dict:
    return GoogleIntegrationService().disconnect(user.user_id, "calendar")


@router.post("/api/google/gmail/sync", response_model=SyncResponse)
def sync_gmail(
    request: GmailSyncRequest,
    user: UserRecord | None = Depends(get_current_user_optional),
) -> SyncResponse:
    query = gmail_query_for_range(request.range) if request.range else request.query
    stats = get_personal_ingestion_service().sync_gmail(
        user_id=resolve_user_id(request.user_id, user),
        max_results=request.max_results,
        use_mock=request.use_mock,
        scenario=request.scenario,
        query=build_gmail_query(query, include_read=request.include_read, include_unread=request.include_unread),
        include_spam_trash=request.include_spam_trash,
    )
    return SyncResponse(**stats.__dict__)


@router.get("/api/google/gmail/summary", response_model=GmailSummaryResponse)
def gmail_summary(
    user_id: str = "default",
    user: UserRecord | None = Depends(get_current_user_optional),
) -> GmailSummaryResponse:
    return GmailSummaryResponse(**get_personal_ingestion_service().gmail_summary(user_id=resolve_user_id(user_id, user)))


@router.post("/api/google/calendar/sync", response_model=SyncResponse)
def sync_calendar(
    request: CalendarSyncRequest,
    user: UserRecord | None = Depends(get_current_user_optional),
) -> SyncResponse:
    validate_calendar_dates(request.start_date, request.end_date)
    days_ahead = calendar_days_for_range(request.range) if request.range and not (request.start_date and request.end_date) else request.days_ahead
    stats = get_personal_ingestion_service().sync_calendar(
        user_id=resolve_user_id(request.user_id, user),
        days_ahead=days_ahead,
        start_date=request.start_date,
        end_date=request.end_date,
        calendar_ids=request.calendar_ids,
        include_all_calendars=request.include_all_calendars,
        include_holidays=request.include_holidays,
        use_mock=request.use_mock,
        scenario=request.scenario,
        include_cancelled=request.include_cancelled,
    )
    return SyncResponse(**stats.__dict__)


@router.get("/api/google/calendar/calendars", response_model=CalendarListResponse)
def calendar_calendars(user: UserRecord = Depends(get_current_user)) -> CalendarListResponse:
    service = get_personal_ingestion_service()
    if not GoogleTokenStore().is_connected(user.user_id, "calendar"):
        return CalendarListResponse(connected=False, calendars=[])
    return CalendarListResponse(connected=True, calendars=service.list_calendars(user_id=user.user_id))


@router.get("/api/google/sync-status")
def google_sync_status(
    type: str,
    user_id: str = "default",
    user: UserRecord | None = Depends(get_current_user_optional),
) -> dict[str, object]:
    integration = type.lower().strip()
    if integration not in {"gmail", "calendar"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="type must be gmail or calendar")
    return get_personal_ingestion_service().sync_status(
        user_id=resolve_user_id(user_id, user),
        integration=integration,
    )


@router.get("/api/google/calendar/today", response_model=CalendarTodayResponse)
def calendar_today(
    user_id: str = "default",
    user: UserRecord | None = Depends(get_current_user_optional),
) -> CalendarTodayResponse:
    return CalendarTodayResponse(**get_personal_ingestion_service().today_calendar(user_id=resolve_user_id(user_id, user)))


@router.get("/api/assistant/daily-briefing", response_model=DailyBriefingResponse)
def daily_briefing(
    user_id: str = "default",
    user: UserRecord | None = Depends(get_current_user_optional),
) -> DailyBriefingResponse:
    return DailyBriefingResponse(**get_personal_ingestion_service().daily_briefing(user_id=resolve_user_id(user_id, user)))


@lru_cache(maxsize=1)
def get_personal_ingestion_service() -> PersonalIngestionService:
    return PersonalIngestionService()


def integration_connect_start(integration: str, user: UserRecord):
    service = GoogleIntegrationOAuthService()
    if not service.configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth chưa được cấu hình trên máy này.",
        )
    state = service.create_state(user_id=user.user_id, integration=integration)
    return RedirectResponse(
        service.authorization_url(state=state, integration=integration, login_hint=expected_google_email(user)),
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )


def integration_connect_start_url(integration: str, user: UserRecord) -> dict[str, str]:
    service = GoogleIntegrationOAuthService()
    if not service.configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth chưa được cấu hình trên máy này.",
        )
    state = service.create_state(user_id=user.user_id, integration=integration)
    return {
        "url": service.authorization_url(state=state, integration=integration, login_hint=expected_google_email(user)),
        "integration": integration,
    }


def integration_connect_callback(integration: str, *, code: str | None, state: str | None, error: str | None):
    frontend_url = get_backend_settings().frontend_url.rstrip("/")
    if error:
        return RedirectResponse(f"{frontend_url}/settings?{urlencode({'error': error})}")
    if not code or not state:
        return RedirectResponse(f"{frontend_url}/settings?{urlencode({'error': 'Thiếu mã xác thực Google.'})}")

    service = GoogleIntegrationOAuthService()
    state_payload = service.consume_state(state, integration)
    if not state_payload:
        return RedirectResponse(f"{frontend_url}/settings?{urlencode({'error': 'Phiên kết nối Google đã hết hạn hoặc không hợp lệ.'})}")

    try:
        token = service.exchange_code(code=code, integration=integration)
        account_email = service.account_email(str(token.get("access_token") or ""))
        user = get_user_for_callback(state_payload.user_id)
        expected_email = expected_google_email(user) if user else None
        if expected_email and account_email and expected_email != account_email:
            GoogleTokenStore().delete_token(state_payload.user_id, integration)
            message = (
                f"Bạn đã chọn tài khoản Google khác với tài khoản đăng nhập ban đầu. "
                f"Vui lòng kết nối lại bằng {expected_email}."
            )
            return RedirectResponse(f"{frontend_url}/settings?{urlencode({'error': message})}")
        GoogleTokenStore().save_token(
            state_payload.user_id,
            integration,
            token,
            google_account_email=account_email,
        )
    except Exception:
        return RedirectResponse(f"{frontend_url}/settings?{urlencode({'error': 'Không hoàn tất được kết nối Google.'})}")

    return RedirectResponse(f"{frontend_url}/settings?{urlencode({'connected': integration})}")


def expected_google_email(user: UserRecord | None) -> str | None:
    if user is None:
        return None
    metadata_email = str(user.metadata.get("google_email") or "").strip().lower()
    if metadata_email:
        return metadata_email
    if user.metadata.get("auth_provider") == "google":
        return user.email.strip().lower()
    return None


def get_user_for_callback(user_id: str) -> UserRecord | None:
    from backend.app.services.auth.auth_service import get_user_store

    return get_user_store().get_by_id(user_id)


def build_gmail_query(query: str, *, include_read: bool, include_unread: bool) -> str:
    parts = [query.strip()] if query.strip() else []
    if include_unread and not include_read:
        parts.append("is:unread")
    elif include_read and not include_unread:
        parts.append("is:read")
    elif not include_read and not include_unread:
        parts.append("is:unread")
    return " ".join(parts).strip()


def gmail_query_for_range(range_value: str | None) -> str:
    mapping = {
        "7d": "newer_than:7d",
        "30d": "newer_than:30d",
        "90d": "newer_than:90d",
        "1y": "newer_than:365d",
        "all_recent": "",
    }
    return mapping.get((range_value or "90d").strip(), "newer_than:90d")


def calendar_days_for_range(range_value: str | None) -> int:
    mapping = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
    return mapping.get((range_value or "7d").strip(), 7)


def validate_calendar_dates(start_date: str | None, end_date: str | None) -> None:
    if not start_date and not end_date:
        return
    if not start_date or not end_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_date and end_date must be provided together")
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid calendar date format") from exc
    if end < start:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_date must be before or equal to end_date")
    if end - start > timedelta(days=365):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Calendar sync date range cannot exceed 365 days")

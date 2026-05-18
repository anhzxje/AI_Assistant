"""JSONL-backed local user store."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

from pydantic import BaseModel, Field

from backend.app.config import get_backend_settings
from backend.app.services.auth.password_utils import hash_password, verify_password


class UserRecord(BaseModel):
    user_id: str
    email: str
    display_name: str
    role: str
    password_hash: str
    created_at: datetime
    updated_at: datetime | None = None
    disabled: bool = False
    metadata: dict = Field(default_factory=dict)

    def public(self) -> dict:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "display_name": self.display_name,
            "role": self.role,
            "role_label": "Người quản lý" if self.role == "admin" else "Người dùng",
            "disabled": self.disabled,
        }


class UserStore:
    def __init__(self, path: Path | None = None) -> None:
        settings = get_backend_settings()
        self.path = path or settings.data_settings.resolved_data_root / "personal_memory" / "auth" / "users.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ensure_seed_users()

    def list_users(self) -> list[UserRecord]:
        if not self.path.exists():
            return []
        users: list[UserRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                users.append(UserRecord.model_validate_json(line))
        return users

    def get_by_email(self, email: str) -> UserRecord | None:
        normalized = normalize_email(email)
        return next((user for user in self.list_users() if user.email == normalized), None)

    def get_by_id(self, user_id: str) -> UserRecord | None:
        return next((user for user in self.list_users() if user.user_id == user_id), None)

    def verify_credentials(self, email: str, password: str) -> UserRecord | None:
        user = self.get_by_email(email)
        if user is None or user.disabled:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def upsert_google_user(self, email: str, display_name: str, google_sub: str | None = None) -> UserRecord:
        normalized = normalize_email(email)
        users = self.list_users()
        now = datetime.now(timezone.utc)
        for index, user in enumerate(users):
            if user.email != normalized:
                continue
            if user.role == "admin" and user.metadata.get("auth_provider") != "google":
                raise ValueError("google_login_cannot_grant_admin")
            updated = user.model_copy(
                update={
                    "display_name": display_name or user.display_name,
                    "role": "user",
                    "updated_at": now,
                    "metadata": {
                        **user.metadata,
                        "auth_provider": "google",
                        "google_email": normalized,
                        "google_sub": google_sub,
                    },
                }
            )
            users[index] = updated
            self._write_users(users)
            return updated

        created = UserRecord(
            user_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"google:{normalized}")),
            email=normalized,
            display_name=display_name or normalized.split("@", 1)[0],
            role="user",
            password_hash="",
            created_at=now,
            updated_at=now,
            metadata={"auth_provider": "google", "google_email": normalized, "google_sub": google_sub},
        )
        users.append(created)
        self._write_users(users)
        return created

    def ensure_seed_users(self) -> None:
        users = self._read_users_without_seed()
        by_email = {user.email: user for user in users}
        changed = False
        for seed in seed_user_specs():
            if seed["email"] in by_email:
                continue
            users.append(
                UserRecord(
                    user_id=seed.get("user_id") or str(uuid.uuid5(uuid.NAMESPACE_DNS, seed["email"])),
                    email=seed["email"],
                    display_name=seed["display_name"],
                    role=seed["role"],
                    password_hash=hash_password(seed["password"]),
                    created_at=datetime.now(timezone.utc),
                    metadata={"seeded": True},
                )
            )
            changed = True
        if changed or not self.path.exists():
            self._write_users(users)

    def _read_users_without_seed(self) -> list[UserRecord]:
        if not self.path.exists():
            return []
        users: list[UserRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            users.append(UserRecord.model_validate_json(line))
        return users

    def _write_users(self, users: list[UserRecord]) -> None:
        lines = [json.dumps(user.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) for user in users]
        self.path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def seed_user_specs() -> list[dict[str, str]]:
    return [
        {
            "user_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "admin@omni.local")),
            "email": "admin@omni.local",
            "password": "admin123456",
            "role": "admin",
            "display_name": "Omni Admin",
        },
        {
            "user_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "user@omni.local")),
            "email": "user@omni.local",
            "password": "user123456",
            "role": "user",
            "display_name": "Omni User",
        },
        {
            "user_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "user2@omni.local")),
            "email": "user2@omni.local",
            "password": "user2123456",
            "role": "user",
            "display_name": "Người dùng 2",
        },
        *[
            {
                "user_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, email)),
                "email": email,
                "password": "test123456",
                "role": role,
                "display_name": display_name,
            }
            for email, display_name, role in [
                ("student.clean@omni.local", "Sinh viên Clean", "user"),
                ("student.noisy@omni.local", "Sinh viên Noisy", "user"),
                ("student.deadline@omni.local", "Sinh viên Deadline", "user"),
                ("lecturer@omni.local", "Giảng viên Demo", "user"),
                ("staff@omni.local", "Cán bộ Quản lý", "admin"),
                ("researcher@omni.local", "Nhà nghiên cứu Demo", "user"),
                ("thesis.student@omni.local", "Sinh viên Luận văn", "user"),
                ("scholarship@omni.local", "Sinh viên Học bổng", "user"),
                ("exam.case@omni.local", "Sinh viên Lịch thi", "user"),
                ("empty.user@omni.local", "Người dùng mới", "user"),
            ]
        ],
    ]

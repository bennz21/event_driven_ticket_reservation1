from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User, UserRole, UserStatus

bearer_scheme = HTTPBearer(auto_error=False)
AUTH_COOKIE_NAME = "access_token"


@dataclass
class CurrentActor:
    role: str  # "admin" | "organizer" | "public"
    email: str
    name: str
    user: Optional[User] = None

    @property
    def id(self) -> Optional[int]:
        return self.user.id if self.user is not None else None


def _extract_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    cookie_token = request.cookies.get(AUTH_COOKIE_NAME)
    if cookie_token:
        return cookie_token
    if credentials is not None and credentials.scheme.lower() == "bearer":
        return credentials.credentials
    return None


def get_current_actor(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> CurrentActor:
    token = _extract_token(request, credentials)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    role = payload.get("role")
    email = payload.get("email", "")
    sub = payload.get("sub")

    if role == "admin":
        if email != settings.ADMIN_EMAIL.strip().lower() or sub != "admin":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin session.",
            )
        return CurrentActor(role="admin", email=email, name="Platform Admin", user=None)

    if role not in (UserRole.ORGANIZER.value, UserRole.PUBLIC.value):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session role.",
        )

    try:
        user_id = int(sub)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identifier in token.",
        ) from exc

    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account no longer exists.",
        )

    if user.status == UserStatus.BLOCKED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been blocked by an administrator.",
        )

    if user.role.value != role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role mismatch.",
        )

    return CurrentActor(
        role=user.role.value,
        email=user.email,
        name=user.name,
        user=user,
    )


def require_admin(actor: CurrentActor = Depends(get_current_actor)) -> CurrentActor:
    if actor.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return actor


def require_organizer(actor: CurrentActor = Depends(get_current_actor)) -> CurrentActor:
    if actor.role != UserRole.ORGANIZER.value or actor.user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Event Organizer access required.",
        )
    return actor


def require_public(actor: CurrentActor = Depends(get_current_actor)) -> CurrentActor:
    if actor.role != UserRole.PUBLIC.value or actor.user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="General Public access required.",
        )
    return actor

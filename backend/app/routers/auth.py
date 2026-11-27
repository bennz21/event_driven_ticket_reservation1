import hmac
import secrets
from typing import Literal, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AUTH_COOKIE_NAME, CurrentActor, get_current_actor
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_oauth_state_token,
    hash_password,
    verify_google_id_token,
    verify_oauth_state_token,
    verify_password,
)
from app.models import User, UserRole, UserStatus
from app.schemas import AuthIdentity, AuthResponse, LoginRequest, SignupRequest

router = APIRouter()


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
        path="/",
    )


def _login_user_by_role(
    req: LoginRequest,
    expected_role: UserRole,
    response: Response,
    db: Session,
) -> AuthResponse:
    user = db.execute(select(User).where(User.email == req.email)).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if user.password_hash.startswith("!oauth:"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account uses Google Sign-In. Please click Continue with Google.",
        )

    if not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if user.role != expected_role:
        expected_label = "Event Organizer" if expected_role == UserRole.ORGANIZER else "General Public"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This login page is for {expected_label} accounts only.",
        )

    if user.status == UserStatus.BLOCKED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been blocked by an administrator.",
        )

    token = create_access_token(
        subject=str(user.id),
        role=user.role.value,
        name=user.name,
        email=user.email,
    )
    _set_auth_cookie(response, token)
    return AuthResponse(
        access_token=token,
        user=AuthIdentity(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role.value,
            status=user.status.value,
        ),
    )


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(req: SignupRequest, response: Response, db: Session = Depends(get_db)):
    """Create an Event Organizer or General Public account (Admin signup is not allowed)."""
    admin_email = settings.ADMIN_EMAIL.strip().lower()
    if req.email == admin_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email is reserved and cannot be registered.",
        )

    existing = db.execute(select(User).where(User.email == req.email)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        name=req.name,
        email=req.email,
        password_hash=hash_password(req.password),
        role=UserRole(req.role),
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(
        subject=str(user.id),
        role=user.role.value,
        name=user.name,
        email=user.email,
    )
    _set_auth_cookie(response, token)
    return AuthResponse(
        access_token=token,
        user=AuthIdentity(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role.value,
            status=user.status.value,
        ),
    )


@router.post("/admin/login", response_model=AuthResponse)
def admin_login(req: LoginRequest, response: Response):
    """Dedicated Admin login validated strictly against .env credentials."""
    expected_email = settings.ADMIN_EMAIL.strip().lower()
    expected_password = settings.ADMIN_PASSWORD

    email_ok = hmac.compare_digest(req.email, expected_email)
    password_ok = bool(expected_password) and hmac.compare_digest(req.password, expected_password)

    if not (email_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials.",
        )

    token = create_access_token(
        subject="admin",
        role="admin",
        name="Platform Admin",
        email=expected_email,
    )
    _set_auth_cookie(response, token)
    return AuthResponse(
        access_token=token,
        user=AuthIdentity(
            id=None,
            name="Platform Admin",
            email=expected_email,
            role="admin",
            status="active",
        ),
    )


@router.post("/organizer/login", response_model=AuthResponse)
def organizer_login(
    req: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """Dedicated Event Organizer login."""
    return _login_user_by_role(req, UserRole.ORGANIZER, response, db)


@router.post("/public/login", response_model=AuthResponse)
def public_login(
    req: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """Dedicated General Public login."""
    return _login_user_by_role(req, UserRole.PUBLIC, response, db)


# --- Google OAuth 2.0 (for General Public & Event Organizer) ---

def _get_google_redirect_uri(request: Request) -> str:
    explicit = (settings.GOOGLE_REDIRECT_URI or "").strip()
    if explicit:
        return explicit

    configured_base = (settings.BACKEND_PUBLIC_URL or "").strip().rstrip("/")
    if configured_base and configured_base != "http://localhost:8000":
        return f"{configured_base}{settings.API_V1_STR}/auth/oauth/google/callback"

    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if host:
        return f"{proto}://{host}{settings.API_V1_STR}/auth/oauth/google/callback"

    return f"{configured_base or 'http://localhost:8000'}{settings.API_V1_STR}/auth/oauth/google/callback"


@router.get("/oauth/google/login")
def google_oauth_login(
    request: Request,
    role: Literal["public", "organizer"] = Query(default="public"),
):
    if not (settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured in .env.",
        )

    state = create_oauth_state_token(role)
    redirect_uri = _get_google_redirect_uri(request)
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return RedirectResponse(url=f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")


@router.get("/oauth/google/callback")
def google_oauth_callback(
    request: Request,
    code: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    frontend_base = settings.FRONTEND_URL.rstrip("/")

    def error_redirect(msg: str, target_path: str = "/login/public") -> RedirectResponse:
        return RedirectResponse(
            url=f"{frontend_base}{target_path}?{urlencode({'oauth_error': msg})}",
            status_code=status.HTTP_302_FOUND,
        )

    if error or not code:
        return error_redirect(error or "Google sign-in was cancelled.")

    try:
        intended_role = verify_oauth_state_token(state or "")
    except ValueError as exc:
        return error_redirect(str(exc))

    login_path = f"/login/{intended_role}"
    redirect_uri = _get_google_redirect_uri(request)

    try:
        with httpx.Client(timeout=10.0) as client:
            token_resp = client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_resp.raise_for_status()
            id_token = token_resp.json().get("id_token")

        if not id_token:
            raise ValueError("Google token response did not include id_token.")

        claims = verify_google_id_token(id_token, expected_audience=settings.GOOGLE_CLIENT_ID)
    except Exception as exc:
        return error_redirect(f"Google sign-in verification failed: {exc}", login_path)

    email = str(claims.get("email", "")).strip().lower()
    name = str(claims.get("name") or (email.split("@")[0] if email else "Google User")).strip()
    if not email or not claims.get("email_verified", False):
        return error_redirect("Google account must have a verified email address.", login_path)

    if email == settings.ADMIN_EMAIL.strip().lower():
        return error_redirect("Admin must sign in via the Admin Login page.", "/login/admin")

    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        user = User(
            name=name[:150],
            email=email,
            password_hash=f"!oauth:google:{secrets.token_hex(16)}",
            role=UserRole(intended_role),
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if user.status == UserStatus.BLOCKED:
            return error_redirect("Your account has been blocked by an administrator.", login_path)
        if user.role.value != intended_role:
            role_label = "Event Organizer" if user.role == UserRole.ORGANIZER else "General Public"
            return error_redirect(
                f"This email is registered as {role_label}. Please sign in on the {role_label} page.",
                f"/login/{user.role.value}",
            )

    jwt_token = create_access_token(
        subject=str(user.id),
        role=user.role.value,
        name=user.name,
        email=user.email,
    )
    resp = RedirectResponse(url=f"{frontend_base}/{user.role.value}", status_code=status.HTTP_302_FOUND)
    _set_auth_cookie(resp, jwt_token)
    return resp


@router.get("/me", response_model=AuthIdentity)
def get_me(actor: CurrentActor = Depends(get_current_actor)):
    """Return the authenticated actor from the HTTP-only JWT cookie or Bearer token."""
    return AuthIdentity(
        id=actor.id,
        name=actor.name,
        email=actor.email,
        role=actor.role,
        status=actor.user.status.value if actor.user else "active",
    )


@router.post("/logout")
def logout(response: Response):
    """Clear the HTTP-only JWT cookie."""
    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/")
    return {"message": "Signed out."}

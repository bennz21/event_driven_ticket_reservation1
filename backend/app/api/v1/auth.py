import json
from typing import List, Optional
from urllib.parse import parse_qs, urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import bearer_scheme, get_auth_service, get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_apple_client_secret,
    decode_access_token,
    verify_oidc_id_token,
)
from app.models import Reservation, User
from app.schemas import (
    AuthProvidersResponse,
    AuthTokenResponse,
    OAuthDemoRequest,
    OAuthExchangeRequest,
    OAuthProviderStatus,
    ReservationResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter()

_GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")
_APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
_APPLE_ISSUERS = ("https://appleid.apple.com",)


def _google_configured() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def _apple_configured() -> bool:
    return bool(settings.APPLE_CLIENT_ID)


def _apple_code_exchange_configured() -> bool:
    return bool(
        settings.APPLE_CLIENT_ID
        and settings.APPLE_TEAM_ID
        and settings.APPLE_KEY_ID
        and settings.APPLE_PRIVATE_KEY
    )


def _frontend_oauth_redirect(params: dict) -> RedirectResponse:
    base = settings.FRONTEND_URL.rstrip("/")
    return RedirectResponse(url=f"{base}/?{urlencode(params)}", status_code=status.HTTP_302_FOUND)


@router.post("/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
async def register_account(
    req: UserRegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Create a new email/password account and return a JWT access token."""
    return await auth_service.register_local(
        full_name=req.full_name,
        email=req.email,
        password=req.password,
    )


@router.post("/login", response_model=AuthTokenResponse)
async def login_account(
    req: UserLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Authenticate an email/password account and return a JWT access token."""
    return await auth_service.login_local(email=req.email, password=req.password)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user


@router.post("/logout")
async def logout_account(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    """Revoke the current JWT token (uses Redis when available)."""
    if credentials and credentials.scheme.lower() == "bearer":
        try:
            payload = decode_access_token(credentials.credentials)
            if payload.get("jti") and payload.get("exp"):
                await AuthService.revoke_token(payload["jti"], int(payload["exp"]))
        except ValueError:
            pass
    return {"message": "Signed out."}


@router.get("/reservations", response_model=List[ReservationResponse])
async def get_my_reservations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all confirmed reservations and digital tickets for the signed-in user."""
    query = (
        select(Reservation)
        .options(selectinload(Reservation.tickets))
        .where(Reservation.user_id == current_user.id)
        .order_by(Reservation.created_at.desc())
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/providers", response_model=AuthProvidersResponse)
async def get_auth_providers():
    """Report which social OAuth providers are configured vs running in dev preview mode."""
    google_ok = _google_configured()
    apple_ok = _apple_configured()
    return AuthProvidersResponse(
        google=OAuthProviderStatus(
            configured=google_ok,
            demo_enabled=settings.OAUTH_ALLOW_DEMO_LOGIN and not google_ok,
        ),
        apple=OAuthProviderStatus(
            configured=apple_ok,
            demo_enabled=settings.OAUTH_ALLOW_DEMO_LOGIN and not apple_ok,
        ),
    )


# --- Google OAuth 2.0 / OIDC ---

@router.get("/oauth/google/login")
async def google_oauth_login():
    if not _google_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env.",
        )

    state = await AuthService.create_oauth_state("google")
    redirect_uri = f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}{settings.API_V1_STR}/auth/oauth/google/callback"
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
async def google_oauth_callback(
    code: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
    auth_service: AuthService = Depends(get_auth_service),
):
    if error or not code:
        return _frontend_oauth_redirect({"oauth_error": error or "Google sign-in was cancelled."})

    if not await AuthService.consume_oauth_state(state or "", "google"):
        return _frontend_oauth_redirect({"oauth_error": "Invalid or expired Google OAuth state."})

    redirect_uri = f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}{settings.API_V1_STR}/auth/oauth/google/callback"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(
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
            token_data = token_resp.json()

        id_token = token_data.get("id_token")
        if not id_token:
            raise ValueError("Google token response did not contain an id_token.")

        claims = await verify_oidc_id_token(
            id_token=id_token,
            jwks_url=_GOOGLE_JWKS_URL,
            expected_issuers=_GOOGLE_ISSUERS,
            expected_audience=settings.GOOGLE_CLIENT_ID,
        )
    except Exception as exc:
        return _frontend_oauth_redirect({"oauth_error": f"Google verification failed: {exc}"})

    auth_res = await auth_service.upsert_oauth_user(
        provider="google",
        provider_user_id=str(claims["sub"]),
        email=claims.get("email"),
        full_name=claims.get("name"),
        avatar_url=claims.get("picture"),
        email_verified=bool(claims.get("email_verified", False)),
    )
    one_time_code = await AuthService.create_one_time_code(auth_res)
    return _frontend_oauth_redirect({"oauth_code": one_time_code})


# --- Sign in with Apple ---

@router.get("/oauth/apple/login")
async def apple_oauth_login():
    if not _apple_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sign in with Apple is not configured. Set APPLE_CLIENT_ID in .env.",
        )

    state = await AuthService.create_oauth_state("apple")
    redirect_uri = f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}{settings.API_V1_STR}/auth/oauth/apple/callback"
    params = {
        "client_id": settings.APPLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code id_token",
        "response_mode": "form_post",
        "scope": "name email",
        "state": state,
    }
    return RedirectResponse(url=f"https://appleid.apple.com/auth/authorize?{urlencode(params)}")


@router.post("/oauth/apple/callback")
async def apple_oauth_callback(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    raw_body = (await request.body()).decode("utf-8")
    form_data = {k: v[0] for k, v in parse_qs(raw_body, keep_blank_values=True).items() if v}
    code = form_data.get("code")
    id_token = form_data.get("id_token")
    state = form_data.get("state")
    user = form_data.get("user")
    error = form_data.get("error")

    if error:
        return _frontend_oauth_redirect({"oauth_error": error})

    if not await AuthService.consume_oauth_state(state or "", "apple"):
        return _frontend_oauth_redirect({"oauth_error": "Invalid or expired Apple OAuth state."})

    try:
        token_to_verify = id_token
        if not token_to_verify and code and _apple_code_exchange_configured():
            redirect_uri = (
                f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}{settings.API_V1_STR}/auth/oauth/apple/callback"
            )
            async with httpx.AsyncClient(timeout=10.0) as client:
                token_resp = await client.post(
                    "https://appleid.apple.com/auth/token",
                    data={
                        "client_id": settings.APPLE_CLIENT_ID,
                        "client_secret": create_apple_client_secret(),
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": redirect_uri,
                    },
                )
                token_resp.raise_for_status()
                token_to_verify = token_resp.json().get("id_token")

        if not token_to_verify:
            raise ValueError("Apple callback did not provide an id_token.")

        claims = await verify_oidc_id_token(
            id_token=token_to_verify,
            jwks_url=_APPLE_JWKS_URL,
            expected_issuers=_APPLE_ISSUERS,
            expected_audience=settings.APPLE_CLIENT_ID,
        )

        # Apple sends user's name only on the very first sign-in in the `user` form JSON field
        full_name = None
        if user:
            try:
                user_json = json.loads(user)
                name_obj = user_json.get("name", {})
                parts = [name_obj.get("firstName", ""), name_obj.get("lastName", "")]
                joined = " ".join(p for p in parts if p).strip()
                if joined:
                    full_name = joined
            except Exception:
                pass
    except Exception as exc:
        return _frontend_oauth_redirect({"oauth_error": f"Apple verification failed: {exc}"})

    auth_res = await auth_service.upsert_oauth_user(
        provider="apple",
        provider_user_id=str(claims["sub"]),
        email=claims.get("email"),
        full_name=full_name,
        email_verified=str(claims.get("email_verified", "true")).lower() == "true",
    )
    one_time_code = await AuthService.create_one_time_code(auth_res)
    return _frontend_oauth_redirect({"oauth_code": one_time_code})


@router.post("/oauth/exchange", response_model=AuthTokenResponse)
async def exchange_oauth_code(req: OAuthExchangeRequest):
    """Exchange a one-time OAuth redirect code for a JWT access token and user profile."""
    return await AuthService.exchange_one_time_code(req.code)


@router.post("/oauth/demo", response_model=AuthTokenResponse)
async def demo_oauth_login(
    req: OAuthDemoRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Development-only Google/Apple sign-in simulation when OAUTH_ALLOW_DEMO_LOGIN=true
    and live provider credentials are not configured in .env.
    """
    if not settings.OAUTH_ALLOW_DEMO_LOGIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo OAuth sign-in is disabled.",
        )

    if req.provider == "google" and _google_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Live Google OAuth is configured; use /auth/oauth/google/login.",
        )
    if req.provider == "apple" and _apple_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Live Apple OAuth is configured; use /auth/oauth/apple/login.",
        )

    default_email = f"demo.{req.provider}@example.com"
    email = (req.email or default_email).strip().lower()
    default_name = "Google Demo User" if req.provider == "google" else "Apple Demo User"
    full_name = (req.full_name or default_name).strip()

    return await auth_service.upsert_oauth_user(
        provider=req.provider,
        provider_user_id=f"demo_{req.provider}_{email}",
        email=email,
        full_name=full_name,
        email_verified=True,
    )

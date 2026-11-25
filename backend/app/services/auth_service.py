import json
import secrets
import time
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import redis_service
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas import AuthTokenResponse, UserResponse

# In-memory TTL fallback stores when Redis is unavailable
_memory_states: Dict[str, Tuple[str, float]] = {}
_memory_codes: Dict[str, Tuple[str, float]] = {}
_memory_revoked_jtis: Dict[str, float] = {}


def _prune_expired(store: Dict[str, Tuple[Any, float]]) -> None:
    now = time.monotonic()
    expired = [k for k, (_, exp) in store.items() if now >= exp]
    for k in expired:
        del store[k]


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _issue_auth_response(self, user: User) -> AuthTokenResponse:
        token, _, _ = create_access_token(
            user_id=user.id,
            email=user.email,
            auth_provider=user.auth_provider,
        )
        return AuthTokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )

    async def register_local(self, full_name: str, email: str, password: str) -> AuthTokenResponse:
        normalized_email = email.strip().lower()
        existing = (
            await self.db.execute(select(User).where(User.email == normalized_email))
        ).scalar_one_or_none()

        if existing is not None:
            if existing.auth_provider != "local" and not existing.password_hash:
                provider_label = existing.auth_provider.capitalize()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"An account with this email already exists via {provider_label} Sign-In. Please sign in with {provider_label}.",
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )

        user = User(
            email=normalized_email,
            full_name=full_name.strip(),
            password_hash=hash_password(password),
            auth_provider="local",
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return self._issue_auth_response(user)

    async def login_local(self, email: str, password: str) -> AuthTokenResponse:
        normalized_email = email.strip().lower()
        user = (
            await self.db.execute(select(User).where(User.email == normalized_email))
        ).scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        if not user.password_hash:
            provider_label = user.auth_provider.capitalize()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"This account uses {provider_label} Sign-In. Please continue with {provider_label}.",
            )

        if not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account has been disabled.",
            )

        return self._issue_auth_response(user)

    async def upsert_oauth_user(
        self,
        provider: str,
        provider_user_id: str,
        email: Optional[str],
        full_name: Optional[str],
        avatar_url: Optional[str] = None,
        email_verified: bool = True,
    ) -> AuthTokenResponse:
        normalized_email = email.strip().lower() if email else None

        # 1. Lookup by (provider, provider_user_id)
        user = (
            await self.db.execute(
                select(User).where(
                    and_(
                        User.auth_provider == provider,
                        User.provider_user_id == provider_user_id,
                    )
                )
            )
        ).scalar_one_or_none()

        # 2. If not found and provider confirmed email is verified, link by email
        if user is None and normalized_email and email_verified:
            user = (
                await self.db.execute(select(User).where(User.email == normalized_email))
            ).scalar_one_or_none()

        if user is None:
            fallback_name = (
                full_name.strip()
                if full_name and full_name.strip()
                else (normalized_email.split("@")[0] if normalized_email else f"{provider.capitalize()} User")
            )
            user = User(
                email=normalized_email,
                full_name=fallback_name,
                auth_provider=provider,
                provider_user_id=provider_user_id,
                avatar_url=avatar_url,
            )
            self.db.add(user)
        else:
            if avatar_url and not user.avatar_url:
                user.avatar_url = avatar_url
            if full_name and full_name.strip() and user.full_name.endswith(" User"):
                user.full_name = full_name.strip()

        await self.db.commit()
        await self.db.refresh(user)
        return self._issue_auth_response(user)

    # --- OAuth State & One-Time Exchange Codes ---

    @staticmethod
    async def create_oauth_state(provider: str) -> str:
        state = secrets.token_urlsafe(24)
        key = f"oauth_state:{state}"
        if redis_service.is_available:
            try:
                await redis_service._client.set(key, provider, ex=600)
                return state
            except Exception:
                pass
        _prune_expired(_memory_states)
        _memory_states[state] = (provider, time.monotonic() + 600)
        return state

    @staticmethod
    async def consume_oauth_state(state: str, expected_provider: str) -> bool:
        if not state:
            return False
        key = f"oauth_state:{state}"
        if redis_service.is_available:
            try:
                val = await redis_service._client.get(key)
                if val == expected_provider:
                    await redis_service._client.delete(key)
                    return True
                return False
            except Exception:
                pass
        _prune_expired(_memory_states)
        entry = _memory_states.pop(state, None)
        return entry is not None and entry[0] == expected_provider

    @staticmethod
    async def create_one_time_code(auth_response: AuthTokenResponse) -> str:
        code = secrets.token_urlsafe(32)
        payload_json = auth_response.model_dump_json()
        key = f"oauth_code:{code}"
        if redis_service.is_available:
            try:
                await redis_service._client.set(key, payload_json, ex=120)
                return code
            except Exception:
                pass
        _prune_expired(_memory_codes)
        _memory_codes[code] = (payload_json, time.monotonic() + 120)
        return code

    @staticmethod
    async def exchange_one_time_code(code: str) -> AuthTokenResponse:
        key = f"oauth_code:{code}"
        payload_json: Optional[str] = None
        if redis_service.is_available:
            try:
                payload_json = await redis_service._client.get(key)
                if payload_json is not None:
                    await redis_service._client.delete(key)
            except Exception:
                payload_json = None

        if payload_json is None:
            _prune_expired(_memory_codes)
            entry = _memory_codes.pop(code, None)
            if entry is not None:
                payload_json = entry[0]

        if not payload_json:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OAuth exchange code.",
            )

        return AuthTokenResponse(**json.loads(payload_json))

    # --- Token Revocation ---

    @staticmethod
    async def revoke_token(jti: str, exp: int) -> None:
        ttl = max(1, int(exp - time.time()))
        key = f"revoked_jti:{jti}"
        if redis_service.is_available:
            try:
                await redis_service._client.set(key, "1", ex=ttl)
                return
            except Exception:
                pass
        _memory_revoked_jtis[jti] = time.monotonic() + ttl

    @staticmethod
    async def is_token_revoked(jti: str) -> bool:
        if not jti:
            return False
        key = f"revoked_jti:{jti}"
        if redis_service.is_available:
            try:
                return (await redis_service._client.get(key)) is not None
            except Exception:
                pass
        now = time.monotonic()
        exp = _memory_revoked_jtis.get(jti)
        if exp is None:
            return False
        if now >= exp:
            del _memory_revoked_jtis[jti]
            return False
        return True

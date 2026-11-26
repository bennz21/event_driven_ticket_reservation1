import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid
from typing import Any, Dict, Optional, Tuple

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")
_jwks_cache: Optional[Tuple[float, Dict[str, Dict[str, Any]]]] = None


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad_len = (-len(data)) % 4
    return base64.urlsafe_b64decode(data + ("=" * pad_len))


def hash_password(password: str) -> str:
    """Hash password with bcrypt via passlib."""
    return pwd_context.hash(password)


def verify_password(password: str, stored_hash: Optional[str]) -> bool:
    """Verify plaintext password against stored bcrypt hash."""
    if not stored_hash or stored_hash.startswith("!oauth:"):
        return False
    try:
        return pwd_context.verify(password, stored_hash)
    except Exception:
        return False


def create_access_token(
    subject: str,
    role: str,
    name: str,
    email: str,
    expires_minutes: Optional[int] = None,
) -> str:
    """Create a signed HS256 JWT token carrying the user's role and expiry."""
    now = int(time.time())
    ttl_seconds = (expires_minutes or settings.JWT_EXPIRE_MINUTES) * 60
    header = {"alg": settings.JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": subject,
        "role": role,
        "name": name,
        "email": email,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(settings.JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(sig)}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """Verify and decode an HS256 JWT token."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token format.")

    header_b64, payload_b64, sig_b64 = parts
    try:
        header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        provided_sig = _b64url_decode(sig_b64)
    except Exception as exc:
        raise ValueError("Malformed token encoding.") from exc

    if header.get("alg") != settings.JWT_ALGORITHM:
        raise ValueError("Unsupported token algorithm.")

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()

    if not hmac.compare_digest(provided_sig, expected_sig):
        raise ValueError("Invalid token signature.")

    exp = payload.get("exp")
    if not isinstance(exp, (int, float)) or int(time.time()) >= int(exp):
        raise ValueError("Token has expired.")

    return payload


def create_oauth_state_token(role: str) -> str:
    """Create a short-lived signed state token carrying the target signup/login role."""
    payload = {
        "role": role,
        "nonce": secrets.token_hex(12),
        "exp": int(time.time()) + 600,
    }
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{payload_b64}.{_b64url_encode(sig)}"


def verify_oauth_state_token(state: str) -> str:
    """Verify signed OAuth state token and return the target role ('public' or 'organizer')."""
    try:
        payload_b64, sig_b64 = state.split(".")
        provided_sig = _b64url_decode(sig_b64)
        expected_sig = hmac.new(
            settings.JWT_SECRET_KEY.encode("utf-8"),
            payload_b64.encode("ascii"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(provided_sig, expected_sig):
            raise ValueError("Invalid OAuth state signature.")
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if int(time.time()) >= int(payload.get("exp", 0)):
            raise ValueError("OAuth state expired.")
        role = payload.get("role")
        if role not in ("public", "organizer"):
            raise ValueError("Invalid role in OAuth state.")
        return role
    except Exception as exc:
        raise ValueError("Invalid or expired Google OAuth state.") from exc


def _get_google_jwks(force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
    global _jwks_cache
    now = time.monotonic()
    if not force_refresh and _jwks_cache is not None and (now - _jwks_cache[0]) < 3600:
        return _jwks_cache[1]

    with httpx.Client(timeout=10.0) as client:
        resp = client.get(_GOOGLE_JWKS_URL)
        resp.raise_for_status()
        data = resp.json()

    keys = {k["kid"]: k for k in data.get("keys", []) if "kid" in k}
    _jwks_cache = (now, keys)
    return keys


def verify_google_id_token(id_token: str, expected_audience: str) -> Dict[str, Any]:
    """Verify a Google OIDC RS256 ID token against Google's JWKS."""
    parts = id_token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid Google ID token format.")

    header_b64, payload_b64, sig_b64 = parts
    header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
    payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    signature = _b64url_decode(sig_b64)

    if header.get("alg") != "RS256":
        raise ValueError("Unsupported Google ID token algorithm.")
    kid = header.get("kid")
    if not kid:
        raise ValueError("Google ID token missing key ID.")

    keys = _get_google_jwks()
    jwk = keys.get(kid)
    if jwk is None:
        keys = _get_google_jwks(force_refresh=True)
        jwk = keys.get(kid)
    if jwk is None:
        raise ValueError("Google signing key not found.")

    n = int.from_bytes(_b64url_decode(jwk["n"]), "big")
    e = int.from_bytes(_b64url_decode(jwk["e"]), "big")
    public_key = rsa.RSAPublicNumbers(e, n).public_key()
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    try:
        public_key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
    except InvalidSignature as exc:
        raise ValueError("Invalid Google ID token signature.") from exc

    if payload.get("iss") not in _GOOGLE_ISSUERS:
        raise ValueError("Unexpected Google ID token issuer.")
    if payload.get("aud") != expected_audience:
        raise ValueError("Unexpected Google ID token audience.")
    if int(payload.get("exp", 0)) <= int(time.time()):
        raise ValueError("Google ID token expired.")

    return payload

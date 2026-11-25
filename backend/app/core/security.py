import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from typing import Any, Dict, Optional, Tuple

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa, utils

from app.core.config import settings

# Simple in-memory JWKS cache: url -> (fetched_at_monotonic, keys_by_kid)
_jwks_cache: Dict[str, Tuple[float, Dict[str, Dict[str, Any]]]] = {}
_JWKS_CACHE_TTL_SECONDS = 3600


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad_len = (-len(data)) % 4
    return base64.urlsafe_b64decode(data + ("=" * pad_len))


# --- Password Hashing (scrypt) ---

def hash_password(password: str) -> str:
    """Hash a password using scrypt with a random 16-byte salt."""
    salt = os.urandom(16)
    n, r, p = 16384, 8, 1
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=32)
    return f"scrypt${n}${r}${p}${_b64url_encode(salt)}${_b64url_encode(derived)}"


def verify_password(password: str, stored_hash: Optional[str]) -> bool:
    """Verify a plaintext password against a stored scrypt hash."""
    if not stored_hash:
        return False
    try:
        algo, n_s, r_s, p_s, salt_b64, digest_b64 = stored_hash.split("$")
        if algo != "scrypt":
            return False
        salt = _b64url_decode(salt_b64)
        expected = _b64url_decode(digest_b64)
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n_s),
            r=int(r_s),
            p=int(p_s),
            dklen=len(expected),
        )
        return hmac.compare_digest(derived, expected)
    except Exception:
        return False


# --- App JWT (HS256) ---

def create_access_token(
    user_id: int,
    email: Optional[str],
    auth_provider: str,
    expires_minutes: Optional[int] = None,
) -> Tuple[str, str, int]:
    """Create a signed HS256 JWT access token. Returns (token, jti, ttl_seconds)."""
    now = int(time.time())
    ttl_seconds = (expires_minutes or settings.JWT_EXPIRE_MINUTES) * 60
    jti = uuid.uuid4().hex
    header = {"alg": settings.JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "email": email or "",
        "provider": auth_provider,
        "jti": jti,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(settings.JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(sig)}", jti, ttl_seconds


def decode_access_token(token: str) -> Dict[str, Any]:
    """Verify and decode an HS256 JWT access token. Raises ValueError on invalid/expired tokens."""
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


# --- OAuth OIDC ID Token Verification (Google & Apple) ---

async def _get_jwks_keys(jwks_url: str, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
    now = time.monotonic()
    cached = _jwks_cache.get(jwks_url)
    if not force_refresh and cached is not None and (now - cached[0]) < _JWKS_CACHE_TTL_SECONDS:
        return cached[1]

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(jwks_url)
        resp.raise_for_status()
        data = resp.json()

    keys = {k["kid"]: k for k in data.get("keys", []) if "kid" in k}
    _jwks_cache[jwks_url] = (now, keys)
    return keys


def _rsa_public_key_from_jwk(jwk: Dict[str, Any]) -> rsa.RSAPublicKey:
    n = int.from_bytes(_b64url_decode(jwk["n"]), "big")
    e = int.from_bytes(_b64url_decode(jwk["e"]), "big")
    return rsa.RSAPublicNumbers(e, n).public_key()


async def verify_oidc_id_token(
    id_token: str,
    jwks_url: str,
    expected_issuers: Tuple[str, ...],
    expected_audience: str,
) -> Dict[str, Any]:
    """Verify an RS256 OIDC ID token (Google / Apple) against the provider's JWKS."""
    parts = id_token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid OIDC ID token format.")

    header_b64, payload_b64, sig_b64 = parts
    header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
    payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    signature = _b64url_decode(sig_b64)

    if header.get("alg") != "RS256":
        raise ValueError(f"Unsupported OIDC ID token alg: {header.get('alg')}")

    kid = header.get("kid")
    if not kid:
        raise ValueError("OIDC ID token header missing 'kid'.")

    keys = await _get_jwks_keys(jwks_url)
    jwk = keys.get(kid)
    if jwk is None:
        # Provider may have rotated keys; refresh once
        keys = await _get_jwks_keys(jwks_url, force_refresh=True)
        jwk = keys.get(kid)
    if jwk is None:
        raise ValueError("Matching signing key not found in provider JWKS.")

    public_key = _rsa_public_key_from_jwk(jwk)
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    try:
        public_key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
    except InvalidSignature as exc:
        raise ValueError("Invalid OIDC ID token signature.") from exc

    now = int(time.time())
    if payload.get("iss") not in expected_issuers:
        raise ValueError("Unexpected OIDC issuer.")
    if payload.get("aud") != expected_audience:
        raise ValueError("Unexpected OIDC audience.")
    if int(payload.get("exp", 0)) <= now:
        raise ValueError("OIDC ID token expired.")

    return payload


def create_apple_client_secret() -> str:
    """Create an ES256-signed client_secret JWT for Sign in with Apple token exchange."""
    now = int(time.time())
    header = {"alg": "ES256", "kid": settings.APPLE_KEY_ID, "typ": "JWT"}
    payload = {
        "iss": settings.APPLE_TEAM_ID,
        "iat": now,
        "exp": now + 300,
        "aud": "https://appleid.apple.com",
        "sub": settings.APPLE_CLIENT_ID,
    }
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    pem = settings.APPLE_PRIVATE_KEY.replace("\\n", "\n").encode("utf-8")
    private_key = serialization.load_pem_private_key(pem, password=None)
    der_sig = private_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
    r, s = utils.decode_dss_signature(der_sig)
    raw_sig = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    return f"{header_b64}.{payload_b64}.{_b64url_encode(raw_sig)}"

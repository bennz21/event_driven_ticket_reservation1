import datetime
import json
import time
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.core.config import settings
from app.core.database import Base
from app.core.redis import redis_service
from app.core.security import _b64url_encode, verify_oidc_id_token
from app.main import app
from app.models import Event, Seat
from app.services.auth_service import AuthService


class AuthSystemTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async def _override_get_db():
            async with self.session_factory() as session:
                yield session

        app.dependency_overrides[get_db] = _override_get_db
        redis_service.set_client(None)

        async with self.session_factory() as db:
            db.add(
                Event(
                    id=1,
                    title="Auth Test Event",
                    description="Test",
                    venue_name="Test Venue",
                    event_date=datetime.datetime.utcnow() + datetime.timedelta(days=5),
                    total_rows=1,
                    seats_per_row=2,
                    base_price=50.0,
                )
            )
            await db.flush()
            db.add_all(
                [
                    Seat(id=1, event_id=1, row="A", seat_number=1, tier="VIP", price=90.0),
                    Seat(id=2, event_id=1, row="A", seat_number=2, tier="VIP", price=90.0),
                ]
            )
            await db.commit()

        self.transport = httpx.ASGITransport(app=app)
        self.client = httpx.AsyncClient(transport=self.transport, base_url="http://test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_register_login_me_and_logout_revocation(self) -> None:
        # Reject short password
        bad_reg = await self.client.post(
            "/api/v1/auth/register",
            json={"full_name": "Ada", "email": "ada@example.com", "password": "short"},
        )
        self.assertEqual(bad_reg.status_code, 422)

        # Register account
        reg = await self.client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Ada Lovelace",
                "email": "Ada@Example.com",
                "password": "supersecurepassword",
            },
        )
        self.assertEqual(reg.status_code, 201)
        reg_data = reg.json()
        self.assertEqual(reg_data["user"]["email"], "ada@example.com")
        self.assertEqual(reg_data["user"]["auth_provider"], "local")
        token = reg_data["access_token"]

        # Duplicate email fails with 409
        dup = await self.client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Ada Two",
                "email": "ada@example.com",
                "password": "supersecurepassword",
            },
        )
        self.assertEqual(dup.status_code, 409)

        # Wrong password fails with 401
        bad_login = await self.client.post(
            "/api/v1/auth/login",
            json={"email": "ada@example.com", "password": "wrongpassword"},
        )
        self.assertEqual(bad_login.status_code, 401)

        # Valid login succeeds
        login = await self.client.post(
            "/api/v1/auth/login",
            json={"email": "ada@example.com", "password": "supersecurepassword"},
        )
        self.assertEqual(login.status_code, 200)
        token = login.json()["access_token"]

        # /me works with Bearer token
        me = await self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["full_name"], "Ada Lovelace")

        # Logout revokes token
        logout = await self.client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(logout.status_code, 200)

        me_after = await self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(me_after.status_code, 401)

    async def test_google_and_apple_demo_login_and_reservation_linking(self) -> None:
        orig_demo = settings.OAUTH_ALLOW_DEMO_LOGIN
        orig_g_id = settings.GOOGLE_CLIENT_ID
        orig_a_id = settings.APPLE_CLIENT_ID
        try:
            settings.OAUTH_ALLOW_DEMO_LOGIN = True
            settings.GOOGLE_CLIENT_ID = ""
            settings.APPLE_CLIENT_ID = ""

            providers = (await self.client.get("/api/v1/auth/providers")).json()
            self.assertFalse(providers["google"]["configured"])
            self.assertTrue(providers["google"]["demo_enabled"])
            self.assertTrue(providers["apple"]["demo_enabled"])

            g_res = await self.client.post(
                "/api/v1/auth/oauth/demo",
                json={"provider": "google", "email": "guser@gmail.com", "full_name": "Google User"},
            )
            self.assertEqual(g_res.status_code, 200)
            g_data = g_res.json()
            self.assertEqual(g_data["user"]["auth_provider"], "google")

            a_res = await self.client.post(
                "/api/v1/auth/oauth/demo",
                json={"provider": "apple", "email": "auser@icloud.com", "full_name": "Apple User"},
            )
            self.assertEqual(a_res.status_code, 200)
            a_data = a_res.json()
            self.assertEqual(a_data["user"]["auth_provider"], "apple")
            apple_token = a_data["access_token"]

            # Hold and confirm a reservation while authenticated -> linked to user
            hold = await self.client.post(
                "/api/v1/events/1/seats/hold",
                json={"seat_ids": [1], "session_id": "sess_apple"},
            )
            self.assertEqual(hold.status_code, 200)

            confirm = await self.client.post(
                "/api/v1/events/1/reservations/confirm",
                headers={"Authorization": f"Bearer {apple_token}"},
                json={
                    "seat_ids": [1],
                    "session_id": "sess_apple",
                    "customer_name": "Apple User",
                    "customer_email": "",
                },
            )
            self.assertEqual(confirm.status_code, 201)
            self.assertEqual(confirm.json()["user_id"], a_data["user"]["id"])

            my_res = await self.client.get(
                "/api/v1/auth/reservations",
                headers={"Authorization": f"Bearer {apple_token}"},
            )
            self.assertEqual(my_res.status_code, 200)
            self.assertEqual(len(my_res.json()), 1)
            self.assertEqual(len(my_res.json()[0]["tickets"]), 1)

            # Demo endpoint is forbidden when OAUTH_ALLOW_DEMO_LOGIN is False
            settings.OAUTH_ALLOW_DEMO_LOGIN = False
            blocked = await self.client.post(
                "/api/v1/auth/oauth/demo",
                json={"provider": "google"},
            )
            self.assertEqual(blocked.status_code, 403)
        finally:
            settings.OAUTH_ALLOW_DEMO_LOGIN = orig_demo
            settings.GOOGLE_CLIENT_ID = orig_g_id
            settings.APPLE_CLIENT_ID = orig_a_id

    async def test_oidc_rs256_id_token_verification_and_one_time_code_exchange(self) -> None:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pub_numbers = private_key.public_key().public_numbers()
        n_bytes = pub_numbers.n.to_bytes((pub_numbers.n.bit_length() + 7) // 8, "big")
        e_bytes = pub_numbers.e.to_bytes((pub_numbers.e.bit_length() + 7) // 8, "big")
        jwk = {
            "kid": "test-kid-1",
            "kty": "RSA",
            "alg": "RS256",
            "n": _b64url_encode(n_bytes),
            "e": _b64url_encode(e_bytes),
        }

        header_b64 = _b64url_encode(
            json.dumps({"alg": "RS256", "kid": "test-kid-1", "typ": "JWT"}).encode("utf-8")
        )
        payload_b64 = _b64url_encode(
            json.dumps(
                {
                    "iss": "https://accounts.google.com",
                    "aud": "test-google-client-id",
                    "sub": "google-sub-123",
                    "email": "oauth.real@gmail.com",
                    "email_verified": True,
                    "name": "Real OAuth User",
                    "exp": int(time.time()) + 300,
                }
            ).encode("utf-8")
        )
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        sig = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        id_token = f"{header_b64}.{payload_b64}.{_b64url_encode(sig)}"

        with patch(
            "app.core.security._get_jwks_keys",
            new=AsyncMock(return_value={"test-kid-1": jwk}),
        ):
            claims = await verify_oidc_id_token(
                id_token=id_token,
                jwks_url="https://example.invalid/certs",
                expected_issuers=("https://accounts.google.com",),
                expected_audience="test-google-client-id",
            )
            self.assertEqual(claims["sub"], "google-sub-123")

            with self.assertRaises(ValueError):
                await verify_oidc_id_token(
                    id_token=id_token,
                    jwks_url="https://example.invalid/certs",
                    expected_issuers=("https://accounts.google.com",),
                    expected_audience="wrong-audience",
                )

        # Test one-time code exchange (succeeds once, fails on replay)
        async with self.session_factory() as db:
            auth_svc = AuthService(db)
            auth_res = await auth_svc.upsert_oauth_user(
                provider="google",
                provider_user_id=claims["sub"],
                email=claims["email"],
                full_name=claims["name"],
            )
            code = await AuthService.create_one_time_code(auth_res)

        ex1 = await self.client.post("/api/v1/auth/oauth/exchange", json={"code": code})
        self.assertEqual(ex1.status_code, 200)
        self.assertEqual(ex1.json()["user"]["email"], "oauth.real@gmail.com")

        ex2 = await self.client.post("/api/v1/auth/oauth/exchange", json={"code": code})
        self.assertEqual(ex2.status_code, 400)


if __name__ == "__main__":
    unittest.main()

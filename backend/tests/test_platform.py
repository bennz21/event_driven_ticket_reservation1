import datetime
import json
import time
import unittest
from unittest.mock import MagicMock, patch

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import _b64url_encode, create_oauth_state_token
from app.main import app


class PlatformIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False, class_=Session)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_end_to_end_roles_approval_booking_payment_and_cancellation(self) -> None:
        # 1. Admin cannot sign up via /signup
        bad_admin_signup = self.client.post(
            "/api/v1/auth/signup",
            json={
                "name": "Fake Admin",
                "email": settings.ADMIN_EMAIL,
                "password": "Password123!",
                "role": "admin",
            },
        )
        self.assertEqual(bad_admin_signup.status_code, 422)

        # 2. Organizer signup + separate login check
        org_client = TestClient(app)
        org_signup = org_client.post(
            "/api/v1/auth/signup",
            json={
                "name": "Olivia Organizer",
                "email": "olivia@events.com",
                "password": "Password123!",
                "role": "organizer",
            },
        )
        self.assertEqual(org_signup.status_code, 201)
        self.assertEqual(org_signup.json()["user"]["role"], "organizer")

        # Organizer cannot log into public login endpoint
        wrong_portal = org_client.post(
            "/api/v1/auth/public/login",
            json={"email": "olivia@events.com", "password": "Password123!"},
        )
        self.assertEqual(wrong_portal.status_code, 403)

        # Organizer cannot access admin endpoints
        self.assertEqual(org_client.get("/api/v1/admin/users").status_code, 403)

        # 3. Organizer creates an event -> starts as pending, invisible to public
        future_date = (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
        ev_res = org_client.post(
            "/api/v1/organizer/events",
            json={
                "title": "Neon Symphony",
                "description": "Live electronic orchestra show.",
                "event_date": future_date,
                "event_time": "20:00:00",
                "venue": "Grand Hall",
                "ticket_price": 45.00,
                "total_tickets": 5,
            },
        )
        self.assertEqual(ev_res.status_code, 201)
        event_id = ev_res.json()["id"]
        self.assertEqual(ev_res.json()["approval_status"], "pending")

        public_list_before = self.client.get("/api/v1/public/events").json()
        self.assertEqual(len(public_list_before), 0)

        # 4. Admin logs in using .env credentials and approves event
        admin_client = TestClient(app)
        admin_login = admin_client.post(
            "/api/v1/auth/admin/login",
            json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
        )
        self.assertEqual(admin_login.status_code, 200)
        self.assertEqual(admin_login.json()["user"]["role"], "admin")

        approve = admin_client.post(f"/api/v1/admin/events/{event_id}/approve")
        self.assertEqual(approve.status_code, 200)
        self.assertEqual(approve.json()["approval_status"], "approved")

        # Now public can browse & search it
        public_search = self.client.get("/api/v1/public/events?q=Neon").json()
        self.assertEqual(len(public_search), 1)

        # 5. Public user signs up, exceeds max qty rejected, books 3 tickets, fails payment -> tickets released
        pub_client = TestClient(app)
        pub_signup = pub_client.post(
            "/api/v1/auth/signup",
            json={
                "name": "Paul Public",
                "email": "paul@public.com",
                "password": "Password123!",
                "role": "public",
            },
        )
        self.assertEqual(pub_signup.status_code, 201)

        too_many = pub_client.post(
            "/api/v1/public/bookings",
            json={"event_id": event_id, "ticket_count": 6},
        )
        self.assertEqual(too_many.status_code, 400)

        bk_fail = pub_client.post(
            "/api/v1/public/bookings",
            json={"event_id": event_id, "ticket_count": 3},
        )
        self.assertEqual(bk_fail.status_code, 201)
        bk_fail_id = bk_fail.json()["id"]

        # Available tickets reduced to 2 while pending
        self.assertEqual(
            self.client.get(f"/api/v1/public/events/{event_id}").json()["available_tickets"],
            2,
        )

        # Failed payment restores tickets back to 5
        pay_fail = pub_client.post(
            f"/api/v1/public/bookings/{bk_fail_id}/pay",
            json={"payment_method": "card", "simulate_outcome": "failed"},
        )
        self.assertEqual(pay_fail.status_code, 200)
        self.assertEqual(pay_fail.json()["status"], "failed")
        self.assertEqual(pay_fail.json()["payment"]["status"], "failed")
        self.assertEqual(
            self.client.get(f"/api/v1/public/events/{event_id}").json()["available_tickets"],
            5,
        )

        # 6. Public books 4 tickets and pays successfully -> 4 unique ticket codes generated
        bk_ok = pub_client.post(
            "/api/v1/public/bookings",
            json={"event_id": event_id, "ticket_count": 4},
        )
        self.assertEqual(bk_ok.status_code, 201)
        bk_ok_id = bk_ok.json()["id"]

        pay_ok = pub_client.post(
            f"/api/v1/public/bookings/{bk_ok_id}/pay",
            json={"payment_method": "upi", "simulate_outcome": "success"},
        )
        self.assertEqual(pay_ok.status_code, 200)
        self.assertEqual(pay_ok.json()["status"], "confirmed")
        self.assertEqual(pay_ok.json()["payment"]["status"], "success")
        self.assertEqual(len(pay_ok.json()["tickets"]), 4)

        # Trying to book 2 more when only 1 left returns 409 Conflict
        overbook = pub_client.post(
            "/api/v1/public/bookings",
            json={"event_id": event_id, "ticket_count": 2},
        )
        self.assertEqual(overbook.status_code, 409)

        # Organizer sees bookings for their event
        org_bookings = org_client.get("/api/v1/organizer/bookings").json()
        self.assertEqual(len(org_bookings), 2)

        # 7. Public cancels confirmed booking -> payment refunded and tickets restored to 5
        cancelled = pub_client.post(f"/api/v1/public/bookings/{bk_ok_id}/cancel")
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.json()["status"], "cancelled")
        self.assertEqual(cancelled.json()["payment"]["status"], "refunded")
        self.assertEqual(
            self.client.get(f"/api/v1/public/events/{event_id}").json()["available_tickets"],
            5,
        )

        # 8. Organizer edits event -> resets approval_status to pending
        edited = org_client.put(
            f"/api/v1/organizer/events/{event_id}",
            json={
                "title": "Neon Symphony Redux",
                "description": "Updated live show.",
                "event_date": future_date,
                "event_time": "21:00:00",
                "venue": "Grand Hall",
                "ticket_price": 55.00,
                "total_tickets": 10,
            },
        )
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.json()["approval_status"], "pending")

        # 9. Admin views payments and blocks public user -> blocked user cannot log in or access /me
        self.assertGreaterEqual(len(admin_client.get("/api/v1/admin/payments").json()), 2)
        pub_id = pub_signup.json()["user"]["id"]
        blk = admin_client.patch(
            f"/api/v1/admin/users/{pub_id}/status",
            json={"status": "blocked"},
        )
        self.assertEqual(blk.status_code, 200)
        self.assertEqual(pub_client.get("/api/v1/auth/me").status_code, 403)
        relogin = pub_client.post(
            "/api/v1/auth/public/login",
            json={"email": "paul@public.com", "password": "Password123!"},
        )
        self.assertEqual(relogin.status_code, 403)

    def test_google_oauth_signup_login_and_role_isolation(self) -> None:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pub_nums = private_key.public_key().public_numbers()
        jwk = {
            "kid": "g-kid-1",
            "kty": "RSA",
            "alg": "RS256",
            "n": _b64url_encode(pub_nums.n.to_bytes((pub_nums.n.bit_length() + 7) // 8, "big")),
            "e": _b64url_encode(pub_nums.e.to_bytes((pub_nums.e.bit_length() + 7) // 8, "big")),
        }

        header_b64 = _b64url_encode(
            json.dumps({"alg": "RS256", "kid": "g-kid-1", "typ": "JWT"}).encode("utf-8")
        )
        payload_b64 = _b64url_encode(
            json.dumps(
                {
                    "iss": "https://accounts.google.com",
                    "aud": settings.GOOGLE_CLIENT_ID or "test-google-client-id",
                    "sub": "google-user-99",
                    "email": "gorg@events.com",
                    "email_verified": True,
                    "name": "Google Organizer",
                    "exp": int(time.time()) + 300,
                }
            ).encode("utf-8")
        )
        sig = private_key.sign(
            f"{header_b64}.{payload_b64}".encode("ascii"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        id_token = f"{header_b64}.{payload_b64}.{_b64url_encode(sig)}"

        orig_gid = settings.GOOGLE_CLIENT_ID
        orig_gsec = settings.GOOGLE_CLIENT_SECRET
        try:
            settings.GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID or "test-google-client-id"
            settings.GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET or "test-google-secret"

            login_redir = self.client.get(
                "/api/v1/auth/oauth/google/login?role=organizer",
                follow_redirects=False,
            )
            self.assertEqual(login_redir.status_code, 307)
            self.assertIn("accounts.google.com", login_redir.headers["location"])

            state = create_oauth_state_token("organizer")
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            mock_resp.json.return_value = {"id_token": id_token}

            with patch("app.routers.auth.httpx.Client") as mock_http_cls, patch(
                "app.core.security._get_google_jwks",
                return_value={"g-kid-1": jwk},
            ):
                mock_http_cls.return_value.__enter__.return_value.post.return_value = mock_resp

                cb = self.client.get(
                    f"/api/v1/auth/oauth/google/callback?code=authcode&state={state}",
                    follow_redirects=False,
                )
                self.assertEqual(cb.status_code, 302)
                self.assertTrue(cb.headers["location"].endswith("/organizer"))
                self.assertIn("access_token=", cb.headers.get("set-cookie", ""))

                # User created in DB as organizer can hit /auth/me via cookie
                me = self.client.get("/api/v1/auth/me")
                self.assertEqual(me.status_code, 200)
                self.assertEqual(me.json()["role"], "organizer")
                self.assertEqual(me.json()["email"], "gorg@events.com")

                # Attempting to sign in with same Google email on 'public' portal is rejected
                wrong_state = create_oauth_state_token("public")
                cb_wrong = self.client.get(
                    f"/api/v1/auth/oauth/google/callback?code=authcode&state={wrong_state}",
                    follow_redirects=False,
                )
                self.assertEqual(cb_wrong.status_code, 302)
                self.assertIn("oauth_error=", cb_wrong.headers["location"])
        finally:
            settings.GOOGLE_CLIENT_ID = orig_gid
            settings.GOOGLE_CLIENT_SECRET = orig_gsec

    def test_seated_event_creation_seat_selection_and_lifecycle(self) -> None:
        org_client = TestClient(app)
        org_client.post(
            "/api/v1/auth/signup",
            json={
                "name": "Seated Organizer",
                "email": "seated.org@events.com",
                "password": "Password123!",
                "role": "organizer",
            },
        )

        future_date = (datetime.date.today() + datetime.timedelta(days=12)).isoformat()
        ev_res = org_client.post(
            "/api/v1/organizer/events",
            json={
                "title": "Arena Live Seated",
                "description": "Numbered row seating event.",
                "event_date": future_date,
                "event_time": "19:30:00",
                "venue": "Main Arena",
                "ticket_price": 75.00,
                "seating_type": "seated",
                "total_rows": 2,
                "seats_per_row": 3,
            },
        )
        self.assertEqual(ev_res.status_code, 201)
        ev_data = ev_res.json()
        self.assertEqual(ev_data["seating_type"], "seated")
        self.assertEqual(ev_data["total_tickets"], 6)
        self.assertEqual(ev_data["available_tickets"], 6)
        event_id = ev_data["id"]

        admin_client = TestClient(app)
        admin_client.post(
            "/api/v1/auth/admin/login",
            json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
        )
        self.assertEqual(
            admin_client.post(f"/api/v1/admin/events/{event_id}/approve").status_code,
            200,
        )

        pub_a = TestClient(app)
        pub_a.post(
            "/api/v1/auth/signup",
            json={
                "name": "Buyer A",
                "email": "buyera@example.com",
                "password": "Password123!",
                "role": "public",
            },
        )
        pub_b = TestClient(app)
        pub_b.post(
            "/api/v1/auth/signup",
            json={
                "name": "Buyer B",
                "email": "buyerb@example.com",
                "password": "Password123!",
                "role": "public",
            },
        )

        seats = pub_a.get(f"/api/v1/public/events/{event_id}/seats").json()
        self.assertEqual(len(seats), 6)
        seat1, seat2 = seats[0], seats[1]

        # Booking seated event without seat_ids is rejected
        no_seats = pub_a.post(
            "/api/v1/public/bookings",
            json={"event_id": event_id, "ticket_count": 2},
        )
        self.assertEqual(no_seats.status_code, 400)

        # Buyer A locks seats [1, 2]
        bk_a = pub_a.post(
            "/api/v1/public/bookings",
            json={"event_id": event_id, "seat_ids": [seat1["id"], seat2["id"]]},
        )
        self.assertEqual(bk_a.status_code, 201)
        bk_a_id = bk_a.json()["id"]

        # Buyer B cannot book seat 1 while pending
        conflict = pub_b.post(
            "/api/v1/public/bookings",
            json={"event_id": event_id, "seat_ids": [seat1["id"]]},
        )
        self.assertEqual(conflict.status_code, 409)

        # Buyer A pays successfully -> tickets carry seat_label A1, A2
        paid = pub_a.post(
            f"/api/v1/public/bookings/{bk_a_id}/pay",
            json={"payment_method": "card", "simulate_outcome": "success"},
        )
        self.assertEqual(paid.status_code, 200)
        self.assertEqual(paid.json()["status"], "confirmed")
        labels = sorted(t["seat_label"] for t in paid.json()["tickets"])
        self.assertEqual(labels, ["A1", "A2"])

        seats_after_pay = pub_a.get(f"/api/v1/public/events/{event_id}/seats").json()
        self.assertEqual(seats_after_pay[0]["status"], "booked")
        self.assertEqual(seats_after_pay[1]["status"], "booked")

        # Buyer A cancels -> seats A1, A2 become available again and Buyer B can book A1
        cancelled = pub_a.post(f"/api/v1/public/bookings/{bk_a_id}/cancel")
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.json()["status"], "cancelled")

        bk_b = pub_b.post(
            "/api/v1/public/bookings",
            json={"event_id": event_id, "seat_ids": [seat1["id"]]},
        )
        self.assertEqual(bk_b.status_code, 201)


if __name__ == "__main__":
    unittest.main()

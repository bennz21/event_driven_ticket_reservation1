import datetime
import json
import unittest
from unittest.mock import MagicMock, patch

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import ApprovalStatus, Event, SeatingType, User, UserRole, UserStatus
from app.services import pinecone_service


class PineconeOptimizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(
            bind=self.engine, autocommit=False, autoflush=False, class_=Session
        )
        self.db = self.SessionLocal()
        self.org = User(
            name="Org",
            email="org@test.com",
            password_hash="hash",
            role=UserRole.ORGANIZER,
            status=UserStatus.ACTIVE,
        )
        self.db.add(self.org)
        self.db.commit()
        self.db.refresh(self.org)

        pinecone_service.close_pinecone_client()
        pinecone_service._state.quota_blocked_until = 0.0
        pinecone_service._query_cache.clear()
        pinecone_service._embed_cache.clear()

    def tearDown(self) -> None:
        pinecone_service.close_pinecone_client()
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_hash_excludes_price_and_tickets_and_batches_upserts(self) -> None:
        future_date = datetime.date.today() + datetime.timedelta(days=15)
        e1 = Event(
            organizer_id=self.org.id,
            title="Acoustic Night",
            description="Intimate live acoustic guitar concert " + ("x" * 400),
            event_date=future_date,
            event_time=datetime.time(19, 30),
            venue="Auditorium One, Austin",
            ticket_price=50.00,
            seating_type=SeatingType.OPEN,
            total_tickets=100,
            available_tickets=100,
            approval_status=ApprovalStatus.APPROVED,
        )
        e_pending = Event(
            organizer_id=self.org.id,
            title="Pending Draft",
            description="Should never be indexed",
            event_date=future_date,
            event_time=datetime.time(18, 0),
            venue="Draft Hall",
            ticket_price=30.00,
            seating_type=SeatingType.OPEN,
            total_tickets=50,
            available_tickets=50,
            approval_status=ApprovalStatus.PENDING,
        )
        e_past = Event(
            organizer_id=self.org.id,
            title="Past Concert",
            description="Already happened",
            event_date=datetime.date.today() - datetime.timedelta(days=2),
            event_time=datetime.time(20, 0),
            venue="Old Hall",
            ticket_price=20.00,
            seating_type=SeatingType.OPEN,
            total_tickets=50,
            available_tickets=0,
            approval_status=ApprovalStatus.APPROVED,
        )
        self.db.add_all([e1, e_pending, e_past])
        self.db.commit()

        # Price & available_tickets changes do NOT alter searchable text or hash
        h_before = pinecone_service.compute_event_hash(e1)
        e1.ticket_price = 99.00
        e1.available_tickets = 12
        self.assertEqual(pinecone_service.compute_event_hash(e1), h_before)

        # Compact searchable text truncates long descriptions
        self.assertLess(len(pinecone_service.build_searchable_text(e1)), 340)

        upsert_payloads = []
        with patch.object(pinecone_service, "_pinecone_configured", return_value=True), \
             patch.object(pinecone_service, "_gemini_configured", return_value=True), \
             patch.object(pinecone_service, "_get_host_and_client") as mock_hc, \
             patch.object(pinecone_service, "_get_embeddings_batch", return_value=[[0.1, 0.2]]):

            pinecone_service._state.index_mode = "vectors"
            pinecone_service._state.index_mode = "vectors"
            fake_client = MagicMock()
            fake_resp = MagicMock(status_code=200)
            fake_resp.json.return_value = {"upsertedCount": 1}

            def fake_request(method, url, **kwargs):
                if url.endswith("/vectors/upsert"):
                    upsert_payloads.append(kwargs["json"])
                return fake_resp

            fake_client.request.side_effect = fake_request
            mock_hc.return_value = ("example-host.pinecone.io", fake_client)

            written = pinecone_service.sync_events_to_pinecone([e1, e_pending, e_past], db=self.db)
            self.assertEqual(written, 1)
            self.assertEqual(len(upsert_payloads), 1)
            vec = upsert_payloads[0]["vectors"][0]
            self.assertEqual(vec["id"], f"event-{e1.id}")
            self.assertNotIn("text", vec["metadata"])
            self.assertEqual(set(vec["metadata"].keys()), {"event_id", "event_date", "city", "seating_type", "price"})
            self.assertEqual(e1.embedding_hash, h_before)

            # Re-syncing without searchable changes skips completely (0 writes, 0 embeddings)
            written_again = pinecone_service.sync_events_to_pinecone([e1], db=self.db)
            self.assertEqual(written_again, 0)
            self.assertEqual(len(upsert_payloads), 1)

    def test_documents_schema_mode_upserts_and_searches_without_gemini(self) -> None:
        future_date = datetime.date.today() + datetime.timedelta(days=12)
        ev = Event(
            organizer_id=self.org.id,
            title="Cyber Symphony",
            description="Orchestral synth showcase",
            event_date=future_date,
            event_time=datetime.time(20, 0),
            venue="Grand Hall, Tokyo",
            ticket_price=75.00,
            seating_type=SeatingType.SEATED,
            total_rows=4,
            seats_per_row=5,
            total_tickets=20,
            available_tickets=20,
            approval_status=ApprovalStatus.APPROVED,
        )
        self.db.add(ev)
        self.db.commit()

        calls = []
        with patch.object(pinecone_service, "_pinecone_configured", return_value=True), \
             patch.object(pinecone_service, "_get_host_and_client") as mock_hc, \
             patch.object(pinecone_service, "_get_embeddings_batch") as mock_embed:
            pinecone_service._state.index_mode = "documents"
            fake_client = MagicMock()

            def fake_request(method, url, **kwargs):
                calls.append((url, kwargs["json"]))
                if url.endswith("/documents/upsert"):
                    resp = MagicMock(status_code=202, content=b"")
                    return resp
                resp = MagicMock(status_code=200)
                if url.endswith("/documents/search"):
                    resp.json.return_value = {
                        "matches": [{"_id": f"event-{ev.id}", "_score": 0.42}],
                        "usage": {"read_units": 1},
                    }
                return resp

            fake_client.request.side_effect = fake_request
            mock_hc.return_value = ("example-host.pinecone.io", fake_client)

            self.assertEqual(pinecone_service.sync_events_to_pinecone([ev], db=self.db), 1)
            mock_embed.assert_not_called()
            self.assertTrue(calls[0][0].endswith("/namespaces/events/documents/upsert"))
            self.assertEqual(calls[0][1]["documents"][0]["_id"], f"event-{ev.id}")

            ids = pinecone_service.search_event_ids("orchestral synth", top_k=3)
            self.assertEqual(ids, [ev.id])
            self.assertTrue(calls[1][0].endswith("/namespaces/events/documents/search"))
            self.assertEqual(calls[1][1]["include_fields"], ["event_id"])

    def test_short_input_skip_ttl_cache_and_429_circuit_breaker(self) -> None:
        # Empty / short / greeting inputs never hit Pinecone or Gemini
        with patch.object(pinecone_service, "_get_embeddings_batch") as mock_embed:
            self.assertEqual(pinecone_service.search_event_ids(""), [])
            self.assertEqual(pinecone_service.search_event_ids("ab"), [])
            self.assertEqual(pinecone_service.search_event_ids("hi"), [])
            mock_embed.assert_not_called()

        # Repeated search hits TTL cache on 2nd call -> only 1 HTTP query executed
        future_date = datetime.date.today() + datetime.timedelta(days=10)
        ev = Event(
            organizer_id=self.org.id,
            title="Jazz Evening",
            description="Saxophone quartet live",
            event_date=future_date,
            event_time=datetime.time(20, 0),
            venue="Blue Note, Chicago",
            ticket_price=40.00,
            seating_type=SeatingType.OPEN,
            total_tickets=80,
            available_tickets=80,
            approval_status=ApprovalStatus.APPROVED,
        )
        self.db.add(ev)
        self.db.commit()

        query_calls = 0
        with patch.object(pinecone_service, "_pinecone_configured", return_value=True), \
             patch.object(pinecone_service, "_get_host_and_client") as mock_hc, \
             patch.object(pinecone_service, "_get_embeddings_batch", return_value=[[0.5, 0.5]]):

            pinecone_service._state.index_mode = "vectors"
            fake_client = MagicMock()
            ok_resp = MagicMock(status_code=200)
            ok_resp.json.return_value = {
                "matches": [{"id": f"event-{ev.id}", "score": 0.91}],
                "usage": {"readUnits": 2},
            }

            def fake_request(method, url, **kwargs):
                nonlocal query_calls
                query_calls += 1
                self.assertFalse(kwargs["json"]["includeMetadata"])
                self.assertEqual(kwargs["json"]["topK"], 3)
                self.assertIn("event_date", kwargs["json"]["filter"])
                return ok_resp

            fake_client.request.side_effect = fake_request
            mock_hc.return_value = ("example-host.pinecone.io", fake_client)

            ids1 = pinecone_service.search_event_ids("jazz music chicago", top_k=3)
            ids2 = pinecone_service.search_event_ids("  Jazz Music Chicago  ", top_k=3)
            self.assertEqual(ids1, [ev.id])
            self.assertEqual(ids2, [ev.id])
            self.assertEqual(query_calls, 1)

        # Monthly 429 limit trips circuit breaker cleanly and degrades to []
        pinecone_service._query_cache.clear()
        with patch.object(pinecone_service, "_pinecone_configured", return_value=True), \
             patch.object(pinecone_service, "_gemini_configured", return_value=True), \
             patch.object(pinecone_service, "_get_embeddings_batch", return_value=[[0.5, 0.5]]):
            pinecone_service._state.initialized = True
            pinecone_service._state.host = "example-host.pinecone.io"
            mock_http = MagicMock()
            limit_resp = MagicMock(
                status_code=429,
                text='{"message":"Monthly read unit quota limit exceeded"}',
                headers={},
            )
            mock_http.request.return_value = limit_resp
            pinecone_service._state.http = mock_http

            ids_fail = pinecone_service.search_event_ids("symphony orchestra")
            self.assertEqual(ids_fail, [])
            self.assertTrue(pinecone_service._is_quota_blocked())

    def test_cleanup_past_events_deletes_only_when_needed(self) -> None:
        past_ev = Event(
            organizer_id=self.org.id,
            title="Yesterday Show",
            description="Past",
            event_date=datetime.date.today() - datetime.timedelta(days=1),
            event_time=datetime.time(19, 0),
            venue="Past Venue",
            ticket_price=25.00,
            seating_type=SeatingType.OPEN,
            total_tickets=20,
            available_tickets=10,
            approval_status=ApprovalStatus.APPROVED,
            embedding_hash="abc123",
        )
        self.db.add(past_ev)
        self.db.commit()

        with patch.object(pinecone_service, "delete_event_vectors", return_value=1) as mock_del:
            deleted = pinecone_service.cleanup_past_events(self.db)
            self.assertEqual(deleted, 1)
            mock_del.assert_called_once_with([past_ev.id])
            self.db.refresh(past_ev)
            self.assertIsNone(past_ev.embedding_hash)

            # Second run with no stale rows makes 0 Pinecone calls
            mock_del.reset_mock()
            self.assertEqual(pinecone_service.cleanup_past_events(self.db), 0)
            mock_del.assert_not_called()

const API_BASE = '/api/v1';

// Session ID unique to this browser tab (stored in sessionStorage)
export function getSessionId() {
  let sessionId = sessionStorage.getItem('ticket_app_session_id');
  if (!sessionId) {
    sessionId = `user_${Math.random().toString(36).substring(2, 9)}`;
    sessionStorage.setItem('ticket_app_session_id', sessionId);
  }
  return sessionId;
}

export async function fetchEvents() {
  const res = await fetch(`${API_BASE}/events`);
  if (!res.ok) throw new Error('Failed to fetch events');
  return res.json();
}

export async function fetchSeats(eventId) {
  const res = await fetch(`${API_BASE}/events/${eventId}/seats`);
  if (!res.ok) throw new Error('Failed to fetch seats');
  return res.json();
}

export async function holdSeats(eventId, seatIds, sessionId) {
  const res = await fetch(`${API_BASE}/events/${eventId}/seats/hold`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ seat_ids: seatIds, session_id: sessionId }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to hold seats' }));
    throw new Error(error.detail || 'Failed to hold seats');
  }
  return res.json();
}

export async function releaseSeats(eventId, seatIds, sessionId) {
  const res = await fetch(`${API_BASE}/events/${eventId}/seats/release`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ seat_ids: seatIds, session_id: sessionId }),
  });
  if (!res.ok) throw new Error('Failed to release seats');
  return res.json();
}

export async function confirmReservation(eventId, data) {
  const res = await fetch(`${API_BASE}/events/${eventId}/reservations/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Reservation failed' }));
    throw new Error(error.detail || 'Reservation failed');
  }
  return res.json();
}

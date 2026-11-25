const API_BASE = '/api/v1';
const TOKEN_STORAGE_KEY = 'ticket_app_access_token';

// Session ID unique to this browser tab (stored in sessionStorage)
export function getSessionId() {
  let sessionId = sessionStorage.getItem('ticket_app_session_id');
  if (!sessionId) {
    sessionId = `user_${Math.random().toString(36).substring(2, 9)}`;
    sessionStorage.setItem('ticket_app_session_id', sessionId);
  }
  return sessionId;
}

export function getStoredToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token) {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearStoredToken() {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

function authHeaders() {
  const token = getStoredToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function parseErrorDetail(res, fallback) {
  const error = await res.json().catch(() => ({ detail: fallback }));
  if (Array.isArray(error.detail)) {
    return error.detail.map((d) => d.msg || String(d)).join(', ');
  }
  return error.detail || fallback;
}

// --- Auth API ---

export async function registerAccount({ full_name, email, password }) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ full_name, email, password }),
  });
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, 'Failed to create account'));
  }
  return res.json();
}

export async function loginAccount({ email, password }) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, 'Sign in failed'));
  }
  return res.json();
}

export async function fetchCurrentUser() {
  const token = getStoredToken();
  if (!token) return null;
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) {
    clearStoredToken();
    return null;
  }
  return res.json();
}

export async function logoutAccount() {
  const token = getStoredToken();
  if (token) {
    await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      headers: { ...authHeaders() },
    }).catch(() => {});
  }
  clearStoredToken();
}

export async function fetchMyReservations() {
  const res = await fetch(`${API_BASE}/auth/reservations`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, 'Failed to load tickets'));
  }
  return res.json();
}

export async function fetchAuthProviders() {
  const res = await fetch(`${API_BASE}/auth/providers`);
  if (!res.ok) {
    return {
      google: { configured: false, demo_enabled: false },
      apple: { configured: false, demo_enabled: false },
    };
  }
  return res.json();
}

export function getOAuthLoginUrl(provider) {
  return `${API_BASE}/auth/oauth/${provider}/login`;
}

export async function exchangeOAuthCode(code) {
  const res = await fetch(`${API_BASE}/auth/oauth/exchange`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  });
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, 'OAuth login failed'));
  }
  return res.json();
}

export async function demoOAuthLogin({ provider, email, full_name }) {
  const res = await fetch(`${API_BASE}/auth/oauth/demo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider, email, full_name }),
  });
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, `${provider} sign-in failed`));
  }
  return res.json();
}

// --- Events, Seats & Reservations ---

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
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ seat_ids: seatIds, session_id: sessionId }),
  });
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, 'Failed to hold seats'));
  }
  return res.json();
}

export async function releaseSeats(eventId, seatIds, sessionId) {
  const res = await fetch(`${API_BASE}/events/${eventId}/seats/release`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ seat_ids: seatIds, session_id: sessionId }),
  });
  if (!res.ok) throw new Error('Failed to release seats');
  return res.json();
}

export async function confirmReservation(eventId, data) {
  const res = await fetch(`${API_BASE}/events/${eventId}/reservations/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, 'Reservation failed'));
  }
  return res.json();
}

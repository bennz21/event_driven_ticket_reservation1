const rawApiUrl = import.meta.env.VITE_API_URL || '';
const API_BASE = rawApiUrl ? `${rawApiUrl.replace(/\/+$/, '')}/api/v1` : '/api/v1';

async function apiFetch(path, options = {}) {
  const { headers = {}, ...rest } = options;
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...headers,
    },
    ...rest,
  });

  if (res.status === 204) {
    return null;
  }

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    if (data?.detail) {
      message = Array.isArray(data.detail)
        ? data.detail.map((d) => d.msg || String(d)).join(', ')
        : String(data.detail);
    }
    const err = new Error(message);
    err.status = res.status;
    throw err;
  }
  return data;
}

// --- Auth ---
export function signupAccount(payload) {
  return apiFetch('/auth/signup', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function loginByRole(role, payload) {
  return apiFetch(`/auth/${role}/login`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function fetchCurrentSession() {
  try {
    return await apiFetch('/auth/me');
  } catch (err) {
    if (err.status === 401 || err.status === 403) {
      return null;
    }
    throw err;
  }
}

export function logoutSession() {
  return apiFetch('/auth/logout', { method: 'POST' });
}

export function getGoogleOAuthUrl(role) {
  return `${API_BASE}/auth/oauth/google/login?role=${encodeURIComponent(role)}`;
}

// --- Admin ---
export function adminFetchEvents(approvalStatus = '') {
  const qs = approvalStatus ? `?approval_status=${encodeURIComponent(approvalStatus)}` : '';
  return apiFetch(`/admin/events${qs}`);
}

export function adminApproveEvent(eventId) {
  return apiFetch(`/admin/events/${eventId}/approve`, { method: 'POST' });
}

export function adminRejectEvent(eventId) {
  return apiFetch(`/admin/events/${eventId}/reject`, { method: 'POST' });
}

export function adminFetchUsers(role = '') {
  const qs = role ? `?role=${encodeURIComponent(role)}` : '';
  return apiFetch(`/admin/users${qs}`);
}

export function adminUpdateUserStatus(userId, status) {
  return apiFetch(`/admin/users/${userId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}

export function adminDeleteUser(userId) {
  return apiFetch(`/admin/users/${userId}`, { method: 'DELETE' });
}

export function adminFetchBookings() {
  return apiFetch('/admin/bookings');
}

export function adminFetchPayments() {
  return apiFetch('/admin/payments');
}

// --- Organizer ---
export function organizerFetchEvents() {
  return apiFetch('/organizer/events');
}

export function organizerCreateEvent(payload) {
  return apiFetch('/organizer/events', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function organizerUpdateEvent(eventId, payload) {
  return apiFetch(`/organizer/events/${eventId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function organizerDeleteEvent(eventId) {
  return apiFetch(`/organizer/events/${eventId}`, { method: 'DELETE' });
}

export function organizerFetchBookings() {
  return apiFetch('/organizer/bookings');
}

// --- Public ---
export function publicBrowseEvents(query = '') {
  const qs = query.trim() ? `?q=${encodeURIComponent(query.trim())}` : '';
  return apiFetch(`/public/events${qs}`);
}

export function publicFetchEventSeats(eventId) {
  return apiFetch(`/public/events/${eventId}/seats`);
}

export function publicCreateBooking(payload) {
  return apiFetch('/public/bookings', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function publicPayBooking(bookingId, payload) {
  return apiFetch(`/public/bookings/${bookingId}/pay`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function publicFetchBookings() {
  return apiFetch('/public/bookings');
}

export function publicFetchBookingDetail(bookingId) {
  return apiFetch(`/public/bookings/${bookingId}`);
}

export function publicCancelBooking(bookingId) {
  return apiFetch(`/public/bookings/${bookingId}/cancel`, { method: 'POST' });
}

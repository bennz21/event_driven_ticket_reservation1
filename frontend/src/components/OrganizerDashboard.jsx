import React, { useCallback, useEffect, useState } from 'react';
import {
  Armchair,
  Calendar,
  CalendarRange,
  Edit3,
  MapPin,
  Plus,
  Ticket,
  Trash2,
  Users,
  X,
} from 'lucide-react';
import {
  organizerCreateEvent,
  organizerDeleteEvent,
  organizerFetchBookings,
  organizerFetchEvents,
  organizerUpdateEvent,
} from '../api/client';

const EMPTY_FORM = {
  title: '',
  description: '',
  event_date: '',
  event_time: '19:00',
  venue: '',
  ticket_price: '50.00',
  seating_type: 'seated',
  total_rows: '6',
  seats_per_row: '10',
  total_tickets: '100',
};

const APPROVAL_BADGE = {
  pending: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  approved: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  rejected: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
};

export default function OrganizerDashboard() {
  const [events, setEvents] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const loadData = useCallback(async () => {
    setError('');
    try {
      const [ev, bk] = await Promise.all([
        organizerFetchEvents(),
        organizerFetchBookings(),
      ]);
      setEvents(ev);
      setBookings(bk);
    } catch (err) {
      setError(err.message || 'Failed to load organizer data.');
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const openCreate = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setShowForm(true);
    setError('');
    setNotice('');
  };

  const openEdit = (ev) => {
    setEditingId(ev.id);
    setForm({
      title: ev.title,
      description: ev.description,
      event_date: ev.event_date,
      event_time: String(ev.event_time).slice(0, 5),
      venue: ev.venue,
      ticket_price: String(ev.ticket_price),
      seating_type: ev.seating_type || 'open',
      total_rows: String(ev.total_rows || 6),
      seats_per_row: String(ev.seats_per_row || 10),
      total_tickets: String(ev.total_tickets),
    });
    setShowForm(true);
    setError('');
    setNotice('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    setNotice('');
    try {
      const isSeated = form.seating_type === 'seated';
      const payload = {
        title: form.title,
        description: form.description,
        event_date: form.event_date,
        event_time: form.event_time.length === 5 ? `${form.event_time}:00` : form.event_time,
        venue: form.venue,
        ticket_price: Number(form.ticket_price),
        seating_type: form.seating_type,
        total_rows: isSeated ? Number(form.total_rows) : null,
        seats_per_row: isSeated ? Number(form.seats_per_row) : null,
        total_tickets: isSeated
          ? Number(form.total_rows) * Number(form.seats_per_row)
          : Number(form.total_tickets),
      };
      if (editingId) {
        await organizerUpdateEvent(editingId, payload);
        setNotice('Event updated and resubmitted with "pending" status for Admin approval.');
      } else {
        await organizerCreateEvent(payload);
        setNotice('Event created with "pending" status. It will be public once approved by Admin.');
      }
      setShowForm(false);
      await loadData();
    } catch (err) {
      setError(err.message || 'Could not save event.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (ev) => {
    if (!window.confirm(`Delete "${ev.title}"?`)) return;
    try {
      await organizerDeleteEvent(ev.id);
      await loadData();
    } catch (err) {
      setError(err.message);
    }
  };

  const confirmedBookings = bookings.filter((b) => b.status === 'confirmed');
  const totalSold = confirmedBookings.reduce((sum, b) => sum + b.ticket_count, 0);
  const seatedPreviewCount =
    (Number(form.total_rows) || 0) * (Number(form.seats_per_row) || 0);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center">
            <CalendarRange className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Event Organizer Studio</h1>
            <p className="text-xs text-slate-400">
              Create seated or open-ticket events and track confirmed sales.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={openCreate}
          className="self-start px-5 py-2.5 rounded-full bg-[#1a73e8] hover:bg-[#2b84f8] text-white text-xs sm:text-sm font-semibold flex items-center gap-2 shadow-[0_0_20px_rgba(26,115,232,0.35)]"
        >
          <Plus className="w-4 h-4" />
          <span>Create Event</span>
        </button>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-2xl bg-[#081021] border border-[#172542] p-4">
          <div className="text-xs text-slate-400">My Events</div>
          <div className="mt-1.5 text-2xl font-extrabold font-mono text-white">{events.length}</div>
        </div>
        <div className="rounded-2xl bg-[#081021] border border-[#172542] p-4">
          <div className="text-xs text-slate-400">Tickets Sold (Confirmed)</div>
          <div className="mt-1.5 text-2xl font-extrabold font-mono text-emerald-400">{totalSold}</div>
        </div>
        <div className="rounded-2xl bg-[#081021] border border-[#172542] p-4">
          <div className="text-xs text-slate-400">Bookings on My Events</div>
          <div className="mt-1.5 text-2xl font-extrabold font-mono text-[#60b5ff]">{bookings.length}</div>
        </div>
      </div>

      {notice && (
        <div className="p-3.5 rounded-xl bg-emerald-950/60 border border-emerald-600/40 text-emerald-300 text-xs">
          {notice}
        </div>
      )}
      {error && (
        <div className="p-3.5 rounded-xl bg-rose-950/70 border border-rose-600/60 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {/* Event Form Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="animate-modal-pop bg-[#091224] border border-[#192848] rounded-2xl w-full max-w-lg p-6 sm:p-8 shadow-2xl relative max-h-[90vh] overflow-y-auto">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="absolute top-5 right-5 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
            <h2 className="text-lg font-bold text-white">
              {editingId ? 'Edit Event (resets to pending)' : 'Create New Event'}
            </h2>
            <form onSubmit={handleSubmit} className="mt-5 space-y-4">
              {/* Seating Mode Selector */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-2">
                  Event Seating Format
                </label>
                <div className="grid grid-cols-2 gap-2.5">
                  <button
                    type="button"
                    onClick={() => setForm({ ...form, seating_type: 'seated' })}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      form.seating_type === 'seated'
                        ? 'bg-[#1a73e8]/20 border-[#2684ff] text-white'
                        : 'bg-[#060d1c] border-[#172542] text-slate-400 hover:text-white'
                    }`}
                  >
                    <Armchair className="w-4 h-4 text-[#2684ff] mb-1.5" />
                    <div className="text-xs font-bold">Limited Seated Event</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">
                      Public picks numbered seats
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setForm({ ...form, seating_type: 'open' })}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      form.seating_type === 'open'
                        ? 'bg-[#1a73e8]/20 border-[#2684ff] text-white'
                        : 'bg-[#060d1c] border-[#172542] text-slate-400 hover:text-white'
                    }`}
                  >
                    <Users className="w-4 h-4 text-emerald-400 mb-1.5" />
                    <div className="text-xs font-bold">Open Event</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">
                      Total ticket count only
                    </div>
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Title</label>
                <input
                  type="text"
                  required
                  minLength={3}
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#060d1c] border border-[#1b2b4d] text-sm text-white focus:outline-none focus:ring-2 focus:ring-[#2684ff]"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Description</label>
                <textarea
                  required
                  minLength={5}
                  rows={3}
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#060d1c] border border-[#1b2b4d] text-sm text-white focus:outline-none focus:ring-2 focus:ring-[#2684ff]"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Date</label>
                  <input
                    type="date"
                    required
                    value={form.event_date}
                    onChange={(e) => setForm({ ...form, event_date: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#060d1c] border border-[#1b2b4d] text-sm text-white focus:outline-none focus:ring-2 focus:ring-[#2684ff]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Time</label>
                  <input
                    type="time"
                    required
                    value={form.event_time}
                    onChange={(e) => setForm({ ...form, event_time: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#060d1c] border border-[#1b2b4d] text-sm text-white focus:outline-none focus:ring-2 focus:ring-[#2684ff]"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Venue</label>
                <input
                  type="text"
                  required
                  minLength={2}
                  value={form.venue}
                  onChange={(e) => setForm({ ...form, venue: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#060d1c] border border-[#1b2b4d] text-sm text-white focus:outline-none focus:ring-2 focus:ring-[#2684ff]"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Ticket Price ($)</label>
                <input
                  type="number"
                  required
                  min="0.01"
                  step="0.01"
                  value={form.ticket_price}
                  onChange={(e) => setForm({ ...form, ticket_price: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#060d1c] border border-[#1b2b4d] text-sm text-white focus:outline-none focus:ring-2 focus:ring-[#2684ff]"
                />
              </div>

              {form.seating_type === 'seated' ? (
                <div className="rounded-xl bg-[#060d1c] border border-[#172542] p-3.5 space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-slate-300 mb-1">
                        Rows (A–Z, max 26)
                      </label>
                      <input
                        type="number"
                        required
                        min="1"
                        max="26"
                        value={form.total_rows}
                        onChange={(e) => setForm({ ...form, total_rows: e.target.value })}
                        className="w-full px-3 py-2 rounded-lg bg-[#091224] border border-[#1b2b4d] text-sm text-white focus:outline-none focus:ring-2 focus:ring-[#2684ff]"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-300 mb-1">
                        Seats per Row (max 30)
                      </label>
                      <input
                        type="number"
                        required
                        min="1"
                        max="30"
                        value={form.seats_per_row}
                        onChange={(e) => setForm({ ...form, seats_per_row: e.target.value })}
                        className="w-full px-3 py-2 rounded-lg bg-[#091224] border border-[#1b2b4d] text-sm text-white focus:outline-none focus:ring-2 focus:ring-[#2684ff]"
                      />
                    </div>
                  </div>
                  <div className="text-xs text-[#60b5ff] font-mono">
                    Total generated seats: <strong>{seatedPreviewCount}</strong>
                  </div>
                </div>
              ) : (
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Total Tickets Available
                  </label>
                  <input
                    type="number"
                    required
                    min="1"
                    value={form.total_tickets}
                    onChange={(e) => setForm({ ...form, total_tickets: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#060d1c] border border-[#1b2b4d] text-sm text-white focus:outline-none focus:ring-2 focus:ring-[#2684ff]"
                  />
                </div>
              )}

              <button
                type="submit"
                disabled={submitting}
                className="w-full py-3 rounded-full bg-[#1a73e8] hover:bg-[#2b84f8] text-white font-semibold text-sm disabled:opacity-50"
              >
                {submitting ? 'Saving...' : editingId ? 'Save Changes (Submit for Approval)' : 'Create Event'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* My Events List */}
      <div className="space-y-3">
        <h2 className="text-lg font-bold text-white">My Listed Events</h2>
        {events.length === 0 ? (
          <div className="rounded-2xl bg-[#081021] border border-[#172542] p-10 text-center text-sm text-slate-400">
            You haven&apos;t created any events yet. Click <strong>Create Event</strong> to submit one.
          </div>
        ) : (
          events.map((ev) => (
            <div
              key={ev.id}
              className="rounded-2xl bg-[#081021] border border-[#172542] p-5 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4"
            >
              <div className="space-y-1.5">
                <div className="flex flex-wrap items-center gap-2.5">
                  <h3 className="text-base font-bold text-white">{ev.title}</h3>
                  <span
                    className={`text-[10px] uppercase font-mono px-2.5 py-0.5 rounded-full border ${
                      APPROVAL_BADGE[ev.approval_status]
                    }`}
                  >
                    {ev.approval_status}
                  </span>
                  <span className="text-[10px] uppercase font-mono px-2.5 py-0.5 rounded-full border bg-[#0d1c3b] border-[#1f3b73] text-[#60b5ff]">
                    {ev.seating_type === 'seated'
                      ? `Seated (${ev.total_rows}×${ev.seats_per_row})`
                      : 'Open Event'}
                  </span>
                </div>
                <p className="text-xs text-slate-400 max-w-2xl">{ev.description}</p>
                <div className="flex flex-wrap gap-4 text-xs text-slate-400 pt-1">
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-[#2684ff]" />
                    {ev.venue}
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-[#2684ff]" />
                    {ev.event_date} {String(ev.event_time).slice(0, 5)}
                  </span>
                  <span className="text-emerald-400 font-semibold">${ev.ticket_price.toFixed(2)}</span>
                  <span className="font-mono text-white">
                    Available: {ev.available_tickets} / {ev.total_tickets}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  type="button"
                  onClick={() => openEdit(ev)}
                  className="px-4 py-2 rounded-full bg-[#0c1830] hover:bg-[#132345] border border-[#22355a] text-xs font-semibold text-white flex items-center gap-1.5"
                >
                  <Edit3 className="w-3.5 h-3.5 text-[#2684ff]" />
                  <span>Edit</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleDelete(ev)}
                  className="px-4 py-2 rounded-full bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/40 text-xs font-semibold text-rose-300 flex items-center gap-1.5"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Delete</span>
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Bookings for Organizer's Events */}
      <div className="space-y-3">
        <h2 className="text-lg font-bold text-white">Bookings &amp; Tickets Sold (Your Events)</h2>
        <div className="rounded-2xl bg-[#081021] border border-[#172542] overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-[#14203b] text-slate-400 uppercase font-mono text-[11px]">
              <tr>
                <th className="px-5 py-3.5">Booking</th>
                <th className="px-5 py-3.5">Event</th>
                <th className="px-5 py-3.5">Buyer</th>
                <th className="px-5 py-3.5">Qty</th>
                <th className="px-5 py-3.5">Amount</th>
                <th className="px-5 py-3.5">Status</th>
                <th className="px-5 py-3.5">Ticket Codes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#14203b]">
              {bookings.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-8 text-center text-slate-400">
                    No bookings for your events yet.
                  </td>
                </tr>
              ) : (
                bookings.map((b) => (
                  <tr key={b.id} className="hover:bg-[#0c162e]/60">
                    <td className="px-5 py-3.5 font-mono text-[#60b5ff]">#{b.id}</td>
                    <td className="px-5 py-3.5 text-white font-medium">{b.event_title}</td>
                    <td className="px-5 py-3.5 text-slate-300">{b.user_name} ({b.user_email})</td>
                    <td className="px-5 py-3.5 font-mono text-white">{b.ticket_count}</td>
                    <td className="px-5 py-3.5 font-mono text-emerald-400">${b.total_amount.toFixed(2)}</td>
                    <td className="px-5 py-3.5 uppercase font-mono text-[11px] text-slate-200">{b.status}</td>
                    <td className="px-5 py-3.5 font-mono text-[11px] text-slate-300">
                      {b.tickets.length > 0 ? (
                        <span className="inline-flex items-center gap-1">
                          <Ticket className="w-3 h-3 text-[#2684ff]" />
                          {b.tickets
                            .map((t) => (t.seat_label ? `${t.seat_label} (${t.ticket_code})` : t.ticket_code))
                            .join(', ')}
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

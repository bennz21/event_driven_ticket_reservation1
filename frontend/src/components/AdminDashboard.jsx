import React, { useCallback, useEffect, useState } from 'react';
import {
  Ban,
  Calendar,
  CheckCircle2,
  CreditCard,
  RefreshCw,
  Shield,
  Ticket,
  Trash2,
  UserCheck,
  Users,
  XCircle,
} from 'lucide-react';
import {
  adminApproveEvent,
  adminDeleteUser,
  adminFetchBookings,
  adminFetchEvents,
  adminFetchPayments,
  adminFetchUsers,
  adminRejectEvent,
  adminUpdateUserStatus,
} from '../api/client';

const STATUS_BADGE = {
  pending: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  approved: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  rejected: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  active: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  blocked: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  confirmed: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  cancelled: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
  failed: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  success: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  refunded: 'bg-sky-500/15 text-sky-300 border-sky-500/30',
};

export default function AdminDashboard() {
  const [tab, setTab] = useState('events');
  const [events, setEvents] = useState([]);
  const [users, setUsers] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [payments, setPayments] = useState([]);
  const [eventFilter, setEventFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [ev, us, bk, py] = await Promise.all([
        adminFetchEvents(eventFilter),
        adminFetchUsers(),
        adminFetchBookings(),
        adminFetchPayments(),
      ]);
      setEvents(ev);
      setUsers(us);
      setBookings(bk);
      setPayments(py);
    } catch (err) {
      setError(err.message || 'Failed to load admin data');
    } finally {
      setLoading(false);
    }
  }, [eventFilter]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const handleApprove = async (id) => {
    try {
      await adminApproveEvent(id);
      await loadAll();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleReject = async (id) => {
    try {
      await adminRejectEvent(id);
      await loadAll();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleToggleBlock = async (u) => {
    const nextStatus = u.status === 'active' ? 'blocked' : 'active';
    try {
      await adminUpdateUserStatus(u.id, nextStatus);
      await loadAll();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteUser = async (u) => {
    if (!window.confirm(`Remove ${u.name} (${u.email}) and all their associated records?`)) return;
    try {
      await adminDeleteUser(u.id);
      await loadAll();
    } catch (err) {
      setError(err.message);
    }
  };

  const pendingCount = events.filter((e) => e.approval_status === 'pending').length;
  const totalRevenue = payments
    .filter((p) => p.status === 'success')
    .reduce((acc, p) => acc + p.amount, 0);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center">
            <Shield className="w-5 h-5 text-rose-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Admin Control Center</h1>
            <p className="text-xs text-slate-400">
              Approve events, manage Organizer &amp; Public accounts, and monitor bookings &amp; payments.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={loadAll}
          className="self-start px-4 py-2 rounded-full bg-[#0b162d] hover:bg-[#122244] border border-[#1f345c] text-xs font-semibold text-white flex items-center gap-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Pending Approvals', value: pendingCount, icon: Calendar, color: 'text-amber-400' },
          { label: 'Registered Accounts', value: users.length, icon: Users, color: 'text-[#2684ff]' },
          { label: 'Total Bookings', value: bookings.length, icon: Ticket, color: 'text-emerald-400' },
          { label: 'Confirmed Revenue', value: `$${totalRevenue.toFixed(2)}`, icon: CreditCard, color: 'text-sky-400' },
        ].map((s) => (
          <div key={s.label} className="rounded-2xl bg-[#081021] border border-[#172542] p-4">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>{s.label}</span>
              <s.icon className={`w-4 h-4 ${s.color}`} />
            </div>
            <div className="mt-2 text-2xl font-extrabold text-white font-mono">{s.value}</div>
          </div>
        ))}
      </div>

      {error && (
        <div className="p-3 rounded-xl bg-rose-950/70 border border-rose-600/60 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-[#14203b] pb-3">
        {[
          { id: 'events', label: `Events (${events.length})` },
          { id: 'users', label: `Users (${users.length})` },
          { id: 'bookings', label: `Bookings (${bookings.length})` },
          { id: 'payments', label: `Payments (${payments.length})` },
        ].map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-full text-xs font-semibold transition-all ${
              tab === t.id
                ? 'bg-[#1a73e8] text-white'
                : 'bg-[#091224] text-slate-400 hover:text-white border border-[#172542]'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Events Tab */}
      {tab === 'events' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            {['', 'pending', 'approved', 'rejected'].map((st) => (
              <button
                key={st || 'all'}
                type="button"
                onClick={() => setEventFilter(st)}
                className={`px-3 py-1 rounded-full text-xs font-medium border ${
                  eventFilter === st
                    ? 'bg-[#1a73e8]/20 border-[#2684ff] text-[#60b5ff]'
                    : 'bg-[#081021] border-[#172542] text-slate-400 hover:text-white'
                }`}
              >
                {st ? st.toUpperCase() : 'ALL'}
              </button>
            ))}
          </div>

          {events.length === 0 ? (
            <div className="rounded-2xl bg-[#081021] border border-[#172542] p-10 text-center text-sm text-slate-400">
              No events found in MySQL for this filter.
            </div>
          ) : (
            <div className="space-y-3">
              {events.map((ev) => (
                <div
                  key={ev.id}
                  className="rounded-2xl bg-[#081021] border border-[#172542] p-5 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4"
                >
                  <div className="space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2.5">
                      <h3 className="text-base font-bold text-white">{ev.title}</h3>
                      <span
                        className={`text-[10px] uppercase font-mono px-2.5 py-0.5 rounded-full border ${
                          STATUS_BADGE[ev.approval_status]
                        }`}
                      >
                        {ev.approval_status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 max-w-2xl">{ev.description}</p>
                    <div className="flex flex-wrap gap-4 text-xs text-slate-400 pt-1">
                      <span>Organizer: <strong className="text-slate-200">{ev.organizer_name}</strong></span>
                      <span>Venue: <strong className="text-slate-200">{ev.venue}</strong></span>
                      <span>Date: <strong className="text-slate-200">{ev.event_date} {ev.event_time}</strong></span>
                      <span>Price: <strong className="text-emerald-400">${ev.ticket_price.toFixed(2)}</strong></span>
                      <span>Tickets: <strong className="text-white">{ev.available_tickets}/{ev.total_tickets}</strong></span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {ev.approval_status !== 'approved' && (
                      <button
                        type="button"
                        onClick={() => handleApprove(ev.id)}
                        className="px-4 py-2 rounded-full bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Approve</span>
                      </button>
                    )}
                    {ev.approval_status !== 'rejected' && (
                      <button
                        type="button"
                        onClick={() => handleReject(ev.id)}
                        className="px-4 py-2 rounded-full bg-rose-600/20 hover:bg-rose-600/35 border border-rose-500/40 text-rose-300 text-xs font-semibold flex items-center gap-1.5"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        <span>Reject</span>
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Users Tab */}
      {tab === 'users' && (
        <div className="rounded-2xl bg-[#081021] border border-[#172542] overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-[#14203b] text-slate-400 uppercase font-mono text-[11px]">
              <tr>
                <th className="px-5 py-3.5">ID</th>
                <th className="px-5 py-3.5">Name</th>
                <th className="px-5 py-3.5">Email</th>
                <th className="px-5 py-3.5">Role</th>
                <th className="px-5 py-3.5">Status</th>
                <th className="px-5 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#14203b]">
              {users.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-slate-400">
                    No organizer or public accounts registered yet.
                  </td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id} className="hover:bg-[#0c162e]/60">
                    <td className="px-5 py-3.5 font-mono text-slate-400">#{u.id}</td>
                    <td className="px-5 py-3.5 font-semibold text-white">{u.name}</td>
                    <td className="px-5 py-3.5 text-slate-300">{u.email}</td>
                    <td className="px-5 py-3.5 capitalize text-[#60b5ff] font-medium">{u.role}</td>
                    <td className="px-5 py-3.5">
                      <span
                        className={`text-[10px] uppercase font-mono px-2.5 py-0.5 rounded-full border ${
                          STATUS_BADGE[u.status]
                        }`}
                      >
                        {u.status}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-right space-x-2">
                      <button
                        type="button"
                        onClick={() => handleToggleBlock(u)}
                        className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-semibold border ${
                          u.status === 'active'
                            ? 'bg-amber-500/15 border-amber-500/40 text-amber-300 hover:bg-amber-500/25'
                            : 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/25'
                        }`}
                      >
                        {u.status === 'active' ? <Ban className="w-3 h-3" /> : <UserCheck className="w-3 h-3" />}
                        <span>{u.status === 'active' ? 'Block' : 'Unblock'}</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteUser(u)}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-semibold bg-rose-500/15 border border-rose-500/40 text-rose-300 hover:bg-rose-500/25"
                      >
                        <Trash2 className="w-3 h-3" />
                        <span>Remove</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Bookings Tab */}
      {tab === 'bookings' && (
        <div className="rounded-2xl bg-[#081021] border border-[#172542] overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-[#14203b] text-slate-400 uppercase font-mono text-[11px]">
              <tr>
                <th className="px-5 py-3.5">Booking</th>
                <th className="px-5 py-3.5">Buyer</th>
                <th className="px-5 py-3.5">Event</th>
                <th className="px-5 py-3.5">Tickets</th>
                <th className="px-5 py-3.5">Total</th>
                <th className="px-5 py-3.5">Status</th>
                <th className="px-5 py-3.5">Booked At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#14203b]">
              {bookings.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-8 text-center text-slate-400">
                    No bookings recorded yet.
                  </td>
                </tr>
              ) : (
                bookings.map((b) => (
                  <tr key={b.id} className="hover:bg-[#0c162e]/60">
                    <td className="px-5 py-3.5 font-mono text-[#60b5ff]">#{b.id}</td>
                    <td className="px-5 py-3.5 text-white">{b.user_name} ({b.user_email})</td>
                    <td className="px-5 py-3.5 text-slate-200">{b.event_title}</td>
                    <td className="px-5 py-3.5 font-mono text-white">{b.ticket_count}</td>
                    <td className="px-5 py-3.5 font-mono text-emerald-400">${b.total_amount.toFixed(2)}</td>
                    <td className="px-5 py-3.5">
                      <span className={`text-[10px] uppercase font-mono px-2.5 py-0.5 rounded-full border ${STATUS_BADGE[b.status]}`}>
                        {b.status}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-slate-400">{new Date(b.booked_at).toLocaleString()}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Payments Tab */}
      {tab === 'payments' && (
        <div className="rounded-2xl bg-[#081021] border border-[#172542] overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-[#14203b] text-slate-400 uppercase font-mono text-[11px]">
              <tr>
                <th className="px-5 py-3.5">Payment</th>
                <th className="px-5 py-3.5">Booking</th>
                <th className="px-5 py-3.5">Buyer</th>
                <th className="px-5 py-3.5">Event</th>
                <th className="px-5 py-3.5">Amount</th>
                <th className="px-5 py-3.5">Status</th>
                <th className="px-5 py-3.5">Transaction ID</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#14203b]">
              {payments.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-8 text-center text-slate-400">
                    No payments recorded yet.
                  </td>
                </tr>
              ) : (
                payments.map((p) => (
                  <tr key={p.id} className="hover:bg-[#0c162e]/60">
                    <td className="px-5 py-3.5 font-mono text-slate-300">#{p.id}</td>
                    <td className="px-5 py-3.5 font-mono text-[#60b5ff]">#{p.booking_id}</td>
                    <td className="px-5 py-3.5 text-white">{p.user_name}</td>
                    <td className="px-5 py-3.5 text-slate-200">{p.event_title}</td>
                    <td className="px-5 py-3.5 font-mono text-emerald-400">${p.amount.toFixed(2)}</td>
                    <td className="px-5 py-3.5">
                      <span className={`text-[10px] uppercase font-mono px-2.5 py-0.5 rounded-full border ${STATUS_BADGE[p.status]}`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 font-mono text-slate-400">
                      {p.gateway_transaction_id || '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

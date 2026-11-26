import React, { useCallback, useEffect, useState } from 'react';
import {
  Armchair,
  Calendar,
  Check,
  CheckCircle2,
  CreditCard,
  Download,
  Lock,
  MapPin,
  Search,
  Ticket,
  X,
  XCircle,
} from 'lucide-react';
import {
  publicBrowseEvents,
  publicCancelBooking,
  publicCreateBooking,
  publicFetchBookingDetail,
  publicFetchBookings,
  publicFetchEventSeats,
  publicPayBooking,
} from '../api/client';

const BOOKING_BADGE = {
  pending: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  confirmed: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  cancelled: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
  failed: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
};

export default function PublicDashboard({ user }) {
  const [events, setEvents] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [eventSeats, setEventSeats] = useState([]);
  const [seatsLoading, setSeatsLoading] = useState(false);
  const [selectedSeatIds, setSelectedSeatIds] = useState([]);
  const [ticketCount, setTicketCount] = useState(1);
  const [activeBooking, setActiveBooking] = useState(null);
  const [paymentMethod, setPaymentMethod] = useState('card');
  const [ticketModalBooking, setTicketModalBooking] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const loadData = useCallback(
    async (q = searchQuery) => {
      setError('');
      try {
        const [ev, bk] = await Promise.all([
          publicBrowseEvents(q),
          publicFetchBookings(),
        ]);
        setEvents(ev);
        setBookings(bk);
      } catch (err) {
        setError(err.message || 'Failed to load events.');
      }
    },
    [searchQuery]
  );

  useEffect(() => {
    loadData('');
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearch = (e) => {
    e.preventDefault();
    loadData(searchQuery);
  };

  const openBookModal = async (ev) => {
    setSelectedEvent(ev);
    setTicketCount(1);
    setSelectedSeatIds([]);
    setEventSeats([]);
    setActiveBooking(null);
    setError('');

    if (ev.seating_type === 'seated') {
      setSeatsLoading(true);
      try {
        const seats = await publicFetchEventSeats(ev.id);
        setEventSeats(seats);
      } catch (err) {
        setError(err.message || 'Failed to load seat map.');
      } finally {
        setSeatsLoading(false);
      }
    }
  };

  const toggleSeatSelection = (seat) => {
    if (seat.status !== 'available') return;
    setError('');
    setSelectedSeatIds((prev) => {
      if (prev.includes(seat.id)) {
        return prev.filter((id) => id !== seat.id);
      }
      if (prev.length >= 5) {
        setError('Maximum 5 seats allowed per booking.');
        return prev;
      }
      return [...prev, seat.id];
    });
  };

  const handleCreatePendingBooking = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const payload =
        selectedEvent.seating_type === 'seated'
          ? { event_id: selectedEvent.id, seat_ids: selectedSeatIds }
          : { event_id: selectedEvent.id, ticket_count: Number(ticketCount) };
      const booking = await publicCreateBooking(payload);
      setActiveBooking(booking);
      await loadData(searchQuery);
    } catch (err) {
      setError(err.message || 'Could not reserve tickets.');
      if (selectedEvent.seating_type === 'seated') {
        publicFetchEventSeats(selectedEvent.id).then(setEventSeats).catch(() => {});
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handlePayment = async (simulateOutcome) => {
    if (!activeBooking) return;
    setSubmitting(true);
    setError('');
    try {
      const updated = await publicPayBooking(activeBooking.id, {
        payment_method: paymentMethod,
        card_last4: '4242',
        simulate_outcome: simulateOutcome,
      });
      setActiveBooking(updated);
      await loadData(searchQuery);
    } catch (err) {
      setError(err.message || 'Payment failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancelBooking = async (bookingId) => {
    if (!window.confirm('Cancel this booking and return the tickets to availability?')) return;
    setError('');
    try {
      await publicCancelBooking(bookingId);
      await loadData(searchQuery);
    } catch (err) {
      setError(err.message || 'Could not cancel booking.');
    }
  };

  const handleOpenTicketView = async (bookingId) => {
    try {
      const detail = await publicFetchBookingDetail(bookingId);
      setTicketModalBooking(detail);
    } catch (err) {
      setError(err.message || 'Could not load ticket details.');
    }
  };

  const handleDownloadTicket = (booking) => {
    const lines = [
      '=== SEATSTREAM DIGITAL TICKET ===',
      `Booking ID: #${booking.id}`,
      `Attendee: ${booking.user_name || user.name} (${booking.user_email || user.email})`,
      `Event: ${booking.event_title}`,
      `Venue: ${booking.venue}`,
      `Date & Time: ${booking.event_date} ${String(booking.event_time || '').slice(0, 5)}`,
      `Tickets (${booking.ticket_count}):`,
      ...booking.tickets.map(
        (t, i) => `  ${i + 1}. ${t.seat_label ? `Seat ${t.seat_label} — ` : ''}${t.ticket_code}`
      ),
      `Total Paid: $${booking.total_amount.toFixed(2)}`,
      `Transaction ID: ${booking.payment?.gateway_transaction_id || 'N/A'}`,
      `Status: ${booking.status.toUpperCase()}`,
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `seatstream-booking-${booking.id}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Group seats by row_label for the seat map modal
  const seatsByRow = eventSeats.reduce((acc, s) => {
    if (!acc[s.row_label]) acc[s.row_label] = [];
    acc[s.row_label].push(s);
    return acc;
  }, {});
  const rowLabels = Object.keys(seatsByRow).sort();
  const selectedSeatLabels = eventSeats
    .filter((s) => selectedSeatIds.includes(s.id))
    .map((s) => `${s.row_label}${s.seat_number}`);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">
      {/* Search & Browse Approved Events */}
      <div className="space-y-5">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white">Browse Approved Events</h1>
            <p className="text-xs text-slate-400">
              Select seats on seated events or choose ticket quantity on open events (max 5 per booking).
            </p>
          </div>

          <form onSubmit={handleSearch} className="flex items-center gap-2 w-full md:w-96">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search by title or venue..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-3.5 py-2 rounded-full bg-[#081021] border border-[#192848] text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-[#2684ff]"
              />
            </div>
            <button
              type="submit"
              className="px-4 py-2 rounded-full bg-[#1a73e8] hover:bg-[#2b84f8] text-xs font-semibold text-white"
            >
              Search
            </button>
          </form>
        </div>

        {error && !selectedEvent && (
          <div className="p-3.5 rounded-xl bg-rose-950/70 border border-rose-600/60 text-rose-300 text-xs">
            {error}
          </div>
        )}

        {events.length === 0 ? (
          <div className="rounded-2xl bg-[#081021] border border-[#172542] p-12 text-center text-sm text-slate-400">
            No approved events match your search right now.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {events.map((ev) => {
              const soldOut = ev.available_tickets <= 0;
              const isSeated = ev.seating_type === 'seated';
              return (
                <div
                  key={ev.id}
                  className="rounded-2xl bg-[#081021] border border-[#172542] p-6 flex flex-col justify-between gap-4 hover:border-[#2a4980] transition-colors"
                >
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="inline-flex items-center gap-1 text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-[#0d1c3b] border border-[#1f3b73] text-[#60b5ff]">
                        {isSeated ? (
                          <>
                            <Armchair className="w-3 h-3" />
                            <span>Seated ({ev.total_rows}×{ev.seats_per_row})</span>
                          </>
                        ) : (
                          <span>Open Event</span>
                        )}
                      </span>
                      <span
                        className={`text-[11px] font-mono px-2.5 py-0.5 rounded-full border ${
                          soldOut
                            ? 'bg-rose-500/15 border-rose-500/30 text-rose-300'
                            : 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300'
                        }`}
                      >
                        {soldOut ? 'Sold Out' : `${ev.available_tickets} left`}
                      </span>
                    </div>

                    <h2 className="text-lg font-bold text-white">{ev.title}</h2>
                    <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed">
                      {ev.description}
                    </p>

                    <div className="pt-2 space-y-1 text-xs text-slate-300">
                      <div className="flex items-center gap-2">
                        <MapPin className="w-3.5 h-3.5 text-[#2684ff]" />
                        <span>{ev.venue}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Calendar className="w-3.5 h-3.5 text-[#2684ff]" />
                        <span>
                          {ev.event_date} · {String(ev.event_time).slice(0, 5)}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-[#14203b] flex items-center justify-between">
                    <div>
                      <div className="text-[11px] text-slate-400">Ticket Price</div>
                      <div className="text-lg font-extrabold font-mono text-emerald-400">
                        ${ev.ticket_price.toFixed(2)}
                      </div>
                    </div>
                    <button
                      type="button"
                      disabled={soldOut}
                      onClick={() => openBookModal(ev)}
                      className="px-5 py-2.5 rounded-full bg-[#1a73e8] hover:bg-[#2b84f8] disabled:bg-slate-800 disabled:text-slate-500 disabled:cursor-not-allowed text-xs font-semibold text-white transition-all"
                    >
                      {soldOut ? 'Sold Out' : isSeated ? 'Select Seats' : 'Book Tickets'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Booking History & Tickets */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-white">My Bookings &amp; Tickets</h2>
        {bookings.length === 0 ? (
          <div className="rounded-2xl bg-[#081021] border border-[#172542] p-10 text-center text-sm text-slate-400">
            You haven&apos;t booked any tickets yet.
          </div>
        ) : (
          <div className="space-y-3">
            {bookings.map((b) => (
              <div
                key={b.id}
                className="rounded-2xl bg-[#081021] border border-[#172542] p-5 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4"
              >
                <div className="space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <span className="font-mono text-xs text-[#60b5ff] font-bold">
                      Booking #{b.id}
                    </span>
                    <span
                      className={`text-[10px] uppercase font-mono px-2.5 py-0.5 rounded-full border ${
                        BOOKING_BADGE[b.status]
                      }`}
                    >
                      {b.status}
                    </span>
                    <h3 className="text-base font-bold text-white">{b.event_title}</h3>
                  </div>

                  <div className="flex flex-wrap gap-4 text-xs text-slate-400">
                    <span>Venue: <strong className="text-slate-200">{b.venue}</strong></span>
                    <span>Event Date: <strong className="text-slate-200">{b.event_date} {String(b.event_time || '').slice(0, 5)}</strong></span>
                    <span>Qty: <strong className="text-white font-mono">{b.ticket_count}</strong></span>
                    <span>Total: <strong className="text-emerald-400 font-mono">${b.total_amount.toFixed(2)}</strong></span>
                    {b.tickets?.some((t) => t.seat_label) && (
                      <span>
                        Seats:{' '}
                        <strong className="text-[#60b5ff] font-mono">
                          {b.tickets.map((t) => t.seat_label).filter(Boolean).join(', ')}
                        </strong>
                      </span>
                    )}
                    {b.payment && (
                      <span>Payment: <strong className="text-slate-200 uppercase font-mono">{b.payment.status}</strong></span>
                    )}
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2 shrink-0">
                  {b.status === 'pending' && (
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedEvent({
                          id: b.event_id,
                          title: b.event_title,
                          ticket_price: b.total_amount / b.ticket_count,
                          available_tickets: b.ticket_count,
                          seating_type: 'open',
                        });
                        setActiveBooking(b);
                      }}
                      className="px-4 py-2 rounded-full bg-[#1a73e8] hover:bg-[#2b84f8] text-white text-xs font-semibold flex items-center gap-1.5"
                    >
                      <CreditCard className="w-3.5 h-3.5" />
                      <span>Complete Payment</span>
                    </button>
                  )}

                  {b.status === 'confirmed' && (
                    <button
                      type="button"
                      onClick={() => handleOpenTicketView(b.id)}
                      className="px-4 py-2 rounded-full bg-[#0c1830] hover:bg-[#132345] border border-[#22355a] text-white text-xs font-semibold flex items-center gap-1.5"
                    >
                      <Ticket className="w-3.5 h-3.5 text-[#2684ff]" />
                      <span>View / Download Ticket</span>
                    </button>
                  )}

                  {(b.status === 'pending' || b.status === 'confirmed') && (
                    <button
                      type="button"
                      onClick={() => handleCancelBooking(b.id)}
                      className="px-4 py-2 rounded-full bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/40 text-rose-300 text-xs font-semibold flex items-center gap-1.5"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Cancel Booking</span>
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Booking & Payment Gateway Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div
            className={`animate-modal-pop bg-[#091224] border border-[#192848] rounded-2xl w-full p-6 sm:p-8 shadow-2xl relative max-h-[90vh] overflow-y-auto ${
              !activeBooking && selectedEvent.seating_type === 'seated' ? 'max-w-2xl' : 'max-w-md'
            }`}
          >
            <button
              type="button"
              onClick={() => setSelectedEvent(null)}
              className="absolute top-5 right-5 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            {error && (
              <div className="mb-4 p-3 rounded-xl bg-rose-950/70 border border-rose-600/60 text-rose-300 text-xs">
                {error}
              </div>
            )}

            {!activeBooking ? (
              <form onSubmit={handleCreatePendingBooking} className="space-y-4">
                <div>
                  <h3 className="text-lg font-bold text-white">
                    {selectedEvent.seating_type === 'seated' ? 'Select Your Seats' : 'Book Tickets'}
                  </h3>
                  <p className="text-xs text-slate-400">{selectedEvent.title}</p>
                </div>

                {selectedEvent.seating_type === 'seated' ? (
                  <div className="space-y-4">
                    {/* Stage Banner */}
                    <div className="max-w-md mx-auto h-9 bg-gradient-to-b from-[#1a73e8]/25 to-transparent border-t-2 border-[#2684ff]/80 rounded-t-[60px] flex items-center justify-center">
                      <span className="text-[10px] uppercase tracking-[0.28em] font-semibold text-[#60b5ff] font-mono">
                        STAGE / SCREEN
                      </span>
                    </div>

                    {seatsLoading ? (
                      <div className="py-10 text-center text-xs text-slate-400">
                        Loading live seat map...
                      </div>
                    ) : (
                      <div className="space-y-2 overflow-x-auto pb-2">
                        {rowLabels.map((row) => (
                          <div key={row} className="flex items-center justify-center gap-1.5">
                            <span className="w-5 text-center text-[11px] font-mono font-bold text-slate-500">
                              {row}
                            </span>
                            <div className="flex gap-1.5">
                              {seatsByRow[row].map((seat) => {
                                const isSelected = selectedSeatIds.includes(seat.id);
                                const isPending = seat.status === 'pending';
                                const isBooked = seat.status === 'booked';

                                let seatCls =
                                  'bg-[#0c1730] border-[#1d3157] text-slate-300 hover:border-[#2684ff] hover:bg-[#12254a] hover:text-white';
                                if (isSelected) {
                                  seatCls =
                                    'bg-[#1a73e8] border-[#60a5fa] text-white shadow-[0_0_12px_rgba(38,132,255,0.5)] scale-105';
                                } else if (isPending) {
                                  seatCls =
                                    'bg-amber-950/60 border-amber-600/70 text-amber-400 cursor-not-allowed';
                                } else if (isBooked) {
                                  seatCls =
                                    'bg-[#050a18] border-[#111c33] text-slate-700 cursor-not-allowed opacity-50';
                                }

                                return (
                                  <button
                                    key={seat.id}
                                    type="button"
                                    disabled={isPending || isBooked}
                                    onClick={() => toggleSeatSelection(seat)}
                                    title={`Seat ${seat.row_label}${seat.seat_number} (${seat.status})`}
                                    className={`w-8 h-8 rounded-lg border text-[11px] font-mono font-semibold flex items-center justify-center transition-all ${seatCls}`}
                                  >
                                    {isSelected ? (
                                      <Check className="w-3.5 h-3.5" />
                                    ) : isPending || isBooked ? (
                                      <Lock className="w-3 h-3" />
                                    ) : (
                                      seat.seat_number
                                    )}
                                  </button>
                                );
                              })}
                            </div>
                            <span className="w-5 text-center text-[11px] font-mono font-bold text-slate-500">
                              {row}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Legend */}
                    <div className="flex flex-wrap items-center justify-center gap-4 text-[11px] text-slate-400 pt-2 border-t border-[#14203b]">
                      <span className="flex items-center gap-1.5">
                        <span className="w-3.5 h-3.5 rounded bg-[#0c1730] border border-[#1d3157]" />
                        Available
                      </span>
                      <span className="flex items-center gap-1.5 text-[#60b5ff]">
                        <span className="w-3.5 h-3.5 rounded bg-[#1a73e8] border border-[#60a5fa]" />
                        Selected
                      </span>
                      <span className="flex items-center gap-1.5 text-amber-400">
                        <span className="w-3.5 h-3.5 rounded bg-amber-950/80 border border-amber-600" />
                        Pending
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="w-3.5 h-3.5 rounded bg-[#050a18] border border-[#111c33]" />
                        Booked
                      </span>
                    </div>

                    {/* Selection Summary */}
                    <div className="rounded-xl bg-[#060d1c] border border-[#172542] p-3.5 flex items-center justify-between text-xs">
                      <div>
                        <div className="text-slate-400">Selected Seats (Max 5)</div>
                        <div className="font-mono font-bold text-white mt-0.5">
                          {selectedSeatLabels.length > 0 ? selectedSeatLabels.join(', ') : 'None selected'}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-slate-400">Total</div>
                        <div className="font-mono font-bold text-emerald-400 text-sm">
                          ${(selectedSeatIds.length * Number(selectedEvent.ticket_price)).toFixed(2)}
                        </div>
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={submitting || selectedSeatIds.length === 0}
                      className="w-full py-3 rounded-full bg-[#1a73e8] hover:bg-[#2b84f8] disabled:opacity-40 text-white font-semibold text-sm"
                    >
                      {submitting
                        ? 'Locking seats...'
                        : `Reserve ${selectedSeatIds.length || ''} Seat(s) & Pay`}
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="rounded-xl bg-[#060d1c] border border-[#172542] p-4 space-y-2 text-xs">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Price per ticket</span>
                        <span className="font-mono text-white">
                          ${Number(selectedEvent.ticket_price).toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Available</span>
                        <span className="font-mono text-emerald-400">
                          {selectedEvent.available_tickets}
                        </span>
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-slate-300 mb-1.5">
                        Number of Tickets (Max 5)
                      </label>
                      <select
                        value={ticketCount}
                        onChange={(e) => setTicketCount(Number(e.target.value))}
                        className="w-full px-3.5 py-2.5 rounded-xl bg-[#060d1c] border border-[#1b2b4d] text-sm text-white focus:outline-none focus:ring-2 focus:ring-[#2684ff]"
                      >
                        {[1, 2, 3, 4, 5]
                          .filter((n) => n <= selectedEvent.available_tickets)
                          .map((n) => (
                            <option key={n} value={n}>
                              {n} {n === 1 ? 'Ticket' : 'Tickets'} — $
                              {(n * Number(selectedEvent.ticket_price)).toFixed(2)}
                            </option>
                          ))}
                      </select>
                    </div>

                    <button
                      type="submit"
                      disabled={submitting}
                      className="w-full py-3 rounded-full bg-[#1a73e8] hover:bg-[#2b84f8] text-white font-semibold text-sm disabled:opacity-50"
                    >
                      {submitting ? 'Reserving tickets...' : 'Continue to Payment Gateway'}
                    </button>
                  </>
                )}
              </form>
            ) : activeBooking.status === 'pending' ? (
              <div className="space-y-4">
                <div className="flex items-center gap-2.5">
                  <CreditCard className="w-5 h-5 text-[#2684ff]" />
                  <div>
                    <h3 className="text-lg font-bold text-white">Payment Gateway</h3>
                    <p className="text-xs text-slate-400">
                      Booking #{activeBooking.id} — Tickets held pending payment
                    </p>
                  </div>
                </div>

                <div className="rounded-xl bg-[#060d1c] border border-[#172542] p-4 flex justify-between items-center text-sm">
                  <span className="text-slate-300">{activeBooking.ticket_count} Ticket(s)</span>
                  <span className="text-emerald-400 font-mono font-bold text-base">
                    ${activeBooking.total_amount.toFixed(2)}
                  </span>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    Payment Method
                  </label>
                  <select
                    value={paymentMethod}
                    onChange={(e) => setPaymentMethod(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#060d1c] border border-[#1b2b4d] text-sm text-white"
                  >
                    <option value="card">Credit / Debit Card</option>
                    <option value="upi">UPI Instant Pay</option>
                    <option value="netbanking">NetBanking</option>
                  </select>
                </div>

                <div className="space-y-2.5 pt-1">
                  <button
                    type="button"
                    disabled={submitting}
                    onClick={() => handlePayment('success')}
                    className="w-full py-3 rounded-full bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm disabled:opacity-50"
                  >
                    {submitting ? 'Processing...' : `Pay $${activeBooking.total_amount.toFixed(2)} (Confirm)`}
                  </button>
                  <button
                    type="button"
                    disabled={submitting}
                    onClick={() => handlePayment('failed')}
                    className="w-full py-2.5 rounded-full bg-rose-600/20 hover:bg-rose-600/35 border border-rose-500/40 text-rose-300 font-semibold text-xs disabled:opacity-50"
                  >
                    Simulate Payment Failure (Release Tickets)
                  </button>
                </div>
              </div>
            ) : activeBooking.status === 'confirmed' ? (
              <div className="text-center space-y-4">
                <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto" />
                <h3 className="text-xl font-bold text-white">Booking Confirmed!</h3>
                <p className="text-xs text-slate-400">
                  Booking #{activeBooking.id} · Txn {activeBooking.payment?.gateway_transaction_id}
                </p>
                <div className="bg-[#060d1c] border border-[#172542] rounded-xl p-3 space-y-2 text-left">
                  {activeBooking.tickets.map((t) => (
                    <div key={t.id} className="font-mono text-xs text-white flex items-center justify-between gap-2">
                      <span className="flex items-center gap-2">
                        <Ticket className="w-3.5 h-3.5 text-[#2684ff]" />
                        <span>{t.ticket_code}</span>
                      </span>
                      {t.seat_label && (
                        <span className="text-[#60b5ff] font-bold">Seat {t.seat_label}</span>
                      )}
                    </div>
                  ))}
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleDownloadTicket(activeBooking)}
                    className="flex-1 py-2.5 rounded-full bg-[#1a73e8] hover:bg-[#2b84f8] text-white text-xs font-semibold flex items-center justify-center gap-1.5"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download Ticket</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelectedEvent(null)}
                    className="px-5 py-2.5 rounded-full bg-[#0e1b36] border border-[#22355a] text-white text-xs font-semibold"
                  >
                    Done
                  </button>
                </div>
              </div>
            ) : (
              <div className="text-center space-y-4">
                <XCircle className="w-12 h-12 text-rose-400 mx-auto" />
                <h3 className="text-xl font-bold text-white">Payment Failed</h3>
                <p className="text-xs text-slate-400">
                  Booking #{activeBooking.id} failed and your held tickets/seats were released back to the event.
                </p>
                <button
                  type="button"
                  onClick={() => setSelectedEvent(null)}
                  className="w-full py-2.5 rounded-full bg-[#0e1b36] border border-[#22355a] text-white text-xs font-semibold"
                >
                  Close
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Ticket Detail & Download Modal */}
      {ticketModalBooking && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="animate-modal-pop bg-[#091224] border border-[#192848] rounded-2xl w-full max-w-md p-6 sm:p-8 shadow-2xl relative space-y-4">
            <button
              type="button"
              onClick={() => setTicketModalBooking(null)}
              className="absolute top-5 right-5 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
            <h3 className="text-lg font-bold text-white">
              Digital Tickets — Booking #{ticketModalBooking.id}
            </h3>
            <div className="bg-[#060d1c] border border-[#172542] rounded-xl p-4 space-y-2 text-xs">
              <div className="text-white font-bold text-sm">{ticketModalBooking.event_title}</div>
              <div className="text-slate-400">{ticketModalBooking.venue}</div>
              <div className="text-slate-400">
                {ticketModalBooking.event_date} {String(ticketModalBooking.event_time || '').slice(0, 5)}
              </div>
              <div className="pt-2 border-t border-[#14203b] space-y-1.5">
                {ticketModalBooking.tickets.map((t) => (
                  <div
                    key={t.id}
                    className="bg-[#0b1936] border border-[#1b3568] rounded-lg px-3 py-2 font-mono text-white flex items-center justify-between gap-2"
                  >
                    <span className="flex items-center gap-2">
                      <Ticket className="w-3.5 h-3.5 text-[#2684ff]" />
                      <span>{t.ticket_code}</span>
                    </span>
                    {t.seat_label && (
                      <span className="text-[#60b5ff] font-bold">Seat {t.seat_label}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
            <button
              type="button"
              onClick={() => handleDownloadTicket(ticketModalBooking)}
              className="w-full py-2.5 rounded-full bg-[#1a73e8] hover:bg-[#2b84f8] text-white text-xs font-semibold flex items-center justify-center gap-1.5"
            >
              <Download className="w-4 h-4" />
              <span>Download Ticket File</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

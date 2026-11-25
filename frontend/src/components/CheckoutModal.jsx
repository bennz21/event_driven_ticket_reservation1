import React, { useEffect, useState } from 'react';
import { X, CheckCircle2, Ticket, QrCode } from 'lucide-react';

export default function CheckoutModal({
  isOpen,
  onClose,
  selectedSeats,
  onConfirm,
  isSubmitting,
  completedReservation,
  user,
}) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen) return;
    setName((prev) => prev || user?.full_name || '');
    setEmail((prev) => prev || user?.email || '');
    setError('');
  }, [isOpen, user]);

  if (!isOpen) return null;

  const total = selectedSeats.reduce((sum, s) => sum + s.price, 0);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Please provide your name.');
      return;
    }
    setError('');
    try {
      await onConfirm({ name: name.trim(), email: email.trim() });
    } catch (err) {
      setError(err.message || 'Checkout failed');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 sm:p-8 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-slate-400 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {completedReservation ? (
          /* Success Screen */
          <div className="text-center py-4 space-y-4">
            <div className="w-16 h-16 bg-emerald-500/20 text-emerald-400 rounded-full flex items-center justify-center mx-auto border border-emerald-500/30">
              <CheckCircle2 className="w-9 h-9" />
            </div>
            <h3 className="text-xl font-bold text-white">Tickets Confirmed!</h3>
            <p className="text-sm text-slate-400">
              Reservation #{completedReservation.id} has been registered and verified across the event bus.
            </p>

            <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-4 text-left space-y-3 font-mono text-xs">
              <div className="flex justify-between border-b border-slate-800/80 pb-2">
                <span className="text-slate-400">Customer</span>
                <span className="text-white font-medium">{completedReservation.customer_name}</span>
              </div>
              <div className="flex justify-between border-b border-slate-800/80 pb-2">
                <span className="text-slate-400">Seats Reserved</span>
                <span className="text-indigo-400 font-bold">
                  {selectedSeats.map((s) => `${s.row}${s.seat_number}`).join(', ')}
                </span>
              </div>
              <div className="flex justify-between border-b border-slate-800/80 pb-2">
                <span className="text-slate-400">Total Paid</span>
                <span className="text-emerald-400 font-bold">${completedReservation.total_amount.toFixed(2)}</span>
              </div>

              {/* Digital ticket code cards */}
              <div className="pt-2">
                <span className="text-slate-400 block mb-2 font-sans font-medium text-xs">
                  Your Digital Tickets:
                </span>
                <div className="space-y-2">
                  {completedReservation.tickets.map((t) => (
                    <div
                      key={t.id}
                      className="bg-indigo-950/40 border border-indigo-800/40 rounded-lg p-2.5 flex items-center justify-between"
                    >
                      <div className="flex items-center space-x-2">
                        <Ticket className="w-4 h-4 text-indigo-400" />
                        <span className="font-mono text-white text-xs">{t.ticket_code}</span>
                      </div>
                      <QrCode className="w-4 h-4 text-indigo-300" />
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <button
              onClick={onClose}
              className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition-all shadow-lg shadow-indigo-600/30"
            >
              Done
            </button>
          </div>
        ) : (
          /* Checkout Form */
          <div>
            <div className="flex items-center space-x-3 mb-6">
              <div className="p-2 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
                <Ticket className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Complete Reservation</h3>
                <p className="text-xs text-slate-400">Seats are temporarily held for you.</p>
              </div>
            </div>

            {error && (
              <div className="mb-4 p-3 rounded-xl bg-rose-950/70 border border-rose-600/60 text-rose-300 text-xs">
                {error}
              </div>
            )}

            {/* Selected seats list */}
            <div className="bg-slate-950/60 rounded-xl p-4 border border-slate-800 mb-6 space-y-2">
              <div className="text-xs text-slate-400 font-medium">Selected Seats:</div>
              <div className="flex flex-wrap gap-2">
                {selectedSeats.map((s) => (
                  <span
                    key={s.id}
                    className="px-2.5 py-1 rounded bg-indigo-950 border border-indigo-700/60 text-indigo-300 text-xs font-mono font-medium"
                  >
                    {s.row}{s.seat_number} (${s.price})
                  </span>
                ))}
              </div>
              <div className="pt-3 border-t border-slate-800 flex justify-between items-center text-sm font-medium">
                <span className="text-slate-300">Total Price:</span>
                <span className="text-emerald-400 font-mono text-base font-bold">${total.toFixed(2)}</span>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Alex Mercer"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Email (optional for ticket receipt)
                </label>
                <input
                  type="email"
                  placeholder="alex@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm transition-all shadow-lg shadow-emerald-600/20 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? 'Confirming with Event Bus...' : `Confirm & Pay $${total.toFixed(2)}`}
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}

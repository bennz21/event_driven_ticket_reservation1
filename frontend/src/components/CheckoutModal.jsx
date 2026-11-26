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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="bg-[#091224] border border-[#192848] rounded-2xl w-full max-w-lg p-6 sm:p-8 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-slate-400 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {completedReservation ? (
          <div className="text-center py-4 space-y-4">
            <div className="w-16 h-16 bg-emerald-500/20 text-emerald-400 rounded-full flex items-center justify-center mx-auto border border-emerald-500/30">
              <CheckCircle2 className="w-9 h-9" />
            </div>
            <h3 className="text-xl font-bold text-white">Tickets Confirmed!</h3>
            <p className="text-sm text-slate-400">
              Reservation #{completedReservation.id} has been registered and verified across the event bus.
            </p>

            <div className="bg-[#060d1c] border border-[#172542] rounded-xl p-4 text-left space-y-3 font-mono text-xs">
              <div className="flex justify-between border-b border-[#14203b] pb-2">
                <span className="text-slate-400">Customer</span>
                <span className="text-white font-medium">{completedReservation.customer_name}</span>
              </div>
              <div className="flex justify-between border-b border-[#14203b] pb-2">
                <span className="text-slate-400">Seats Reserved</span>
                <span className="text-[#60a5fa] font-bold">
                  {selectedSeats.map((s) => `${s.row}${s.seat_number}`).join(', ')}
                </span>
              </div>
              <div className="flex justify-between border-b border-[#14203b] pb-2">
                <span className="text-slate-400">Total Paid</span>
                <span className="text-emerald-400 font-bold">${completedReservation.total_amount.toFixed(2)}</span>
              </div>

              <div className="pt-2">
                <span className="text-slate-400 block mb-2 font-sans font-medium text-xs">
                  Your Digital Tickets:
                </span>
                <div className="space-y-2">
                  {completedReservation.tickets.map((t) => (
                    <div
                      key={t.id}
                      className="bg-[#0b1936] border border-[#1b3568] rounded-lg p-2.5 flex items-center justify-between"
                    >
                      <div className="flex items-center space-x-2">
                        <Ticket className="w-4 h-4 text-[#2684ff]" />
                        <span className="font-mono text-white text-xs">{t.ticket_code}</span>
                      </div>
                      <QrCode className="w-4 h-4 text-[#60a5fa]" />
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <button
              onClick={onClose}
              className="w-full py-3 rounded-full bg-[#1a73e8] hover:bg-[#2b84f8] text-white font-semibold text-sm transition-all shadow-[0_0_20px_rgba(26,115,232,0.35)]"
            >
              Done
            </button>
          </div>
        ) : (
          <div>
            <div className="flex items-center space-x-3 mb-6">
              <div className="p-2 rounded-xl bg-[#1a73e8]/20 text-[#2684ff] border border-[#2684ff]/30">
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

            <div className="bg-[#060d1c] rounded-xl p-4 border border-[#172542] mb-6 space-y-2">
              <div className="text-xs text-slate-400 font-medium">Selected Seats:</div>
              <div className="flex flex-wrap gap-2">
                {selectedSeats.map((s) => (
                  <span
                    key={s.id}
                    className="px-2.5 py-1 rounded-lg bg-[#0d1d3d] border border-[#1f3b73] text-[#60a5fa] text-xs font-mono font-medium"
                  >
                    {s.row}{s.seat_number} (${s.price})
                  </span>
                ))}
              </div>
              <div className="pt-3 border-t border-[#14203b] flex justify-between items-center text-sm font-medium">
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
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#060d1c] border border-[#1b2b4d] text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-[#2684ff] transition-all"
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
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#060d1c] border border-[#1b2b4d] text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-[#2684ff] transition-all"
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full py-3 rounded-full bg-[#1a73e8] hover:bg-[#2b84f8] text-white font-semibold text-sm transition-all shadow-[0_0_20px_rgba(26,115,232,0.35)] disabled:opacity-50 disabled:cursor-not-allowed"
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

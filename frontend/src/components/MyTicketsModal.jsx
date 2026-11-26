import React, { useEffect, useState } from 'react';
import { X, Ticket, QrCode, Calendar } from 'lucide-react';
import { fetchMyReservations } from '../api/client';

export default function MyTicketsModal({ isOpen, onClose, user }) {
  const [reservations, setReservations] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen || !user) return;
    setIsLoading(true);
    setError('');
    fetchMyReservations()
      .then(setReservations)
      .catch((err) => setError(err.message || 'Failed to load tickets'))
      .finally(() => setIsLoading(false));
  }, [isOpen, user]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="bg-[#091224] border border-[#192848] rounded-2xl w-full max-w-xl p-6 sm:p-8 shadow-2xl relative max-h-[85vh] flex flex-col">
        <button
          onClick={onClose}
          aria-label="Close my tickets"
          className="absolute top-5 right-5 text-slate-400 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 mb-5">
          <div className="p-2 rounded-xl bg-[#1a73e8]/20 text-[#2684ff] border border-[#2684ff]/30">
            <Ticket className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">My Reservations & Tickets</h3>
            <p className="text-xs text-slate-400">
              Signed in as {user?.full_name} ({user?.email})
            </p>
          </div>
        </div>

        <div className="overflow-y-auto space-y-4 pr-1 flex-1">
          {isLoading && <p className="text-sm text-slate-400 py-8 text-center">Loading your tickets...</p>}

          {error && (
            <div className="p-3 rounded-xl bg-rose-950/70 border border-rose-600/60 text-rose-300 text-xs">
              {error}
            </div>
          )}

          {!isLoading && !error && reservations.length === 0 && (
            <div className="text-center py-10 bg-[#060d1c] border border-[#172542] rounded-xl">
              <Ticket className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-sm text-slate-300 font-medium">No confirmed tickets yet</p>
              <p className="text-xs text-slate-500 mt-1">
                Select seats on the map and complete checkout to see your tickets here.
              </p>
            </div>
          )}

          {reservations.map((res) => (
            <div
              key={res.id}
              className="bg-[#060d1c] border border-[#172542] rounded-xl p-4 space-y-3"
            >
              <div className="flex items-center justify-between border-b border-[#14203b] pb-2.5">
                <div>
                  <span className="text-xs font-mono text-[#60a5fa] font-semibold">
                    Reservation #{res.id}
                  </span>
                  <div className="flex items-center gap-1.5 text-[11px] text-slate-400 mt-0.5">
                    <Calendar className="w-3 h-3" />
                    <span>{new Date(res.created_at).toLocaleString()}</span>
                  </div>
                </div>
                <span className="text-emerald-400 font-mono text-sm font-bold">
                  ${res.total_amount.toFixed(2)}
                </span>
              </div>

              <div className="space-y-2">
                {res.tickets.map((t) => (
                  <div
                    key={t.id}
                    className="bg-[#0b1936] border border-[#1b3568] rounded-lg px-3 py-2 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2">
                      <Ticket className="w-4 h-4 text-[#2684ff]" />
                      <span className="font-mono text-xs text-white">{t.ticket_code}</span>
                    </div>
                    <QrCode className="w-4 h-4 text-[#60a5fa]" />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

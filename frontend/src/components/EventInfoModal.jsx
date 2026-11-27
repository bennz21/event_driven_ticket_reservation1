import React from 'react';
import { X, Calendar, MapPin, IndianRupee, Ticket, ArrowRight, Sparkles } from 'lucide-react';

export default function EventInfoModal({
  isOpen,
  onClose,
  event,
  availableSeatsCount,
  totalSeatsCount,
  user,
  onEnterWorkspace,
  onOpenAuth,
}) {
  if (!isOpen || !event) return null;

  const tiers = [
    { name: 'VIP (Rows A–B)', price: (event.base_price * 1.8).toFixed(2) },
    { name: 'Premium (Rows C–D)', price: (event.base_price * 1.3).toFixed(2) },
    { name: 'Standard (Rows E–F)', price: event.base_price.toFixed(2) },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="animate-modal-pop bg-[#091224] border border-[#192848] rounded-2xl w-full max-w-lg p-6 sm:p-8 shadow-2xl relative">
        <button
          type="button"
          onClick={onClose}
          aria-label="Close event details"
          className="absolute top-5 right-5 text-slate-400 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-[#1a73e8]/15 border border-[#2684ff]/30 text-[#60a5fa] text-xs font-semibold mb-4">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Upcoming Event</span>
        </div>

        <h3 className="text-2xl font-bold text-white">{event.title}</h3>
        <p className="text-sm text-slate-300 mt-2 leading-relaxed">{event.description}</p>

        <div className="mt-5 grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div className="rounded-xl bg-[#060d1c] border border-[#172542] p-3">
            <div className="text-slate-400 flex items-center gap-1.5 mb-1">
              <MapPin className="w-3.5 h-3.5 text-[#2684ff]" />
              <span>Venue</span>
            </div>
            <div className="text-white font-semibold">{event.venue_name}</div>
          </div>

          <div className="rounded-xl bg-[#060d1c] border border-[#172542] p-3">
            <div className="text-slate-400 flex items-center gap-1.5 mb-1">
              <Calendar className="w-3.5 h-3.5 text-[#2684ff]" />
              <span>Date</span>
            </div>
            <div className="text-white font-semibold">
              {new Date(event.event_date).toLocaleDateString()}
            </div>
          </div>

          <div className="rounded-xl bg-[#060d1c] border border-[#172542] p-3">
            <div className="text-slate-400 flex items-center gap-1.5 mb-1">
              <Ticket className="w-3.5 h-3.5 text-emerald-400" />
              <span>Availability</span>
            </div>
            <div className="text-emerald-400 font-mono font-semibold">
              {totalSeatsCount > 0 ? `${availableSeatsCount}/${totalSeatsCount} open` : 'Live'}
            </div>
          </div>
        </div>

        <div className="mt-5 rounded-xl bg-[#060d1c] border border-[#172542] p-4 space-y-2.5">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <IndianRupee className="w-3.5 h-3.5 text-[#2684ff]" />
            <span>Seating Tiers</span>
          </div>
          {tiers.map((tier) => (
            <div
              key={tier.name}
              className="flex items-center justify-between text-sm border-t border-[#14203b] pt-2 first:border-t-0 first:pt-0"
            >
              <span className="text-slate-300">{tier.name}</span>
              <span className="font-mono font-semibold text-white">₹{tier.price}</span>
            </div>
          ))}
        </div>

        <div className="mt-6">
          {user ? (
            <button
              type="button"
              onClick={() => {
                onClose();
                onEnterWorkspace();
              }}
              className="w-full py-3 rounded-full bg-[#1a73e8] hover:bg-[#2b84f8] text-white font-semibold text-sm transition-all shadow-[0_0_20px_rgba(26,115,232,0.35)] flex items-center justify-center gap-2"
            >
              <span>Select Seats on Live Map</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              type="button"
              onClick={() => {
                onClose();
                onOpenAuth('register');
              }}
              className="w-full py-3 rounded-full bg-[#1a73e8] hover:bg-[#2b84f8] text-white font-semibold text-sm transition-all shadow-[0_0_20px_rgba(26,115,232,0.35)] flex items-center justify-center gap-2"
            >
              <span>Create Account or Sign In to Book</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

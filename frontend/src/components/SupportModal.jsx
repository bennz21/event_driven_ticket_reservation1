import React from 'react';
import { X, ShieldCheck, Clock, Radio, UserCheck } from 'lucide-react';

export default function SupportModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  const faqs = [
    {
      icon: Clock,
      title: 'How long are seats held?',
      body: 'Once you select a seat on the Live Seat Map, it is locked exclusively for your session for 5 minutes so you can finish checkout without anyone else claiming it.',
    },
    {
      icon: ShieldCheck,
      title: 'How does SeatStream prevent double-booking?',
      body: 'Seat holds use atomic distributed locks backed by MySQL persistence and an automatic expiration sweeper.',
    },
    {
      icon: Radio,
      title: 'Do seat updates appear automatically?',
      body: 'Yes. Every hold, release, and ticket confirmation is pushed immediately to all viewers over WebSockets.',
    },
    {
      icon: UserCheck,
      title: 'How do I view my confirmed tickets?',
      body: 'Sign in with Email or Google and click "My Tickets" in the navigation bar at any time.',
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="bg-[#091224] border border-[#192848] rounded-2xl w-full max-w-lg p-6 sm:p-8 shadow-2xl relative">
        <button
          type="button"
          onClick={onClose}
          aria-label="Close support modal"
          className="absolute top-5 right-5 text-slate-400 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <h3 className="text-xl font-bold text-white">SeatStream Support</h3>
        <p className="text-xs text-slate-400 mt-1">
          Quick answers about real-time seat holds, accounts, and digital tickets.
        </p>

        <div className="mt-5 space-y-3">
          {faqs.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.title}
                className="rounded-xl bg-[#060d1c] border border-[#172542] p-4 flex items-start gap-3"
              >
                <div className="w-8 h-8 rounded-lg bg-[#0d1a35] border border-[#1b2f57] flex items-center justify-center shrink-0 mt-0.5">
                  <Icon className="w-4 h-4 text-[#2684ff]" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-white">{item.title}</h4>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">{item.body}</p>
                </div>
              </div>
            );
          })}
        </div>

        <button
          type="button"
          onClick={onClose}
          className="mt-6 w-full py-2.5 rounded-full bg-[#0e1b36] hover:bg-[#15284e] border border-[#22365c] text-sm font-semibold text-white transition-colors"
        >
          Close
        </button>
      </div>
    </div>
  );
}

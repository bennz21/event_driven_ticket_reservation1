import React from 'react';
import {
  Ticket,
  UserPlus,
  LogIn,
  ShieldCheck,
  Radio,
  Clock,
  Sparkles,
  ArrowRight,
  Calendar,
  MapPin,
  CheckCircle2,
} from 'lucide-react';

export default function HomeScreen({
  featuredEvent,
  availableSeatsCount,
  totalSeatsCount,
  user,
  onOpenAuth,
  onEnterWorkspace,
}) {
  const highlights = [
    {
      icon: Radio,
      title: 'Real-Time Seat Availability',
      description:
        'Watch seats lock, release, and confirm live across every connected buyer via WebSockets—no stale refreshes.',
      accent: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    },
    {
      icon: ShieldCheck,
      title: 'Zero Double-Booking Locks',
      description:
        'Distributed Redis locks and optimistic concurrency ensure two buyers can never claim the same seat at once.',
      accent: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20',
    },
    {
      icon: Clock,
      title: '5-Minute Hold & Instant Tickets',
      description:
        'Reserve your preferred VIP, Premium, or Standard seats with a live countdown timer and get digital ticket codes on checkout.',
      accent: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    },
  ];

  const useCases = [
    'Browse live concerts & shows with interactive row-by-row seating tiers',
    'Hold multiple seats together while completing checkout without losing your spot',
    'Sign in with Email, Google, or Apple to save reservations & digital tickets',
    'Track live seat activity and confirmations in real time across sessions',
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-16 space-y-14">
      {/* Hero Section */}
      <section className="relative overflow-hidden rounded-3xl border border-slate-800 bg-gradient-to-br from-indigo-950/60 via-slate-900/90 to-slate-950 p-8 sm:p-12 lg:p-14 shadow-2xl">
        {/* Subtle decorative glow */}
        <div className="pointer-events-none absolute -top-24 -right-24 h-72 w-72 rounded-full bg-indigo-600/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-24 -left-24 h-72 w-72 rounded-full bg-emerald-500/10 blur-3xl" />

        <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
          <div className="lg:col-span-7 space-y-6">
            <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-semibold">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              <span>Real-Time Ticket & Seat Reservation Platform</span>
            </div>

            <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-tight">
              Book live event seats{' '}
              <span className="bg-gradient-to-r from-indigo-400 via-sky-400 to-emerald-400 bg-clip-text text-transparent">
                without race conditions.
              </span>
            </h1>

            <p className="text-base sm:text-lg text-slate-300 leading-relaxed max-w-2xl">
              SeatStream lets you explore interactive venue seat maps, temporarily lock your
              favorite seats in real time, and confirm digital tickets instantly—with Google, Apple,
              or email sign-in.
            </p>

            {/* Primary Create Account & Sign In CTA Buttons */}
            {user ? (
              <div className="flex flex-wrap items-center gap-3 pt-2">
                <button
                  onClick={onEnterWorkspace}
                  className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-semibold text-sm transition-all shadow-lg shadow-indigo-600/30 flex items-center gap-2"
                >
                  <Ticket className="w-4 h-4" />
                  <span>Open Live Seat Map</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
                <span className="text-xs text-emerald-300 px-3 py-2 rounded-lg bg-emerald-950/50 border border-emerald-800/50">
                  Signed in as <strong>{user.full_name}</strong>
                </span>
              </div>
            ) : (
              <div className="space-y-4 pt-2">
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                  <button
                    onClick={() => onOpenAuth('register')}
                    className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-semibold text-sm transition-all shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2"
                  >
                    <UserPlus className="w-4 h-4" />
                    <span>Create Account</span>
                  </button>

                  <button
                    onClick={() => onOpenAuth('login')}
                    className="px-6 py-3.5 rounded-xl bg-slate-800/90 hover:bg-slate-700 border border-slate-700 text-white font-semibold text-sm transition-all flex items-center justify-center gap-2"
                  >
                    <LogIn className="w-4 h-4 text-indigo-400" />
                    <span>Sign In</span>
                  </button>
                </div>

                <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-400">
                  <span>Supports Email, Google &amp; Apple Sign-In</span>
                  <span className="text-slate-700">•</span>
                  <button
                    type="button"
                    onClick={onEnterWorkspace}
                    className="text-indigo-400 hover:text-indigo-300 font-medium inline-flex items-center gap-1 transition-colors"
                  >
                    <span>Browse Live Seat Map as Guest</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Right Card: What you can do + Featured Event Preview */}
          <div className="lg:col-span-5 space-y-4">
            <div className="rounded-2xl bg-slate-950/80 border border-slate-800 p-6 space-y-4">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                What you can use SeatStream for
              </h2>
              <ul className="space-y-3">
                {useCases.map((item) => (
                  <li key={item} className="flex items-start gap-2.5 text-sm text-slate-300">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {featuredEvent && (
              <div className="rounded-2xl bg-slate-900/80 border border-indigo-900/50 p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-indigo-400">
                    Featured Event Live Now
                  </span>
                  {totalSeatsCount > 0 && (
                    <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                      {availableSeatsCount}/{totalSeatsCount} seats open
                    </span>
                  )}
                </div>
                <div className="text-base font-bold text-white">{featuredEvent.title}</div>
                <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400">
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-indigo-400" />
                    {featuredEvent.venue_name}
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-indigo-400" />
                    {new Date(featuredEvent.event_date).toLocaleDateString()}
                  </span>
                  <span className="text-emerald-400 font-semibold">
                    From ${featuredEvent.base_price.toFixed(2)}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Feature Highlights Grid */}
      <section className="space-y-6">
        <div className="text-center max-w-2xl mx-auto space-y-2">
          <h2 className="text-2xl font-bold text-white">How SeatStream Works</h2>
          <p className="text-sm text-slate-400">
            Built for high-concurrency ticket drops so every seat selection is instant, fair, and
            verifiable.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {highlights.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.title}
                className="rounded-2xl bg-slate-900/70 border border-slate-800 p-6 space-y-3 hover:border-slate-700 transition-colors"
              >
                <div
                  className={`w-10 h-10 rounded-xl border flex items-center justify-center ${item.accent}`}
                >
                  <Icon className="w-5 h-5" />
                </div>
                <h3 className="text-base font-bold text-white">{item.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{item.description}</p>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

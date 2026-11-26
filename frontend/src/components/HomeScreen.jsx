import React from 'react';
import {
  Ticket,
  LogIn,
  ShieldCheck,
  Zap,
  ArrowRight,
  Calendar,
  MapPin,
} from 'lucide-react';
import heroSeatsImg from '../assets/hero-seats.jpg';

export default function HomeScreen({
  featuredEvent,
  user,
  onOpenAuth,
  onEnterWorkspace,
  onOpenEventInfo,
  onOpenMyTickets,
}) {
  const features = [
    {
      icon: Zap,
      title: 'Real-Time Booking',
      subtitle: 'Lock seats instantly',
    },
    {
      icon: ShieldCheck,
      title: 'Secure & Reliable',
      subtitle: 'Your data is safe',
    },
    {
      icon: Ticket,
      title: 'Seamless Experience',
      subtitle: 'Book in just a few clicks',
    },
  ];

  return (
    <div className="relative overflow-hidden bg-[#050a18]">
      {/* Right-aligned Theater Seats Hero Artwork with seamless left & bottom fade */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[560px] sm:h-[620px] overflow-hidden">
        <img
          src={heroSeatsImg}
          alt=""
          aria-hidden="true"
          className="h-full w-full object-cover object-right opacity-90"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-[#050a18] via-[#050a18]/75 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#050a18] via-transparent to-[#050a18]/30" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-10 pb-12 sm:pt-14 sm:pb-16">
        {/* Hero Copy */}
        <div className="max-w-xl">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-[#0b1730]/90 border border-[#1d3563] text-slate-200 text-xs font-medium backdrop-blur-sm">
            <Zap className="w-3.5 h-3.5 text-[#3898ff] fill-[#3898ff]" />
            <span>Real-Time Ticket &amp; Seat Reservation</span>
          </div>

          <h1 className="mt-6 text-4xl sm:text-5xl lg:text-[54px] font-extrabold text-white tracking-tight leading-[1.08]">
            Book live event seats
            <br />
            without <span className="text-[#2684ff]">race conditions.</span>
          </h1>

          <p className="mt-5 text-base sm:text-[17px] text-slate-300 leading-relaxed max-w-lg">
            SeatStream lets you explore interactive venue seat maps, temporarily lock your favorite
            seats in real time, and confirm digital tickets instantly – with Google or email
            sign-in.
          </p>

          {/* CTA Buttons */}
          {user ? (
            <div className="mt-8 flex flex-wrap items-center gap-3.5">
              <button
                type="button"
                onClick={onEnterWorkspace}
                className="px-6 py-3 rounded-full bg-[#1a73e8] hover:bg-[#2b84f8] text-white font-semibold text-sm transition-all shadow-[0_0_25px_rgba(26,115,232,0.45)] flex items-center gap-2"
              >
                <Ticket className="w-4 h-4" />
                <span>Open Live Seat Map</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <button
                type="button"
                onClick={onOpenMyTickets}
                className="px-6 py-3 rounded-full bg-[#0a1428]/90 hover:bg-[#11203d] border border-[#22365c] text-white font-semibold text-sm transition-all"
              >
                My Tickets
              </button>
            </div>
          ) : (
            <div className="mt-8 flex flex-wrap items-center gap-3.5">
              <button
                type="button"
                onClick={() => onOpenAuth('register')}
                className="px-6 py-3 rounded-full bg-[#1a73e8] hover:bg-[#2b84f8] text-white font-semibold text-sm transition-all shadow-[0_0_25px_rgba(26,115,232,0.45)] flex items-center gap-2"
              >
                <Ticket className="w-4 h-4" />
                <span>Create Account</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <button
                type="button"
                onClick={() => onOpenAuth('login')}
                className="px-6 py-3 rounded-full bg-[#0a1428]/90 hover:bg-[#11203d] border border-[#22365c] text-white font-semibold text-sm transition-all flex items-center gap-2"
              >
                <LogIn className="w-4 h-4 text-[#2684ff]" />
                <span>Sign In</span>
              </button>
            </div>
          )}
        </div>

        {/* 3 Feature Highlights Row */}
        <div className="mt-16 sm:mt-20 grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-4xl">
          {features.map((item) => {
            const Icon = item.icon;
            return (
              <div key={item.title} className="flex items-center space-x-3.5">
                <div className="w-11 h-11 rounded-xl bg-[#0b162d]/90 border border-[#1a2b4d] flex items-center justify-center shrink-0">
                  <Icon className="w-5 h-5 text-[#2684ff]" />
                </div>
                <div>
                  <div className="text-sm font-semibold text-white">{item.title}</div>
                  <div className="text-xs text-slate-400 mt-0.5">{item.subtitle}</div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Bottom Upcoming Event Card */}
        {featuredEvent && (
          <div className="mt-10 rounded-2xl bg-[#081021]/90 border border-[#172542] px-5 py-4 sm:px-7 sm:py-5 backdrop-blur-md flex flex-col md:flex-row md:items-center md:justify-between gap-4 shadow-xl">
            <div className="flex flex-col sm:flex-row sm:items-center gap-4 sm:gap-10">
              <div className="flex items-center space-x-3">
                <div className="w-11 h-11 rounded-xl bg-[#0d1a35] border border-[#1b2f57] flex items-center justify-center shrink-0">
                  <Calendar className="w-5 h-5 text-[#2684ff]" />
                </div>
                <span className="text-sm font-medium text-slate-300">Upcoming Event</span>
              </div>

              <div>
                <h2 className="text-base sm:text-lg font-bold text-white">
                  {featuredEvent.title}
                </h2>
                <div className="mt-1 flex flex-wrap items-center gap-4 text-xs text-slate-400">
                  <span className="flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-[#2684ff]" />
                    <span>{featuredEvent.venue_name}</span>
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-[#2684ff]" />
                    <span>{new Date(featuredEvent.event_date).toLocaleDateString()}</span>
                  </span>
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={onOpenEventInfo}
              className="self-start md:self-center px-5 py-2.5 rounded-full bg-[#0c1830] hover:bg-[#132345] border border-[#22355a] text-xs sm:text-sm font-medium text-white transition-colors flex items-center gap-2 shrink-0"
            >
              <span>View Details</span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-300" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

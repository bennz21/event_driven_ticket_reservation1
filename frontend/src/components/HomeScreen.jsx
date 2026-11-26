import React, { useEffect, useState } from 'react';
import {
  Ticket,
  LogIn,
  Zap,
  ArrowRight,
  Calendar,
  CalendarRange,
  MapPin,
  Shield,
  Users,
} from 'lucide-react';
import heroSeatsImg from '../assets/hero-seats.jpg';
import { publicBrowseEvents } from '../api/client';

const AMBIENT_PARTICLES = [
  { left: '48%', top: '76%', size: 'w-1.5 h-1.5', duration: '5.5s', delay: '0s' },
  { left: '54%', top: '62%', size: 'w-2 h-2', duration: '6.8s', delay: '0.6s' },
  { left: '60%', top: '82%', size: 'w-1.5 h-1.5', duration: '6.0s', delay: '1.3s' },
  { left: '66%', top: '54%', size: 'w-2.5 h-2.5', duration: '7.2s', delay: '0.3s' },
  { left: '71%', top: '74%', size: 'w-2 h-2', duration: '6.4s', delay: '1.9s' },
  { left: '76%', top: '60%', size: 'w-1.5 h-1.5', duration: '5.9s', delay: '0.9s' },
  { left: '81%', top: '80%', size: 'w-2 h-2', duration: '7.5s', delay: '2.4s' },
  { left: '86%', top: '56%', size: 'w-2 h-2', duration: '6.3s', delay: '0.4s' },
  { left: '91%', top: '72%', size: 'w-2 h-2', duration: '6.1s', delay: '1.7s' },
];

export default function HomeScreen({ user, onNavigate }) {
  const [parallax, setParallax] = useState({ x: 0, y: 0, glowX: 65, glowY: 40, active: false });
  const [portalHighlight, setPortalHighlight] = useState(0);
  const [upcomingEvents, setUpcomingEvents] = useState([]);
  const [eventsLoading, setEventsLoading] = useState(true);

  useEffect(() => {
    const id = setInterval(() => {
      setPortalHighlight((prev) => (prev + 1) % 3);
    }, 2800);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    let active = true;
    publicBrowseEvents()
      .then((data) => {
        if (active && Array.isArray(data)) {
          setUpcomingEvents(data);
        }
      })
      .catch(() => {
        if (active) setUpcomingEvents([]);
      })
      .finally(() => {
        if (active) setEventsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const handleMouseMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const nx = (e.clientX - rect.left) / rect.width;
    const ny = (e.clientY - rect.top) / rect.height;
    setParallax({
      x: (nx - 0.5) * 20,
      y: (ny - 0.5) * 12,
      glowX: nx * 100,
      glowY: ny * 100,
      active: true,
    });
  };

  const roles = [
    {
      icon: Users,
      title: 'General Public',
      subtitle: 'Browse approved events, book up to 5 tickets, pay & download passes',
      path: '/login/public',
      cta: 'Public Sign In',
    },
    {
      icon: CalendarRange,
      title: 'Event Organizers',
      subtitle: 'Create, edit & manage events and track ticket sales in real time',
      path: '/login/organizer',
      cta: 'Organizer Login',
    },
    {
      icon: Shield,
      title: 'Platform Admin',
      subtitle: 'Approve events, moderate accounts, and audit bookings & payments',
      path: '/login/admin',
      cta: 'Admin Login',
    },
  ];

  const dashboardPath =
    user?.role === 'admin' ? '/admin' : user?.role === 'organizer' ? '/organizer' : '/public';

  return (
    <div
      onMouseMove={handleMouseMove}
      onMouseLeave={() => setParallax((prev) => ({ ...prev, x: 0, y: 0, active: false }))}
      className="relative overflow-hidden bg-[#050a18]"
    >
      {/* Perspective Grid */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 animate-grid-pulse"
        style={{
          backgroundImage:
            'linear-gradient(to right, rgba(38, 132, 255, 0.1) 1px, transparent 1px), linear-gradient(to bottom, rgba(38, 132, 255, 0.1) 1px, transparent 1px)',
          backgroundSize: '52px 52px',
          maskImage: 'radial-gradient(ellipse at 72% 35%, black 18%, transparent 74%)',
        }}
      />

      {/* Mouse Spotlight */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 transition-opacity duration-500"
        style={{
          opacity: parallax.active ? 1 : 0,
          background: `radial-gradient(560px circle at ${parallax.glowX}% ${parallax.glowY}%, rgba(38, 132, 255, 0.18), transparent 65%)`,
        }}
      />

      {/* Hero Artwork + Sonar Rings */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[580px] sm:h-[640px] overflow-hidden">
        <div
          className="h-full w-full transition-transform duration-300 ease-out"
          style={{ transform: `translate3d(${-parallax.x}px, ${-parallax.y}px, 0)` }}
        >
          <img
            src={heroSeatsImg}
            alt=""
            aria-hidden="true"
            className="h-full w-full object-cover object-right opacity-90 animate-hero-drift will-change-transform"
          />
        </div>

        <div
          aria-hidden="true"
          className="absolute -top-24 right-[8%] h-[145%] w-72 bg-gradient-to-b from-[#2684ff]/25 via-[#3898ff]/12 to-transparent blur-2xl animate-spotlight-sweep"
        />

        <div className="absolute right-[19%] top-[44%] -translate-y-1/2 flex items-center justify-center">
          <div className="h-72 w-72 rounded-full bg-[#2684ff]/25 blur-[95px] animate-aura-pulse" />
          <span className="absolute h-40 w-40 rounded-full border border-[#3898ff]/50 animate-sonar-ring" />
          <span
            style={{ animationDelay: '1.1s' }}
            className="absolute h-40 w-40 rounded-full border border-[#60b5ff]/40 animate-sonar-ring"
          />
        </div>

        {AMBIENT_PARTICLES.map((p, idx) => (
          <span
            key={idx}
            style={{
              left: p.left,
              top: p.top,
              '--duration': p.duration,
              '--delay': p.delay,
            }}
            className={`absolute rounded-full bg-[#7cc4ff] shadow-[0_0_14px_rgba(96,181,255,0.95)] animate-particle ${p.size}`}
          />
        ))}

        <div className="absolute inset-0 bg-gradient-to-r from-[#050a18] via-[#050a18]/78 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#050a18] via-transparent to-[#050a18]/30" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-10 pb-14 sm:pt-14 sm:pb-20">
        <div className="max-w-2xl">
          <div
            style={{ animationDelay: '0ms' }}
            className="animate-fade-up inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-[#0b1730]/90 border border-[#1d3563] text-slate-200 text-xs font-medium backdrop-blur-sm"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#3898ff] opacity-80" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#2684ff]" />
            </span>
            <Zap className="w-3.5 h-3.5 text-[#3898ff] fill-[#3898ff]" />
            <span>Transactional MySQL Event &amp; Ticket Booking</span>
          </div>

          <h1
            style={{ animationDelay: '90ms' }}
            className="animate-fade-up mt-6 text-4xl sm:text-5xl lg:text-[54px] font-extrabold text-white tracking-tight leading-[1.08]"
          >
            Book live event tickets
            <br />
            without{' '}
            <span className="relative inline-block">
              <span className="bg-gradient-to-r from-[#2684ff] via-[#a6dbff] to-[#2684ff] bg-clip-text text-transparent animate-text-shimmer">
                race conditions.
              </span>
              <span
                aria-hidden="true"
                className="absolute -bottom-1 left-0 right-0 h-[3px] rounded-full bg-gradient-to-r from-[#2684ff] via-[#7cc4ff] to-transparent animate-underline-sweep"
              />
            </span>
          </h1>

          <p
            style={{ animationDelay: '180ms' }}
            className="animate-fade-up mt-5 text-base sm:text-[17px] text-slate-300 leading-relaxed max-w-xl"
          >
            SeatStream connects Event Organizers, Administrators, and attendees on a single
            transactional platform with row-locked inventory, payment gateway verification, and
            instant digital tickets.
          </p>

          {user ? (
            <div
              style={{ animationDelay: '260ms' }}
              className="animate-fade-up mt-8 flex flex-wrap items-center gap-3.5"
            >
              <button
                type="button"
                onClick={() => onNavigate(dashboardPath)}
                className="group relative overflow-hidden px-6 py-3 rounded-full bg-[#1a73e8] hover:bg-[#2b84f8] text-white font-semibold text-sm transition-all duration-300 hover:-translate-y-0.5 animate-cta-glow flex items-center gap-2"
              >
                <span
                  aria-hidden="true"
                  className="pointer-events-none absolute inset-y-0 w-16 bg-gradient-to-r from-transparent via-white/35 to-transparent animate-btn-sheen"
                />
                <Ticket className="w-4 h-4 relative z-10" />
                <span className="relative z-10">Go to My Dashboard</span>
                <ArrowRight className="w-4 h-4 relative z-10 animate-arrow-nudge" />
              </button>
            </div>
          ) : (
            <div
              style={{ animationDelay: '260ms' }}
              className="animate-fade-up mt-8 flex flex-wrap items-center gap-3.5"
            >
              <button
                type="button"
                onClick={() => onNavigate('/signup')}
                className="group relative overflow-hidden px-6 py-3 rounded-full bg-[#1a73e8] hover:bg-[#2b84f8] text-white font-semibold text-sm transition-all duration-300 hover:-translate-y-0.5 animate-cta-glow flex items-center gap-2"
              >
                <span
                  aria-hidden="true"
                  className="pointer-events-none absolute inset-y-0 w-16 bg-gradient-to-r from-transparent via-white/35 to-transparent animate-btn-sheen"
                />
                <Ticket className="w-4 h-4 relative z-10" />
                <span className="relative z-10">Create Account</span>
                <ArrowRight className="w-4 h-4 relative z-10 animate-arrow-nudge" />
              </button>

              <button
                type="button"
                onClick={() => onNavigate('/login/public')}
                className="group px-6 py-3 rounded-full bg-[#0a1428]/90 hover:bg-[#11203d] border border-[#22365c] hover:border-[#3898ff]/60 text-white font-semibold text-sm transition-all duration-300 hover:-translate-y-0.5 flex items-center gap-2"
              >
                <LogIn className="w-4 h-4 text-[#2684ff]" />
                <span>Sign In</span>
              </button>
            </div>
          )}
        </div>

        {/* 3 Role Portals */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-5">
          {roles.map((r, idx) => {
            const Icon = r.icon;
            const highlighted = portalHighlight === idx;
            return (
              <div
                key={r.title}
                style={{ animationDelay: `${340 + idx * 90}ms` }}
                className={`animate-fade-up relative overflow-hidden rounded-2xl bg-[#081021]/90 border p-6 backdrop-blur-md transition-all duration-300 hover:-translate-y-1 flex flex-col justify-between gap-5 ${
                  highlighted
                    ? 'border-[#2684ff]/70 shadow-[0_0_30px_rgba(26,115,232,0.2)]'
                    : 'border-[#172542] hover:border-[#2a4980]'
                }`}
              >
                <div className="space-y-3">
                  <div className="w-11 h-11 rounded-xl bg-[#0d1a35] border border-[#1b2f57] flex items-center justify-center">
                    <Icon className="w-5 h-5 text-[#2684ff]" />
                  </div>
                  <h2 className="text-base font-bold text-white">{r.title}</h2>
                  <p className="text-xs text-slate-400 leading-relaxed">{r.subtitle}</p>
                </div>

                {!user && (
                  <button
                    type="button"
                    onClick={() => onNavigate(r.path)}
                    className="group self-start px-4 py-2 rounded-full bg-[#0c1830] hover:bg-[#132345] border border-[#22355a] hover:border-[#3898ff]/60 text-xs font-semibold text-white transition-all flex items-center gap-1.5"
                  >
                    <span>{r.cta}</span>
                    <ArrowRight className="w-3.5 h-3.5 text-[#2684ff] transition-transform group-hover:translate-x-0.5" />
                  </button>
                )}
              </div>
            );
          })}
        </div>

        {/* Upcoming Events Section (loaded live from MySQL) */}
        <div
          style={{ animationDelay: '600ms' }}
          className="animate-fade-up relative overflow-hidden mt-10 rounded-2xl bg-[#081021]/90 border border-[#172542] p-6 backdrop-blur-md space-y-5"
        >
          <div
            aria-hidden="true"
            className="pointer-events-none absolute top-0 left-0 h-[1.5px] w-1/2 bg-gradient-to-r from-transparent via-[#3898ff]/85 to-transparent animate-border-scan"
          />

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center space-x-3">
              <div className="relative w-10 h-10 rounded-xl bg-[#0d1a35] border border-[#1b2f57] flex items-center justify-center shrink-0">
                <Calendar className="w-5 h-5 text-[#2684ff]" />
                <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#3898ff] opacity-75" />
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#2684ff]" />
                </span>
              </div>
              <div>
                <h2 className="text-base sm:text-lg font-bold text-white">Upcoming Events</h2>
                <p className="text-xs text-slate-400">
                  Admin-approved events available for ticket booking
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => onNavigate(user?.role === 'public' ? '/public' : '/login/public')}
              className="group px-4 py-2 rounded-full bg-[#0c1830] hover:bg-[#132345] border border-[#22355a] hover:border-[#3898ff]/60 text-xs font-semibold text-white transition-all flex items-center gap-1.5"
            >
              <span>{user?.role === 'public' ? 'Browse All Events' : 'Sign In to Book'}</span>
              <ArrowRight className="w-3.5 h-3.5 text-[#2684ff] transition-transform group-hover:translate-x-0.5" />
            </button>
          </div>

          {eventsLoading ? (
            <div className="py-6 text-center text-xs text-slate-400">
              Loading upcoming events...
            </div>
          ) : upcomingEvents.length === 0 ? (
            <div className="rounded-xl bg-[#050a18]/70 border border-[#14203b] px-5 py-6 text-center text-xs sm:text-sm text-slate-400">
              No approved upcoming events yet. Events created by organizers appear here once
              approved by an admin.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {upcomingEvents.slice(0, 6).map((ev) => {
                const soldOut = ev.available_tickets <= 0;
                return (
                  <div
                    key={ev.id}
                    className="rounded-xl bg-[#060d1c] border border-[#172542] hover:border-[#2a4980] p-4 flex flex-col justify-between gap-3 transition-all"
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[11px] font-mono text-[#60b5ff]">
                          ${ev.ticket_price.toFixed(2)}
                        </span>
                        <span
                          className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                            soldOut
                              ? 'bg-rose-500/15 border-rose-500/30 text-rose-300'
                              : 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300'
                          }`}
                        >
                          {soldOut ? 'Sold Out' : `${ev.available_tickets} left`}
                        </span>
                      </div>
                      <h3 className="text-sm font-bold text-white line-clamp-1">{ev.title}</h3>
                      <div className="space-y-1 text-xs text-slate-400">
                        <div className="flex items-center gap-1.5">
                          <MapPin className="w-3.5 h-3.5 text-[#2684ff] shrink-0" />
                          <span className="truncate">{ev.venue}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Calendar className="w-3.5 h-3.5 text-[#2684ff] shrink-0" />
                          <span>
                            {ev.event_date} · {String(ev.event_time).slice(0, 5)}
                          </span>
                        </div>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() =>
                        onNavigate(user?.role === 'public' ? '/public' : '/login/public')
                      }
                      className="w-full py-2 rounded-full bg-[#0e1b36] hover:bg-[#1a73e8] border border-[#22355a] hover:border-[#2684ff] text-xs font-semibold text-white transition-all"
                    >
                      {soldOut
                        ? 'Sold Out'
                        : user?.role === 'public'
                          ? ev.seating_type === 'seated'
                            ? 'Select Seats'
                            : 'Book Tickets'
                          : 'Sign In to Book'}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

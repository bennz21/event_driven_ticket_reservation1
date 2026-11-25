import React from 'react';
import { Ticket, User, RotateCcw, LogIn, UserPlus, LogOut, Home, LayoutGrid } from 'lucide-react';

export default function Navbar({
  isConnected,
  sessionId,
  onResetSession,
  user,
  onOpenAuth,
  onOpenMyTickets,
  onLogout,
  activeView,
  onNavigate,
}) {
  const providerBadge =
    user?.auth_provider === 'google'
      ? 'Google'
      : user?.auth_provider === 'apple'
        ? 'Apple'
        : null;

  return (
    <header className="border-b border-slate-800 bg-slate-900/70 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-3">
        {/* Brand + View Switcher */}
        <div className="flex items-center space-x-4">
          <button
            type="button"
            onClick={() => onNavigate('home')}
            className="flex items-center space-x-3 text-left group"
          >
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-emerald-400 flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
              <Ticket className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-bold text-lg text-white tracking-tight flex items-center gap-2">
                SeatStream
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  Event-Driven
                </span>
              </span>
              <p className="text-xs text-slate-400 hidden sm:block">
                Real-Time Concurrency & Ticket Reservation System
              </p>
            </div>
          </button>

          <nav className="hidden md:flex items-center space-x-1 pl-2 border-l border-slate-800">
            <button
              type="button"
              onClick={() => onNavigate('home')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                activeView === 'home'
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/70'
              }`}
            >
              <Home className="w-3.5 h-3.5" />
              <span>Home</span>
            </button>
            <button
              type="button"
              onClick={() => onNavigate('workspace')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                activeView === 'workspace'
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/70'
              }`}
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              <span>Live Seat Map</span>
            </button>
          </nav>
        </div>

        {/* Right side status indicators & account controls */}
        <div className="flex items-center space-x-2 sm:space-x-3">
          {/* Live WS connection status */}
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-slate-800/80 border border-slate-700/60 text-xs">
            <span className={`h-2.5 w-2.5 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
            <span className="font-medium text-slate-300 hidden md:inline">
              {isConnected ? 'Real-Time Sync' : 'Connecting WS...'}
            </span>
          </div>

          {/* Session ID Pill */}
          <div className="hidden lg:flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-indigo-950/60 border border-indigo-800/50 text-xs text-indigo-300">
            <User className="w-3.5 h-3.5 text-indigo-400" />
            <span className="font-mono">{sessionId}</span>
            <button
              onClick={onResetSession}
              title="Switch user session (simulates another buyer)"
              className="p-1 hover:bg-indigo-900/60 rounded transition-colors text-indigo-400 hover:text-white"
            >
              <RotateCcw className="w-3 h-3" />
            </button>
          </div>

          {/* Account Controls */}
          {user ? (
            <div className="flex items-center space-x-2">
              <button
                onClick={onOpenMyTickets}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold text-slate-200 flex items-center gap-1.5 transition-colors"
              >
                <Ticket className="w-3.5 h-3.5 text-emerald-400" />
                <span className="hidden sm:inline">My Tickets</span>
              </button>

              <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-emerald-950/50 border border-emerald-700/40 text-xs">
                <span className="font-semibold text-emerald-200 max-w-[120px] truncate">
                  {user.full_name}
                </span>
                {providerBadge && (
                  <span className="hidden md:inline text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    {providerBadge}
                  </span>
                )}
                <button
                  onClick={onLogout}
                  title="Sign out"
                  className="p-1 hover:bg-emerald-900/60 rounded text-emerald-300 hover:text-white transition-colors"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <button
                onClick={() => onOpenAuth('login')}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold text-slate-200 flex items-center gap-1.5 transition-colors"
              >
                <LogIn className="w-3.5 h-3.5 text-indigo-400" />
                <span>Sign In</span>
              </button>
              <button
                onClick={() => onOpenAuth('register')}
                className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white flex items-center gap-1.5 transition-colors shadow-md shadow-indigo-600/20"
              >
                <UserPlus className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Create Account</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

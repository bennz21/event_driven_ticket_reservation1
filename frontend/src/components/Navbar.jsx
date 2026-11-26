import React from 'react';
import { Armchair, User, LogOut, Ticket } from 'lucide-react';

export default function Navbar({
  isConnected,
  user,
  onOpenAuth,
  onOpenMyTickets,
  onOpenEventInfo,
  onOpenSupport,
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
    <header className="border-b border-[#13203d] bg-[#050a18]/90 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Left: Brand */}
        <button
          type="button"
          onClick={() => onNavigate('home')}
          className="flex items-center space-x-2.5 text-left group shrink-0"
        >
          <div className="h-9 w-9 rounded-xl bg-[#1a73e8]/15 border border-[#2684ff]/30 flex items-center justify-center group-hover:bg-[#1a73e8]/25 transition-colors">
            <Armchair className="w-5 h-5 text-[#2684ff]" />
          </div>
          <span className="font-bold text-lg text-white tracking-tight">SeatStream</span>
        </button>

        {/* Center: Navigation Links */}
        <nav className="hidden md:flex items-center space-x-7 h-full">
          <button
            type="button"
            onClick={() => onNavigate('home')}
            className={`relative h-full px-1 text-sm font-medium transition-colors flex items-center ${
              activeView === 'home' ? 'text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>Home</span>
            {activeView === 'home' && (
              <span className="absolute bottom-0 left-0 right-0 h-[2px] rounded-full bg-[#2684ff]" />
            )}
          </button>

          {user && (
            <button
              type="button"
              onClick={() => onNavigate('workspace')}
              className={`relative h-full px-1 text-sm font-medium transition-colors flex items-center ${
                activeView === 'workspace' ? 'text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              <span>Live Seat Map</span>
              {activeView === 'workspace' && (
                <span className="absolute bottom-0 left-0 right-0 h-[2px] rounded-full bg-[#2684ff]" />
              )}
            </button>
          )}

          <button
            type="button"
            onClick={onOpenEventInfo}
            className="h-full px-1 text-sm font-medium text-slate-400 hover:text-white transition-colors flex items-center"
          >
            Event Info
          </button>

          <button
            type="button"
            onClick={onOpenSupport}
            className="h-full px-1 text-sm font-medium text-slate-400 hover:text-white transition-colors flex items-center"
          >
            Support
          </button>
        </nav>

        {/* Right: Account Controls */}
        <div className="flex items-center space-x-3 shrink-0">
          {user && activeView === 'workspace' && (
            <div
              title={isConnected ? 'WebSocket connected' : 'Connecting WebSocket'}
              className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-[#0b152b] border border-[#1a2c4f] text-[11px] text-slate-300"
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'
                }`}
              />
              <span>{isConnected ? 'Live' : 'Syncing'}</span>
            </div>
          )}

          {user ? (
            <div className="flex items-center space-x-2.5">
              <button
                type="button"
                onClick={onOpenMyTickets}
                className="px-3.5 py-1.5 rounded-full bg-[#0b162d] hover:bg-[#122244] border border-[#1f345c] text-xs font-semibold text-slate-200 flex items-center gap-1.5 transition-colors"
              >
                <Ticket className="w-3.5 h-3.5 text-[#2684ff]" />
                <span className="hidden sm:inline">My Tickets</span>
              </button>

              <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-[#0b162d] border border-[#1f345c] text-xs">
                <span className="font-semibold text-white max-w-[120px] truncate">
                  {user.full_name}
                </span>
                {providerBadge && (
                  <span className="hidden md:inline text-[10px] px-1.5 py-0.5 rounded-full bg-[#1a73e8]/20 text-[#60a5fa] border border-[#2684ff]/30">
                    {providerBadge}
                  </span>
                )}
                <button
                  type="button"
                  onClick={onLogout}
                  title="Sign out"
                  className="p-0.5 text-slate-400 hover:text-white transition-colors"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center space-x-3">
              <button
                type="button"
                onClick={() => onOpenAuth('login')}
                title="Sign In"
                aria-label="Sign In"
                className="p-2 rounded-full text-slate-300 hover:text-white hover:bg-[#0d1933] transition-colors"
              >
                <User className="w-5 h-5" />
              </button>
              <button
                type="button"
                onClick={() => onOpenAuth('register')}
                className="px-5 py-2 rounded-full bg-[#1a73e8] hover:bg-[#2b84f8] text-xs sm:text-sm font-semibold text-white transition-all shadow-[0_0_20px_rgba(26,115,232,0.35)]"
              >
                Create Account
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

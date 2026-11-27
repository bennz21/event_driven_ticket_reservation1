import React from 'react';
import { Armchair, LogOut, Shield, CalendarRange, Ticket, UserPlus, LogIn, Sun, Moon } from 'lucide-react';

export default function Navbar({ user, theme = 'dark', onToggleTheme, currentPath, onNavigate, onLogout }) {
  const roleBadge =
    user?.role === 'admin'
      ? { label: 'Admin', style: 'bg-rose-500/15 text-rose-300 border-rose-500/30', icon: Shield }
      : user?.role === 'organizer'
        ? { label: 'Organizer', style: 'bg-amber-500/15 text-amber-300 border-amber-500/30', icon: CalendarRange }
        : user?.role === 'public'
          ? { label: 'Public', style: 'bg-[#1a73e8]/20 text-[#60b5ff] border-[#2684ff]/30', icon: Ticket }
          : null;

  const dashboardPath =
    user?.role === 'admin' ? '/admin' : user?.role === 'organizer' ? '/organizer' : '/public';

  return (
    <header className="border-b border-[#13203d] bg-[#050a18]/95 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        <button
          type="button"
          onClick={() => onNavigate('/')}
          className="flex items-center space-x-2.5 text-left group shrink-0"
        >
          <div className="h-9 w-9 rounded-xl bg-[#1a73e8]/15 border border-[#2684ff]/30 flex items-center justify-center group-hover:bg-[#1a73e8]/25 transition-colors">
            <Armchair className="w-5 h-5 text-[#2684ff]" />
          </div>
          <span className="font-bold text-lg text-white tracking-tight">SeatStream</span>
        </button>

        <nav className="hidden md:flex items-center space-x-6 h-full">
          <button
            type="button"
            onClick={() => onNavigate('/')}
            className={`relative h-full px-1 text-sm font-medium transition-colors flex items-center ${
              currentPath === '/' ? 'text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>Home</span>
            {currentPath === '/' && (
              <span className="absolute bottom-0 left-0 right-0 h-[2px] rounded-full bg-[#2684ff]" />
            )}
          </button>

          {user ? (
            <button
              type="button"
              onClick={() => onNavigate(dashboardPath)}
              className={`relative h-full px-1 text-sm font-medium transition-colors flex items-center ${
                currentPath === dashboardPath ? 'text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              <span>
                {user.role === 'admin'
                  ? 'Admin Console'
                  : user.role === 'organizer'
                    ? 'Organizer Studio'
                    : 'Events & Bookings'}
              </span>
              {currentPath === dashboardPath && (
                <span className="absolute bottom-0 left-0 right-0 h-[2px] rounded-full bg-[#2684ff]" />
              )}
            </button>
          ) : (
            <>
              <button
                type="button"
                onClick={() => onNavigate('/login/public')}
                className={`relative h-full px-1 text-sm font-medium transition-colors flex items-center ${
                  currentPath === '/login/public' ? 'text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                <span>Public Login</span>
                {currentPath === '/login/public' && (
                  <span className="absolute bottom-0 left-0 right-0 h-[2px] rounded-full bg-[#2684ff]" />
                )}
              </button>
              <button
                type="button"
                onClick={() => onNavigate('/login/organizer')}
                className={`relative h-full px-1 text-sm font-medium transition-colors flex items-center ${
                  currentPath === '/login/organizer' ? 'text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                <span>Organizer Login</span>
                {currentPath === '/login/organizer' && (
                  <span className="absolute bottom-0 left-0 right-0 h-[2px] rounded-full bg-[#2684ff]" />
                )}
              </button>
              <button
                type="button"
                onClick={() => onNavigate('/login/admin')}
                className={`relative h-full px-1 text-sm font-medium transition-colors flex items-center ${
                  currentPath === '/login/admin' ? 'text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                <span>Admin Login</span>
                {currentPath === '/login/admin' && (
                  <span className="absolute bottom-0 left-0 right-0 h-[2px] rounded-full bg-[#2684ff]" />
                )}
              </button>
            </>
          )}
        </nav>

        <div className="flex items-center space-x-2.5 sm:space-x-3 shrink-0">
          {onToggleTheme && (
            <button
              type="button"
              onClick={onToggleTheme}
              aria-label={theme === 'dark' ? 'Switch to Light mode' : 'Switch to Dark mode'}
              title={theme === 'dark' ? 'Switch to Light mode' : 'Switch to Dark mode'}
              className={`group flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-semibold transition-all duration-300 ${
                theme === 'light'
                  ? 'bg-white hover:bg-blue-50 border-[#d5e3fb] text-[#1e3a8a] shadow-sm'
                  : 'bg-[#0a1428] hover:bg-[#11203d] border-[#22365c] text-slate-200'
              }`}
            >
              {theme === 'dark' ? (
                <>
                  <Sun className="w-3.5 h-3.5 text-amber-400 transition-transform duration-300 group-hover:rotate-45" />
                  <span className="hidden sm:inline">Light</span>
                </>
              ) : (
                <>
                  <Moon className="w-3.5 h-3.5 text-[#1a73e8] transition-transform duration-300 group-hover:-rotate-12" />
                  <span className="hidden sm:inline">Dark</span>
                </>
              )}
            </button>
          )}
          {user ? (
            <div className="flex items-center space-x-2.5">
              {roleBadge && (
                <span
                  className={`hidden sm:inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1 rounded-full border ${roleBadge.style}`}
                >
                  <roleBadge.icon className="w-3 h-3" />
                  {roleBadge.label}
                </span>
              )}
              <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-[#0b162d] border border-[#1f345c] text-xs">
                <span className="font-semibold text-white max-w-[140px] truncate">{user.name}</span>
                <button
                  type="button"
                  onClick={onLogout}
                  title="Sign out"
                  aria-label="Sign out"
                  className="p-0.5 text-slate-400 hover:text-white transition-colors"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center space-x-2.5">
              <button
                type="button"
                onClick={() => onNavigate('/login/public')}
                className="px-4 py-2 rounded-full bg-[#0a1428] hover:bg-[#11203d] border border-[#22365c] text-xs sm:text-sm font-medium text-white flex items-center gap-1.5 transition-colors"
              >
                <LogIn className="w-3.5 h-3.5 text-[#2684ff]" />
                <span>Sign In</span>
              </button>
              <button
                type="button"
                onClick={() => onNavigate('/signup')}
                className="px-5 py-2 rounded-full bg-[#1a73e8] hover:bg-[#2b84f8] text-xs sm:text-sm font-semibold text-white flex items-center gap-1.5 transition-all shadow-[0_0_20px_rgba(26,115,232,0.35)]"
              >
                <UserPlus className="w-3.5 h-3.5" />
                <span>Create Account</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

import React, { useEffect, useState } from 'react';
import { ArrowRight, CalendarRange, Eye, EyeOff, Lock, Mail, Shield, Users } from 'lucide-react';
import { getGoogleOAuthUrl, loginByRole } from '../api/client';

function GoogleLogo() {
  return (
    <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17Z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.11-6.72-4.96H1.29v3.14C3.26 21.3 7.31 24 12 24Z"
      />
      <path
        fill="#FBBC05"
        d="M5.28 14.24c-.24-.72-.38-1.49-.38-2.24s.14-1.52.38-2.24V6.62H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.38l3.99-3.14Z"
      />
      <path
        fill="#EA4335"
        d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.62l3.99 3.14c.95-2.85 3.6-4.96 6.72-4.96Z"
      />
    </svg>
  );
}

const ROLE_META = {
  public: {
    title: 'General Public Sign In',
    subtitle: 'Sign in to browse approved events, book tickets, and manage bookings.',
    icon: Users,
    accent: 'text-[#2684ff] bg-[#1a73e8]/15 border-[#2684ff]/30',
  },
  organizer: {
    title: 'Event Organizer Login',
    subtitle: 'Sign in to create, edit, and track ticket sales for your events.',
    icon: CalendarRange,
    accent: 'text-amber-400 bg-amber-500/15 border-amber-500/30',
  },
  admin: {
    title: 'Admin Portal Login',
    subtitle: 'Restricted administrator login validated against environment credentials.',
    icon: Shield,
    accent: 'text-rose-400 bg-rose-500/15 border-rose-500/30',
  },
};

export default function LoginPage({ role, externalError = '', onAuthSuccess, onNavigate }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(externalError);

  useEffect(() => {
    setError(externalError || '');
  }, [externalError, role]);

  const meta = ROLE_META[role] || ROLE_META.public;
  const Icon = meta.icon;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      const res = await loginByRole(role, { email, password });
      onAuthSuccess(res.user);
    } catch (err) {
      setError(err.message || 'Sign in failed.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto px-4 py-12">
      <div className="animate-modal-pop bg-[#091224] border border-[#192848] rounded-2xl p-6 sm:p-8 shadow-2xl">
        <div className="flex items-center space-x-3 mb-4">
          <div className={`w-10 h-10 rounded-xl border flex items-center justify-center ${meta.accent}`}>
            <Icon className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">{meta.title}</h1>
            <p className="text-xs text-slate-400">{meta.subtitle}</p>
          </div>
        </div>

        {/* Role Portal Switcher */}
        <div className="grid grid-cols-3 gap-1 p-1 rounded-full bg-[#060d1c] border border-[#172542] mb-5">
          {(['public', 'organizer', 'admin']).map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => {
                setError('');
                onNavigate(`/login/${r}`);
              }}
              className={`py-1.5 rounded-full text-xs font-semibold capitalize transition-all ${
                role === r ? 'bg-[#1a73e8] text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              {r}
            </button>
          ))}
        </div>

        {role !== 'admin' && (
          <>
            <button
              type="button"
              onClick={() => {
                window.location.href = getGoogleOAuthUrl(role);
              }}
              className="w-full py-2.5 px-4 rounded-full bg-white hover:bg-slate-100 text-slate-900 font-semibold text-sm transition-all flex items-center justify-center gap-2.5 shadow-sm"
            >
              <GoogleLogo />
              <span>Continue with Google</span>
            </button>

            <div className="relative my-5">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-[#172542]" />
              </div>
              <div className="relative flex justify-center text-[11px] uppercase tracking-wider">
                <span className="bg-[#091224] px-3 text-slate-500 font-medium">
                  or continue with email
                </span>
              </div>
            </div>
          </>
        )}

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-950/70 border border-rose-600/60 text-rose-300 text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">Email Address</label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="email"
                required
                placeholder={role === 'admin' ? 'admin@seatstream.com' : 'you@example.com'}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-3.5 py-2.5 rounded-xl bg-[#060d1c] border border-[#1b2b4d] text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-[#2684ff]"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type={showPassword ? 'text' : 'password'}
                required
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-10 py-2.5 rounded-xl bg-[#060d1c] border border-[#1b2b4d] text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-[#2684ff]"
              />
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3 rounded-full bg-[#1a73e8] hover:bg-[#2b84f8] text-white font-semibold text-sm transition-all shadow-[0_0_20px_rgba(26,115,232,0.35)] disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <span>{isLoading ? 'Signing in...' : 'Sign In'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        {role !== 'admin' && (
          <div className="mt-5 pt-4 border-t border-[#172542] text-center text-xs text-slate-400">
            Don&apos;t have an account?{' '}
            <button
              type="button"
              onClick={() => onNavigate('/signup')}
              className="text-[#60b5ff] hover:text-white font-semibold"
            >
              Create Account
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

import React, { useState } from 'react';
import { ArrowRight, CalendarRange, Eye, EyeOff, Lock, Mail, User, Users } from 'lucide-react';
import { getGoogleOAuthUrl, signupAccount } from '../api/client';

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

export default function SignupPage({ onAuthSuccess, onNavigate }) {
  const [role, setRole] = useState('public');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    setIsLoading(true);
    try {
      const res = await signupAccount({ name, email, password, role });
      onAuthSuccess(res.user);
    } catch (err) {
      setError(err.message || 'Signup failed.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto px-4 py-12">
      <div className="animate-modal-pop bg-[#091224] border border-[#192848] rounded-2xl p-6 sm:p-8 shadow-2xl">
        <h1 className="text-2xl font-bold text-white">Create an account</h1>
        <p className="text-xs text-slate-400 mt-1">
          Choose your account type to get started on SeatStream.
        </p>

        {/* Account Type Selector: Public or Organizer only */}
        <div className="mt-5 grid grid-cols-2 gap-2.5">
          <button
            type="button"
            onClick={() => setRole('public')}
            className={`p-3 rounded-xl border text-left transition-all ${
              role === 'public'
                ? 'bg-[#1a73e8]/20 border-[#2684ff] text-white shadow-[0_0_16px_rgba(38,132,255,0.2)]'
                : 'bg-[#060d1c] border-[#172542] text-slate-400 hover:text-white'
            }`}
          >
            <Users className="w-4 h-4 text-[#2684ff] mb-1.5" />
            <div className="text-xs font-bold">General Public</div>
            <div className="text-[11px] text-slate-400 mt-0.5">Browse &amp; book tickets</div>
          </button>

          <button
            type="button"
            onClick={() => setRole('organizer')}
            className={`p-3 rounded-xl border text-left transition-all ${
              role === 'organizer'
                ? 'bg-[#1a73e8]/20 border-[#2684ff] text-white shadow-[0_0_16px_rgba(38,132,255,0.2)]'
                : 'bg-[#060d1c] border-[#172542] text-slate-400 hover:text-white'
            }`}
          >
            <CalendarRange className="w-4 h-4 text-amber-400 mb-1.5" />
            <div className="text-xs font-bold">Event Organizer</div>
            <div className="text-[11px] text-slate-400 mt-0.5">List &amp; manage events</div>
          </button>
        </div>

        {/* Continue with Google */}
        <div className="mt-5">
          <button
            type="button"
            onClick={() => {
              window.location.href = getGoogleOAuthUrl(role);
            }}
            className="w-full py-2.5 px-4 rounded-full bg-white hover:bg-slate-100 text-slate-900 font-semibold text-sm transition-all flex items-center justify-center gap-2.5 shadow-sm"
          >
            <GoogleLogo />
            <span>
              Continue with Google ({role === 'organizer' ? 'Organizer' : 'Public'})
            </span>
          </button>
        </div>

        <div className="relative my-5">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-[#172542]" />
          </div>
          <div className="relative flex justify-center text-[11px] uppercase tracking-wider">
            <span className="bg-[#091224] px-3 text-slate-500 font-medium">
              or sign up with email
            </span>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-950/70 border border-rose-600/60 text-rose-300 text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">Full Name</label>
            <div className="relative">
              <User className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                required
                minLength={2}
                placeholder="Alex Mercer"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full pl-10 pr-3.5 py-2.5 rounded-xl bg-[#060d1c] border border-[#1b2b4d] text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-[#2684ff]"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">Email Address</label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="email"
                required
                placeholder="you@example.com"
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
                minLength={8}
                placeholder="At least 8 characters"
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
            <span>
              {isLoading
                ? 'Creating account...'
                : `Create ${role === 'organizer' ? 'Organizer' : 'Public'} Account`}
            </span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        <div className="mt-5 pt-4 border-t border-[#172542] text-center text-xs text-slate-400">
          Already have an account?{' '}
          <button
            type="button"
            onClick={() => onNavigate(role === 'organizer' ? '/login/organizer' : '/login/public')}
            className="text-[#60b5ff] hover:text-white font-semibold"
          >
            Sign in as {role === 'organizer' ? 'Organizer' : 'Public'}
          </button>
        </div>
      </div>
    </div>
  );
}

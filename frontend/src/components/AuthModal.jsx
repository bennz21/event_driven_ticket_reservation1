import React, { useEffect, useState } from 'react';
import { X, Mail, Lock, User, Eye, EyeOff, ArrowRight, Sparkles } from 'lucide-react';
import {
  demoOAuthLogin,
  fetchAuthProviders,
  getOAuthLoginUrl,
  loginAccount,
  registerAccount,
} from '../api/client';

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

function AppleLogo() {
  return (
    <svg className="w-4 h-4 shrink-0 fill-current" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M16.365 1.43c0 1.14-.493 2.27-1.177 3.08-.744.9-1.99 1.57-2.987 1.57-.12 0-.23-.02-.3-.03-.01-.06-.04-.22-.04-.39 0-1.15.572-2.27 1.206-2.98.804-.94 2.142-1.64 3.248-1.68.03.13.05.28.05.43Zm4.565 15.71c-.03.07-.463 1.58-1.518 3.12-.945 1.34-1.94 2.71-3.43 2.71-1.517 0-1.9-.88-3.63-.88-1.698 0-2.302.91-3.67.91-1.377 0-2.332-1.26-3.428-2.8-1.287-1.82-2.323-4.63-2.323-7.28 0-4.28 2.797-6.55 5.552-6.55 1.448 0 2.675.95 3.6.95.865 0 2.222-1.01 3.902-1.01.613 0 2.886.06 4.374 2.19-.13.09-2.383 1.37-2.383 4.19 0 3.26 2.854 4.42 2.955 4.45Z" />
    </svg>
  );
}

export default function AuthModal({
  isOpen,
  initialMode = 'login',
  onClose,
  onAuthSuccess,
  externalError = '',
}) {
  const [mode, setMode] = useState(initialMode);
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [providers, setProviders] = useState({
    google: { configured: false, demo_enabled: false },
    apple: { configured: false, demo_enabled: false },
  });
  const [demoProvider, setDemoProvider] = useState(null); // 'google' | 'apple' | null
  const [demoEmail, setDemoEmail] = useState('');
  const [demoName, setDemoName] = useState('');

  useEffect(() => {
    if (!isOpen) return;
    setMode(initialMode);
    setError(externalError || '');
    setDemoProvider(null);
    fetchAuthProviders().then(setProviders);
  }, [isOpen, initialMode, externalError]);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (mode === 'register' && password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    setIsLoading(true);
    try {
      const authRes =
        mode === 'register'
          ? await registerAccount({ full_name: fullName, email, password })
          : await loginAccount({ email, password });
      onAuthSuccess(authRes);
      onClose();
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSocialClick = (provider) => {
    setError('');
    const status = providers[provider];
    if (status?.configured) {
      window.location.href = getOAuthLoginUrl(provider);
      return;
    }
    if (status?.demo_enabled) {
      setDemoProvider(provider);
      setDemoEmail(provider === 'google' ? 'alex.mercer@gmail.com' : 'alex.mercer@icloud.com');
      setDemoName('Alex Mercer');
      return;
    }
    const envVar = provider === 'google' ? 'GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET' : 'APPLE_CLIENT_ID';
    setError(
      `${provider === 'google' ? 'Google' : 'Apple'} sign-in is not configured yet. Set ${envVar} (or OAUTH_ALLOW_DEMO_LOGIN=true for local preview) in .env.`
    );
  };

  const handleDemoSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      const authRes = await demoOAuthLogin({
        provider: demoProvider,
        email: demoEmail,
        full_name: demoName,
      });
      onAuthSuccess(authRes);
      onClose();
    } catch (err) {
      setError(err.message || 'Social sign-in failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 sm:p-8 shadow-2xl relative">
        <button
          onClick={onClose}
          aria-label="Close authentication modal"
          className="absolute top-5 right-5 text-slate-400 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {demoProvider ? (
          <div>
            <div className="flex items-center space-x-3 mb-5">
              <div className="p-2.5 rounded-xl bg-slate-800 border border-slate-700">
                {demoProvider === 'google' ? <GoogleLogo /> : <AppleLogo />}
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">
                  Continue with {demoProvider === 'google' ? 'Google' : 'Apple'}
                </h3>
                <p className="text-xs text-slate-400">Local OAuth preview (backed by MySQL account)</p>
              </div>
            </div>

            <div className="mb-4 p-3 rounded-xl bg-indigo-950/50 border border-indigo-700/40 text-indigo-200 text-xs flex items-start gap-2">
              <Sparkles className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
              <span>
                Running in dev preview mode. Add live{' '}
                <code className="text-indigo-300">
                  {demoProvider === 'google' ? 'GOOGLE_CLIENT_ID' : 'APPLE_CLIENT_ID'}
                </code>{' '}
                credentials in <code className="text-indigo-300">.env</code> to use real OAuth redirects.
              </span>
            </div>

            {error && (
              <div className="mb-4 p-3 rounded-xl bg-rose-950/70 border border-rose-600/60 text-rose-300 text-xs">
                {error}
              </div>
            )}

            <form onSubmit={handleDemoSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Name</label>
                <input
                  type="text"
                  required
                  value={demoName}
                  onChange={(e) => setDemoName(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  {demoProvider === 'google' ? 'Google' : 'Apple ID'} Email
                </label>
                <input
                  type="email"
                  required
                  value={demoEmail}
                  onChange={(e) => setDemoEmail(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setDemoProvider(null);
                    setError('');
                  }}
                  className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium transition-colors"
                >
                  Back
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition-all disabled:opacity-50"
                >
                  {isLoading
                    ? 'Signing in...'
                    : `Continue as ${demoName.split(' ')[0] || 'User'}`}
                </button>
              </div>
            </form>
          </div>
        ) : (
          <div>
            {/* Mode Tabs */}
            <div className="grid grid-cols-2 gap-1 p-1 rounded-xl bg-slate-950 border border-slate-800 mb-6 mt-1">
              <button
                type="button"
                onClick={() => {
                  setMode('login');
                  setError('');
                }}
                className={`py-2 rounded-lg text-xs font-semibold transition-all ${
                  mode === 'login'
                    ? 'bg-indigo-600 text-white shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => {
                  setMode('register');
                  setError('');
                }}
                className={`py-2 rounded-lg text-xs font-semibold transition-all ${
                  mode === 'register'
                    ? 'bg-indigo-600 text-white shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Create Account
              </button>
            </div>

            <div className="mb-5">
              <h3 className="text-xl font-bold text-white">
                {mode === 'login' ? 'Welcome back' : 'Create your account'}
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                {mode === 'login'
                  ? 'Sign in to sync your tickets and speed through checkout.'
                  : 'Save your reservations and digital tickets across sessions.'}
              </p>
            </div>

            {error && (
              <div className="mb-4 p-3 rounded-xl bg-rose-950/70 border border-rose-600/60 text-rose-300 text-xs">
                {error}
              </div>
            )}

            {/* Social Login Buttons */}
            <div className="space-y-2.5 mb-5">
              <button
                type="button"
                onClick={() => handleSocialClick('google')}
                className="w-full py-2.5 px-4 rounded-xl bg-white hover:bg-slate-100 text-slate-900 font-semibold text-sm transition-all flex items-center justify-center gap-2.5 shadow-sm"
              >
                <GoogleLogo />
                <span>Continue with Google</span>
              </button>

              <button
                type="button"
                onClick={() => handleSocialClick('apple')}
                className="w-full py-2.5 px-4 rounded-xl bg-black hover:bg-slate-950 border border-slate-700 text-white font-semibold text-sm transition-all flex items-center justify-center gap-2.5"
              >
                <AppleLogo />
                <span>Continue with Apple</span>
              </button>
            </div>

            <div className="relative my-5">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-800" />
              </div>
              <div className="relative flex justify-center text-[11px] uppercase tracking-wider">
                <span className="bg-slate-900 px-3 text-slate-500 font-medium">
                  or continue with email
                </span>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {mode === 'register' && (
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">Full Name</label>
                  <div className="relative">
                    <User className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      required
                      minLength={2}
                      placeholder="Alex Mercer"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      className="w-full pl-10 pr-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                </div>
              )}

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
                    className="w-full pl-10 pr-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
                    minLength={mode === 'register' ? 8 : 1}
                    placeholder={mode === 'register' ? 'At least 8 characters' : 'Enter your password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full pl-10 pr-10 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
                className="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-semibold text-sm transition-all shadow-lg shadow-indigo-600/25 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <span>
                  {isLoading
                    ? mode === 'login'
                      ? 'Signing in...'
                      : 'Creating account...'
                    : mode === 'login'
                      ? 'Sign In'
                      : 'Create Account'}
                </span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}

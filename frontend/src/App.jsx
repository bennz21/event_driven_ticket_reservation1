import React, { useCallback, useEffect, useState } from 'react';
import Navbar from './components/Navbar';
import HomeScreen from './components/HomeScreen';
import SignupPage from './components/SignupPage';
import LoginPage from './components/LoginPage';
import AdminDashboard from './components/AdminDashboard';
import OrganizerDashboard from './components/OrganizerDashboard';
import PublicDashboard from './components/PublicDashboard';
import ChatWidget from './components/ChatWidget';
import { fetchCurrentSession, logoutSession } from './api/client';

function roleHomePath(role) {
  if (role === 'admin') return '/admin';
  if (role === 'organizer') return '/organizer';
  return '/public';
}

export default function App() {
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [currentPath, setCurrentPath] = useState(() => window.location.pathname || '/');
  const [oauthError, setOauthError] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('oauth_error') || '';
  });

  const navigate = useCallback((path) => {
    if (window.location.pathname !== path) {
      window.history.pushState({}, '', path);
    }
    setOauthError('');
    setCurrentPath(path);
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.has('oauth_error')) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }
    const onPopState = () => setCurrentPath(window.location.pathname || '/');
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  useEffect(() => {
    fetchCurrentSession()
      .then((actor) => {
        if (actor) {
          setUser(actor);
        }
      })
      .finally(() => setAuthChecked(true));
  }, []);

  const handleAuthSuccess = (authenticatedUser) => {
    setUser(authenticatedUser);
    navigate(roleHomePath(authenticatedUser.role));
  };

  const handleLogout = async () => {
    await logoutSession();
    setUser(null);
    navigate('/');
  };

  const renderPage = () => {
    if (!authChecked) {
      return (
        <div className="flex-1 flex items-center justify-center py-20 text-sm text-slate-400">
          Loading session...
        </div>
      );
    }

    if (currentPath === '/') {
      return <HomeScreen user={user} onNavigate={navigate} />;
    }

    if (currentPath === '/signup') {
      if (user) return <HomeScreen user={user} onNavigate={navigate} />;
      return <SignupPage onAuthSuccess={handleAuthSuccess} onNavigate={navigate} />;
    }

    if (currentPath === '/login/admin') {
      if (user) {
        return user.role === 'admin' ? <AdminDashboard /> : <HomeScreen user={user} onNavigate={navigate} />;
      }
      return <LoginPage role="admin" externalError={oauthError} onAuthSuccess={handleAuthSuccess} onNavigate={navigate} />;
    }

    if (currentPath === '/login/organizer') {
      if (user) {
        return user.role === 'organizer' ? <OrganizerDashboard /> : <HomeScreen user={user} onNavigate={navigate} />;
      }
      return <LoginPage role="organizer" externalError={oauthError} onAuthSuccess={handleAuthSuccess} onNavigate={navigate} />;
    }

    if (currentPath === '/login/public') {
      if (user) {
        return user.role === 'public' ? <PublicDashboard user={user} /> : <HomeScreen user={user} onNavigate={navigate} />;
      }
      return <LoginPage role="public" externalError={oauthError} onAuthSuccess={handleAuthSuccess} onNavigate={navigate} />;
    }

    if (currentPath === '/admin') {
      if (!user) return <LoginPage role="admin" onAuthSuccess={handleAuthSuccess} onNavigate={navigate} />;
      if (user.role !== 'admin') return <HomeScreen user={user} onNavigate={navigate} />;
      return <AdminDashboard />;
    }

    if (currentPath === '/organizer') {
      if (!user) return <LoginPage role="organizer" onAuthSuccess={handleAuthSuccess} onNavigate={navigate} />;
      if (user.role !== 'organizer') return <HomeScreen user={user} onNavigate={navigate} />;
      return <OrganizerDashboard />;
    }

    if (currentPath === '/public') {
      if (!user) return <LoginPage role="public" onAuthSuccess={handleAuthSuccess} onNavigate={navigate} />;
      if (user.role !== 'public') return <HomeScreen user={user} onNavigate={navigate} />;
      return <PublicDashboard user={user} />;
    }

    return <HomeScreen user={user} onNavigate={navigate} />;
  };

  return (
    <div className="min-h-screen bg-[#050a18] text-slate-100 flex flex-col">
      <Navbar
        user={user}
        currentPath={currentPath}
        onNavigate={navigate}
        onLogout={handleLogout}
      />
      <main className="flex-1">{renderPage()}</main>
      <ChatWidget />
    </div>
  );
}

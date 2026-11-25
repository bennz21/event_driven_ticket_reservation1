import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Navbar';
import SeatMap from './components/SeatMap';
import HoldTimer from './components/HoldTimer';
import CheckoutModal from './components/CheckoutModal';
import ActivityFeed from './components/ActivityFeed';
import AuthModal from './components/AuthModal';
import MyTicketsModal from './components/MyTicketsModal';
import HomeScreen from './components/HomeScreen';
import {
  getSessionId,
  fetchEvents,
  fetchSeats,
  holdSeats,
  releaseSeats,
  confirmReservation,
  fetchCurrentUser,
  setStoredToken,
  logoutAccount,
  exchangeOAuthCode,
} from './api/client';
import { useEventWebSocket } from './hooks/useEventWebSocket';
import { Calendar, MapPin, DollarSign, Sparkles } from 'lucide-react';

export default function App() {
  const [sessionId, setSessionId] = useState(getSessionId());
  const [events, setEvents] = useState([]);
  const [selectedEventId, setSelectedEventId] = useState(null);
  const [seats, setSeats] = useState([]);
  const [isHolding, setIsHolding] = useState(false);
  const [holdExpiration, setHoldExpiration] = useState(null);
  const [isCheckoutOpen, setIsCheckoutOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [completedReservation, setCompletedReservation] = useState(null);
  const [user, setUser] = useState(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState('login');
  const [oauthBannerError, setOauthBannerError] = useState('');
  const [isMyTicketsOpen, setIsMyTicketsOpen] = useState(false);
  const [activeView, setActiveView] = useState('home');

  // Real-time WebSocket hook
  const { isConnected, lastMessage, eventFeed } = useEventWebSocket(selectedEventId);

  // Restore authenticated user or complete OAuth redirect callback
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const oauthCode = params.get('oauth_code');
    const oauthError = params.get('oauth_error');

    if (oauthCode || oauthError) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    if (oauthCode) {
      exchangeOAuthCode(oauthCode)
        .then((res) => {
          setStoredToken(res.access_token);
          setUser(res.user);
          setActiveView('workspace');
        })
        .catch((err) => {
          setOauthBannerError(err.message || 'Social sign-in failed');
          setAuthModalMode('login');
          setIsAuthModalOpen(true);
        });
      return;
    }

    if (oauthError) {
      setOauthBannerError(oauthError);
      setAuthModalMode('login');
      setIsAuthModalOpen(true);
    }

    fetchCurrentUser().then((u) => {
      if (u) {
        setUser(u);
      }
    });
  }, []);

  // Load initial events
  useEffect(() => {
    async function loadEvents() {
      try {
        const data = await fetchEvents();
        setEvents(data);
        if (data.length > 0) {
          setSelectedEventId(data[0].id);
        }
      } catch (err) {
        console.error('Failed to load events:', err);
      }
    }
    loadEvents();
  }, []);

  // Fetch seats whenever selectedEventId changes
  const loadSeats = useCallback(async () => {
    if (!selectedEventId) return;
    try {
      const data = await fetchSeats(selectedEventId);
      setSeats(data);
      // Determine if there are already held seats for this session
      const myHeldSeats = data.filter(
        (s) => s.status === 'held' && s.held_by_session_id === sessionId
      );
      if (myHeldSeats.length > 0 && myHeldSeats[0].held_until) {
        setHoldExpiration(myHeldSeats[0].held_until);
      } else {
        setHoldExpiration(null);
      }
    } catch (err) {
      console.error('Failed to load seats:', err);
    }
  }, [selectedEventId, sessionId]);

  useEffect(() => {
    loadSeats();
  }, [loadSeats]);

  // Handle incoming WebSocket messages to update seats incrementally
  useEffect(() => {
    if (!lastMessage || lastMessage.event_id !== selectedEventId) return;

    if (lastMessage.type === 'seat.held') {
      const { seat_ids, session_id: lockSessionId, held_until } = lastMessage.payload;
      setSeats((prev) =>
        prev.map((s) => {
          if (seat_ids.includes(s.id)) {
            return {
              ...s,
              status: 'held',
              held_by_session_id: lockSessionId,
              held_until,
            };
          }
          return s;
        })
      );
      if (lockSessionId === sessionId) {
        setHoldExpiration(held_until);
      }
    } else if (lastMessage.type === 'seat.released') {
      const { seat_ids } = lastMessage.payload;
      setSeats((prev) =>
        prev.map((s) => {
          if (seat_ids.includes(s.id)) {
            return {
              ...s,
              status: 'available',
              held_by_session_id: null,
              held_until: null,
            };
          }
          return s;
        })
      );
    } else if (lastMessage.type === 'reservation.confirmed') {
      const { seat_ids } = lastMessage.payload;
      setSeats((prev) =>
        prev.map((s) => {
          if (seat_ids.includes(s.id)) {
            return {
              ...s,
              status: 'reserved',
              held_by_session_id: null,
              held_until: null,
            };
          }
          return s;
        })
      );
    }
  }, [lastMessage, selectedEventId, sessionId]);

  // Switch/Reset user session
  const handleResetSession = () => {
    const newSession = `user_${Math.random().toString(36).substring(2, 9)}`;
    sessionStorage.setItem('ticket_app_session_id', newSession);
    setSessionId(newSession);
    setHoldExpiration(null);
    setCompletedReservation(null);
  };

  // Toggle seat hold / release
  const handleToggleSeat = async (seat) => {
    if (isHolding) return;
    setIsHolding(true);
    try {
      const isAlreadyHeldByMe = seat.status === 'held' && seat.held_by_session_id === sessionId;

      if (isAlreadyHeldByMe) {
        // Release seat
        await releaseSeats(selectedEventId, [seat.id], sessionId);
        setSeats((prev) =>
          prev.map((s) =>
            s.id === seat.id
              ? { ...s, status: 'available', held_by_session_id: null, held_until: null }
              : s
          )
        );
      } else {
        // Hold seat
        const result = await holdSeats(selectedEventId, [seat.id], sessionId);
        if (result.success) {
          setHoldExpiration(result.held_until);
          setSeats((prev) =>
            prev.map((s) =>
              s.id === seat.id
                ? {
                    ...s,
                    status: 'held',
                    held_by_session_id: sessionId,
                    held_until: result.held_until,
                  }
                : s
            )
          );
        } else {
          alert(result.message);
          loadSeats(); // Refresh if conflicted
        }
      }
    } catch (err) {
      alert(err.message || 'Error updating seat hold');
      loadSeats();
    } finally {
      setIsHolding(false);
    }
  };

  // Seats currently held by this session
  const myHeldSeats = seats.filter(
    (s) => s.status === 'held' && s.held_by_session_id === sessionId
  );

  const currentEvent = events.find((e) => e.id === selectedEventId) || events[0];

  const handleConfirmReservation = async ({ name, email }) => {
    setIsSubmitting(true);
    try {
      const result = await confirmReservation(selectedEventId, {
        seat_ids: myHeldSeats.map((s) => s.id),
        session_id: sessionId,
        customer_name: name,
        customer_email: email,
      });
      setCompletedReservation(result);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAuthSuccess = (authResponse) => {
    setStoredToken(authResponse.access_token);
    setUser(authResponse.user);
    setOauthBannerError('');
    setActiveView('workspace');
  };

  const handleLogout = async () => {
    await logoutAccount();
    setUser(null);
    setActiveView('home');
  };

  const openAuthModal = (mode) => {
    setOauthBannerError('');
    setAuthModalMode(mode);
    setIsAuthModalOpen(true);
  };

  const availableSeatsCount = seats.filter((s) => s.status === 'available').length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar
        isConnected={isConnected}
        sessionId={sessionId}
        onResetSession={handleResetSession}
        user={user}
        onOpenAuth={openAuthModal}
        onOpenMyTickets={() => setIsMyTicketsOpen(true)}
        onLogout={handleLogout}
        activeView={activeView}
        onNavigate={setActiveView}
      />

      {activeView === 'home' ? (
        <main className="flex-1">
          <HomeScreen
            featuredEvent={currentEvent}
            availableSeatsCount={availableSeatsCount}
            totalSeatsCount={seats.length}
            user={user}
            onOpenAuth={openAuthModal}
            onEnterWorkspace={() => setActiveView('workspace')}
          />
        </main>
      ) : (
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Event Header Banner */}
        {currentEvent && (
          <div className="relative overflow-hidden bg-gradient-to-r from-indigo-900/40 via-purple-900/20 to-slate-900/60 border border-indigo-900/40 rounded-2xl p-6 sm:p-8 backdrop-blur-md">
            <div className="relative z-10 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
              <div className="space-y-2">
                <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Featured Live Event</span>
                </div>
                <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                  {currentEvent.title}
                </h1>
                <p className="text-sm text-slate-300 max-w-2xl leading-relaxed">
                  {currentEvent.description}
                </p>

                <div className="flex flex-wrap items-center gap-4 pt-2 text-xs text-slate-400 font-medium">
                  <div className="flex items-center space-x-1.5">
                    <MapPin className="w-4 h-4 text-indigo-400" />
                    <span>{currentEvent.venue_name}</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <Calendar className="w-4 h-4 text-indigo-400" />
                    <span>{new Date(currentEvent.event_date).toLocaleDateString()}</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <DollarSign className="w-4 h-4 text-emerald-400" />
                    <span>From ${currentEvent.base_price.toFixed(2)}</span>
                  </div>
                </div>
              </div>

              {/* Hold Timer / Checkout Action Panel */}
              <div className="flex flex-col sm:flex-row items-center gap-4 self-start lg:self-center">
                {myHeldSeats.length > 0 && (
                  <HoldTimer
                    heldUntil={holdExpiration}
                    onExpired={() => {
                      loadSeats();
                      setHoldExpiration(null);
                    }}
                  />
                )}

                <button
                  disabled={myHeldSeats.length === 0}
                  onClick={() => setIsCheckoutOpen(true)}
                  className="w-full sm:w-auto px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-sm transition-all shadow-lg shadow-emerald-600/20 flex items-center justify-center space-x-2"
                >
                  <span>Checkout {myHeldSeats.length > 0 ? `(${myHeldSeats.length} Seats)` : ''}</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Main Content Grid: Seat Map + Live Event Stream */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <SeatMap
              seats={seats}
              sessionId={sessionId}
              onToggleSeat={handleToggleSeat}
              isHolding={isHolding}
            />
          </div>

          <div className="lg:col-span-1">
            <ActivityFeed feed={eventFeed} />
          </div>
        </div>
      </main>
      )}

      {/* Checkout Modal */}
      <CheckoutModal
        isOpen={isCheckoutOpen}
        onClose={() => {
          setIsCheckoutOpen(false);
          if (completedReservation) {
            setCompletedReservation(null);
            loadSeats();
          }
        }}
        selectedSeats={myHeldSeats}
        onConfirm={handleConfirmReservation}
        isSubmitting={isSubmitting}
        completedReservation={completedReservation}
        user={user}
      />

      {/* Auth Modal (Email, Google, Apple) */}
      <AuthModal
        isOpen={isAuthModalOpen}
        initialMode={authModalMode}
        onClose={() => {
          setIsAuthModalOpen(false);
          setOauthBannerError('');
        }}
        onAuthSuccess={handleAuthSuccess}
        externalError={oauthBannerError}
      />

      {/* User's Confirmed Tickets */}
      <MyTicketsModal
        isOpen={isMyTicketsOpen}
        onClose={() => setIsMyTicketsOpen(false)}
        user={user}
      />
    </div>
  );
}

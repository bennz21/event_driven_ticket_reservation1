import { useState, useRef, useCallback } from 'react';

const API_BASE = '/api/v1';

/**
 * useChatbot
 * Manages chat messages, session state, and the fetch call to the backend.
 */
export function useChatbot() {
  const [messages, setMessages] = useState([
    {
      role: 'bot',
      text: "👋 Hi! I'm your ticket assistant. Ask me about events, seats, pricing, or how to book. I can also take voice input!",
    },
  ]);
  const [loading, setLoading] = useState(false);
  const sessionIdRef = useRef(null);

  const sendMessage = useCallback(async (text) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    // Optimistic UI: add user message immediately
    setMessages((prev) => [...prev, { role: 'user', text: trimmed }]);
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/chatbot/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionIdRef.current,
          message: trimmed,
        }),
      });

      if (!res.ok) {
        throw new Error(`Server error ${res.status}`);
      }

      const data = await res.json();
      sessionIdRef.current = data.session_id;

      setMessages((prev) => [...prev, { role: 'bot', text: data.reply }]);
      return data.reply;   // returned so voice hook can speak it
    } catch (err) {
      const errMsg = '⚠️ Could not reach the assistant. Please try again.';
      setMessages((prev) => [...prev, { role: 'bot', text: errMsg }]);
    } finally {
      setLoading(false);
    }
  }, [loading]);

  const clearChat = useCallback(async () => {
    if (sessionIdRef.current) {
      await fetch(`${API_BASE}/chatbot/session/${sessionIdRef.current}`, {
        method: 'DELETE',
      }).catch(() => {});
      sessionIdRef.current = null;
    }
    setMessages([
      {
        role: 'bot',
        text: "Chat cleared! How can I help you?",
      },
    ]);
  }, []);

  return { messages, loading, sendMessage, clearChat };
}

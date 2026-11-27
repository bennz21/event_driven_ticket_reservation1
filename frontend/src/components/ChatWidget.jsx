import { useState, useRef, useEffect, useCallback } from 'react';
import {
  MessageCircle,
  X,
  Mic,
  MicOff,
  Send,
  Volume2,
  VolumeX,
  Trash2,
  Bot,
  User,
} from 'lucide-react';
import { useChatbot } from '../hooks/useChatbot';
import { useVoice } from '../hooks/useVoice';

/**
 * ChatWidget
 * A floating, animated chat panel that sits in the bottom-right corner.
 * Supports both text and voice input, with TTS for bot replies.
 */
export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [ttsEnabled, setTtsEnabled] = useState(false);   // user can toggle TTS on/off
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  const { messages, loading, sendMessage, clearChat } = useChatbot();

  // When a voice transcript arrives, send it as a chat message
  const handleTranscript = useCallback(
    async (transcript) => {
      setInput('');
      const reply = await sendMessage(transcript);
      if (ttsEnabled && reply) speak(reply);
    },
    [sendMessage, ttsEnabled]
  );

  const { listening, speaking, supported, startListening, stopListening, speak, stopSpeaking } =
    useVoice({ onTranscript: handleTranscript });

  // Send typed message
  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput('');
    const reply = await sendMessage(text);
    if (ttsEnabled && reply) speak(reply);
  }, [input, loading, sendMessage, ttsEnabled, speak]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, open]);

  // Focus input when panel opens
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 100);
  }, [open]);

  return (
    <>
      {/* ── Floating toggle button ─────────────────────────────────────── */}
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label={open ? 'Close chat' : 'Open chat assistant'}
        className={`
          fixed bottom-6 right-6 z-50
          w-14 h-14 rounded-full shadow-2xl
          flex items-center justify-center
          transition-all duration-300
          ${open
            ? 'bg-[#0e1b36] border border-[#22355a] hover:bg-[#15284e]'
            : 'bg-[#1a73e8] hover:bg-[#2b84f8] shadow-[0_0_24px_rgba(26,115,232,0.5)] animate-cta-glow'}
        `}
      >
        {open ? (
          <X size={22} className="text-white" />
        ) : (
          <MessageCircle size={22} className="text-white" />
        )}
      </button>

      {/* ── Chat panel ─────────────────────────────────────────────────── */}
      {open && (
        <div
          className="
            fixed bottom-24 right-6 z-50
            w-80 sm:w-96
            h-[520px]
            flex flex-col
            rounded-2xl shadow-2xl
            bg-[#091224] border border-[#192848]
            overflow-hidden
            animate-modal-pop
          "
        >
          {/* Header */}
          <div className="keep-white flex items-center justify-between px-4 py-3 bg-[#124596] border-b border-[#1f3b73]">
            <div className="flex items-center gap-2">
              <Bot size={18} className="text-white" />
              <span className="text-sm font-semibold text-white">Ticket Assistant</span>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" title="Online" />
            </div>
            <div className="flex items-center gap-2">
              {/* TTS toggle */}
              <button
                onClick={() => {
                  setTtsEnabled((v) => !v);
                  if (speaking) stopSpeaking();
                }}
                className="text-sky-200 hover:text-white transition-colors"
                title={ttsEnabled ? 'Mute voice replies' : 'Enable voice replies'}
              >
                {ttsEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
              </button>
              {/* Clear chat */}
              <button
                onClick={clearChat}
                className="text-sky-200 hover:text-white transition-colors"
                title="Clear conversation"
              >
                <Trash2 size={15} />
              </button>
              {/* Close */}
              <button
                onClick={() => setOpen(false)}
                className="text-sky-200 hover:text-white transition-colors"
                title="Close"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3 text-sm">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
              >
                {/* Avatar */}
                <div
                  className={`
                    flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs
                    ${msg.role === 'user'
                      ? 'bg-[#1a73e8] text-white'
                      : 'bg-[#0e1b36] border border-[#1f3b73] text-[#60b5ff]'}
                  `}
                >
                  {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
                </div>

                {/* Bubble */}
                <div
                  className={`
                    max-w-[78%] px-3 py-2 rounded-2xl leading-relaxed whitespace-pre-wrap
                    ${msg.role === 'user'
                      ? 'bg-[#1a73e8] text-white rounded-tr-sm'
                      : 'bg-[#060d1c] border border-[#172542] text-slate-100 rounded-tl-sm'}
                  `}
                >
                  {msg.text}
                </div>
              </div>
            ))}

            {/* Typing indicator */}
            {loading && (
              <div className="flex gap-2 items-center">
                <div className="w-7 h-7 rounded-full bg-[#0e1b36] border border-[#1f3b73] flex items-center justify-center">
                  <Bot size={14} className="text-[#60b5ff]" />
                </div>
                <div className="bg-[#060d1c] border border-[#172542] px-4 py-2 rounded-2xl rounded-tl-sm flex gap-1 items-center">
                  <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:0ms]" />
                  <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:150ms]" />
                  <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:300ms]" />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Voice status banner */}
          {listening && (
            <div className="px-4 py-1.5 bg-red-900/60 border-t border-red-800 text-xs text-red-300 flex items-center gap-2 animate-pulse">
              <Mic size={12} />
              Listening… speak now
            </div>
          )}
          {speaking && (
            <div className="px-4 py-1.5 bg-[#0d1c3b] border-t border-[#1f3b73] text-xs text-[#60b5ff] flex items-center gap-2">
              <Volume2 size={12} />
              Speaking…
            </div>
          )}

          {/* Input area */}
          <div className="px-3 py-3 border-t border-[#172542] flex gap-2 items-end">
            <textarea
              ref={inputRef}
              rows={1}
              className="
                flex-1 resize-none text-sm
                bg-[#060d1c] border border-[#1b2b4d]
                text-slate-100 placeholder-slate-500
                rounded-xl px-3 py-2 outline-none
                focus:ring-2 focus:ring-[#2684ff]
                max-h-28 overflow-y-auto
              "
              placeholder="Ask about events, seats…"
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                // Auto-grow
                e.target.style.height = 'auto';
                e.target.style.height = `${e.target.scrollHeight}px`;
              }}
              onKeyDown={handleKeyDown}
            />

            {/* Mic button — hidden when not supported */}
            {supported && (
              <button
                onClick={listening ? stopListening : startListening}
                disabled={loading}
                title={listening ? 'Stop recording' : 'Voice input'}
                className={`
                  p-2 rounded-xl transition-all flex-shrink-0
                  ${listening
                    ? 'bg-red-600 text-white ring-2 ring-red-400 animate-pulse'
                    : 'bg-[#0e1b36] border border-[#22355a] text-slate-300 hover:bg-[#15284e]'}
                  disabled:opacity-40
                `}
              >
                {listening ? <MicOff size={17} /> : <Mic size={17} />}
              </button>
            )}

            {/* Send button */}
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              title="Send message"
              className="
                p-2 rounded-xl flex-shrink-0
                bg-[#1a73e8] hover:bg-[#2b84f8]
                text-white transition-colors
                disabled:opacity-40 disabled:cursor-not-allowed
              "
            >
              <Send size={17} />
            </button>
          </div>

          {/* Hint footer */}
          {!supported && (
            <p className="text-center text-xs text-slate-600 pb-2 px-4">
              Voice input requires Chrome or Edge
            </p>
          )}
        </div>
      )}
    </>
  );
}

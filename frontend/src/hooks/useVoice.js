import { useRef, useState, useCallback } from 'react';

/**
 * useVoice
 * Wraps the browser's Web Speech API for:
 *   - Speech-to-Text  (startListening / stopListening)
 *   - Text-to-Speech  (speak / stopSpeaking)
 *
 * Both are no-ops when the browser doesn't support the API.
 *
 * @param {object} opts
 * @param {(transcript: string) => void} opts.onTranscript  called with final STT text
 */
export function useVoice({ onTranscript }) {
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [supported, setSupported] = useState(() => {
    return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
  });
  const recognitionRef = useRef(null);

  // ── Speech-to-Text ────────────────────────────────────────────────────────
  const startListening = useCallback(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setSupported(false);
      alert('Voice input is not supported in your browser. Please use Chrome or Edge.');
      return;
    }

    // Stop any ongoing recognition before starting a new one
    recognitionRef.current?.abort();

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.continuous = false;

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      if (transcript) {
        onTranscript(transcript);
      }
    };

    recognition.onend = () => setListening(false);

    recognition.onerror = (event) => {
      console.warn('Speech recognition error:', event.error);
      setListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  }, [onTranscript]);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    setListening(false);
  }, []);

  // ── Text-to-Speech ────────────────────────────────────────────────────────
  const speak = useCallback((text) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();   // stop anything already playing

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-US';
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);

    window.speechSynthesis.speak(utterance);
  }, []);

  const stopSpeaking = useCallback(() => {
    window.speechSynthesis?.cancel();
    setSpeaking(false);
  }, []);

  return {
    listening,
    speaking,
    supported,
    startListening,
    stopListening,
    speak,
    stopSpeaking,
  };
}

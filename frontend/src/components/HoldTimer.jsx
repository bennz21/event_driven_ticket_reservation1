import React, { useState, useEffect } from 'react';
import { Timer, AlertTriangle } from 'lucide-react';

export default function HoldTimer({ heldUntil, onExpired }) {
  const [secondsLeft, setSecondsLeft] = useState(0);

  useEffect(() => {
    if (!heldUntil) {
      setSecondsLeft(0);
      return;
    }

    const target = new Date(heldUntil).getTime();

    const updateTimer = () => {
      const now = new Date().getTime();
      const diff = Math.max(0, Math.floor((target - now) / 1000));
      setSecondsLeft(diff);

      if (diff === 0 && onExpired) {
        onExpired();
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);

    return () => clearInterval(interval);
  }, [heldUntil, onExpired]);

  if (secondsLeft <= 0) return null;

  const minutes = Math.floor(secondsLeft / 60);
  const remainingSeconds = secondsLeft % 60;
  const isUrgent = secondsLeft < 60;

  return (
    <div
      className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg border text-xs font-mono transition-all ${
        isUrgent
          ? 'bg-rose-950/80 border-rose-500 text-rose-300 animate-pulse'
          : 'bg-amber-950/50 border-amber-500/60 text-amber-300'
      }`}
    >
      {isUrgent ? <AlertTriangle className="w-4 h-4 text-rose-400" /> : <Timer className="w-4 h-4 text-amber-400" />}
      <span>
        Hold expires in:{' '}
        <strong className="font-bold">
          {String(minutes).padStart(2, '0')}:{String(remainingSeconds).padStart(2, '0')}
        </strong>
      </span>
    </div>
  );
}

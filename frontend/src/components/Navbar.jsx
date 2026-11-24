import React from 'react';
import { Ticket, Radio, User, RotateCcw } from 'lucide-react';

export default function Navbar({ isConnected, sessionId, onResetSession }) {
  return (
    <header className="border-b border-slate-800 bg-slate-900/70 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-emerald-400 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Ticket className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="font-bold text-lg text-white tracking-tight flex items-center gap-2">
              SeatStream
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                Event-Driven
              </span>
            </span>
            <p className="text-xs text-slate-400 hidden sm:block">
              Real-Time Concurrency & Ticket Reservation System
            </p>
          </div>
        </div>

        {/* Right side status indicators */}
        <div className="flex items-center space-x-3 sm:space-x-4">
          {/* Live WS connection status */}
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-slate-800/80 border border-slate-700/60 text-xs">
            <span className={`h-2.5 w-2.5 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
            <span className="font-medium text-slate-300 hidden md:inline">
              {isConnected ? 'Real-Time Sync' : 'Connecting WS...'}
            </span>
          </div>

          {/* Session ID Pill */}
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-indigo-950/60 border border-indigo-800/50 text-xs text-indigo-300">
            <User className="w-3.5 h-3.5 text-indigo-400" />
            <span className="font-mono">{sessionId}</span>
            <button
              onClick={onResetSession}
              title="Switch user session (simulates another buyer)"
              className="p-1 hover:bg-indigo-900/60 rounded transition-colors text-indigo-400 hover:text-white"
            >
              <RotateCcw className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}

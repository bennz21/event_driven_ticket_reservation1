import React from 'react';
import { Lock, Check } from 'lucide-react';

export default function SeatMap({ seats, sessionId, onToggleSeat, isHolding }) {
  // Group seats by row
  const rows = ['A', 'B', 'C', 'D', 'E', 'F'];

  return (
    <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 sm:p-8 backdrop-blur-sm shadow-xl">
      {/* Stage Graphic */}
      <div className="mb-12 text-center">
        <div className="w-full max-w-xl mx-auto h-12 bg-gradient-to-b from-indigo-500/20 to-transparent border-t-2 border-indigo-400/80 rounded-t-[80px] flex items-center justify-center shadow-lg shadow-indigo-500/10">
          <span className="text-xs uppercase tracking-[0.3em] font-semibold text-indigo-300 font-mono">
            STAGE / SCREEN
          </span>
        </div>
      </div>

      {/* Seating Grid */}
      <div className="space-y-3 max-w-2xl mx-auto overflow-x-auto pb-4">
        {rows.map((rowLetter) => {
          const rowSeats = seats.filter((s) => s.row === rowLetter);
          return (
            <div key={rowLetter} className="flex items-center justify-center space-x-2">
              <span className="w-6 text-center text-xs font-mono font-bold text-slate-500">
                {rowLetter}
              </span>

              <div className="flex space-x-2">
                {rowSeats.map((seat) => {
                  const isReserved = seat.status === 'reserved';
                  const isHeldByMe = seat.status === 'held' && seat.held_by_session_id === sessionId;
                  const isHeldByOther = seat.status === 'held' && seat.held_by_session_id !== sessionId;
                  const isAvailable = seat.status === 'available';

                  let btnStyle = 'bg-slate-800/80 border-slate-700 text-slate-300 hover:border-emerald-400 hover:bg-emerald-950/30';
                  if (isReserved) {
                    btnStyle = 'bg-slate-950/80 border-slate-900 text-slate-700 cursor-not-allowed opacity-50';
                  } else if (isHeldByMe) {
                    btnStyle = 'bg-indigo-600 border-indigo-400 text-white shadow-lg shadow-indigo-500/30 scale-105 ring-2 ring-indigo-400';
                  } else if (isHeldByOther) {
                    btnStyle = 'bg-amber-950/60 border-amber-600/70 text-amber-400 cursor-not-allowed animate-pulse';
                  }

                  return (
                    <button
                      key={seat.id}
                      disabled={isReserved || isHeldByOther || isHolding}
                      onClick={() => onToggleSeat(seat)}
                      title={`Seat ${seat.row}${seat.seat_number} - ${seat.tier} - $${seat.price} (${seat.status})`}
                      className={`relative w-8 h-8 sm:w-10 sm:h-10 rounded-lg border text-xs font-mono font-medium flex items-center justify-center transition-all duration-200 select-none ${btnStyle}`}
                    >
                      {isReserved ? (
                        <Lock className="w-3.5 h-3.5 text-slate-700" />
                      ) : isHeldByMe ? (
                        <Check className="w-4 h-4 text-white" />
                      ) : isHeldByOther ? (
                        <Lock className="w-3.5 h-3.5 text-amber-400" />
                      ) : (
                        seat.seat_number
                      )}
                    </button>
                  );
                })}
              </div>

              <span className="w-6 text-center text-xs font-mono font-bold text-slate-500">
                {rowLetter}
              </span>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="mt-8 pt-6 border-t border-slate-800 flex flex-wrap items-center justify-center gap-6 text-xs text-slate-400">
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 rounded bg-slate-800 border border-slate-700" />
          <span>Available</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 rounded bg-indigo-600 border border-indigo-400 ring-2 ring-indigo-400/30" />
          <span className="text-indigo-300 font-medium">Selected by You</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 rounded bg-amber-950/80 border border-amber-500 text-amber-400 flex items-center justify-center text-[10px]">
            <Lock className="w-2.5 h-2.5" />
          </div>
          <span className="text-amber-400">Locked by Someone Else</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 rounded bg-slate-950 border border-slate-900 opacity-60" />
          <span>Reserved / Sold</span>
        </div>
      </div>
    </div>
  );
}

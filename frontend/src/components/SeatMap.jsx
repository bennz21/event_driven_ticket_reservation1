import React from 'react';
import { Lock, Check } from 'lucide-react';

export default function SeatMap({ seats, sessionId, onToggleSeat, isHolding }) {
  const rows = ['A', 'B', 'C', 'D', 'E', 'F'];

  return (
    <div className="bg-[#081021]/90 border border-[#172542] rounded-2xl p-6 sm:p-8 backdrop-blur-sm shadow-xl">
      {/* Stage Graphic */}
      <div className="mb-12 text-center">
        <div className="w-full max-w-xl mx-auto h-12 bg-gradient-to-b from-[#1a73e8]/25 to-transparent border-t-2 border-[#2684ff]/80 rounded-t-[80px] flex items-center justify-center shadow-[0_-4px_24px_rgba(38,132,255,0.18)]">
          <span className="text-xs uppercase tracking-[0.3em] font-semibold text-[#60a5fa] font-mono">
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

                  let btnStyle =
                    'bg-[#0c1730] border-[#1d3157] text-slate-300 hover:border-[#2684ff] hover:bg-[#12254a] hover:text-white';
                  if (isReserved) {
                    btnStyle = 'bg-[#050a18] border-[#111c33] text-slate-700 cursor-not-allowed opacity-50';
                  } else if (isHeldByMe) {
                    btnStyle =
                      'bg-[#1a73e8] border-[#60a5fa] text-white shadow-[0_0_16px_rgba(38,132,255,0.5)] scale-105 ring-2 ring-[#3898ff]/70';
                  } else if (isHeldByOther) {
                    btnStyle = 'bg-amber-950/60 border-amber-600/70 text-amber-400 cursor-not-allowed animate-pulse';
                  }

                  return (
                    <button
                      key={seat.id}
                      disabled={isReserved || isHeldByOther || isHolding}
                      onClick={() => onToggleSeat(seat)}
                      title={`Seat ${seat.row}${seat.seat_number} - ${seat.tier} - ₹${seat.price} (${seat.status})`}
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
      <div className="mt-8 pt-6 border-t border-[#14203b] flex flex-wrap items-center justify-center gap-6 text-xs text-slate-400">
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 rounded bg-[#0c1730] border border-[#1d3157]" />
          <span>Available</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 rounded bg-[#1a73e8] border border-[#60a5fa] ring-2 ring-[#3898ff]/30" />
          <span className="text-[#60a5fa] font-medium">Selected by You</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 rounded bg-amber-950/80 border border-amber-500 text-amber-400 flex items-center justify-center text-[10px]">
            <Lock className="w-2.5 h-2.5" />
          </div>
          <span className="text-amber-400">Locked by Someone Else</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 rounded bg-[#050a18] border border-[#111c33] opacity-60" />
          <span>Reserved / Sold</span>
        </div>
      </div>
    </div>
  );
}

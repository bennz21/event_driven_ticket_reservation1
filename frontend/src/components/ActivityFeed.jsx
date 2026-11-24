import React from 'react';
import { Activity, Radio, Lock, Unlock, CheckCircle } from 'lucide-react';

export default function ActivityFeed({ feed }) {
  const getIcon = (type) => {
    switch (type) {
      case 'seat.held':
        return <Lock className="w-3.5 h-3.5 text-amber-400" />;
      case 'seat.released':
        return <Unlock className="w-3.5 h-3.5 text-emerald-400" />;
      case 'reservation.confirmed':
        return <CheckCircle className="w-3.5 h-3.5 text-indigo-400" />;
      default:
        return <Radio className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  const getBadgeStyle = (type) => {
    switch (type) {
      case 'seat.held':
        return 'border-amber-900/40 bg-amber-950/20 text-amber-300';
      case 'seat.released':
        return 'border-emerald-900/40 bg-emerald-950/20 text-emerald-300';
      case 'reservation.confirmed':
        return 'border-indigo-900/40 bg-indigo-950/20 text-indigo-300';
      default:
        return 'border-slate-800 bg-slate-900 text-slate-300';
    }
  };

  return (
    <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-sm shadow-xl flex flex-col h-[520px]">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <Activity className="w-4 h-4 text-indigo-400" />
          <h3 className="font-semibold text-sm text-white">Live Event Stream</h3>
        </div>
        <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 animate-pulse">
          Subscribed
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2.5 pt-4 pr-1">
        {feed.length === 0 ? (
          <div className="text-center py-12 text-slate-600 text-xs">
            Awaiting live domain events...
          </div>
        ) : (
          feed.map((item) => (
            <div
              key={item.id}
              className={`p-3 rounded-xl border text-xs flex items-start space-x-3 transition-all ${getBadgeStyle(
                item.type
              )}`}
            >
              <div className="mt-0.5">{getIcon(item.type)}</div>
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-[10px] uppercase opacity-75 font-semibold">
                    {item.type}
                  </span>
                  <span className="text-[10px] font-mono text-slate-500">{item.timestamp}</span>
                </div>
                <p className="text-slate-200 text-xs leading-relaxed">{item.message}</p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

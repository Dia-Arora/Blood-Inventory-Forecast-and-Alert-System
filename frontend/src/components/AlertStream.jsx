import React, { useMemo, useState } from 'react';
import { Bell, CheckCircle2 } from 'lucide-react';

function buildEvents(simulateData, dayIndex) {
  const events = [];
  Object.entries(simulateData).forEach(([bloodType, series]) => {
    for (let i = 0; i <= dayIndex; i++) {
      const day = series[i];
      if (day.shortage_risk === 'CRITICAL') {
        events.push({
          id: `${bloodType}-shortage-${i}`, severity: 'critical', type: 'shortage', group: bloodType, day: i,
          message: `${bloodType} stock at CRITICAL coverage (${Math.round(day.stock)} units).`,
        });
      } else if (day.shortage_risk === 'WARNING') {
        events.push({
          id: `${bloodType}-shortage-${i}`, severity: 'warning', type: 'shortage', group: bloodType, day: i,
          message: `${bloodType} stock coverage running low (${Math.round(day.stock)} units).`,
        });
      }
      if (day.expired > 0) {
        events.push({
          id: `${bloodType}-wastage-${i}`, severity: day.wastage_risk === 'HIGH' ? 'critical' : 'warning', type: 'expiry', group: bloodType, day: i,
          message: `${Math.round(day.expired)} units of ${bloodType} expired unused.`,
        });
      }
    }
  });
  return events.sort((a, b) => b.day - a.day);
}

export default function AlertStream({ simulateData, dayIndex }) {
  const [filter, setFilter] = useState('ALL');
  const events = useMemo(() => buildEvents(simulateData, dayIndex), [simulateData, dayIndex]);
  const filtered = events.filter(e =>
    filter === 'ALL' ? true :
    filter === 'CRITICAL' ? e.severity === 'critical' :
    filter === 'WARNING' ? e.severity === 'warning' :
    e.type === 'expiry'
  );

  return (
    <div className="bg-white border border-gray-200 rounded-2xl p-5 h-[720px] flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <h2 className="font-outfit text-[16px] font-normal text-gray-900 flex items-center gap-2">
          <Bell className="w-4 h-4 text-rose-500" /> <span>Alert Stream</span>
        </h2>
        <span className="text-[11px] font-normal text-gray-400">Day {dayIndex + 1}</span>
      </div>
      <div className="flex gap-1.5 mb-4">
        {['ALL', 'CRITICAL', 'WARNING', 'EXPIRY'].map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`text-[11px] font-normal px-2.5 py-1 rounded-lg transition-all ${filter === f ? 'bg-gray-900 text-white shadow-2xs' : 'bg-gray-100 text-gray-500 hover:bg-gray-200/80'}`}>
            {f}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto space-y-2.5 custom-scrollbar">
        {filtered.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <CheckCircle2 className="w-8 h-8 mx-auto mb-2 opacity-40" />
            <p className="font-sans text-[13px]">No active alerts</p>
          </div>
        ) : filtered.map(e => (
          <div key={e.id} className={`p-3.5 rounded-xl border text-[13px] transition-all hover:shadow-2xs ${e.severity === 'critical' ? 'bg-rose-50/60 border-rose-200/80' : 'bg-amber-50/60 border-amber-200/80'}`}>
            <div className="flex justify-between items-start mb-1.5">
              <div className="flex gap-1.5">
                <span className={`px-2 py-0.5 rounded-md text-[9px] font-normal uppercase tracking-wider ${e.severity === 'critical' ? 'bg-rose-500 text-white' : 'bg-amber-500 text-white'}`}>{e.severity}</span>
                <span className="px-2 py-0.5 rounded-md text-[9px] font-normal bg-gray-800 text-white">{e.group}</span>
              </div>
              <span className="text-[10px] text-gray-400 font-outfit">Day {e.day + 1}</span>
            </div>
            <p className="font-sans text-gray-600 leading-relaxed text-[12.5px]">{e.message}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

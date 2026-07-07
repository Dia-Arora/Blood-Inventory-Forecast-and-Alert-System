import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { ChevronDown, AlertTriangle } from 'lucide-react';

const RISK_STYLES = {
  SAFE: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200/60', bar: 'bg-gradient-to-r from-emerald-400 to-emerald-500', label: 'Safe' },
  WARNING: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200/60', bar: 'bg-gradient-to-r from-amber-400 to-amber-500', label: 'Warning' },
  CRITICAL: { bg: 'bg-rose-50', text: 'text-rose-600', border: 'border-rose-200/60', bar: 'bg-gradient-to-r from-rose-400 to-rose-500', label: 'Critical' },
};

const WASTAGE_STYLES = {
  LOW: { text: 'text-gray-500', label: 'Low' },
  MED: { text: 'text-amber-700', label: 'Medium' },
  HIGH: { text: 'text-rose-600', label: 'High' },
};

export default function HealthBarCard({ bloodType, series, dayIndex }) {
  const [expanded, setExpanded] = useState(false);
  const today = series[dayIndex];
  const maxStock = Math.max(...series.map(d => d.stock), 1);
  const pct = Math.min(100, Math.max(2, (today.stock / maxStock) * 100));
  const st = RISK_STYLES[today.shortage_risk] || RISK_STYLES.SAFE;
  const wst = WASTAGE_STYLES[today.wastage_risk] || WASTAGE_STYLES.LOW;
  const isCritical = today.shortage_risk === 'CRITICAL';
  const justWasted = today.expired > 0;

  return (
    <div
      className={`p-5 rounded-2xl border bg-white transition-all duration-300 cursor-pointer hover:-translate-y-0.5 ${isCritical ? 'border-rose-300' : 'border-gray-200/80 hover:border-rose-300'}`}
      onClick={() => setExpanded(e => !e)}
    >
      <div key={justWasted ? `${bloodType}-${dayIndex}-flash` : `${bloodType}-stable`} className={justWasted ? 'anim-shake' : ''}>
        <div className="flex justify-between items-center mb-3">
          <span className="font-outfit text-[22px] font-normal text-gray-900">{bloodType}</span>
          <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-normal uppercase tracking-wider border ${st.bg} ${st.text} ${st.border} ${isCritical ? 'animate-pulse' : ''}`}>
            {st.label}
          </span>
        </div>

        <div className="flex justify-between items-baseline mb-1.5">
          <span className="font-sans text-[12px] text-gray-400">Current Stock</span>
          <span className="font-outfit text-[16px] font-normal text-gray-800">
            {Math.round(today.stock)} <span className="font-sans text-[12px] text-gray-400">units</span>
          </span>
        </div>

        <div className="h-2.5 w-full bg-gray-100/80 rounded-full my-2 overflow-hidden p-0.5 border border-gray-200/40">
          <div className={`h-full ${st.bar} rounded-full transition-all duration-700 shadow-2xs`} style={{ width: `${pct}%` }} />
        </div>
      </div>

      {/* Level A: always-visible readout */}
      <div className="bg-gray-50/80 rounded-xl p-3 mt-3 border border-gray-100/80 grid grid-cols-2 gap-2 text-[11.5px]">
        <div className="flex flex-col">
          <span className="font-sans text-[11px] text-gray-400">Demand today</span>
          <span className="font-outfit font-normal text-[13px] text-gray-700">{Math.round(today.demand)} units</span>
        </div>
        <div className="flex flex-col">
          <span className="font-sans text-[11px] text-gray-400">Supply today</span>
          <span className="font-outfit font-normal text-[13px] text-gray-700">{Math.round(today.supply)} units</span>
        </div>
        <div className="flex flex-col">
          <span className="font-sans text-[11px] text-gray-400">Shortage risk</span>
          <span className={`font-outfit font-normal text-[13px] ${st.text}`}>{st.label}</span>
        </div>
        <div className="flex flex-col">
          <span className="font-sans text-[11px] text-gray-400">Wastage risk</span>
          <span className={`font-outfit font-normal text-[13px] ${wst.text}`}>{wst.label}</span>
        </div>
      </div>

      {justWasted && (
        <div className="mt-3 flex items-center gap-1.5 text-[11px] font-normal text-rose-600 bg-rose-50/80 border border-rose-200/60 px-3 py-1.5 rounded-xl">
          <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />
          <span>{Math.round(today.expired)} units expired today</span>
        </div>
      )}

      <button
        className="mt-3 flex items-center gap-1 text-[11px] font-normal text-gray-400 hover:text-rose-500 transition-colors"
        onClick={(e) => { e.stopPropagation(); setExpanded(x => !x); }}
      >
        <ChevronDown className={`w-3.5 h-3.5 transition-transform ${expanded ? 'rotate-180' : ''}`} />
        {expanded ? 'Hide 30-day trend' : 'Show 30-day trend'}
      </button>

      {expanded && (
        <div className="mt-3 border-t border-gray-100 pt-3" onClick={(e) => e.stopPropagation()}>
          <div className="h-[160px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={series} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
                <CartesianGrid strokeDasharray="4 4" stroke="#f3f4f6" vertical={false} />
                <XAxis dataKey="date" stroke="#9ca3af" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} minTickGap={30} />
                <YAxis stroke="#9ca3af" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '12px', fontSize: '12px' }} />
                <Line type="monotone" dataKey="demand" stroke="#f43f5e" strokeWidth={2} dot={false} name="Demand" />
                <Line type="monotone" dataKey="supply" stroke="#3b82f6" strokeWidth={2} dot={false} name="Supply" />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="flex gap-[2px] mt-2">
            {series.map((d, i) => (
              <div
                key={i}
                title={`${d.date}: ${d.shortage_risk}${d.expired > 0 ? ' - wastage' : ''}`}
                className={`flex-1 h-2 rounded-sm ${
                  d.shortage_risk === 'CRITICAL' ? 'bg-rose-400' : d.shortage_risk === 'WARNING' ? 'bg-amber-300' : 'bg-emerald-300'
                } ${d.expired > 0 ? 'ring-2 ring-offset-1 ring-gray-700' : ''}`}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

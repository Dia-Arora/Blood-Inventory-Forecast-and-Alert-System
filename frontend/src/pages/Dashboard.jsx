import React, { useEffect, useState, useCallback } from 'react';
import { Clock, RefreshCcw, Droplet, AlertTriangle, Calendar, TrendingUp, TrendingDown, Play, Pause, SkipForward, Zap } from 'lucide-react';
import { fetchSimulation, fetchScenarios } from '../lib/api';
import HealthBarCard from '../components/HealthBarCard';
import AlertStream from '../components/AlertStream';

const BLOOD_TYPES = ['A', 'B', 'AB', 'O'];
const SIM_DAYS = 30;

export default function Dashboard() {
  const [simulateData, setSimulateData] = useState(null);
  const [error, setError] = useState(null);
  const [dayIndex, setDayIndex] = useState(0);
  const [autoPlay, setAutoPlay] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [scenarios, setScenarios] = useState([]);
  const [scenario, setScenario] = useState('default');

  useEffect(() => {
    fetchScenarios().then(setScenarios).catch(() => {});
  }, []);

  const loadSimulation = useCallback(() => {
    setError(null);
    fetchSimulation(SIM_DAYS, scenario)
      .then(data => {
        setSimulateData(data);
        setDayIndex(0);
        setLastRefresh(new Date());
      })
      .catch(err => setError(err.message));
  }, [scenario]);

  useEffect(() => { loadSimulation(); }, [loadSimulation]);

  useEffect(() => {
    if (!autoPlay || !simulateData) return;
    const iv = setInterval(() => {
      setDayIndex(d => {
        if (d >= SIM_DAYS - 1) { setAutoPlay(false); return d; }
        return d + 1;
      });
    }, 800);
    return () => clearInterval(iv);
  }, [autoPlay, simulateData]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md">
          <AlertTriangle className="w-10 h-10 text-rose-400 mx-auto mb-3" />
          <p className="font-outfit text-gray-900 mb-1">Couldn't reach the BloodIQ backend</p>
          <p className="font-sans text-[13px] text-gray-500 mb-4">{error}</p>
          <button onClick={loadSimulation} className="text-[13px] font-normal bg-gray-900 text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition-colors">Retry</button>
        </div>
      </div>
    );
  }

  if (!simulateData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="font-outfit text-gray-400">Loading simulation...</p>
      </div>
    );
  }

  const totalStock = BLOOD_TYPES.reduce((acc, bt) => acc + simulateData[bt][dayIndex].stock, 0);
  const criticalCount = BLOOD_TYPES.filter(bt => simulateData[bt][dayIndex].shortage_risk === 'CRITICAL').length;
  const expiringToday = BLOOD_TYPES.reduce((acc, bt) => acc + simulateData[bt][dayIndex].expired, 0);
  const suppliedToday = BLOOD_TYPES.reduce((acc, bt) => acc + simulateData[bt][dayIndex].supply, 0);

  return (
    <div className="bg-gray-50 min-h-screen pb-8">
      <div className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between sticky top-16 z-40">
        <div className="flex items-center gap-5">
          <h1 className="font-outfit text-xl font-normal text-gray-900">Dashboard</h1>
          <span className="text-[13px] font-normal text-gray-500 bg-gray-50 px-3 py-1.5 rounded-lg border border-gray-200">
            Day {dayIndex + 1} / {SIM_DAYS} · {simulateData.A[dayIndex].date}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            className="text-[13px] font-normal bg-white border border-gray-200 text-gray-700 px-3 py-1.5 rounded-lg hover:border-rose-300 transition-colors cursor-pointer"
          >
            {scenarios.map(s => (
              <option key={s.key} value={s.key}>{s.label}</option>
            ))}
          </select>
          <button
            onClick={() => setAutoPlay(p => !p)}
            className="flex items-center gap-1.5 text-[13px] font-normal bg-rose-500 text-white px-3 py-1.5 rounded-lg hover:bg-rose-600 transition-colors"
          >
            {autoPlay ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            {autoPlay ? 'Pause' : 'Auto-play'}
          </button>
          <button
            onClick={() => setDayIndex(d => Math.min(d + 1, SIM_DAYS - 1))}
            disabled={dayIndex >= SIM_DAYS - 1}
            className="flex items-center gap-1.5 text-[13px] font-normal bg-gray-900 text-white px-3 py-1.5 rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-40"
          >
            <SkipForward className="w-3.5 h-3.5" /> Next Day
          </button>
          <div className="flex items-center gap-2 text-[12px] text-gray-400 font-normal ml-1">
            <Clock className="w-3.5 h-3.5" /> {lastRefresh.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            <button onClick={loadSimulation} className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"><RefreshCcw className="w-3.5 h-3.5 text-gray-500" /></button>
          </div>
        </div>
      </div>

      <div className="max-w-[1440px] mx-auto p-6 grid grid-cols-12 gap-5">
        <ScenarioBanner scenarios={scenarios} scenario={scenario} />

        <div className="col-span-12 grid grid-cols-2 md:grid-cols-4 gap-4">
          <KPI title="Total Stock" value={Math.round(totalStock)} unit="units" icon={<Droplet className="w-4 h-4 text-rose-400" />} trend="live" up />
          <KPI title="Critical Shortages" value={criticalCount} unit="blood types" icon={<AlertTriangle className="w-4 h-4 text-rose-500" />} trend={criticalCount > 0 ? 'action needed' : 'all clear'} up={criticalCount === 0} color={criticalCount > 0 ? 'text-rose-600' : 'text-emerald-600'} />
          <KPI title="Expired Today" value={Math.round(expiringToday)} unit="units" icon={<Calendar className="w-4 h-4 text-amber-400" />} trend={expiringToday > 0 ? 'wastage' : 'none'} color="text-amber-600" />
          <KPI title="Donations Today" value={Math.round(suppliedToday)} unit="units" icon={<TrendingUp className="w-4 h-4 text-emerald-500" />} trend="incoming" up />
        </div>

        <div className="col-span-12 lg:col-span-3">
          <AlertStream simulateData={simulateData} dayIndex={dayIndex} />
        </div>

        <div className="col-span-12 lg:col-span-9">
          <div className="bg-white border border-gray-200 rounded-2xl p-6">
            <h2 className="font-outfit text-[18px] font-normal text-gray-900 mb-1">Blood Type Status</h2>
            <p className="font-sans text-[13px] text-gray-500 mb-5">Live stock, demand, supply, shortage & wastage risk per blood type</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {BLOOD_TYPES.map(bt => (
                <HealthBarCard key={bt} bloodType={bt} series={simulateData[bt]} dayIndex={dayIndex} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function formatShock(shock) {
  if (!shock) return 'Unaffected (default random behavior)';
  const from = shock.start_day + 1;
  const to = shock.end_day;
  const dayLabel = from === to ? `day ${from}` : `days ${from}–${to}`;
  return `${shock.min.toFixed(2)}x – ${shock.max.toFixed(2)}x, ${dayLabel}`;
}

function ScenarioBanner({ scenarios, scenario }) {
  if (scenario === 'default') return null;
  const active = scenarios.find(s => s.key === scenario);
  if (!active) return null;

  return (
    <div className="col-span-12 bg-amber-50/60 border border-amber-200/70 rounded-2xl p-5 flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <Zap className="w-4 h-4 text-amber-500" />
        <span className="font-outfit text-[15px] font-normal text-gray-900">{active.label}</span>
      </div>
      <p className="font-sans text-[13px] text-gray-600 leading-relaxed">{active.description}</p>
      <div className="flex flex-wrap gap-4">
        <div className="text-[12px] font-normal text-gray-700 bg-white border border-amber-200/60 px-3 py-1.5 rounded-lg">
          <span className="text-gray-400">Demand shock: </span>{formatShock(active.demand_shock)}
        </div>
        <div className="text-[12px] font-normal text-gray-700 bg-white border border-amber-200/60 px-3 py-1.5 rounded-lg">
          <span className="text-gray-400">Supply shock: </span>{formatShock(active.supply_shock)}
        </div>
      </div>
      {active.source && (
        <p className="font-sans text-[11px] text-gray-400 leading-relaxed italic">{active.source}</p>
      )}
    </div>
  );
}

function KPI({ title, value, unit, icon, trend, up, color = 'text-gray-900' }) {
  return (
    <div className="bg-gradient-to-b from-white to-gray-50/50 border border-gray-200/80 rounded-2xl p-5 hover:border-rose-200 hover:shadow-lg hover:shadow-rose-500/5 hover:-translate-y-0.5 transition-all duration-300 group">
      <div className="flex justify-between items-start mb-4">
        <span className="font-outfit text-[12px] font-normal text-gray-500 uppercase tracking-wider">{title}</span>
        <div className="w-9 h-9 bg-rose-50/80 border border-rose-100/60 rounded-xl flex items-center justify-center group-hover:scale-105 transition-transform">{icon}</div>
      </div>
      <div className="flex items-baseline gap-1.5 mb-3">
        <span className={`font-outfit text-3xl font-normal ${color}`}>{value}</span>
        <span className="font-sans text-[12px] text-gray-400">{unit}</span>
      </div>
      <div>
        <span className={`inline-flex items-center gap-1 text-[11px] font-normal px-2 py-0.5 rounded-full border ${up ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 'bg-rose-50 text-rose-600 border-rose-100'}`}>
          {up ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          <span>{trend}</span>
        </span>
      </div>
    </div>
  );
}

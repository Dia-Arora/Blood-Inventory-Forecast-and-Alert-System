import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { AlertTriangle } from 'lucide-react';
import { fetchBacktest } from '../lib/api';

const BLOOD_TYPES = ['A', 'B', 'AB', 'O'];

export default function Backtest() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const load = () => {
    setError(null);
    setData(null);
    fetchBacktest()
      .then(setData)
      .catch(err => setError(err.message));
  };

  useEffect(load, []);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md">
          <AlertTriangle className="w-10 h-10 text-rose-400 mx-auto mb-3" />
          <p className="font-outfit text-gray-900 mb-1">Couldn't reach the BloodIQ backend</p>
          <p className="font-sans text-[13px] text-gray-500 mb-4">{error}</p>
          <button onClick={load} className="text-[13px] font-normal bg-gray-900 text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition-colors">Retry</button>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="font-outfit text-gray-400">Running held-out backtest (fitting supply models can take a few seconds)...</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-50 min-h-screen pb-8">
      <div className="bg-white border-b border-gray-200 px-6 py-3 sticky top-16 z-40">
        <h1 className="font-outfit text-xl font-normal text-gray-900">Model Backtest</h1>
        <p className="font-sans text-[13px] text-gray-500">
          Actual vs. predicted on the last 30 held-out days per blood type &mdash; the models never saw these days during training.
        </p>
      </div>

      <div className="max-w-[1440px] mx-auto p-6 grid grid-cols-1 lg:grid-cols-2 gap-5">
        {BLOOD_TYPES.map(bt => (
          <BloodTypeBacktestCard
            key={bt}
            bloodType={bt}
            demand={data.demand[bt]}
            supply={data.supply[bt]}
          />
        ))}
      </div>
    </div>
  );
}

function mergeSeries(actual, predicted, dates) {
  return dates.map((date, i) => ({ date, actual: actual[i], predicted: predicted[i] }));
}

function BloodTypeBacktestCard({ bloodType, demand, supply }) {
  const demandSeries = mergeSeries(demand.actual, demand.predicted, demand.dates);
  const supplySeries = mergeSeries(supply.actual, supply.predicted, supply.dates);

  return (
    <div className="bg-white border border-gray-200 rounded-2xl p-6">
      <h2 className="font-outfit text-[18px] font-normal text-gray-900 mb-4">{bloodType}</h2>

      <BacktestChart title="Demand (LightGBM)" series={demandSeries} mae={demand.mae} rmse={demand.rmse} actualColor="#f43f5e" predictedColor="#111827" />
      <div className="h-5" />
      <BacktestChart title="Supply (Prophet)" series={supplySeries} mae={supply.mae} rmse={supply.rmse} actualColor="#3b82f6" predictedColor="#111827" />
    </div>
  );
}

function BacktestChart({ title, series, mae, rmse, actualColor, predictedColor }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="font-outfit text-[13px] font-normal text-gray-700">{title}</span>
        <div className="flex gap-2">
          <span className="text-[11px] font-normal text-gray-500 bg-gray-50 border border-gray-200 px-2 py-0.5 rounded-full">MAE {mae}</span>
          <span className="text-[11px] font-normal text-gray-500 bg-gray-50 border border-gray-200 px-2 py-0.5 rounded-full">RMSE {rmse}</span>
        </div>
      </div>
      <div className="h-[180px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={series} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
            <CartesianGrid strokeDasharray="4 4" stroke="#f3f4f6" vertical={false} />
            <XAxis dataKey="date" stroke="#9ca3af" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} minTickGap={30} />
            <YAxis stroke="#9ca3af" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
            <Tooltip contentStyle={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '12px', fontSize: '12px' }} />
            <Legend wrapperStyle={{ fontSize: '11px' }} />
            <Line type="monotone" dataKey="actual" stroke={actualColor} strokeWidth={2} dot={false} name="Actual" />
            <Line type="monotone" dataKey="predicted" stroke={predictedColor} strokeWidth={2} strokeDasharray="4 3" dot={false} name="Predicted" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

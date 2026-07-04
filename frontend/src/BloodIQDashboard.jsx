import React, { useState, useEffect, useMemo } from 'react';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
  Treemap
} from 'recharts';
import { 
  AlertTriangle, Clock, Activity, TrendingUp, TrendingDown, 
  Droplet, Calendar, RefreshCcw, Bell, CheckCircle2, ChevronDown 
} from 'lucide-react';

// --- MOCK DATA GENERATORS ---

const BLOOD_GROUPS = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-'];
const HOSPITALS = ['Hosp-Central', 'Hosp-North', 'Hosp-South', 'Hosp-East', 'Hosp-West'];

const generateForecastData = () => {
  const data = [];
  const today = new Date();
  
  // 14 days historical
  for(let i = -14; i <= 0; i++) {
    const d = new Date(today);
    d.setDate(d.getDate() + i);
    const base = 40 + Math.sin(i / 2) * 10;
    data.push({
      date: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      actual: Math.floor(base + (Math.random() * 8 - 4)),
      predicted: null,
      lower: null,
      upper: null,
      isForecast: false
    });
  }
  
  // 30 days forecast
  const lastActual = data[data.length-1].actual;
  for(let i = 1; i <= 30; i++) {
    const d = new Date(today);
    d.setDate(d.getDate() + i);
    const basePred = lastActual - (i*0.5) + Math.cos(i/3)*15; // Decreasing trend with seasonality
    data.push({
      date: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      actual: null,
      predicted: Math.floor(Math.max(10, basePred)),
      lower: Math.floor(Math.max(5, basePred - 8 - (i*0.3))),
      upper: Math.floor(basePred + 8 + (i*0.3)),
      isForecast: true
    });
  }
  return data;
};

const generateInventoryData = () => {
  return BLOOD_GROUPS.map(bg => {
    const stock = Math.floor(Math.random() * 150) + 10;
    const usage = Math.floor(Math.random() * 30) + 5;
    const daysCover = (stock / usage).toFixed(1);
    
    let status = 'safe';
    if (daysCover <= 3) status = 'critical';
    else if (daysCover <= 7) status = 'warning';
    
    return {
      group: bg,
      stock,
      daysCover,
      status,
      expiring7d: Math.floor(Math.random() * (stock * 0.15)) // up to 15% expiring
    };
  });
};

const INITIAL_ALERTS = [
  { id: 1, severity: 'critical', type: 'shortage', group: 'O-', message: 'O- reserve below 2 days coverage. Central transport en route.', timestamp: '10 mins ago' },
  { id: 2, severity: 'warning', type: 'expiry', group: 'AB+', message: '12 units expiring within 48h. Recommended for elective surgeries.', timestamp: '1 hr ago' },
  { id: 3, severity: 'warning', type: 'demand', group: 'A+', message: 'Projected 40% demand surge over weekend baseline.', timestamp: '3 hrs ago' }
];

const generateHeatmapData = () => {
  return HOSPITALS.map(hosp => ({
    name: hosp,
    children: BLOOD_GROUPS.map(bg => {
      const risk = Math.random();
      return {
        name: bg,
        size: 10 + Math.floor(Math.random() * 50),
        risk: parseFloat(risk.toFixed(2)),
        hospital: hosp
      };
    })
  }));
};

// --- CUSTOM TREEMAP CONTENT ---
const CustomizedTreemapContent = (props) => {
  const { root, depth, x, y, width, height, index, payload, colors, rank, name } = props;
  
  if (depth === 1) {
    return (
      <g>
        <rect x={x} y={y} width={width} height={height} 
              style={{ fill: 'transparent', stroke: '#1e293b', strokeWidth: 2, zIndex: 10 }} />
        {width > 50 && height > 20 && (
          <text x={x + 4} y={y + 14} fontSize={10} fill="#94a3b8" fontWeight="bold" fontFamily="Inter, sans-serif">
            {name}
          </text>
        )}
      </g>
    );
  }
  
  if (depth === 2) {
    const risk = payload.risk;
    // Scarlet (#dc2626) to Navy (#0f172a)
    let fill = '#0f172a';
    if (risk > 0.8) fill = '#dc2626';
    else if (risk > 0.6) fill = '#b91c1c';
    else if (risk > 0.4) fill = '#7f1d1d';
    else if (risk > 0.2) fill = '#1e293b';

    return (
      <g>
        <rect x={x} y={y} width={width} height={height} 
              style={{ fill, stroke: '#0f172a', strokeWidth: 1 }} 
              className="transition-all duration-300 hover:opacity-80 cursor-pointer" />
        {width > 30 && height > 30 && (
          <text x={x + width / 2} y={y + height / 2 + 5} 
                textAnchor="middle" fill="#fff" fontSize={12} fontWeight="bold" fontFamily="Inter, sans-serif">
            {name}
          </text>
        )}
      </g>
    );
  }
  return null;
};

// --- MAIN APPLICATION ---

export default function BloodIQDashboard() {
  const [selectedHospital, setSelectedHospital] = useState(HOSPITALS[0]);
  const [selectedBloodGroup, setSelectedBloodGroup] = useState('O-');
  const [alertFilter, setAlertFilter] = useState('ALL');
  
  const [forecastData, setForecastData] = useState([]);
  const [inventoryData, setInventoryData] = useState([]);
  const [alerts, setAlerts] = useState(INITIAL_ALERTS);
  const [heatmapData, setHeatmapData] = useState([]);
  
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const refreshData = () => {
    setForecastData(generateForecastData());
    setInventoryData(generateInventoryData());
    setHeatmapData(generateHeatmapData());
    setLastRefresh(new Date());
  };

  useEffect(() => {
    refreshData();
    // Simulate real-time updates every minute
    const interval = setInterval(refreshData, 60000);
    return () => clearInterval(interval);
  }, [selectedHospital, selectedBloodGroup]);

  const simulateAlert = () => {
    const bg = BLOOD_GROUPS[Math.floor(Math.random() * BLOOD_GROUPS.length)];
    const newAlert = {
      id: Date.now(),
      severity: 'critical',
      type: 'shortage',
      group: bg,
      message: `CRITICAL: Massive trauma protocol activated. ${bg} stock depleting rapidly.`,
      timestamp: 'Just now'
    };
    setAlerts(prev => [newAlert, ...prev]);
  };

  const filteredAlerts = alerts.filter(a => {
    if (alertFilter === 'ALL') return true;
    if (alertFilter === 'CRITICAL') return a.severity === 'critical';
    if (alertFilter === 'WARNING') return a.severity === 'warning';
    if (alertFilter === 'EXPIRY') return a.type === 'expiry';
    return true;
  });

  // KPI Aggregations
  const totalStock = inventoryData.reduce((acc, curr) => acc + curr.stock, 0);
  const criticalGroups = inventoryData.filter(i => i.status === 'critical').length;
  const totalExpiring = inventoryData.reduce((acc, curr) => acc + curr.expiring7d, 0);

  return (
    <div className="bg-[#0a1628] min-h-screen text-slate-200 font-['Inter',sans-serif] selection:bg-blue-900 overflow-x-hidden">
      {/* GLOBAL STYLES FOR FONTS */}
      <style dangerouslySetInnerHTML={{__html: `
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Syne:wght@500;600;700;800&display=swap');
        .font-syne { font-family: 'Syne', sans-serif; }
      `}} />

      {/* HEADER */}
      <header className="sticky top-0 z-50 bg-[#0f172a] border-b border-slate-800 px-6 py-4 flex items-center justify-between shadow-md">
        <div className="flex items-center gap-3">
          <div className="bg-red-600 p-2 rounded-lg">
            <Activity className="text-white w-6 h-6" />
          </div>
          <div className="flex flex-col">
            <h1 className="font-syne text-2xl font-bold tracking-wide text-white leading-none">Blood<span className="text-red-500">IQ</span></h1>
            <span className="text-[10px] text-slate-400 mt-1 uppercase tracking-wider font-semibold">Inventory Intelligence System</span>
          </div>
        </div>
        
        <div className="flex items-center gap-6">
          <div className="relative group">
            <button className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 px-4 py-2 rounded-md transition-colors border border-slate-700">
              <span className="font-medium">{selectedHospital}</span>
              <ChevronDown className="w-4 h-4 text-slate-400 group-hover:text-white transition-colors" />
            </button>
            {/* Simple dropdown simulation for hover */}
            <div className="absolute top-full right-0 mt-1 w-48 bg-slate-800 border border-slate-700 rounded-md shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200">
              {HOSPITALS.map(h => (
                <div key={h} 
                     className="px-4 py-2 hover:bg-slate-700 cursor-pointer first:rounded-t-md last:rounded-b-md"
                     onClick={() => setSelectedHospital(h)}>
                  {h}
                </div>
              ))}
            </div>
          </div>
          
          <div className="h-8 w-px bg-slate-700"></div>
          
          <div className="flex items-center gap-3 text-sm text-slate-400">
            <Clock className="w-4 h-4" />
            <span>Updated: {lastRefresh.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
            <button onClick={refreshData} className="p-1.5 hover:bg-slate-800 rounded bg-slate-800/50 transition-colors ml-1" title="Refresh Data">
              <RefreshCcw className="w-4 h-4 text-slate-300" />
            </button>
          </div>
        </div>
      </header>

      <main className="p-6 max-w-[1600px] mx-auto grid grid-cols-12 gap-6">
        
        {/* KPI SUMMARY ROW */}
        <div className="col-span-12 grid grid-cols-4 gap-4">
          <KPICard title="Total Inventory" value={`${totalStock} Units`} icon={<Droplet className="w-5 h-5 text-blue-400"/>} trend="+4.2%" trendUp={true} />
          <KPICard title="Critical Shortages" value={criticalGroups} icon={<AlertTriangle className="w-5 h-5 text-red-500"/>} trend="2 less" trendUp={true} valueColor={criticalGroups > 0 ? "text-red-500" : "text-emerald-500"} />
          <KPICard title="Expiring (7 days)" value={`${totalExpiring} Units`} icon={<Calendar className="w-5 h-5 text-amber-500"/>} trend="+12%" trendUp={false} valueColor="text-amber-500" />
          <KPICard title="Model Accuracy (30d)" value="94.2%" icon={<CheckCircle2 className="w-5 h-5 text-emerald-500"/>} trend="+1.1%" trendUp={true} />
        </div>

        {/* LEFT SIDEBAR: ALERTS */}
        <div className="col-span-12 lg:col-span-3 flex flex-col gap-4">
          <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 flex flex-col h-[800px]">
            <div className="flex justify-between items-center mb-6">
              <h2 className="font-syne text-lg font-bold text-white flex items-center gap-2">
                <Bell className="w-5 h-5" /> Alert Feed
              </h2>
              <button onClick={simulateAlert} className="text-xs bg-slate-800 hover:bg-slate-700 px-2 py-1 rounded text-red-400 border border-slate-700 transition-colors">
                Simulate
              </button>
            </div>
            
            <div className="flex gap-2 mb-4 overflow-x-auto pb-2 scrollbar-hide">
              {['ALL', 'CRITICAL', 'WARNING', 'EXPIRY'].map(f => (
                <button 
                  key={f}
                  onClick={() => setAlertFilter(f)}
                  className={`text-xs px-3 py-1.5 rounded-full font-semibold tracking-wider transition-colors whitespace-nowrap
                    ${alertFilter === f 
                      ? 'bg-slate-700 text-white' 
                      : 'bg-slate-800/50 text-slate-400 hover:bg-slate-800 hover:text-slate-300'}`}
                >
                  {f}
                </button>
              ))}
            </div>

            <div className="flex-1 overflow-y-auto pr-2 space-y-3 custom-scrollbar">
              {filteredAlerts.length === 0 ? (
                <div className="text-center py-10 text-slate-500 flex flex-col items-center">
                  <CheckCircle2 className="w-10 h-10 mb-2 opacity-50" />
                  <p>No active alerts in this category.</p>
                </div>
              ) : (
                filteredAlerts.map(alert => (
                  <div key={alert.id} className={`p-4 rounded-lg border-l-4 bg-[#141e33] ${
                    alert.severity === 'critical' ? 'border-l-red-600' : 'border-l-amber-500'
                  }`}>
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          alert.severity === 'critical' ? 'bg-red-950/50 text-red-400' : 'bg-amber-950/50 text-amber-400'
                        }`}>
                          {alert.severity.toUpperCase()}
                        </span>
                        <span className="bg-slate-800 px-2 py-0.5 rounded text-[10px] font-bold text-slate-300">{alert.group}</span>
                      </div>
                      <span className="text-[10px] text-slate-500 leading-none">{alert.timestamp}</span>
                    </div>
                    <p className="text-sm text-slate-300 leading-snug">{alert.message}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* MAIN PANEL */}
        <div className="col-span-12 lg:col-span-9 flex flex-col gap-6">
          
          {/* CHART PANEL */}
          <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-6">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="font-syne text-xl font-bold text-white">Demand Forecast Modeling</h2>
                <p className="text-sm text-slate-400 mt-1">14-day chronological history and 30-day predictive horizon.</p>
              </div>
              
              <div className="flex gap-2">
                {['O-', 'O+', 'A-', 'A+', 'B-'].map(bg => (
                  <button 
                    key={bg}
                    onClick={() => setSelectedBloodGroup(bg)}
                    className={`px-3 py-1.5 rounded text-sm font-medium transition-colors border ${
                      selectedBloodGroup === bg 
                        ? 'bg-blue-600 bg-opacity-20 border-blue-500/50 text-blue-400' 
                        : 'bg-transparent border-slate-700 text-slate-400 hover:border-slate-600 hover:text-slate-200'
                    }`}
                  >
                    {bg}
                  </button>
                ))}
              </div>
            </div>

            <div className="h-[350px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={forecastData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorPred" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorUpper" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.1}/>
                      <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.0}/>
                    </linearGradient>
                  </defs>
                  
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis dataKey="date" stroke="#64748b" tick={{fontSize: 12}} tickLine={false} axisLine={false} minTickGap={30} />
                  <YAxis stroke="#64748b" tick={{fontSize: 12}} tickLine={false} axisLine={false} />
                  
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc', borderRadius: '8px' }}
                    itemStyle={{ color: '#f8fafc' }}
                    labelStyle={{ color: '#94a3b8', marginBottom: '4px' }}
                  />
                  
                  <ReferenceLine x={forecastData[14]?.date} stroke="#64748b" strokeDasharray="3 3" label={{ position: 'top', value: 'FORECAST START', fill: '#64748b', fontSize: 10, dy: -10 }} />
                  
                  {/* Historical */}
                  <Area type="monotone" dataKey="actual" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorActual)" name="Actual Demand" connectNulls />
                  
                  {/* Forecast Confidence Interval */}
                  <Area type="monotone" dataKey="upper" stroke="none" fillOpacity={1} fill="url(#colorUpper)" connectNulls />
                  <Area type="monotone" dataKey="lower" stroke="none" fill="#0f172a" connectNulls />
                  
                  {/* Forecast Line */}
                  <Area type="monotone" dataKey="predicted" stroke="#f59e0b" strokeWidth={2} strokeDasharray="5 5" fillOpacity={1} fill="url(#colorPred)" name="Forecast" connectNulls />
                  
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid grid-cols-12 gap-6">
            {/* INVENTORY STATUS GRID */}
            <div className="col-span-12 xl:col-span-7 bg-[#0f172a] border border-slate-800 rounded-xl p-6">
              <h2 className="font-syne text-lg font-bold text-white mb-4">Inventory Status</h2>
              <div className="grid grid-cols-2 gap-4">
                {inventoryData.map((item) => (
                  <InventoryCard key={item.group} data={item} />
                ))}
              </div>
            </div>

            {/* HEATMAP */}
            <div className="col-span-12 xl:col-span-5 bg-[#0f172a] border border-slate-800 rounded-xl p-6">
               <h2 className="font-syne text-lg font-bold text-white mb-1">Network Shortage Risk</h2>
               <p className="text-xs text-slate-400 mb-4">Hospital × Blood Group Risk Surface</p>
               <div className="h-[240px] w-full rounded-lg overflow-hidden border border-slate-800">
                  {heatmapData.length > 0 && (
                    <ResponsiveContainer width="100%" height="100%">
                      <Treemap
                        data={heatmapData}
                        dataKey="size"
                        aspectRatio={4/3}
                        stroke="#0f172a"
                        fill="#1e293b"
                        content={<CustomizedTreemapContent />}
                      >
                        <Tooltip 
                          content={({ active, payload }) => {
                            if (active && payload && payload.length) {
                              const p = payload[0].payload;
                              return (
                                <div className="bg-slate-900 border border-slate-700 p-3 rounded-lg shadow-xl shadow-black/50">
                                  <p className="font-bold text-white mb-1">{p.hospital} | {p.name}</p>
                                  <p className="text-sm text-slate-300">Risk Score: <span className={p.risk > 0.6 ? 'text-red-400 font-bold' : 'text-slate-200'}>{p.risk}</span></p>
                                  <p className="text-xs text-slate-400 mt-2 italic">
                                    {p.risk > 0.8 ? "Action: Initiate emergency transfer." : 
                                     p.risk > 0.5 ? "Action: Monitor usage closely." : "Action: Standard protocols."}
                                  </p>
                                </div>
                              );
                            }
                            return null;
                          }}
                        />
                      </Treemap>
                    </ResponsiveContainer>
                  )}
               </div>
            </div>
          </div>

        </div>
      </main>
      
      {/* Custom Scrollbar CSS embedded for self-containment */}
      <style dangerouslySetInnerHTML={{__html: `
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #475569; }
        .scrollbar-hide::-webkit-scrollbar { display: none; }
        .scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }
      `}} />
    </div>
  );
}

// --- SUB-COMPONENTS ---

function KPICard({ title, value, icon, trend, trendUp, valueColor = "text-white" }) {
  return (
    <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 hover:border-slate-600 transition-colors group">
      <div className="flex justify-between items-start mb-2">
        <p className="text-sm font-medium text-slate-400">{title}</p>
        <div className="p-2 bg-slate-800 rounded-lg group-hover:bg-slate-700 transition-colors">{icon}</div>
      </div>
      <div className="flex items-end gap-3">
        <h3 className={`font-syne text-3xl font-bold ${valueColor}`}>{value}</h3>
      </div>
      <div className="mt-3 flex items-center gap-1.5">
        <span className={`flex items-center text-xs font-semibold px-1.5 py-0.5 rounded ${
          trendUp ? 'bg-emerald-950/40 text-emerald-400' : 'bg-red-950/40 text-red-400'
        }`}>
          {trendUp ? <TrendingUp className="w-3 h-3 mr-1" /> : <TrendingDown className="w-3 h-3 mr-1" />}
          {trend}
        </span>
        <span className="text-xs text-slate-500">vs historical baseline</span>
      </div>
    </div>
  );
}

function InventoryCard({ data }) {
  const { group, stock, daysCover, status, expiring7d } = data;
  
  const statusConfig = {
    safe: { color: 'bg-emerald-500', bg: 'bg-emerald-950/30' },
    warning: { color: 'bg-amber-500', bg: 'bg-amber-950/30' },
    critical: { color: 'bg-red-600', bg: 'bg-red-950/30' }
  };
  const conf = statusConfig[status];
  const fillPct = Math.min(100, (stock / 200) * 100); // assume 200 is "full"

  return (
    <div className={`p-4 rounded-lg border border-slate-800 ${conf.bg} transition-colors`}>
      <div className="flex justify-between items-center mb-3">
        <div className="flex items-center gap-2">
          <span className="font-syne text-xl font-bold text-white">{group}</span>
        </div>
        <span className="font-bold text-xl text-white">{stock} <span className="text-xs text-slate-400 font-normal">units</span></span>
      </div>
      
      {/* Progress Bar */}
      <div className="h-1.5 w-full bg-slate-800 rounded-full mb-3 overflow-hidden">
        <div className={`h-full ${conf.color} rounded-full transition-all duration-1000`} style={{ width: `${fillPct}%` }}></div>
      </div>
      
      <div className="flex justify-between items-center">
        <div className="text-xs">
          <span className="text-slate-400">Coverage: </span>
          <span className={`font-semibold ${status === 'critical' ? 'text-red-400' : 'text-slate-200'}`}>
            {daysCover} days
          </span>
        </div>
        {expiring7d > 0 && (
          <div className="flex items-center gap-1 text-[10px] text-amber-500 bg-amber-950/40 px-1.5 py-0.5 rounded border border-amber-900/50">
            <Clock className="w-3 h-3" />
            {expiring7d} exp.
          </div>
        )}
      </div>
    </div>
  );
}

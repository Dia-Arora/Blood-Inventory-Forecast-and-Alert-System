import React, { useState, useEffect } from 'react';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Treemap
} from 'recharts';
import { 
  AlertTriangle, Clock, TrendingUp, TrendingDown, 
  Droplet, Calendar, RefreshCcw, Bell, CheckCircle2, ChevronDown 
} from 'lucide-react';

const BLOOD_GROUPS = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-'];
const HOSPITALS = ['Hosp-Central', 'Hosp-North', 'Hosp-South', 'Hosp-East', 'Hosp-West'];

const generateForecastData = () => {
  const data = [];
  const today = new Date();
  for(let i = -14; i <= 0; i++) {
    const d = new Date(today); d.setDate(d.getDate() + i);
    const base = 40 + Math.sin(i / 2) * 10;
    data.push({ date: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }), actual: Math.floor(base + (Math.random() * 8 - 4)), predicted: null, lower: null, upper: null });
  }
  const lastActual = data[data.length-1].actual;
  for(let i = 1; i <= 30; i++) {
    const d = new Date(today); d.setDate(d.getDate() + i);
    const basePred = lastActual - (i*0.5) + Math.cos(i/3)*15;
    data.push({ date: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }), actual: null, predicted: Math.floor(Math.max(10, basePred)), lower: Math.floor(Math.max(5, basePred - 8 - (i*0.3))), upper: Math.floor(basePred + 8 + (i*0.3)) });
  }
  return data;
};

const generateInventoryData = () => BLOOD_GROUPS.map(bg => {
  const stock = Math.floor(Math.random() * 150) + 10;
  const usage = Math.floor(Math.random() * 30) + 5;
  const daysCover = (stock / usage).toFixed(1);
  let status = 'safe';
  if (daysCover <= 3) status = 'critical';
  else if (daysCover <= 7) status = 'warning';
  return { group: bg, stock, daysCover, usage, status, expiring7d: Math.floor(Math.random() * (stock * 0.15)) };
});


const INITIAL_ALERTS = [
  { id: 1, severity: 'critical', type: 'shortage', group: 'O-', message: 'O- reserve below 2 days coverage. Central transport en route.', timestamp: '10 mins ago' },
  { id: 2, severity: 'warning', type: 'expiry', group: 'AB+', message: '12 units expiring within 48h. Recommended for elective surgeries.', timestamp: '1 hr ago' },
  { id: 3, severity: 'warning', type: 'demand', group: 'A+', message: 'Projected 40% demand surge over weekend baseline.', timestamp: '3 hrs ago' }
];

const generateHeatmapData = () => HOSPITALS.map(hosp => ({
  name: hosp,
  children: BLOOD_GROUPS.map(bg => ({ name: bg, size: 10 + Math.floor(Math.random() * 50), risk: parseFloat(Math.random().toFixed(2)), hospital: hosp }))
}));

const TreemapContent = (props) => {
  const { depth, x, y, width, height, payload, name } = props;
  if (!width || !height || width <= 0 || height <= 0) return null;
  if (depth === 1) {
    return (<g><rect x={x} y={y} width={width} height={height} style={{ fill: 'transparent', stroke: '#e5e7eb', strokeWidth: 1 }} />
      {width > 50 && height > 20 && <text x={x+4} y={y+14} fontSize={11} fill="#6b7280" fontWeight="400" fontFamily="Merriweather">{name}</text>}</g>);
  }
  if (depth === 2 && payload) {
    const risk = payload.risk || 0;
    let fill = '#ffffff', textFill = '#374151';
    if (risk > 0.8) { fill = '#fda4af'; textFill = '#9f1239'; }
    else if (risk > 0.6) { fill = '#fecdd3'; textFill = '#be123c'; }
    else if (risk > 0.4) { fill = '#ffe4e6'; textFill = '#e11d48'; }
    else if (risk > 0.2) { fill = '#fff1f2'; textFill = '#374151'; }
    return (<g><rect x={x} y={y} width={width} height={height} style={{ fill, stroke: '#e5e7eb', strokeWidth: 1 }} className="hover:opacity-80 cursor-pointer transition-opacity" />
      {width > 28 && height > 28 && <text x={x+width/2} y={y+height/2+4} textAnchor="middle" fill={textFill} fontSize={12} fontWeight="400" fontFamily="Merriweather">{name}</text>}</g>);
  }
  return null;
};


export default function Dashboard() {
  const [selectedHospital, setSelectedHospital] = useState(HOSPITALS[0]);
  const [selectedBloodGroup, setSelectedBloodGroup] = useState('O-');
  const [alertFilter, setAlertFilter] = useState('ALL');
  const [forecastData, setForecastData] = useState([]);
  const [inventoryData, setInventoryData] = useState([]);
  const [alerts, setAlerts] = useState(INITIAL_ALERTS);
  const [heatmapData, setHeatmapData] = useState([]);
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const [rawDemandData, setRawDemandData] = useState([]);

  const refreshData = async () => {
    try {
      const demandRes = await fetch('http://localhost:8000/api/forecast/demand');
      const supplyRes = await fetch('http://localhost:8000/api/forecast/supply');
      
      if (demandRes.ok && supplyRes.ok) {
        const demandJson = await demandRes.json();
        const supplyJson = await supplyRes.json();
        
        if (demandJson.status === 'success' && demandJson.data) {
           setRawDemandData(demandJson.data);
        }

        if (supplyJson.status === 'success' && supplyJson.data) {
           const sData = supplyJson.data;
           const invData = BLOOD_GROUPS.map(bg => {
              const baseGroup = bg.replace('+', '').replace('-', '');
              const preds = sData[baseGroup] || [];
              const rawStock = preds.length > 0 ? preds[0].predicted_supply : 100;
              const currentStock = Math.floor(bg.includes('+') ? rawStock * 0.8 : rawStock * 0.2); 
              
              let status = 'safe';
              const daysCover = currentStock / 20; 
              if (daysCover <= 3) status = 'critical';
              else if (daysCover <= 7) status = 'warning';
              
              return {
                group: bg,
                stock: currentStock,
                daysCover: parseFloat(daysCover.toFixed(1)),
                usage: 20,
                status: status,
                expiring7d: Math.floor(currentStock * 0.1)
              };
           });
           setInventoryData(invData);
        }
      }
      setHeatmapData(generateHeatmapData());
      setLastRefresh(new Date());
    } catch (e) {
      console.log("Backend offline, using fallback");
      setRawDemandData([]);
      setForecastData(generateForecastData());
      setInventoryData(generateInventoryData());
      setHeatmapData(generateHeatmapData());
      setLastRefresh(new Date());
    }
  };

  useEffect(() => {
    if (!rawDemandData || rawDemandData.length === 0) return;
    
    let multiplier = 0.12; 
    if (selectedBloodGroup.includes('O+')) multiplier = 0.38;
    else if (selectedBloodGroup.includes('O-')) multiplier = 0.07;
    else if (selectedBloodGroup.includes('A+')) multiplier = 0.34;
    else if (selectedBloodGroup.includes('A-')) multiplier = 0.06;
    else if (selectedBloodGroup.includes('B+')) multiplier = 0.09;
    else if (selectedBloodGroup.includes('B-')) multiplier = 0.02;
    else if (selectedBloodGroup.includes('AB+')) multiplier = 0.03;
    else if (selectedBloodGroup.includes('AB-')) multiplier = 0.01;

    const fData = rawDemandData.map((d, i) => {
       const dateObj = new Date(d.date);
       const scaledDemand = Math.floor(d.predicted_demand * multiplier);
       return {
          date: dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          actual: i < 14 ? scaledDemand : null,
          predicted: i >= 14 ? scaledDemand : null,
          lower: i >= 14 ? Math.floor(scaledDemand * 0.8) : null,
          upper: i >= 14 ? Math.floor(scaledDemand * 1.2) : null
       };
    });
    setForecastData(fData); 
  }, [rawDemandData, selectedBloodGroup]);
  
  useEffect(() => { refreshData(); const iv = setInterval(refreshData, 60000); return () => clearInterval(iv); }, [selectedHospital]);

  const simulateAlert = () => {
    const bg = BLOOD_GROUPS[Math.floor(Math.random() * BLOOD_GROUPS.length)];
    setAlerts(prev => [{ id: Date.now(), severity: 'critical', type: 'shortage', group: bg, message: `CRITICAL: ${bg} stock depleting rapidly. Activate emergency protocol.`, timestamp: 'Just now' }, ...prev]);
  };

  const filteredAlerts = alerts.filter(a => alertFilter === 'ALL' ? true : alertFilter === 'CRITICAL' ? a.severity === 'critical' : alertFilter === 'WARNING' ? a.severity === 'warning' : a.type === 'expiry');
  const totalStock = inventoryData.reduce((a, c) => a + c.stock, 0);
  const criticalGroups = inventoryData.filter(i => i.status === 'critical').length;
  const totalExpiring = inventoryData.reduce((a, c) => a + c.expiring7d, 0);

  return (
    <div className="bg-gray-50 min-h-screen pb-8">
      {/* Sub-header */}
      <div className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between sticky top-16 z-40">
        <div className="flex items-center gap-5">
          <h1 className="font-outfit text-xl font-normal text-gray-900">Dashboard</h1>
          <div className="relative group">
            <button className="flex items-center gap-1.5 text-[13px] font-normal text-gray-500 bg-gray-50 px-3 py-1.5 rounded-lg border border-gray-200 hover:border-gray-300 transition-colors">
              {selectedHospital} <ChevronDown className="w-3.5 h-3.5" />
            </button>
            <div className="absolute top-full left-0 mt-1 w-44 bg-white border border-gray-200 rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
              {HOSPITALS.map(h => (
                <div key={h} className="px-3 py-2 text-[13px] text-gray-600 hover:bg-rose-50 hover:text-rose-600 cursor-pointer transition-colors first:rounded-t-lg last:rounded-b-lg" onClick={() => setSelectedHospital(h)}>{h}</div>
              ))}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 text-[12px] text-gray-400 font-normal">
          <Clock className="w-3.5 h-3.5" /> {lastRefresh.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}
          <button onClick={refreshData} className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors ml-1"><RefreshCcw className="w-3.5 h-3.5 text-gray-500" /></button>
        </div>
      </div>

      <div className="max-w-[1440px] mx-auto p-6 grid grid-cols-12 gap-5">
        
        {/* KPIs */}
        <div className="col-span-12 grid grid-cols-2 md:grid-cols-4 gap-4">
          <KPI title="Total Inventory" value={totalStock} unit="units" icon={<Droplet className="w-4 h-4 text-rose-400"/>} trend="+4.2%" up />
          <KPI title="Critical Shortages" value={criticalGroups} unit="groups" icon={<AlertTriangle className="w-4 h-4 text-rose-500"/>} trend="2 resolved" up color={criticalGroups > 0 ? 'text-rose-600' : 'text-emerald-600'} />
          <KPI title="Expiring (7d)" value={totalExpiring} unit="units" icon={<Calendar className="w-4 h-4 text-amber-400"/>} trend="+12%" color="text-amber-600" />
          <KPI title="AI Accuracy" value="94.2%" unit="30d avg" icon={<CheckCircle2 className="w-4 h-4 text-emerald-500"/>} trend="+1.1%" up />
        </div>

        {/* Alerts sidebar */}
        <div className="col-span-12 lg:col-span-3">
          <div className="bg-white border border-gray-200 rounded-2xl p-5 h-[720px] flex flex-col">
            <div className="flex justify-between items-center mb-4">
              <h2 className="font-outfit text-[16px] font-normal text-gray-900 flex items-center gap-2"><Bell className="w-4 h-4 text-rose-500" /> <span>Alert Stream</span></h2>
              <button onClick={simulateAlert} className="text-[11px] font-normal bg-rose-50 text-rose-600 px-2.5 py-1 rounded-lg hover:bg-rose-100 transition-colors border border-rose-100 shadow-2xs">Simulate</button>
            </div>
            <div className="flex gap-1.5 mb-4">
              {['ALL','CRITICAL','WARNING','EXPIRY'].map(f => (
                <button key={f} onClick={() => setAlertFilter(f)}
                  className={`text-[11px] font-normal px-2.5 py-1 rounded-lg transition-all ${alertFilter === f ? 'bg-gray-900 text-white shadow-2xs' : 'bg-gray-100 text-gray-500 hover:bg-gray-200/80'}`}>{f}</button>
              ))}
            </div>
            <div className="flex-1 overflow-y-auto space-y-2.5 custom-scrollbar">
              {filteredAlerts.length === 0 ? (
                <div className="text-center py-12 text-gray-400"><CheckCircle2 className="w-8 h-8 mx-auto mb-2 opacity-40" /><p className="font-sans text-[13px]">No active alerts</p></div>
              ) : filteredAlerts.map(a => (
                <div key={a.id} className={`p-3.5 rounded-xl border text-[13px] transition-all hover:shadow-2xs ${a.severity === 'critical' ? 'bg-rose-50/60 border-rose-200/80' : 'bg-amber-50/60 border-amber-200/80'}`}>
                  <div className="flex justify-between items-start mb-1.5">
                    <div className="flex gap-1.5">
                      <span className={`px-2 py-0.5 rounded-md text-[9px] font-normal uppercase tracking-wider ${a.severity === 'critical' ? 'bg-rose-500 text-white' : 'bg-amber-500 text-white'}`}>{a.severity}</span>
                      <span className="px-2 py-0.5 rounded-md text-[9px] font-normal bg-gray-800 text-white">{a.group}</span>
                    </div>
                    <span className="text-[10px] text-gray-400 font-outfit">{a.timestamp}</span>
                  </div>
                  <p className="font-sans text-gray-600 leading-relaxed text-[12.5px]">{a.message}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Main */}
        <div className="col-span-12 lg:col-span-9 flex flex-col gap-5">
          {/* Chart */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6">
            <div className="flex justify-between items-start mb-6">
              <div>
                <h2 className="font-outfit text-[18px] font-normal text-gray-900">Demand Forecast</h2>
                <p className="font-sans text-[13px] text-gray-500 mt-0.5">14-day historical baseline · 30-day predictive trajectory</p>
              </div>
              <div className="flex gap-1.5">
                {['O-','O+','A-','A+','B-'].map(bg => (
                  <button key={bg} onClick={() => setSelectedBloodGroup(bg)}
                    className={`text-[12px] font-normal px-3 py-1.5 rounded-lg border transition-all ${selectedBloodGroup === bg ? 'bg-rose-500 text-white border-rose-500 shadow-2xs' : 'bg-white border-gray-200 text-gray-500 hover:border-rose-300 hover:bg-rose-50/30'}`}>{bg}</button>
                ))}
              </div>
            </div>
            <div className="h-[320px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={forecastData} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
                  <defs>
                    <linearGradient id="gActual" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#fda4af" stopOpacity={0.15}/><stop offset="95%" stopColor="#fda4af" stopOpacity={0}/></linearGradient>
                    <linearGradient id="gPred" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#fb7185" stopOpacity={0.1}/><stop offset="95%" stopColor="#fb7185" stopOpacity={0}/></linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="4 4" stroke="#f3f4f6" vertical={false} />
                  <XAxis dataKey="date" stroke="#9ca3af" tick={{fontSize:11, fontFamily:'Merriweather'}} tickLine={false} axisLine={false} minTickGap={30} />
                  <YAxis stroke="#9ca3af" tick={{fontSize:11, fontFamily:'Merriweather'}} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ background:'#fff', border:'1px solid #e5e7eb', borderRadius:'12px', boxShadow:'0 4px 12px rgba(0,0,0,0.06)', fontFamily:'Merriweather', fontSize:'13px' }} />
                  <ReferenceLine x={forecastData[14]?.date} stroke="#d1d5db" strokeDasharray="3 3" label={{ value:'TODAY', fill:'#9ca3af', fontSize:10, fontWeight:400 }} />
                  <Area type="monotone" dataKey="actual" stroke="#f43f5e" strokeWidth={2} fill="url(#gActual)" name="Actual" connectNulls />
                  <Area type="monotone" dataKey="predicted" stroke="#fb7185" strokeWidth={2} strokeDasharray="6 4" fill="url(#gPred)" name="Forecast" connectNulls />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid grid-cols-12 gap-5">
            {/* Inventory */}
            <div className="col-span-12 xl:col-span-7 bg-white border border-gray-200 rounded-2xl p-6">
              <h2 className="font-outfit text-[18px] font-normal text-gray-900 mb-5">Inventory Status</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {inventoryData.map(item => <InvCard key={item.group} d={item} />)}
              </div>
            </div>
            {/* Heatmap */}
            <div className="col-span-12 xl:col-span-5 bg-white border border-gray-200 rounded-2xl p-6 flex flex-col">
              <h2 className="font-outfit text-[18px] font-normal text-gray-900 mb-1">Network Risk Distribution</h2>
              <p className="font-sans text-[13px] text-gray-500 mb-4">Hospital node vulnerability × Blood group depletion</p>
              <div className="flex-1 rounded-xl overflow-hidden border border-gray-100 bg-gray-50">
                {heatmapData.length > 0 && (
                  <ResponsiveContainer width="100%" height="100%">
                    <Treemap data={heatmapData} dataKey="size" aspectRatio={4/3} stroke="#fff" fill="#f9fafb" content={<TreemapContent />}>
                      <Tooltip content={({active,payload}) => {
                        if(!active||!payload?.length) return null;
                        const p = payload[0].payload;
                        return (<div className="bg-white border border-gray-200 p-3 rounded-xl shadow-lg text-[13px]">
                          <p className="font-normal text-gray-900">{p.hospital} · {p.name}</p>
                          <p className="text-gray-500 mt-1">Risk: <span className={`font-normal ${p.risk>0.6?'text-rose-500':'text-gray-800'}`}>{p.risk}</span></p>
                          <p className="text-[11px] text-gray-400 mt-1">{p.risk>0.8?'🚨 Emergency transfer needed':p.risk>0.5?'⚠️ Monitor closely':'✓ Normal'}</p>
                        </div>);
                      }} />
                    </Treemap>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
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

function InvCard({ d }) {
  const { group, stock, daysCover, usage, status, expiring7d } = d;
  const statusStyles = {
    safe: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200/60', bar: 'bg-gradient-to-r from-emerald-400 to-emerald-500', label: 'Optimal' },
    warning: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200/60', bar: 'bg-gradient-to-r from-amber-400 to-amber-500', label: 'Monitor' },
    critical: { bg: 'bg-rose-50', text: 'text-rose-600', border: 'border-rose-200/60', bar: 'bg-gradient-to-r from-rose-400 to-rose-500', label: 'Critical' }
  };
  const st = statusStyles[status] || statusStyles.safe;
  const pct = Math.min(100, Math.max(8, (stock / 200) * 100));

  return (
    <div className="p-5 rounded-2xl border border-gray-200/80 bg-white hover:border-rose-300 hover:shadow-xl hover:shadow-rose-500/5 hover:-translate-y-1 transition-all duration-300 flex flex-col justify-between group">
      <div>
        <div className="flex justify-between items-center mb-3">
          <div className="flex items-center gap-2">
            <span className="font-outfit text-[22px] font-normal text-gray-900 group-hover:text-rose-600 transition-colors">{group}</span>
          </div>
          <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-normal uppercase tracking-wider border ${st.bg} ${st.text} ${st.border}`}>
            {st.label}
          </span>
        </div>

        <div className="flex justify-between items-baseline mb-1.5">
          <span className="font-sans text-[12px] text-gray-400">Current Stock</span>
          <span className="font-outfit text-[16px] font-normal text-gray-800">{stock} <span className="font-sans text-[12px] text-gray-400">units</span></span>
        </div>

        <div className="h-2.5 w-full bg-gray-100/80 rounded-full my-2 overflow-hidden p-0.5 border border-gray-200/40">
          <div className={`h-full ${st.bar} rounded-full transition-all duration-700 shadow-2xs`} style={{ width: `${pct}%` }} />
        </div>
      </div>

      <div className="bg-gray-50/80 rounded-xl p-3 mt-3 border border-gray-100/80 flex items-center justify-between text-[11.5px]">
        <div className="flex flex-col">
          <span className="font-sans text-[11px] text-gray-400">Coverage</span>
          <span className={`font-outfit font-normal text-[13px] ${status === 'critical' ? 'text-rose-600' : 'text-gray-700'}`}>{daysCover} days</span>
        </div>
        <div className="h-6 w-[1px] bg-gray-200/60" />
        <div className="flex flex-col text-right">
          <span className="font-sans text-[11px] text-gray-400">Daily Burn</span>
          <span className="font-outfit font-normal text-[13px] text-gray-700">{usage} units/d</span>
        </div>
      </div>

      {expiring7d > 0 && (
        <div className="mt-3 flex items-center justify-between text-[11px] font-normal text-amber-700 bg-amber-50/80 border border-amber-200/60 px-3 py-1.5 rounded-xl">
          <span className="flex items-center gap-1.5 font-sans"><Clock className="w-3.5 h-3.5 text-amber-500" /> <span>Expiring (&lt;7d)</span></span>
          <span className="font-outfit text-[12px] font-normal bg-amber-100 px-1.5 py-0.5 rounded-md">{expiring7d} units</span>
        </div>
      )}
    </div>
  );
}

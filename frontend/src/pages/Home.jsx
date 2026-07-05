import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, BarChart3, ShieldCheck, Zap, Timer, HeartPulse, Activity, Layers, CheckCircle } from 'lucide-react';

export default function Home() {
  return (
    <div className="bg-white">

      {/* ═══ HERO with generated background ═══ */}
      <section className="relative min-h-[85vh] flex items-center overflow-hidden">
        {/* Background Image */}
        <div className="absolute inset-0 z-0">
          <img src="/hero-bg.png" alt="" className="w-full h-full object-cover object-center" />
          <div className="absolute inset-0 bg-gradient-to-b from-white/75 via-white/45 to-white" />
        </div>

        <div className="relative z-10 max-w-6xl mx-auto px-6 py-24 text-center">
          <div className="inline-flex items-center gap-2 bg-white/90 backdrop-blur-md text-rose-500 text-[13px] font-normal px-4 py-2 rounded-full mb-8 border border-rose-100 shadow-sm anim-fade-in hover:shadow-md transition-shadow cursor-default">
            <HeartPulse className="w-4 h-4 text-rose-500 animate-pulse" />
            <span>AI-Powered Blood Inventory System</span>
          </div>

          <h1 className="font-outfit text-4xl md:text-6xl font-normal text-gray-900 mb-6 leading-tight anim-fade-in-d1">
            Smart forecasting for<br />
            <span className="text-rose-500">blood supply chains</span>
          </h1>

          <p className="font-sans text-gray-600 text-lg max-w-xl mx-auto mb-10 leading-relaxed anim-fade-in-d2">
            Predict demand, prevent shortages, and optimize 
            distribution across your hospital network.
          </p>

          <div className="flex items-center justify-center gap-3 anim-fade-in-d3">
            <Link to="/dashboard"
              className="inline-flex items-center gap-2 bg-gray-900 text-white text-[14px] font-normal px-7 py-3.5 rounded-xl hover:bg-rose-600 hover:shadow-lg hover:shadow-rose-500/20 hover:-translate-y-0.5 transition-all transform duration-200">
              <span>Open Dashboard</span> <ArrowRight className="w-4 h-4" />
            </Link>
            <a href="#features"
              className="text-[14px] font-normal text-gray-700 bg-white/80 px-6 py-3.5 rounded-xl hover:text-gray-900 hover:bg-white hover:shadow-md transition-all border border-gray-200/80 backdrop-blur">
              Explore Features
            </a>
          </div>
        </div>
      </section>

      {/* ═══ HOW IT WORKS — Premium SaaS Step Cards ═══ */}
      <section id="features" className="max-w-6xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <span className="inline-block text-[12px] font-medium text-rose-500 bg-rose-50 border border-rose-100/80 px-3 py-1 rounded-full uppercase tracking-wider mb-3">Workflow</span>
          <h2 className="font-outfit text-3xl md:text-4xl font-normal text-gray-900">Three steps to smarter inventory</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            { step: 'Step 01', title: 'Monitor & Ingest', desc: 'Continuously ingest stock levels and consumption patterns across all hospital nodes in real-time.', icon: <Activity className="w-5 h-5" /> },
            { step: 'Step 02', title: 'Predict Demand', desc: 'ML models forecast demand 30 days ahead, factoring in seasonality, trauma baselines, and surgical schedules.', icon: <Zap className="w-5 h-5" /> },
            { step: 'Step 03', title: 'Route & Optimize', desc: 'Route surplus inventory to nodes facing depletion automatically, minimizing waste and preventing stockouts.', icon: <ShieldCheck className="w-5 h-5" /> },
          ].map((item, i) => (
            <div key={item.step} className={`relative p-8 rounded-2xl border border-gray-200/80 bg-gradient-to-b from-white to-gray-50/50 group hover:shadow-xl hover:shadow-rose-500/5 hover:border-rose-200 hover:-translate-y-1.5 transition-all duration-300 cursor-default flex flex-col justify-between overflow-hidden anim-fade-in-d${i+1}`}>
              {/* Top Accent Line */}
              <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-rose-300 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              
              <div>
                <div className="flex items-center justify-between mb-6">
                  <div className="w-12 h-12 rounded-xl bg-rose-50 border border-rose-100/60 flex items-center justify-center text-rose-500 group-hover:bg-rose-500 group-hover:text-white group-hover:shadow-md group-hover:shadow-rose-500/20 group-hover:scale-105 transition-all duration-300">
                    {item.icon}
                  </div>
                  <span className="text-[11px] font-medium text-rose-600 bg-rose-50/80 border border-rose-100 px-2.5 py-1 rounded-full tracking-wide">
                    {item.step}
                  </span>
                </div>
                
                <h3 className="font-outfit text-[19px] font-normal text-gray-900 mb-3 group-hover:text-rose-600 transition-colors">{item.title}</h3>
                <p className="font-sans text-[14px] text-gray-600 leading-relaxed">{item.desc}</p>
              </div>

              <div className="mt-6 pt-4 border-t border-gray-100 flex items-center gap-1.5 text-[12px] text-gray-400 group-hover:text-rose-500 transition-colors">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                <span>Automated pipeline</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ═══ FEATURES — Executive SaaS Cards ═══ */}
      <section className="bg-gray-50/80 border-t border-gray-200/70 py-24">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <span className="inline-block text-[12px] font-medium text-rose-500 bg-rose-50 border border-rose-100/80 px-3 py-1 rounded-full uppercase tracking-wider mb-3">Capabilities</span>
            <h2 className="font-outfit text-3xl md:text-4xl font-normal text-gray-900">Built for healthcare operations</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[
              { tag: 'ML FORECASTING', title: 'Demand Forecasting', desc: '30-day predictions using time-series ML models with 94%+ accuracy across all blood groups.', icon: <BarChart3 className="w-6 h-6 text-rose-500" /> },
              { tag: 'REAL-TIME TRACKING', title: 'Network Monitoring', desc: 'Track all 8 blood groups across every hospital node with instant visibility and audit trails.', icon: <HeartPulse className="w-6 h-6 text-rose-500" /> },
              { tag: 'AUTOMATED ALERTS', title: 'Shortage Alerts', desc: 'Instant notifications when any blood group drops below safe coverage thresholds.', icon: <Zap className="w-6 h-6 text-rose-500" /> },
              { tag: 'WASTE REDUCTION', title: 'Expiry Prevention', desc: 'Flag aging units in advance and recommend redistribution to eliminate inventory expiration.', icon: <Timer className="w-6 h-6 text-rose-500" /> },
            ].map((f, idx) => (
              <div key={f.title} className="bg-white p-7 rounded-2xl border border-gray-200/70 hover:border-rose-300 hover:shadow-xl hover:shadow-rose-500/5 hover:-translate-y-1 transition-all duration-300 flex flex-col sm:flex-row gap-5 group cursor-default relative overflow-hidden">
                <div className="w-14 h-14 rounded-2xl bg-rose-50/80 border border-rose-100/60 flex items-center justify-center flex-shrink-0 group-hover:bg-rose-500 group-hover:text-white group-hover:shadow-lg group-hover:shadow-rose-500/20 group-hover:scale-105 transition-all duration-300">
                  {React.cloneElement(f.icon, { className: 'w-6 h-6 transition-colors group-hover:text-white' })}
                </div>
                <div className="flex-1">
                  <span className="text-[10px] font-medium text-rose-500 uppercase tracking-widest block mb-1">{f.tag}</span>
                  <h3 className="font-outfit text-[18px] font-normal text-gray-900 mb-2 group-hover:text-rose-600 transition-colors">{f.title}</h3>
                  <p className="font-sans text-[14px] text-gray-600 leading-relaxed">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ FINAL CTA ═══ */}
      <section className="py-24 border-t border-gray-200/70 bg-gradient-to-b from-white to-rose-50/20">
        <div className="max-w-2xl mx-auto px-6 text-center">
          <div className="w-12 h-12 bg-rose-100/80 text-rose-500 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-sm">
            <Layers className="w-6 h-6" />
          </div>
          <h2 className="font-outfit text-3xl md:text-4xl font-normal text-gray-900 mb-4">
            Ready to optimize your blood inventory?
          </h2>
          <p className="font-sans text-gray-600 text-[16px] mb-8 leading-relaxed">
            Connect your existing hospital management systems and start monitoring in minutes.
          </p>
          <Link to="/dashboard"
            className="inline-flex items-center gap-2 bg-gray-900 text-white text-[14px] font-normal px-8 py-3.5 rounded-xl hover:bg-rose-600 hover:shadow-lg hover:shadow-rose-500/20 hover:-translate-y-0.5 transition-all transform duration-200">
            <span>Open Live Dashboard</span> <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

    </div>
  );
}

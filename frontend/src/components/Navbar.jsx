import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Activity, Menu, X } from 'lucide-react';

export default function Navbar() {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const links = [
    { to: '/', label: 'Home' },
    { to: '/dashboard', label: 'Dashboard' },
  ];

  return (
    <nav className="bg-white/80 backdrop-blur-lg border-b border-gray-100 sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="bg-rose-400 p-1.5 rounded-lg group-hover:bg-rose-500 transition-colors group-hover:scale-105 transform duration-200">
            <Activity className="text-white w-4 h-4" />
          </div>
          <span className="font-outfit text-lg font-normal text-gray-900">BloodIQ</span>
        </Link>
        
        <div className="hidden md:flex items-center gap-8 text-[15px] font-outfit font-normal">
          {links.map(l => (
            <Link key={l.label} to={l.to}
              className={`transition-colors hover:text-rose-500 ${location.pathname === l.to ? 'text-rose-500' : 'text-gray-500'}`}>
              {l.label}
            </Link>
          ))}
        </div>
        
        <button className="md:hidden" onClick={() => setMobileOpen(!mobileOpen)}>
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {mobileOpen && (
        <div className="md:hidden border-t border-gray-100 bg-white px-6 py-4 space-y-3 font-outfit font-normal">
          {links.map(l => (
            <Link key={l.label} to={l.to} onClick={() => setMobileOpen(false)}
              className="block text-[15px] font-normal text-gray-600 hover:text-gray-900 py-2">{l.label}</Link>
          ))}
        </div>
      )}
    </nav>
  );
}

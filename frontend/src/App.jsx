import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';

export default function App() {
  return (
    <div className="min-h-screen bg-white text-gray-700 flex flex-col font-sans">
      <Navbar />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </main>
      <footer className="bg-gray-50 border-t border-gray-200 py-12">
        <div className="max-w-6xl mx-auto px-6 grid grid-cols-1 md:grid-cols-4 gap-8 text-sm text-gray-500">
          <div>
            <h4 className="font-outfit text-gray-800 font-normal mb-3">BloodIQ</h4>
            <p className="leading-relaxed">AI-powered blood inventory intelligence for modern hospital networks.</p>
          </div>
          <div>
            <h4 className="font-normal text-gray-800 mb-3">Product</h4>
            <ul className="space-y-2"><li>Forecasting</li><li>Alert Engine</li><li>Network Map</li><li>API Access</li></ul>
          </div>
          <div>
            <h4 className="font-normal text-gray-800 mb-3">Company</h4>
            <ul className="space-y-2"><li>About</li><li>Careers</li><li>Security</li><li>Contact</li></ul>
          </div>
          <div>
            <h4 className="font-normal text-gray-800 mb-3">Legal</h4>
            <ul className="space-y-2"><li>Privacy</li><li>Terms</li><li>HIPAA</li><li>Compliance</li></ul>
          </div>
        </div>
        <div className="max-w-6xl mx-auto px-6 mt-8 pt-6 border-t border-gray-200 text-xs text-gray-400 text-center">
          &copy; {new Date().getFullYear()} BloodIQ Systems Inc. All rights reserved.
        </div>
      </footer>
    </div>
  );
}

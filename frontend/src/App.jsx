import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import Backtest from './pages/Backtest';

export default function App() {
  return (
    <div className="min-h-screen bg-white text-gray-700 flex flex-col font-sans">
      <Navbar />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/backtest" element={<Backtest />} />
        </Routes>
      </main>
    </div>
  );
}

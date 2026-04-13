import React, { useState } from 'react';
import MediationChecker from './components/MediationChecker';
import IbcChecker from './components/IbcChecker';

function App() {
  const [activeTab, setActiveTab] = useState('mediation'); // 'mediation' or 'ibc'
  return (
    <div className="min-h-screen bg-slate-950 font-sans selection:bg-indigo-500/30 flex items-center justify-center p-6 relative overflow-hidden">
      {/* Background gradients */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-600/20 blur-[120px] rounded-full" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-600/20 blur-[120px] rounded-full" />
      </div>

      <div className="relative z-10 w-full max-w-4xl mx-auto">
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center p-3 mb-4 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 ring-1 ring-white/10 shadow-2xl shadow-indigo-500/20">
            <img src="/vite.svg" alt="Vite logo" className="w-8 h-8 opacity-90 drop-shadow-[0_0_15px_rgba(99,102,241,0.5)]" />
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-slate-200 via-indigo-200 to-slate-200 mb-4">
            Legal Logic Engine
          </h1>
          <p className="text-lg text-slate-400 font-medium max-w-2xl mx-auto">
            Powered by Tau-Prolog running directly in your browser. Evaluate eligibility based on the Indian Mediation Act 2023.
          </p>
        </div>

        <div className="flex justify-center mb-8 bg-slate-900/50 p-1.5 rounded-xl border border-slate-800 backdrop-blur-md inline-flex mx-auto">
          <button
            onClick={() => setActiveTab('mediation')}
            className={`px-6 py-2 rounded-lg text-sm font-semibold transition-all ${
              activeTab === 'mediation' 
                ? 'bg-indigo-500 text-white shadow-md shadow-indigo-500/20' 
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            Mediation Act 2023
          </button>
          <button
            onClick={() => setActiveTab('ibc')}
            className={`px-6 py-2 rounded-lg text-sm font-semibold transition-all ${
              activeTab === 'ibc' 
                ? 'bg-rose-500 text-white shadow-md shadow-rose-500/20' 
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            IBC Section 7
          </button>
        </div>

        {/* Form and Logic integration */}
        <div className="transition-all duration-300">
          {activeTab === 'mediation' ? <MediationChecker /> : <IbcChecker />}
        </div>
      </div>
    </div>
  );
}

export default App;

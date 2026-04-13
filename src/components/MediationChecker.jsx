import React, { useState } from 'react';
import { checkMediation } from '../logic/prologEngine';
import { SwitchCamera, DollarSign, FileText, CheckCircle2, XCircle, AlertTriangle, Scale } from 'lucide-react';

export default function MediationChecker() {
  const [isCommercial, setIsCommercial] = useState(false);
  const [value, setValue] = useState('');
  const [hasAgreement, setHasAgreement] = useState(false);
  const [isCriminal, setIsCriminal] = useState(false);
  const [isConstitutional, setIsConstitutional] = useState(false);
  
  const [status, setStatus] = useState(null); // 'idle', 'loading', 'eligible', 'ineligible', 'error'
  const [reason, setReason] = useState('');

  const handleCheck = async () => {
    setStatus('loading');
    setReason('');

    try {
      // Build the Prolog facts string based on user input
      let facts = '';
      if (isCommercial) facts += 'is_commercial(true).\n';
      // Tau-prolog requires variables/values in facts to be formatted correctly.
      // If it's a number, it can be passed directly.
      const parsedValue = parseInt(value, 10);
      if (!isNaN(parsedValue)) {
        facts += `value(${parsedValue}).\n`;
      }
      if (hasAgreement) facts += 'pre_litigation_agreement(true).\n';
      if (isCriminal) facts += 'is_criminal(true).\n';
      if (isConstitutional) facts += 'is_constitutional_matter(true).\n';

      // We need to pass the numeric value to the checkMediation query if it's commercial
      // We will adjust our prolog logic slightly in the engine call.
      // Actually, since our mediation.pl rules expect `is_eligible(Value)`, we can 
      // check it by querying `is_eligible(${parsedValue || 0}).`
      
      const isEligible = await checkMediation(facts, parsedValue || 0);

      if (isEligible) {
        setStatus('eligible');
        setReason('This dispute is eligible for mediation under the Indian Mediation Act 2023.');
      } else {
        setStatus('ineligible');
        
        // Determine the reason for UI feedback
        if (isCriminal || isConstitutional) {
           setReason('Criminal and Constitutional matters cannot be mediated.');
        } else if (isCommercial && (isNaN(parsedValue) || parsedValue < 50000)) {
           setReason('Commercial disputes require a minimum value of ₹50,000 to be eligible.');
        } else {
           setReason('This dispute does not meet the criteria for mediation. A pre-litigation agreement or a qualifying commercial dispute is required.');
        }
      }
    } catch (err) {
      console.error(err);
      setStatus('error');
      setReason(typeof err === 'string' ? err : 'An unexpected error occurred while evaluating the logic.');
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-6 bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-3xl shadow-2xl">
      <div className="flex items-center gap-4 mb-8">
        <div className="p-3 bg-indigo-500/20 text-indigo-400 rounded-2xl ring-1 ring-indigo-500/30">
          <Scale className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-slate-100">Mediation Eligibility Checker</h2>
          <p className="text-sm text-slate-400 mt-1">Based on the Indian Mediation Act 2023</p>
        </div>
      </div>

      <div className="space-y-6">
        {/* Toggle Controls */}
        <div className="space-y-4">
          <label className="flex items-center justify-between p-4 rounded-2xl bg-slate-950/50 border border-slate-800/80 cursor-pointer hover:bg-slate-800/50 transition-colors">
            <div className="flex items-center gap-3">
              <SwitchCamera className="w-5 h-5 text-slate-400" />
              <div>
                <div className="font-semibold text-slate-200">Commercial Dispute</div>
                <div className="text-xs text-slate-500">Does this dispute involve commercial transactions?</div>
              </div>
            </div>
            <input
              type="checkbox"
              className="w-5 h-5 rounded border-slate-700 text-indigo-500 focus:ring-indigo-500/50 bg-slate-900"
              checked={isCommercial}
              onChange={(e) => setIsCommercial(e.target.checked)}
            />
          </label>

          {isCommercial && (
            <div className="relative animate-in fade-in slide-in-from-top-2 duration-300">
              <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">
                <DollarSign className="w-4 h-4" />
              </div>
              <input
                type="number"
                placeholder="Dispute Value (₹)"
                className="w-full bg-slate-950/50 border border-slate-800/80 rounded-2xl py-4 pl-12 pr-4 text-sm font-medium text-slate-200 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-transparent transition-all"
                value={value}
                onChange={(e) => setValue(e.target.value)}
              />
            </div>
          )}

          <label className="flex items-center justify-between p-4 rounded-2xl bg-slate-950/50 border border-slate-800/80 cursor-pointer hover:bg-slate-800/50 transition-colors">
            <div className="flex items-center gap-3">
              <FileText className="w-5 h-5 text-slate-400" />
              <div>
                <div className="font-semibold text-slate-200">Pre-existing Agreement</div>
                <div className="text-xs text-slate-500">Is there a pre-litigation mediation agreement?</div>
              </div>
            </div>
            <input
              type="checkbox"
              className="w-5 h-5 rounded border-slate-700 text-indigo-500 focus:ring-indigo-500/50 bg-slate-900"
              checked={hasAgreement}
              onChange={(e) => setHasAgreement(e.target.checked)}
            />
          </label>

          <div className="grid grid-cols-2 gap-4">
             <label className="flex items-center gap-3 p-4 rounded-2xl bg-red-500/5 border border-red-500/10 cursor-pointer hover:bg-red-500/10 transition-colors">
              <input
                type="checkbox"
                className="w-4 h-4 rounded border-red-900/50 text-red-500 focus:ring-red-500/50 bg-slate-900"
                checked={isCriminal}
                onChange={(e) => setIsCriminal(e.target.checked)}
              />
              <span className="text-sm font-medium text-red-200/80">Criminal Matter</span>
            </label>
            <label className="flex items-center gap-3 p-4 rounded-2xl bg-red-500/5 border border-red-500/10 cursor-pointer hover:bg-red-500/10 transition-colors">
              <input
                type="checkbox"
                className="w-4 h-4 rounded border-red-900/50 text-red-500 focus:ring-red-500/50 bg-slate-900"
                checked={isConstitutional}
                onChange={(e) => setIsConstitutional(e.target.checked)}
              />
              <span className="text-sm font-medium text-red-200/80">Constitutional Matter</span>
            </label>
          </div>
        </div>

        {/* Action Button */}
        <button
          onClick={handleCheck}
          disabled={status === 'loading'}
          className="w-full py-4 px-6 rounded-2xl bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 text-white font-bold text-shadow-sm shadow-xl shadow-indigo-500/20 transition-all hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {status === 'loading' ? 'Evaluating Logic...' : 'Check Eligibility'}
        </button>

        {/* Status Card */}
        {status && status !== 'loading' && (
          <div className={`p-5 rounded-2xl border animate-in slide-in-from-bottom-2 duration-300 ${
            status === 'eligible' 
              ? 'bg-emerald-500/10 border-emerald-500/20' 
              : status === 'ineligible' 
                ? 'bg-red-500/10 border-red-500/20'
                : 'bg-amber-500/10 border-amber-500/20'
          }`}>
            <div className="flex items-start gap-4">
              <div className="mt-1">
                {status === 'eligible' && <CheckCircle2 className="w-6 h-6 text-emerald-400" />}
                {status === 'ineligible' && <XCircle className="w-6 h-6 text-red-400" />}
                {status === 'error' && <AlertTriangle className="w-6 h-6 text-amber-400" />}
              </div>
              <div>
                <h3 className={`font-bold text-lg ${
                  status === 'eligible' ? 'text-emerald-300' : status === 'ineligible' ? 'text-red-300' : 'text-amber-300'
                }`}>
                  {status === 'eligible' ? 'Eligible for Mediation' : status === 'ineligible' ? 'Not Eligible' : 'Error'}
                </h3>
                <p className={`text-sm mt-1 leading-relaxed ${
                  status === 'eligible' ? 'text-emerald-200/70' : status === 'ineligible' ? 'text-red-200/70' : 'text-amber-200/70'
                }`}>
                  {reason}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

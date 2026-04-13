import React, { useState } from 'react';
import { checkIbcSection7 } from '../logic/ibcEngine';
import { Building2, FileWarning, CheckCircle2, XCircle, AlertTriangle, ShieldAlert } from 'lucide-react';

export default function IbcChecker() {
  const [defaultOccurred, setDefaultOccurred] = useState(false);
  const [appComplete, setAppComplete] = useState(true);
  const [disciplinaryPending, setDisciplinaryPending] = useState(false);

  const [status, setStatus] = useState(null); 
  const [reason, setReason] = useState('');
  const [aaAction, setAaAction] = useState(null);

  const handleCheck = async () => {
    setStatus('loading');
    setReason('');
    setAaAction(null);

    try {
      // Build the Prolog facts string based on user input
      let facts = '';
      
      // Default Logic
      if (defaultOccurred) facts += 'default_has_occurred.\n';
      else facts += 'default_not_occurred.\n';

      // Application Completeness
      if (appComplete) facts += 'application_is_complete(user_app).\n';
      else facts += 'application_is_incomplete(user_app).\n';
      
      // Disciplinary Logic
      if (!disciplinaryPending) facts += 'no_disciplinary_proceedings_pending(proposed_irp(user_app)).\n';
      else facts += 'disciplinary_proceedings_pending(proposed_irp(user_app)).\n';

      const result = await checkIbcSection7(facts);

      if (result.isValid) {
        setStatus(result.aaAction === 'admit' ? 'eligible' : 'ineligible');
        setAaAction(result.aaAction);
        setReason(result.message);
      } else {
        setStatus('ineligible');
        setAaAction(null);
        setReason(result.message);
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
        <div className="p-3 bg-rose-500/20 text-rose-400 rounded-2xl ring-1 ring-rose-500/30">
          <Building2 className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-slate-100">IBC Section 7 Authority Rules</h2>
          <p className="text-sm text-slate-400 mt-1">Adjudicating Authority Action Simulator</p>
        </div>
      </div>

      <div className="space-y-6">
        
        {/* Basic Validations */}
        <div className="p-4 rounded-2xl border border-slate-800 bg-slate-950/30">
           <h3 className="text-sm font-semibold text-slate-300 mb-4 px-1 uppercase tracking-wider">Financial Default Status</h3>
           <label className="flex items-center justify-between p-3 rounded-xl hover:bg-slate-800/30 transition-colors cursor-pointer">
            <div className="flex items-center gap-3">
              <FileWarning className="w-4 h-4 text-rose-400" />
              <span className="text-sm font-medium text-slate-200">Has Default Occurred?</span>
            </div>
            <input type="checkbox" className="w-4 h-4 rounded border-slate-700 text-rose-500 focus:ring-rose-500/50 bg-slate-900" checked={defaultOccurred} onChange={(e) => setDefaultOccurred(e.target.checked)} />
          </label>
        </div>

        {/* Admission Logic */}
        <div className="p-4 rounded-2xl border border-slate-800 bg-slate-950/30 space-y-2">
          <h3 className="text-sm font-semibold text-slate-300 mb-3 px-1 uppercase tracking-wider">Application Review</h3>
          
          <label className="flex items-center justify-between p-3 rounded-xl hover:bg-slate-800/30 transition-colors cursor-pointer">
            <span className="text-sm font-medium text-slate-200">Is the Application Complete in Form & Manner?</span>
            <input type="checkbox" className="w-4 h-4 rounded border-slate-700 text-cyan-500 bg-slate-900" checked={appComplete} onChange={(e) => setAppComplete(e.target.checked)} />
          </label>
          <label className="flex items-center justify-between p-3 rounded-xl hover:bg-slate-800/30 transition-colors cursor-pointer">
            <div className="flex items-center gap-2">
               <ShieldAlert className="w-4 h-4 text-amber-500" />
               <span className="text-sm font-medium text-slate-200">Disciplinary Proceedings Pending against proposed IRP?</span>
            </div>
            <input type="checkbox" className="w-4 h-4 rounded border-slate-700 text-amber-500 bg-slate-900" checked={disciplinaryPending} onChange={(e) => setDisciplinaryPending(e.target.checked)} />
          </label>
        </div>


        {/* Action Button */}
        <button
          onClick={handleCheck}
          disabled={status === 'loading'}
          className="w-full py-4 px-6 rounded-2xl bg-gradient-to-r from-rose-500 to-indigo-600 hover:from-rose-400 hover:to-indigo-500 text-white font-bold text-shadow-sm shadow-xl shadow-rose-500/20 transition-all hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {status === 'loading' ? 'Evaluating Logic...' : 'Evaluate Admissibility'}
        </button>

        {/* Status Card */}
        {status && status !== 'loading' && (
          <div className={`p-5 rounded-2xl border animate-in slide-in-from-bottom-2 duration-300 ${
            status === 'eligible' && aaAction === 'admit'
              ? 'bg-emerald-500/10 border-emerald-500/20' 
              : 'bg-red-500/10 border-red-500/20'
          }`}>
            <div className="flex items-start gap-4">
              <div className="mt-1">
                {status === 'eligible' && aaAction === 'admit' && <CheckCircle2 className="w-6 h-6 text-emerald-400" />}
                {status === 'ineligible' && <XCircle className="w-6 h-6 text-red-400" />}
                {status === 'error' && <AlertTriangle className="w-6 h-6 text-orange-400" />}
              </div>
              <div>
                <h3 className={`font-bold text-lg ${
                  status === 'eligible' && aaAction === 'admit' ? 'text-emerald-300' 
                  : 'text-red-300'
                }`}>
                  {status === 'eligible' ? `Admitted` : status === 'ineligible' ? 'Rejected' : 'Error'}
                </h3>
                <p className={`text-sm mt-1 leading-relaxed ${
                  status === 'eligible' && aaAction === 'admit' ? 'text-emerald-200/70' 
                  : 'text-red-200/70'
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

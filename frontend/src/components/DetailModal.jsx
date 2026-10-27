import React from 'react';
import { X, CheckCircle2, XCircle, AlertTriangle, Clock, Award, Image as ImageIcon, ExternalLink } from 'lucide-react';

export default function DetailModal({ testCase, onClose }) {
  if (!testCase) return null;

  const status = testCase.Status || 'PENDING';
  const screenshotUrl = testCase.Screenshot ? `/api/screenshots/${testCase.Screenshot.split('/').pop()}` : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
      <div 
        className="bg-white dark:bg-stone-900 border border-stone-200 dark:border-stone-800 rounded-2xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-stone-200 dark:border-stone-800 flex items-center justify-between shrink-0 bg-stone-50/50 dark:bg-stone-800/40">
          <div className="flex items-center space-x-3">
            <span className="font-mono font-bold text-base text-stone-900 dark:text-white">
              {testCase.TestID}
            </span>
            <span className="px-2 py-0.5 rounded text-xs font-medium bg-stone-200 dark:bg-stone-700 text-stone-700 dark:text-stone-300">
              {testCase.Category || 'General'}
            </span>
            {testCase.Conversation && (
              <span className="px-2 py-0.5 rounded text-xs font-mono bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300">
                Conv: {testCase.Conversation}
              </span>
            )}
          </div>

          <div className="flex items-center space-x-2">
            {status === 'PASS' && (
              <span className="flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>PASS</span>
              </span>
            )}
            {status === 'FAIL' && (
              <span className="flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold bg-red-100 text-red-800 dark:bg-red-950/80 dark:text-red-300">
                <XCircle className="w-3.5 h-3.5" />
                <span>FAIL</span>
              </span>
            )}
            {(status === 'ERROR' || status === 'TIMEOUT') && (
              <span className="flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>{status}</span>
              </span>
            )}
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full hover:bg-stone-200 dark:hover:bg-stone-800 text-stone-500 flex items-center justify-center transition"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-4 text-xs">
          {/* Query (Bot Prompt) */}
          <div>
            <label className="font-semibold text-stone-500 dark:text-stone-400 uppercase tracking-wider text-[10px]">
              Query (Bot Prompt)
            </label>
            <div className="mt-1 p-3 rounded-lg bg-stone-100 dark:bg-stone-800 text-stone-900 dark:text-white font-medium text-sm">
              {testCase.Query || testCase.Question}
            </div>
          </div>

          {/* Expected vs Actual Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="font-semibold text-stone-500 dark:text-stone-400 uppercase tracking-wider text-[10px]">
                Expected Answer (Forward to Bot)
              </label>
              <div className="mt-1 p-3 rounded-lg bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300 min-h-[90px] whitespace-pre-line">
                {testCase.ExpectedAnswer || <span className="text-stone-400 italic">None specified</span>}
              </div>
            </div>

            <div>
              <label className="font-semibold text-stone-500 dark:text-stone-400 uppercase tracking-wider text-[10px]">
                Actual Answer (Captured by Bot)
              </label>
              <div className="mt-1 p-3 rounded-lg bg-stone-100 dark:bg-stone-800 text-stone-800 dark:text-stone-200 min-h-[90px] whitespace-pre-line font-mono text-[11px]">
                {testCase.ActualAnswer || <span className="text-stone-400 italic">No reply recorded</span>}
              </div>
            </div>
          </div>

          {/* Optional Subsequent Bot Prompt */}
          {testCase.NextBotPrompt && (
            <div>
              <label className="font-semibold text-stone-500 dark:text-stone-400 uppercase tracking-wider text-[10px]">
                Subsequent Bot Prompt / Next Turn
              </label>
              <div className="mt-1 p-3 rounded-lg bg-stone-50 dark:bg-stone-800/60 border border-stone-200 dark:border-stone-700/60 text-stone-700 dark:text-stone-300 text-xs whitespace-pre-line">
                {testCase.NextBotPrompt}
              </div>
            </div>
          )}

          {/* Metrics & Reason */}
          <div className="p-3.5 rounded-xl border border-stone-200 dark:border-stone-800 bg-stone-50 dark:bg-stone-800/50 space-y-2">
            <div className="flex items-center justify-between text-stone-600 dark:text-stone-300">
              <div className="flex items-center space-x-1.5">
                <Award className="w-4 h-4 text-amber-500" />
                <span className="font-semibold">Comparison Score:</span>
                <span className="font-bold text-stone-900 dark:text-white">
                  {testCase.Score !== null && testCase.Score !== undefined ? `${testCase.Score}%` : 'N/A'}
                </span>
                {testCase.Mode && (
                  <span className="text-[10px] text-stone-400 font-mono">({testCase.Mode} mode)</span>
                )}
              </div>

              <div className="flex items-center space-x-1 text-stone-600 dark:text-stone-300">
                <Clock className="w-3.5 h-3.5 text-stone-400" />
                <span>Response Time:</span>
                <span className="font-bold text-stone-900 dark:text-white font-mono">
                  {testCase.ResponseTimeMs || 0} ms
                </span>
              </div>
            </div>

            {testCase.Reason && (
              <div className="pt-2 border-t border-stone-200 dark:border-stone-700 text-stone-600 dark:text-stone-300">
                <span className="font-semibold text-stone-500 dark:text-stone-400">Judge Reason: </span>
                <span>{testCase.Reason}</span>
              </div>
            )}
          </div>

          {/* Failure Screenshot Preview */}
          {screenshotUrl && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="font-semibold text-stone-500 dark:text-stone-400 uppercase tracking-wider text-[10px] flex items-center space-x-1">
                  <ImageIcon className="w-3.5 h-3.5 text-red-500" />
                  <span>Failure Screenshot</span>
                </label>
                <a
                  href={screenshotUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-orange-600 hover:underline flex items-center space-x-0.5 text-[11px]"
                >
                  <span>Open Full Size</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
              <div className="border border-stone-200 dark:border-stone-800 rounded-lg overflow-hidden bg-stone-950/20 max-h-56 flex items-center justify-center">
                <img
                  src={screenshotUrl}
                  alt="Failure Screenshot"
                  className="max-h-56 object-contain w-auto mx-auto"
                />
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-stone-200 dark:border-stone-800 flex justify-end shrink-0 bg-stone-50 dark:bg-stone-800/40">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-stone-200 dark:bg-stone-700 hover:bg-stone-300 dark:hover:bg-stone-600 text-stone-800 dark:text-stone-200 font-medium text-xs transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

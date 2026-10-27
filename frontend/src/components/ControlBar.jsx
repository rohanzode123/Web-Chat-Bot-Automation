import React from 'react';
import { Play, Pause, Square, RefreshCcw, Download, Sliders, FileSpreadsheet, FileText } from 'lucide-react';

export default function ControlBar({
  isRunning,
  isPaused,
  onRunAll,
  onRunSelected,
  onPause,
  onResume,
  onStop,
  onRerunFailed,
  hasFailedTests,
  selectedCount,
  totalCount,
  speedConfig,
  setSpeedConfig,
  onExportExcel,
  onExportCsv,
  onDownloadTemplate
}) {
  return (
    <div className="bg-stone-50 dark:bg-stone-900/60 border-y border-stone-200 dark:border-stone-800 px-6 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs">
      {/* Run Action Buttons */}
      <div className="flex items-center space-x-2">
        {!isRunning ? (
          <>
            <button
              onClick={onRunAll}
              disabled={totalCount === 0}
              className="flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-orange-600 hover:bg-orange-500 active:scale-95 text-white font-semibold shadow-sm transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play className="w-4 h-4 fill-current" />
              <span>Run All ({totalCount})</span>
            </button>

            <button
              onClick={onRunSelected}
              disabled={selectedCount === 0}
              className="flex items-center space-x-1.5 px-3 py-2 rounded-lg bg-stone-200 dark:bg-stone-800 hover:bg-stone-300 dark:hover:bg-stone-700 text-stone-800 dark:text-stone-200 font-medium transition disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Play className="w-3.5 h-3.5" />
              <span>Run Selected ({selectedCount})</span>
            </button>
          </>
        ) : (
          <>
            {isPaused ? (
              <button
                onClick={onResume}
                className="flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 active:scale-95 text-white font-semibold shadow-sm transition"
              >
                <Play className="w-4 h-4 fill-current" />
                <span>Resume</span>
              </button>
            ) : (
              <button
                onClick={onPause}
                className="flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 active:scale-95 text-white font-semibold shadow-sm transition"
              >
                <Pause className="w-4 h-4 fill-current" />
                <span>Pause</span>
              </button>
            )}

            <button
              onClick={onStop}
              className="flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 active:scale-95 text-white font-semibold shadow-sm transition"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              <span>Stop</span>
            </button>
          </>
        )}

        {hasFailedTests && !isRunning && (
          <button
            onClick={onRerunFailed}
            className="flex items-center space-x-1.5 px-3 py-2 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-700 dark:text-amber-400 border border-amber-500/30 font-medium transition"
          >
            <RefreshCcw className="w-3.5 h-3.5" />
            <span>Re-run Failed</span>
          </button>
        )}
      </div>

      {/* Speed Settings & Downloads */}
      <div className="flex items-center space-x-4">
        {/* Speed Adjustment */}
        <div className="flex items-center space-x-2 bg-stone-100 dark:bg-stone-800/80 border border-stone-200 dark:border-stone-700 rounded-lg px-3 py-1.5 shadow-2xs">
          <Sliders className="w-3.5 h-3.5 text-stone-400" />
          <span className="text-stone-600 dark:text-stone-300 font-medium text-xs">Typing Delay:</span>
          <select
            value={speedConfig.typing_delay_ms}
            onChange={(e) => setSpeedConfig({ ...speedConfig, typing_delay_ms: Number(e.target.value) })}
            className="bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 border border-stone-300 dark:border-stone-700 rounded px-2 py-0.5 font-medium text-xs focus:outline-hidden cursor-pointer"
          >
            <option value={15} className="bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100">Fast (15ms)</option>
            <option value={40} className="bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100">Normal (40ms)</option>
            <option value={80} className="bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100">Human (80ms)</option>
            <option value={0} className="bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100">Instant (0ms)</option>
          </select>

          <span className="text-stone-300 dark:text-stone-600">|</span>

          <span className="text-stone-600 dark:text-stone-300 font-medium text-xs">Wait:</span>
          <select
            value={speedConfig.message_delay_ms}
            onChange={(e) => setSpeedConfig({ ...speedConfig, message_delay_ms: Number(e.target.value) })}
            className="bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100 border border-stone-300 dark:border-stone-700 rounded px-2 py-0.5 font-medium text-xs focus:outline-hidden cursor-pointer"
          >
            <option value={400} className="bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100">0.4s</option>
            <option value={800} className="bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100">0.8s</option>
            <option value={1200} className="bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100">1.2s</option>
            <option value={1500} className="bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100">1.5s</option>
            <option value={3000} className="bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-100">3.0s</option>
          </select>
        </div>

        {/* Export / Template Buttons */}
        <div className="flex items-center space-x-1.5">
          <button
            onClick={onExportExcel}
            title="Download Results as Excel (.xlsx)"
            className="flex items-center space-x-1 px-2.5 py-1.5 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 hover:bg-stone-50 dark:hover:bg-stone-700 text-stone-700 dark:text-stone-200 transition"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
            <span className="hidden sm:inline">.xlsx</span>
          </button>

          <button
            onClick={onExportCsv}
            title="Download Results as CSV"
            className="flex items-center space-x-1 px-2.5 py-1.5 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 hover:bg-stone-50 dark:hover:bg-stone-700 text-stone-700 dark:text-stone-200 transition"
          >
            <FileText className="w-3.5 h-3.5 text-blue-600" />
            <span className="hidden sm:inline">.csv</span>
          </button>

          <button
            onClick={onDownloadTemplate}
            title="Download Sample Test Cases Template"
            className="flex items-center space-x-1 px-2.5 py-1.5 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 hover:bg-stone-50 dark:hover:bg-stone-700 text-stone-700 dark:text-stone-200 transition"
          >
            <Download className="w-3.5 h-3.5 text-orange-500" />
            <span className="hidden md:inline">Sample Template</span>
          </button>
        </div>
      </div>
    </div>
  );
}

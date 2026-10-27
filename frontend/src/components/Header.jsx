import React from 'react';
import { Bot, Settings, Sun, Moon, Link as LinkIcon, Radio, Check, Edit2 } from 'lucide-react';

export default function Header({
  botUrl,
  setBotUrl,
  isEditingUrl,
  setIsEditingUrl,
  onOpenSettings,
  darkMode,
  setDarkMode,
  wsConnected
}) {
  return (
    <header className="h-16 border-b border-stone-200 dark:border-stone-800 bg-white/80 dark:bg-stone-900/80 backdrop-blur-md px-6 flex items-center justify-between z-20 shrink-0 transition-colors">
      {/* Brand & Logo */}
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-600 via-orange-500 to-amber-400 flex items-center justify-center text-white shadow-md shadow-orange-500/20">
          <Bot className="w-6 h-6" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="font-bold text-lg text-stone-900 dark:text-white tracking-tight leading-tight">
              Bot Test Studio
            </h1>
            <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-orange-100 text-orange-800 dark:bg-orange-950/60 dark:text-orange-400 border border-orange-200 dark:border-orange-800">
              v2.0
            </span>
          </div>
          <p className="text-xs text-stone-500 dark:text-stone-400">
            Automated Conversational QA Runner
          </p>
        </div>
      </div>

      {/* Bot URL Bar */}
      <div className="flex-1 max-w-xl mx-6 hidden md:block">
        <div className="flex items-center px-3 py-1.5 rounded-lg border border-stone-200 dark:border-stone-700 bg-stone-50 dark:bg-stone-800/60 focus-within:ring-2 focus-within:ring-orange-500/30 transition">
          <LinkIcon className="w-4 h-4 text-stone-400 dark:text-stone-500 shrink-0 mr-2" />
          <span className="text-xs font-semibold text-stone-400 dark:text-stone-500 shrink-0 mr-1.5 select-none">
            Target URL:
          </span>
          {isEditingUrl ? (
            <input
              type="text"
              value={botUrl}
              onChange={(e) => setBotUrl(e.target.value)}
              className="text-xs text-stone-800 dark:text-stone-200 bg-transparent w-full focus:outline-hidden font-mono"
              placeholder="Enter Target Bot URL (e.g. https://...)"
            />
          ) : (
            <span className="text-xs text-stone-700 dark:text-stone-300 truncate font-mono select-all flex-1">
              {botUrl}
            </span>
          )}
          <button
            onClick={() => setIsEditingUrl(!isEditingUrl)}
            className="ml-2 text-stone-400 hover:text-stone-700 dark:hover:text-stone-200 text-xs shrink-0 p-1"
            title={isEditingUrl ? "Save URL" : "Edit URL"}
          >
            {isEditingUrl ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Edit2 className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Right Controls: WS status, Dark Mode, Settings */}
      <div className="flex items-center space-x-3">
        {/* WebSocket Status Indicator */}
        <div
          className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
            wsConnected
              ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800/60"
              : "bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800/60"
          }`}
          title={wsConnected ? "Connected to backend runner" : "Disconnected from backend"}
        >
          <span className={`w-2 h-2 rounded-full ${wsConnected ? "bg-emerald-500 animate-pulse" : "bg-red-500"}`} />
          <span className="hidden sm:inline">{wsConnected ? "Connected" : "Disconnected"}</span>
        </div>

        {/* Dark/Light mode toggle */}
        <button
          onClick={() => setDarkMode(!darkMode)}
          className="w-9 h-9 rounded-lg border border-stone-200 dark:border-stone-700 hover:bg-stone-100 dark:hover:bg-stone-800 flex items-center justify-center text-stone-600 dark:text-stone-300 transition"
          title={darkMode ? "Switch to light mode" : "Switch to dark mode"}
        >
          {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-stone-700" />}
        </button>

        {/* Settings button */}
        <button
          onClick={onOpenSettings}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-stone-200 dark:border-stone-700 hover:bg-stone-100 dark:hover:bg-stone-800 text-stone-700 dark:text-stone-200 text-xs font-medium transition"
        >
          <Settings className="w-4 h-4" />
          <span className="hidden sm:inline">Settings</span>
        </button>
      </div>
    </header>
  );
}

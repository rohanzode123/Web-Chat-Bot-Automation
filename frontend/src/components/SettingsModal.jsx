import React, { useState } from 'react';
import { X, Save, Plus, Trash2, Sliders, Shield, Key, Eye } from 'lucide-react';

export default function SettingsModal({
  isOpen,
  onClose,
  config,
  onSaveConfig
}) {
  if (!isOpen) return null;

  const [formData, setFormData] = useState({
    bot_url: config?.bot?.url || "",
    headless: config?.bot?.headless ?? true,
    mode: config?.comparison?.mode || "semantic",
    rapidfuzz_threshold: config?.comparison?.rapidfuzz_threshold ?? 80,
    llm_provider: config?.comparison?.llm_provider || "auto",
    bot_reply_timeout_s: config?.timeouts?.bot_reply_timeout_s ?? 30,
    quiet_period_s: config?.timeouts?.quiet_period_s ?? 3.0,
    typing_delay_ms: config?.timeouts?.typing_delay_ms ?? 40,
    pre_messages: config?.pre_messages || []
  });

  const [newPreMsg, setNewPreMsg] = useState('');

  const handleAddPreMsg = () => {
    if (newPreMsg.trim()) {
      setFormData({
        ...formData,
        pre_messages: [...formData.pre_messages, newPreMsg.trim()]
      });
      setNewPreMsg('');
    }
  };

  const handleRemovePreMsg = (idx) => {
    setFormData({
      ...formData,
      pre_messages: formData.pre_messages.filter((_, i) => i !== idx)
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSaveConfig({
      bot: {
        ...config.bot,
        url: formData.bot_url,
        headless: formData.headless
      },
      comparison: {
        ...config.comparison,
        mode: formData.mode,
        rapidfuzz_threshold: Number(formData.rapidfuzz_threshold),
        llm_provider: formData.llm_provider
      },
      timeouts: {
        ...config.timeouts,
        bot_reply_timeout_s: Number(formData.bot_reply_timeout_s),
        quiet_period_s: Number(formData.quiet_period_s),
        typing_delay_ms: Number(formData.typing_delay_ms)
      },
      pre_messages: formData.pre_messages
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
      <div className="bg-white dark:bg-stone-900 border border-stone-200 dark:border-stone-800 rounded-2xl max-w-xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-6 py-4 border-b border-stone-200 dark:border-stone-800 flex items-center justify-between shrink-0 bg-stone-50/50 dark:bg-stone-800/40">
          <div className="flex items-center space-x-2">
            <Sliders className="w-5 h-5 text-orange-500" />
            <h2 className="font-bold text-base text-stone-900 dark:text-white">Runner & Widget Settings</h2>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full hover:bg-stone-200 dark:hover:bg-stone-800 text-stone-500 flex items-center justify-center transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto space-y-5 text-xs flex-1">
          {/* Bot Preview URL */}
          <div>
            <label className="font-semibold text-stone-700 dark:text-stone-300">Bot Preview URL</label>
            <input
              type="text"
              value={formData.bot_url}
              onChange={(e) => setFormData({ ...formData, bot_url: e.target.value })}
              className="mt-1 w-full px-3 py-2 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 text-stone-900 dark:text-white font-mono text-xs focus:ring-1 focus:ring-orange-500 focus:outline-hidden"
              required
            />
          </div>

          {/* Comparison Mode & RapidFuzz Threshold */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="font-semibold text-stone-700 dark:text-stone-300">Answer Comparison Mode</label>
              <select
                value={formData.mode}
                onChange={(e) => setFormData({ ...formData, mode: e.target.value })}
                className="mt-1 w-full px-3 py-2 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 text-stone-900 dark:text-white font-medium focus:ring-1 focus:ring-orange-500 focus:outline-hidden"
              >
                <option value="semantic">Semantic (RapidFuzz / LLM)</option>
                <option value="contains">Contains (Keyword / Substring)</option>
                <option value="exact">Exact (Normalized Match)</option>
              </select>
            </div>

            <div>
              <label className="font-semibold text-stone-700 dark:text-stone-300">
                Fuzzy Match Threshold: {formData.rapidfuzz_threshold}%
              </label>
              <input
                type="range"
                min="50"
                max="100"
                step="5"
                value={formData.rapidfuzz_threshold}
                onChange={(e) => setFormData({ ...formData, rapidfuzz_threshold: e.target.value })}
                className="mt-2.5 w-full accent-orange-600 cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-stone-400">
                <span>50% (Lenient)</span>
                <span>80% (Default)</span>
                <span>100% (Strict)</span>
              </div>
            </div>
          </div>

          {/* Headless & Timeouts */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="font-semibold text-stone-700 dark:text-stone-300">Headless Mode</label>
              <select
                value={formData.headless ? "true" : "false"}
                onChange={(e) => setFormData({ ...formData, headless: e.target.value === "true" })}
                className="mt-1 w-full px-3 py-2 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 text-stone-900 dark:text-white font-medium focus:ring-1 focus:ring-orange-500 focus:outline-hidden"
              >
                <option value="true">Headless (Background)</option>
                <option value="false">Headed (Visible Window)</option>
              </select>
            </div>

            <div>
              <label className="font-semibold text-stone-700 dark:text-stone-300">Quiet Period (s)</label>
              <input
                type="number"
                step="0.5"
                min="1"
                max="10"
                value={formData.quiet_period_s}
                onChange={(e) => setFormData({ ...formData, quiet_period_s: e.target.value })}
                className="mt-1 w-full px-3 py-2 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 text-stone-900 dark:text-white focus:ring-1 focus:ring-orange-500 focus:outline-hidden"
              />
            </div>

            <div>
              <label className="font-semibold text-stone-700 dark:text-stone-300">Max Timeout (s)</label>
              <input
                type="number"
                min="5"
                max="90"
                value={formData.bot_reply_timeout_s}
                onChange={(e) => setFormData({ ...formData, bot_reply_timeout_s: e.target.value })}
                className="mt-1 w-full px-3 py-2 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 text-stone-900 dark:text-white focus:ring-1 focus:ring-orange-500 focus:outline-hidden"
              />
            </div>
          </div>

          {/* Setup / Pre-Messages */}
          <div>
            <label className="font-semibold text-stone-700 dark:text-stone-300">
              Setup Pre-Messages (sent automatically in fresh chat sessions)
            </label>
            <p className="text-[11px] text-stone-400 mt-0.5">
              Useful if your bot requires Name, Phone, or Email before accepting inquiries.
            </p>
            <div className="flex items-center space-x-2 mt-2">
              <input
                type="text"
                placeholder="e.g. John Doe"
                value={newPreMsg}
                onChange={(e) => setNewPreMsg(e.target.value)}
                className="flex-1 px-3 py-1.5 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 text-stone-900 dark:text-white text-xs focus:ring-1 focus:ring-orange-500 focus:outline-hidden"
              />
              <button
                type="button"
                onClick={handleAddPreMsg}
                className="px-3 py-1.5 rounded-lg bg-stone-200 dark:bg-stone-700 hover:bg-stone-300 dark:hover:bg-stone-600 text-stone-800 dark:text-stone-200 font-medium flex items-center space-x-1"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add</span>
              </button>
            </div>

            {formData.pre_messages.length > 0 && (
              <div className="mt-2 space-y-1">
                {formData.pre_messages.map((msg, idx) => (
                  <div key={idx} className="flex items-center justify-between px-3 py-1 rounded bg-stone-100 dark:bg-stone-800/80 text-stone-700 dark:text-stone-300 text-xs">
                    <span>{idx + 1}. {msg}</span>
                    <button
                      type="button"
                      onClick={() => handleRemovePreMsg(idx)}
                      className="text-stone-400 hover:text-red-500"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer Save */}
          <div className="pt-3 border-t border-stone-200 dark:border-stone-800 flex justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-stone-200 dark:bg-stone-700 text-stone-700 dark:text-stone-300 hover:bg-stone-300 dark:hover:bg-stone-600 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-orange-600 hover:bg-orange-500 text-white font-semibold shadow-sm transition"
            >
              <Save className="w-4 h-4" />
              <span>Save Settings</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

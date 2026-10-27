import React, { useState } from 'react';
import { 
  Upload, FileSpreadsheet, CheckCircle2, XCircle, AlertTriangle, 
  Clock, Search, CheckSquare, Square, Eye, AlertCircle
} from 'lucide-react';

export default function TestTable({
  testCases,
  selectedIds,
  setSelectedIds,
  activeFilter,
  setActiveFilter,
  searchQuery,
  setSearchQuery,
  onUploadFile,
  uploadError,
  isUploading,
  onSelectRowForDetail,
  currentRunningId
}) {
  const [isDragging, setIsDragging] = useState(false);

  // Compute summary stats
  const total = testCases.length;
  const passed = testCases.filter(t => t.Status === 'PASS').length;
  const failed = testCases.filter(t => t.Status === 'FAIL').length;
  const errors = testCases.filter(t => t.Status === 'ERROR' || t.Status === 'TIMEOUT').length;
  const passRate = total > 0 ? ((passed / total) * 100).toFixed(1) : 0;

  const validTimes = testCases
    .map(t => Number(t.ResponseTimeMs || 0))
    .filter(t => t > 0);
  const avgTime = validTimes.length > 0 
    ? Math.round(validTimes.reduce((a, b) => a + b, 0) / validTimes.length) 
    : 0;

  // Filter test cases
  const filteredCases = testCases.filter(tc => {
    // Status filter
    if (activeFilter === 'PASS' && tc.Status !== 'PASS') return false;
    if (activeFilter === 'FAIL' && tc.Status !== 'FAIL') return false;
    if (activeFilter === 'ERROR' && !['ERROR', 'TIMEOUT'].includes(tc.Status)) return false;

    // Search query filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchQ = (tc.Query || tc.Question || '').toLowerCase().includes(q);
      const matchExp = (tc.ExpectedAnswer || '').toLowerCase().includes(q);
      const matchId = (tc.TestID || '').toLowerCase().includes(q);
      const matchCat = (tc.Category || '').toLowerCase().includes(q);
      return matchQ || matchExp || matchId || matchCat;
    }
    return true;
  });

  const toggleSelectAll = () => {
    if (selectedIds.length === testCases.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(testCases.map(t => t.id || t.TestID));
    }
  };

  const toggleSelectRow = (id) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(i => i !== id));
    } else {
      setSelectedIds([...selectedIds, id]);
    }
  };

  // Drag and drop handlers
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };
  const handleDragLeave = () => setIsDragging(false);
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onUploadFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden p-6 space-y-4">
      {/* 1. Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 shrink-0">
        <div className="bg-white dark:bg-stone-900 border border-stone-200 dark:border-stone-800 rounded-xl p-3.5 shadow-2xs">
          <div className="text-xs text-stone-500 dark:text-stone-400 font-medium">Total Cases</div>
          <div className="text-2xl font-bold text-stone-900 dark:text-white mt-1">{total}</div>
        </div>

        <div className="bg-white dark:bg-stone-900 border border-emerald-200/60 dark:border-emerald-900/40 rounded-xl p-3.5 shadow-2xs">
          <div className="text-xs text-emerald-600 dark:text-emerald-400 font-medium flex items-center space-x-1">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Passed</span>
          </div>
          <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">{passed}</div>
        </div>

        <div className="bg-white dark:bg-stone-900 border border-red-200/60 dark:border-red-900/40 rounded-xl p-3.5 shadow-2xs">
          <div className="text-xs text-red-600 dark:text-red-400 font-medium flex items-center space-x-1">
            <XCircle className="w-3.5 h-3.5" />
            <span>Failed</span>
          </div>
          <div className="text-2xl font-bold text-red-600 dark:text-red-400 mt-1">{failed}</div>
        </div>

        <div className="bg-white dark:bg-stone-900 border border-stone-200 dark:border-stone-800 rounded-xl p-3.5 shadow-2xs">
          <div className="text-xs text-stone-500 dark:text-stone-400 font-medium">Pass Rate</div>
          <div className={`text-2xl font-bold mt-1 ${Number(passRate) >= 80 ? 'text-emerald-600 dark:text-emerald-400' : 'text-stone-900 dark:text-white'}`}>
            {passRate}%
          </div>
        </div>

        <div className="bg-white dark:bg-stone-900 border border-stone-200 dark:border-stone-800 rounded-xl p-3.5 shadow-2xs col-span-2 sm:col-span-1">
          <div className="text-xs text-stone-500 dark:text-stone-400 font-medium flex items-center space-x-1">
            <Clock className="w-3.5 h-3.5 text-amber-500" />
            <span>Avg Response</span>
          </div>
          <div className="text-2xl font-bold text-stone-900 dark:text-white mt-1">
            {avgTime} <span className="text-xs font-normal text-stone-500">ms</span>
          </div>
        </div>
      </div>

      {/* 2. Drag & Drop Upload Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-4 transition text-center cursor-pointer relative shrink-0 ${
          isDragging
            ? "border-orange-500 bg-orange-50/50 dark:bg-orange-950/20"
            : "border-stone-200 dark:border-stone-800 hover:border-orange-400 dark:hover:border-orange-600 bg-white dark:bg-stone-900/50"
        }`}
      >
        <input
          type="file"
          accept=".xlsx, .xls, .csv"
          onChange={(e) => e.target.files && onUploadFile(e.target.files[0])}
          className="absolute inset-0 opacity-0 cursor-pointer"
        />
        <div className="flex items-center justify-center space-x-3 text-xs text-stone-600 dark:text-stone-300">
          <div className="w-8 h-8 rounded-lg bg-orange-100 dark:bg-orange-950/60 text-orange-600 dark:text-orange-400 flex items-center justify-center">
            <Upload className="w-4 h-4" />
          </div>
          <div className="text-left">
            <p className="font-semibold text-stone-800 dark:text-stone-200">
              {isUploading ? "Uploading & validating test cases..." : "Drop your test cases Excel (.xlsx) or .csv file here"}
            </p>
            <p className="text-stone-400 dark:text-stone-500 text-[11px]">
              Required columns: Question, ExpectedAnswer • Optional: TestID, Category, Conversation, Mode
            </p>
          </div>
        </div>
      </div>

      {/* Validation Error Banner if file has missing columns */}
      {uploadError && (
        <div className="p-3 rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-xs flex items-start space-x-2 shrink-0">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">File Validation Failed: </span>
            <span>{uploadError}</span>
          </div>
        </div>
      )}

      {/* 3. Filter Tabs & Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 shrink-0">
        <div className="flex items-center space-x-1 bg-stone-100 dark:bg-stone-800 p-1 rounded-lg text-xs">
          {['ALL', 'PASS', 'FAIL', 'ERROR'].map(f => (
            <button
              key={f}
              onClick={() => setActiveFilter(f)}
              className={`px-3 py-1 rounded-md font-medium transition ${
                activeFilter === f
                  ? "bg-white dark:bg-stone-700 text-stone-900 dark:text-white shadow-2xs"
                  : "text-stone-500 dark:text-stone-400 hover:text-stone-800 dark:hover:text-stone-200"
              }`}
            >
              {f === 'ALL' && `All (${total})`}
              {f === 'PASS' && `Pass (${passed})`}
              {f === 'FAIL' && `Fail (${failed})`}
              {f === 'ERROR' && `Error (${errors})`}
            </button>
          ))}
        </div>

        <div className="relative w-64">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-stone-400" />
          <input
            type="text"
            placeholder="Search test cases..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 text-stone-800 dark:text-stone-200 focus:outline-hidden focus:ring-1 focus:ring-orange-500"
          />
        </div>
      </div>

      {/* 4. Results Table */}
      <div className="flex-1 overflow-auto rounded-xl border border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-900 shadow-2xs">
        <table className="w-full text-left border-collapse text-xs">
          <thead className="bg-stone-100 dark:bg-stone-800/90 text-stone-600 dark:text-stone-300 font-semibold sticky top-0 z-10 border-b border-stone-200 dark:border-stone-700">
            <tr>
              <th className="py-2.5 px-3 w-8">
                <button onClick={toggleSelectAll} className="flex items-center text-stone-500 hover:text-stone-800">
                  {selectedIds.length === testCases.length && testCases.length > 0 ? (
                    <CheckSquare className="w-4 h-4 text-orange-600" />
                  ) : (
                    <Square className="w-4 h-4" />
                  )}
                </button>
              </th>
              <th className="py-2.5 px-3 w-20">TestID</th>
              <th className="py-2.5 px-3 w-28">Category</th>
              <th className="py-2.5 px-3">Query (Bot Prompt)</th>
              <th className="py-2.5 px-3">Expected Answer (Forward to Bot)</th>
              <th className="py-2.5 px-3">Actual Answer</th>
              <th className="py-2.5 px-3 w-20 text-center">Status</th>
              <th className="py-2.5 px-3 w-16 text-right">Score</th>
              <th className="py-2.5 px-3 w-20 text-right">Time</th>
              <th className="py-2.5 px-2 w-10 text-center"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100 dark:divide-stone-800">
            {filteredCases.length === 0 ? (
              <tr>
                <td colSpan={10} className="py-12 text-center text-stone-400 dark:text-stone-500">
                  No test cases found matching criteria. Upload an Excel file or change filters.
                </td>
              </tr>
            ) : (
              filteredCases.map((tc, idx) => {
                const isSelected = selectedIds.includes(tc.id || tc.TestID);
                const isCurrent = currentRunningId === (tc.id || tc.TestID);

                // Row highlights
                let rowBg = "hover:bg-stone-50/80 dark:hover:bg-stone-800/50";
                if (tc.Status === 'PASS') {
                  rowBg = "bg-emerald-50/40 dark:bg-emerald-950/15 hover:bg-emerald-50 dark:hover:bg-emerald-950/25";
                } else if (tc.Status === 'FAIL') {
                  rowBg = "bg-red-50/40 dark:bg-red-950/15 hover:bg-red-50 dark:hover:bg-red-950/25";
                } else if (tc.Status === 'ERROR' || tc.Status === 'TIMEOUT') {
                  rowBg = "bg-amber-50/40 dark:bg-amber-950/15 hover:bg-amber-50 dark:hover:bg-amber-950/25";
                }

                if (isCurrent) {
                  rowBg = "bg-blue-50/60 dark:bg-blue-950/30 ring-1 ring-blue-500/40";
                }

                return (
                  <tr
                    key={tc.id || idx}
                    onClick={() => onSelectRowForDetail(tc)}
                    className={`transition cursor-pointer ${rowBg}`}
                  >
                    <td className="py-2.5 px-3" onClick={(e) => e.stopPropagation()}>
                      <button onClick={() => toggleSelectRow(tc.id || tc.TestID)}>
                        {isSelected ? (
                          <CheckSquare className="w-4 h-4 text-orange-600" />
                        ) : (
                          <Square className="w-4 h-4 text-stone-400" />
                        )}
                      </button>
                    </td>

                    <td className="py-2.5 px-3 font-mono font-medium text-stone-800 dark:text-stone-200">
                      {tc.TestID || `TC_${idx + 1}`}
                    </td>

                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300">
                        {tc.Category || 'General'}
                      </span>
                    </td>

                    <td className="py-2.5 px-3 font-medium text-stone-900 dark:text-white max-w-[180px] truncate" title={tc.Query || tc.Question}>
                      {tc.Query || tc.Question}
                    </td>

                    <td className="py-2.5 px-3 text-stone-600 dark:text-stone-400 max-w-[160px] truncate" title={tc.ExpectedAnswer}>
                      {tc.ExpectedAnswer}
                    </td>

                    <td className="py-2.5 px-3 text-stone-800 dark:text-stone-200 max-w-[180px] truncate" title={tc.ActualAnswer}>
                      {tc.ActualAnswer || (isCurrent ? <span className="italic text-blue-500 animate-pulse">Running...</span> : <span className="text-stone-400">-</span>)}
                    </td>

                    <td className="py-2.5 px-3 text-center">
                      {tc.Status === 'PASS' && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/70 dark:text-emerald-300">
                          PASS
                        </span>
                      )}
                      {tc.Status === 'FAIL' && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-100 text-red-800 dark:bg-red-950/70 dark:text-red-300">
                          FAIL
                        </span>
                      )}
                      {(tc.Status === 'ERROR' || tc.Status === 'TIMEOUT') && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-950/70 dark:text-amber-300">
                          {tc.Status}
                        </span>
                      )}
                      {tc.Status === 'RUNNING' && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-800 dark:bg-blue-950/70 dark:text-blue-300 animate-pulse">
                          RUNNING
                        </span>
                      )}
                      {tc.Status === 'PENDING' && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-stone-100 text-stone-500 dark:bg-stone-800 dark:text-stone-400">
                          PENDING
                        </span>
                      )}
                    </td>

                    <td className="py-2.5 px-3 text-right font-semibold">
                      {tc.Score !== null && tc.Score !== undefined ? `${tc.Score}%` : '-'}
                    </td>

                    <td className="py-2.5 px-3 text-right text-stone-600 dark:text-stone-400 font-mono">
                      {tc.ResponseTimeMs ? `${tc.ResponseTimeMs}ms` : '-'}
                    </td>

                    <td className="py-2.5 px-2 text-center text-stone-400 hover:text-stone-800 dark:hover:text-white">
                      <Eye className="w-3.5 h-3.5" />
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

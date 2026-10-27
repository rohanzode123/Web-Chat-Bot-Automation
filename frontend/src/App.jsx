import React, { useState, useEffect, useRef } from 'react';
import confetti from 'canvas-confetti';

import Header from './components/Header';
import ControlBar from './components/ControlBar';
import LiveChat from './components/LiveChat';
import TestTable from './components/TestTable';
import SettingsModal from './components/SettingsModal';
import DetailModal from './components/DetailModal';

export default function App() {
  // Theme state
  const [darkMode, setDarkMode] = useState(true);

  // Configuration & Target URL
  const [botUrl, setBotUrl] = useState(
    "https://staging.chat360.io/web_bot/?h=70cdc13d-aac1-4a59-b025-58dc3275a420+website&preview=1"
  );
  const [isEditingUrl, setIsEditingUrl] = useState(false);
  const [config, setConfig] = useState({
    bot: { url: "https://staging.chat360.io/web_bot/?h=70cdc13d-aac1-4a59-b025-58dc3275a420+website&preview=1", headless: true },
    comparison: { mode: "semantic", rapidfuzz_threshold: 80, llm_provider: "auto" },
    timeouts: { bot_reply_timeout_s: 30, quiet_period_s: 3.0, typing_delay_ms: 40, message_delay_ms: 800 },
    pre_messages: []
  });

  // Speed controls
  const [speedConfig, setSpeedConfig] = useState({
    typing_delay_ms: 40,
    message_delay_ms: 800
  });

  // Test cases & Execution State
  const [testCases, setTestCases] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [activeFilter, setActiveFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [uploadError, setUploadError] = useState(null);
  const [isUploading, setIsUploading] = useState(false);

  // Live Chat Stream State
  const [messages, setMessages] = useState([
    {
      sender: 'bot',
      text: "What's your phone number?",
      buttons: []
    }
  ]);
  const [isBotTyping, setIsBotTyping] = useState(false);
  const [currentUserTyping, setCurrentUserTyping] = useState('');

  // Runner controls
  const [isRunning, setIsRunning] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [currentRunningId, setCurrentRunningId] = useState(null);

  // Modals
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [selectedCaseForDetail, setSelectedCaseForDetail] = useState(null);

  // WebSocket
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef(null);

  // Apply dark mode class to html element
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  // Load initial config and default sample template on mount
  useEffect(() => {
    fetch('/api/config')
      .then(res => res.json())
      .then(data => {
        if (data.bot?.url) {
          setBotUrl(data.bot.url);
          setConfig(data);
          if (data.timeouts?.typing_delay_ms) {
            setSpeedConfig({
              typing_delay_ms: data.timeouts.typing_delay_ms,
              message_delay_ms: data.timeouts.message_delay_ms || 800
            });
          }
        }
      })
      .catch(() => {});

    // Initial default test cases matching uploaded Excel series (Name first, Phone second)
    const defaultCases = [
      {
        id: "tc_1",
        TestID: "TC_001",
        Conversation: "CONV_001",
        Category: "Lead Flow",
        Query: "What's your Name?",
        Question: "What's your Name?",
        ExpectedAnswer: "Rohan Sharma",
        Status: "PENDING",
        Score: null,
        ActualAnswer: "",
        Reason: "",
        ResponseTimeMs: 0,
        Screenshot: ""
      },
      {
        id: "tc_2",
        TestID: "TC_002",
        Conversation: "CONV_001",
        Category: "Lead Flow",
        Query: "What's your phone number?",
        Question: "What's your phone number?",
        ExpectedAnswer: "9876543210",
        Status: "PENDING",
        Score: null,
        ActualAnswer: "",
        Reason: "",
        ResponseTimeMs: 0,
        Screenshot: ""
      },
      {
        id: "tc_3",
        TestID: "TC_003",
        Conversation: "CONV_001",
        Category: "Lead Flow",
        Query: "What's your email?",
        Question: "What's your email?",
        ExpectedAnswer: "rohan@example.com",
        Status: "PENDING",
        Score: null,
        ActualAnswer: "",
        Reason: "",
        ResponseTimeMs: 0,
        Screenshot: ""
      },
      {
        id: "tc_4",
        TestID: "TC_004",
        Conversation: "CONV_001",
        Category: "Lead Flow",
        Query: "Enter permanent address?",
        Question: "Enter permanent address?",
        ExpectedAnswer: "42 Park Avenue, Mumbai",
        Status: "PENDING",
        Score: null,
        ActualAnswer: "",
        Reason: "",
        ResponseTimeMs: 0,
        Screenshot: ""
      }
    ];
    setTestCases(defaultCases);
    setSelectedIds(defaultCases.map(t => t.id));
  }, []);

  // Initialize WebSocket Connection
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    const connectWs = () => {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
      };

      ws.onclose = () => {
        setWsConnected(false);
        setTimeout(connectWs, 3000);
      };

      ws.onerror = () => {
        setWsConnected(false);
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          handleWebSocketEvent(payload);
        } catch (e) {
          console.error("WS Parse error", e);
        }
      };
    };

    connectWs();
    return () => {
      wsRef.current?.close();
    };
  }, []);

  // Handle incoming events from backend runner
  const handleWebSocketEvent = (payload) => {
    const { type, data } = payload;

    switch (type) {
      case 'suite_started':
        setIsRunning(true);
        setIsPaused(false);
        break;

      case 'session_starting':
        // Clear chat messages for new session
        setMessages([]);
        setIsBotTyping(true);
        break;

      case 'greeting_loaded':
        setIsBotTyping(false);
        if (data.greeting) {
          setMessages([
            {
              sender: 'bot',
              text: data.greeting,
              buttons: data.buttons || []
            }
          ]);
        }
        break;

      case 'test_step_start':
        setCurrentRunningId(data.test_id || data.id);
        setTestCases(prev => prev.map(tc => {
          if (tc.TestID === data.test_id || tc.id === data.test_id || (data.id && tc.id === data.id)) {
            return { ...tc, Status: 'RUNNING' };
          }
          return tc;
        }));
        break;

      case 'user_typing':
        setCurrentUserTyping(data.current_text);
        break;

      case 'user_message_sent':
        // Confirm user message in chat
        setMessages(prev => [
          ...prev,
          { sender: 'user', text: data.message }
        ]);
        setCurrentUserTyping('');
        break;

      case 'user_clicking':
        setMessages(prev => [
          ...prev,
          { sender: 'user', text: `Clicked: ${data.button}` }
        ]);
        break;

      case 'bot_typing_start':
        setIsBotTyping(true);
        break;

      case 'bot_typing_stop':
        setIsBotTyping(false);
        break;

      case 'bot_bubble_arrived':
        setIsBotTyping(false);
        setMessages(prev => {
          // Avoid duplicate identical bubbles
          const last = prev[prev.length - 1];
          if (last && last.sender === 'bot' && last.text === data.text) {
            return prev;
          }
          return [
            ...prev,
            {
              sender: 'bot',
              text: data.text,
              buttons: data.buttons || []
            }
          ];
        });
        break;

      case 'test_step_result':
        setCurrentRunningId(null);
        setTestCases(prev => prev.map(tc => {
          if (tc.TestID === data.TestID || tc.id === data.TestID || (data.id && tc.id === data.id)) {
            return { ...tc, ...data };
          }
          return tc;
        }));

        // Attach badge to last bot bubble
        setMessages(prev => {
          if (prev.length === 0) return prev;
          const updated = [...prev];
          for (let i = updated.length - 1; i >= 0; i--) {
            if (updated[i].sender === 'bot') {
              updated[i].testResult = data;
              break;
            }
          }
          return updated;
        });
        break;

      case 'suite_finished':
        setIsRunning(false);
        setIsPaused(false);
        setCurrentRunningId(null);
        if (data.summary && data.summary.pass_rate === 100) {
          confetti({ particleCount: 100, spread: 70, origin: { y: 0.6 } });
        }
        break;

      case 'run_paused':
        setIsPaused(true);
        break;

      case 'run_resumed':
        setIsPaused(false);
        break;

      case 'run_stopped':
      case 'suite_stopped':
        setIsRunning(false);
        setIsPaused(false);
        setCurrentRunningId(null);
        break;

      default:
        break;
    }
  };

  // Run Actions
  const startRun = (casesToRun) => {
    if (!wsConnected || casesToRun.length === 0) return;

    // Reset status for selected cases
    const ids = casesToRun.map(c => c.id || c.TestID);
    setTestCases(prev => prev.map(tc => {
      if (ids.includes(tc.id || tc.TestID)) {
        return { ...tc, Status: 'PENDING', Score: null, ActualAnswer: '', Reason: '', ResponseTimeMs: 0 };
      }
      return tc;
    }));

    wsRef.current.send(JSON.stringify({
      action: "start",
      bot_url: botUrl,
      test_cases: casesToRun,
      config_overrides: {
        typing_delay_ms: speedConfig.typing_delay_ms,
        message_delay_ms: speedConfig.message_delay_ms,
        mode: config.comparison.mode,
        rapidfuzz_threshold: config.comparison.rapidfuzz_threshold,
        headless: config.bot.headless
      },
      pre_messages: config.pre_messages || []
    }));
  };

  const handleRunAll = () => startRun(testCases);

  const handleRunSelected = () => {
    const selected = testCases.filter(t => selectedIds.includes(t.id || t.TestID));
    startRun(selected);
  };

  const handlePause = () => {
    wsRef.current?.send(JSON.stringify({ action: "pause" }));
  };

  const handleResume = () => {
    wsRef.current?.send(JSON.stringify({ action: "resume" }));
  };

  const handleStop = () => {
    wsRef.current?.send(JSON.stringify({ action: "stop" }));
  };

  const handleRerunFailed = () => {
    const failed = testCases.filter(t => ['FAIL', 'ERROR', 'TIMEOUT'].includes(t.Status));
    startRun(failed);
  };

  // Upload handling
  const handleUploadFile = async (file) => {
    setUploadError(null);
    setIsUploading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Upload validation failed");
      }

      setTestCases(data.test_cases);
      setSelectedIds(data.test_cases.map(t => t.id));

      if (data.pre_messages && data.pre_messages.length > 0) {
        setConfig(prev => ({ ...prev, pre_messages: data.pre_messages }));
      }
    } catch (e) {
      setUploadError(e.message);
    } finally {
      setIsUploading(false);
    }
  };

  // Exports
  const handleExportExcel = async () => {
    const res = await fetch('/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ format: 'xlsx', results: testCases })
    });
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `results_${new Date().toISOString().replace(/[:.]/g, '_')}.xlsx`;
    a.click();
  };

  const handleExportCsv = async () => {
    const res = await fetch('/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ format: 'csv', results: testCases })
    });
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `results_${new Date().toISOString().replace(/[:.]/g, '_')}.csv`;
    a.click();
  };

  const handleDownloadTemplate = () => {
    window.location.href = '/api/template';
  };

  const hasFailedTests = testCases.some(t => ['FAIL', 'ERROR', 'TIMEOUT'].includes(t.Status));

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-stone-100 dark:bg-stone-950 text-stone-900 dark:text-stone-100 font-sans transition-colors">
      {/* 1. Header */}
      <Header
        botUrl={botUrl}
        setBotUrl={setBotUrl}
        isEditingUrl={isEditingUrl}
        setIsEditingUrl={setIsEditingUrl}
        onOpenSettings={() => setIsSettingsOpen(true)}
        darkMode={darkMode}
        setDarkMode={setDarkMode}
        wsConnected={wsConnected}
      />

      {/* 2. Control Bar */}
      <ControlBar
        isRunning={isRunning}
        isPaused={isPaused}
        onRunAll={handleRunAll}
        onRunSelected={handleRunSelected}
        onPause={handlePause}
        onResume={handleResume}
        onStop={handleStop}
        onRerunFailed={handleRerunFailed}
        hasFailedTests={hasFailedTests}
        selectedCount={selectedIds.length}
        totalCount={testCases.length}
        speedConfig={speedConfig}
        setSpeedConfig={setSpeedConfig}
        onExportExcel={handleExportExcel}
        onExportCsv={handleExportCsv}
        onDownloadTemplate={handleDownloadTemplate}
      />

      {/* 3. Main Workspace Grid */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 overflow-hidden">
        {/* Left Panel: Real Phone Live Chat Widget (5 cols on lg) */}
        <div className="lg:col-span-5 border-r border-stone-200 dark:border-stone-800 bg-stone-200/50 dark:bg-stone-950/60 flex flex-col items-center justify-center overflow-hidden p-3 relative">
          <div className="absolute top-3 left-4 flex items-center space-x-2 z-10">
            <span className="text-[11px] font-bold uppercase tracking-wider text-stone-500 dark:text-stone-400">
              Live Chat Preview
            </span>
            {isRunning && (
              <span className="flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-800 dark:bg-blue-950/80 dark:text-blue-300 animate-pulse">
                Active Session
              </span>
            )}
          </div>

          <LiveChat
            messages={messages}
            isBotTyping={isBotTyping}
            currentUserTyping={currentUserTyping}
            onResetSession={() => {
              setMessages([
                {
                  sender: 'bot',
                  text: "What's your Name?",
                  buttons: []
                }
              ]);
            }}
          />
        </div>

        {/* Right Panel: Test Cases and Live Results (7 cols on lg) */}
        <div className="lg:col-span-7 bg-white dark:bg-stone-900 flex flex-col overflow-hidden">
          <TestTable
            testCases={testCases}
            selectedIds={selectedIds}
            setSelectedIds={setSelectedIds}
            activeFilter={activeFilter}
            setActiveFilter={setActiveFilter}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            onUploadFile={handleUploadFile}
            uploadError={uploadError}
            isUploading={isUploading}
            onSelectRowForDetail={setSelectedCaseForDetail}
            currentRunningId={currentRunningId}
          />
        </div>
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        config={config}
        onSaveConfig={(newCfg) => {
          setConfig(newCfg);
          setBotUrl(newCfg.bot.url);
          fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newCfg)
          });
        }}
      />

      {/* Row Detail & Screenshot Modal */}
      <DetailModal
        testCase={selectedCaseForDetail}
        onClose={() => setSelectedCaseForDetail(null)}
      />
    </div>
  );
}

import React, { useRef, useEffect } from 'react';
import { RefreshCw, X, ArrowUp, Zap, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

const AVATAR_URL = "https://gaadibaazar.s3.ap-south-1.amazonaws.com/media/bot_images/download_S2InFiDn1sTnn3lQ_15-10-26T11-37-22.png";

export default function LiveChat({
  messages,
  isBotTyping,
  currentUserTyping,
  onResetSession,
  sessionStatus
}) {
  const chatBottomRef = useRef(null);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isBotTyping, currentUserTyping]);

  return (
    <div className="flex flex-col items-center justify-center p-2 h-full">
      {/* Real RZ-Work Glass Phone Mockup Card */}
      <div 
        className="w-full max-w-[390px] h-[640px] flex flex-col rounded-[22px] overflow-hidden border relative shadow-2xl transition-all"
        style={{
          background: "linear-gradient(180deg, rgba(75, 63, 56, 0.94) 0%, rgba(53, 44, 38, 0.96) 100%)",
          borderColor: "rgba(255, 255, 255, 0.45)",
          boxShadow: "0 25px 60px -15px rgba(0, 0, 0, 0.5), inset 0 1px 1px 0 rgba(255, 255, 255, 0.2)"
        }}
      >
        {/* Subtle decorative glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-48 h-20 bg-amber-500/10 blur-3xl pointer-events-none rounded-full" />

        {/* 1. Header */}
        <div className="flex items-center justify-between px-5 pt-4 pb-3 border-b border-white/10 z-10 shrink-0">
          <div className="flex items-center space-x-3">
            <div className="relative">
              <img
                src={AVATAR_URL}
                alt="ELI Avatar"
                className="w-10 h-10 rounded-full object-cover ring-2 ring-white/30 shadow-md"
                onError={(e) => {
                  e.target.style.display = 'none';
                  e.target.nextSibling.style.display = 'flex';
                }}
              />
              <div className="hidden w-10 h-10 rounded-full bg-amber-600 text-white font-bold items-center justify-center text-sm shadow">
                ELI
              </div>
              <span className="absolute bottom-0 right-0 w-3 h-3 bg-emerald-500 border-2 border-stone-800 rounded-full" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="font-semibold text-white text-base tracking-wide leading-tight">RZ-Work Bot</h3>
                <span className="px-1.5 py-0.5 text-[10px] font-medium bg-emerald-500/20 text-emerald-300 rounded border border-emerald-500/30">
                  Online
                </span>
              </div>
              <p className="text-white/60 text-xs font-normal">Staging Assistant</p>
            </div>
          </div>

          {/* Action icons */}
          <div className="flex items-center space-x-1.5">
            <button
              onClick={onResetSession}
              title="Reset Chat Session"
              className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 active:scale-95 text-white/80 hover:text-white flex items-center justify-center transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
            <button
              title="Close Widget"
              className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 active:scale-95 text-white/80 hover:text-white flex items-center justify-center transition"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* 2. Chat Scroll Area */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3.5 text-sm z-10">
          {/* Welcome Intro Banner */}
          <div className="text-center py-1">
            <span className="text-[11px] font-medium px-2.5 py-1 rounded-full bg-white/5 text-white/50 border border-white/5">
              Chat session started • Staging Bot
            </span>
          </div>

          {/* Render All Messages */}
          {messages.map((msg, idx) => (
            <div key={idx} className="flex flex-col space-y-1">
              {msg.sender === 'user' ? (
                // User Message (Right-aligned, white pill/card)
                <div className="flex justify-end">
                  <div
                    className="max-w-[80%] px-3.5 py-2.5 rounded-[18px] bg-white text-stone-900 font-medium shadow-md break-words text-[14px] leading-relaxed"
                    style={{
                      boxShadow: "0 2px 8px rgba(0, 0, 0, 0.15)"
                    }}
                  >
                    {msg.text}
                  </div>
                </div>
              ) : (
                // Bot Message (Left-aligned, speech bubble radius: 0 15px 15px 15px)
                <div className="flex flex-col items-start max-w-[86%]">
                  <div
                    className="w-full px-4 py-3 text-white text-[14px] leading-relaxed border border-white/20 shadow-sm"
                    style={{
                      backgroundColor: "rgba(255, 255, 255, 0.12)",
                      borderRadius: "0px 15px 15px 15px",
                      backdropFilter: "blur(12px)"
                    }}
                  >
                    <div className="whitespace-pre-line">{msg.text}</div>

                    {/* Interactive button chips if returned by bot */}
                    {msg.buttons && msg.buttons.length > 0 && (
                      <div className="mt-2.5 pt-2 border-t border-white/15 flex flex-wrap gap-1.5">
                        {msg.buttons.map((btnLabel, bIdx) => (
                          <span
                            key={bIdx}
                            className="px-2.5 py-1 text-xs font-medium rounded-full bg-white/20 hover:bg-white/30 text-white border border-white/30 shadow-xs cursor-pointer select-none transition"
                          >
                            {btnLabel}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Verification Badge & Timing under bot reply */}
                  {msg.testResult && (
                    <div className="flex items-center space-x-2 mt-1 ml-1 text-xs">
                      {msg.testResult.Status === 'PASS' && (
                        <span className="flex items-center space-x-1 px-2 py-0.5 rounded-full font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          <CheckCircle className="w-3 h-3 text-emerald-400" />
                          <span>PASS {msg.testResult.Score ? `(${msg.testResult.Score}%)` : ''}</span>
                        </span>
                      )}
                      {msg.testResult.Status === 'FAIL' && (
                        <span className="flex items-center space-x-1 px-2 py-0.5 rounded-full font-semibold bg-red-500/20 text-red-300 border border-red-500/30">
                          <XCircle className="w-3 h-3 text-red-400" />
                          <span>FAIL {msg.testResult.Score ? `(${msg.testResult.Score}%)` : ''}</span>
                        </span>
                      )}
                      {(msg.testResult.Status === 'ERROR' || msg.testResult.Status === 'TIMEOUT') && (
                        <span className="flex items-center space-x-1 px-2 py-0.5 rounded-full font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                          <AlertTriangle className="w-3 h-3 text-amber-400" />
                          <span>{msg.testResult.Status}</span>
                        </span>
                      )}
                      {msg.testResult.ResponseTimeMs > 0 && (
                        <span className="flex items-center space-x-0.5 text-stone-400 text-[11px]">
                          <Zap className="w-3 h-3 text-amber-400" />
                          <span>{msg.testResult.ResponseTimeMs} ms</span>
                        </span>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}

          {/* Live character-by-character user typing animation bubble */}
          {currentUserTyping && (
            <div className="flex justify-end">
              <div className="max-w-[80%] px-3.5 py-2.5 rounded-[18px] bg-white text-stone-900 font-medium shadow-md text-[14px] flex items-center space-x-1">
                <span>{currentUserTyping}</span>
                <span className="inline-block w-1.5 h-4 bg-stone-500 animate-pulse ml-0.5" />
              </div>
            </div>
          )}

          {/* Bot Typing Indicator (Animated 3 bouncing dots) */}
          {isBotTyping && (
            <div className="flex items-start">
              <div
                className="px-4 py-3 flex items-center space-x-1.5 border border-white/15"
                style={{
                  backgroundColor: "rgba(255, 255, 255, 0.12)",
                  borderRadius: "0px 15px 15px 15px",
                  backdropFilter: "blur(12px)"
                }}
              >
                <div className="w-2 h-2 rounded-full bg-white dot-1" />
                <div className="w-2 h-2 rounded-full bg-white dot-2" />
                <div className="w-2 h-2 rounded-full bg-white dot-3" />
              </div>
            </div>
          )}

          <div ref={chatBottomRef} />
        </div>

        {/* 3. Input Row */}
        <div className="px-4 pt-2 pb-2.5 z-10 shrink-0">
          <div
            className="flex items-center justify-between pl-5 pr-2 py-1.5 rounded-full border transition"
            style={{
              backgroundColor: "rgba(255, 255, 255, 0.09)",
              borderColor: "rgba(183, 151, 164, 0.55)",
              boxShadow: "inset 0 1px 1px 0 rgba(255, 255, 255, 0.04)"
            }}
          >
            <input
              type="text"
              readOnly
              value={currentUserTyping || ""}
              placeholder="Type your message..."
              className="bg-transparent text-white placeholder-white/50 text-[15px] focus:outline-hidden w-full cursor-default"
            />
            <button
              className="w-9 h-9 rounded-full bg-stone-100 hover:bg-white text-stone-900 flex items-center justify-center shrink-0 shadow-sm transition active:scale-95"
              title="Send message"
            >
              <ArrowUp className="w-4 h-4 text-stone-900 stroke-[2.5]" />
            </button>
          </div>

          {/* 4. Footer */}
          <div className="flex items-center justify-center space-x-1.5 pt-2 text-[12px] text-white/60">
            <span>Powered by</span>
            <span className="font-bold text-white/90 tracking-wide">
              rz-work
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

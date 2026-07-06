import React, { useState, useEffect, useRef } from 'react';
import { useChatStore } from '../store/useChatStore';

// Stateful Loading Card for INQUIRY Actions (like payslip)
function InquiryLoadingCard({ steps, onComplete }) {
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    if (currentStep < steps.length) {
      const timer = setTimeout(() => {
        setCurrentStep((prev) => prev + 1);
      }, 900); // 900ms per step for realism
      return () => clearTimeout(timer);
    } else {
      if (onComplete) onComplete();
    }
  }, [currentStep, steps, onComplete]);

  return (
    <div className="action-loading-card animate-fade-in">
      <div className="action-loading-title">
        {currentStep < steps.length ? (
          <div className="action-loading-loader" />
        ) : (
          <i className="fa-solid fa-circle-check" style={{ color: 'var(--success)', marginLeft: '0.4rem' }} />
        )}
        <span>جاري الاتصال بقاعدة بيانات SAP SF...</span>
      </div>
      <div className="action-loading-steps" style={{ marginTop: '0.5rem' }}>
        {steps.map((step, idx) => {
          const isActive = idx === currentStep;
          const isCompleted = idx < currentStep;
          return (
            <div 
              key={idx} 
              className={`action-loading-step-row ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}
              style={{ direction: 'rtl', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}
            >
              <div className="action-loading-step-bullet" />
              <span>{step}</span>
              {isCompleted && (
                <i className="fa-solid fa-check" style={{ fontSize: '0.65rem', marginRight: 'auto', color: 'var(--success)' }} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function BotMessageBubble({ msg, index, activePendingAction, executePendingAction, sendQuery }) {
  const [displayedText, setDisplayedText] = useState('');
  const [thinkingText, setThinkingText] = useState('');
  const [isThinkingDone, setIsThinkingDone] = useState(false);
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(true); // default expanded while thinking
  const [isTypingCompleted, setIsTypingCompleted] = useState(false);
  const [copied, setCopied] = useState(false);
  const [inquiryCompleted, setInquiryCompleted] = useState(false);

  const isHistory = !msg.rawTextBuffer && !msg.rawTextTarget && msg.text;

  // Sync state values with a ref to avoid stale closure scopes in the setInterval callback
  const stateRef = useRef({
    isHistory,
    isThinkingDone: isHistory,
    thinkingText: '',
    displayedText: isHistory ? msg.text : '',
    rawTextBuffer: msg.rawTextBuffer || '',
    rawTextTarget: msg.rawTextTarget || '',
    isStreamClosed: msg.isStreamClosed || isHistory,
    citations: msg.citations || [],
  });

  useEffect(() => {
    stateRef.current.rawTextBuffer = msg.rawTextBuffer || '';
    stateRef.current.rawTextTarget = msg.rawTextTarget || '';
    stateRef.current.isStreamClosed = msg.isStreamClosed || isHistory;
    stateRef.current.citations = msg.citations || [];
  }, [msg.rawTextBuffer, msg.rawTextTarget, msg.isStreamClosed, msg.citations, isHistory]);

  // Unified interval for sequential thinking -> response character-by-character typing
  useEffect(() => {
    if (isHistory) {
      setDisplayedText(msg.text);
      setIsThinkingDone(true);
      setIsThinkingExpanded(false);
      setIsTypingCompleted(true);
      return;
    }

    let thinkingCharIdx = 0;
    let responseCharIdx = 0;
    let targetThinkingText = '';
    let hasInitializedThinkingText = false;

    const interval = setInterval(() => {
      const state = stateRef.current;

      // Phase 1: Thinking typing animation
      if (!state.isThinkingDone) {
        if (state.citations.length === 0) {
          state.isThinkingDone = true;
          setIsThinkingDone(true);
          return;
        }

        if (!hasInitializedThinkingText) {
          const docSources = Array.from(new Set(state.citations.map(c => c.source)));
          targetThinkingText = `جاري مراجعة وتحليل لوائح السياسات المسترجعة من مستند [${docSources.join(', ')}]...`;
          hasInitializedThinkingText = true;
        }

        if (thinkingCharIdx < targetThinkingText.length) {
          const nextText = targetThinkingText.substring(0, thinkingCharIdx + 1);
          setThinkingText(nextText);
          state.thinkingText = nextText;
          thinkingCharIdx++;
        } else {
          state.isThinkingDone = true;
          setIsThinkingDone(true);
        }
        return;
      }

      // Phase 2: Response text typing animation
      const targetResponseText = state.isStreamClosed ? state.rawTextTarget || state.rawTextBuffer : state.rawTextBuffer;

      if (responseCharIdx < targetResponseText.length) {
        const nextText = targetResponseText.substring(0, responseCharIdx + 1);
        setDisplayedText(nextText);
        state.displayedText = nextText;
        responseCharIdx++;
      } else if (state.isStreamClosed) {
        clearInterval(interval);
        setIsTypingCompleted(true);
        setIsThinkingExpanded(false); // Auto collapse thinking on completion
      }
    }, 12);

    return () => clearInterval(interval);
  }, [isHistory, msg.text]);

  const handleCopy = () => {
    navigator.clipboard.writeText(msg.rawTextTarget || msg.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const hasWidget = msg.actionWidget !== undefined && msg.actionWidget !== null;
  const isTransaction = hasWidget && msg.actionWidget.action_type === 'TRANSACTIONAL';
  const isInquiry = hasWidget && msg.actionWidget.action_type === 'INQUIRY';
  
  const inquiryShowText = !isInquiry || inquiryCompleted;

  return (
    <div className="message-bubble">
      {/* Inquiry Animation Handling */}
      {isInquiry && !inquiryCompleted && (
        <InquiryLoadingCard 
          steps={msg.actionWidget.status_steps_ar || []} 
          onComplete={() => setInquiryCompleted(true)}
        />
      )}

      {/* 🧠 Thinking Block */}
      {inquiryShowText && msg.citations && msg.citations.length > 0 && (
        <div className="thinking-process-container animate-fade-in" style={{ marginBottom: '0.6rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', direction: 'rtl', justifyContent: 'flex-start' }}>
            <button
              onClick={() => setIsThinkingExpanded(!isThinkingExpanded)}
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: 'none',
                width: '26px',
                height: '26px',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                color: 'var(--hsa-gold)',
                outline: 'none',
                transition: 'all 0.2s ease',
                padding: 0
              }}
              className="action-icon-btn"
              title={isThinkingExpanded ? "إخفاء مراجع السياسات" : "عرض مراجع السياسات والتفكير"}
            >
              <i className={`fa-solid ${isThinkingExpanded ? 'fa-chevron-up' : 'fa-chevron-down'}`} style={{ fontSize: '0.75rem' }} />
            </button>

            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 600 }}>
              {!isThinkingDone ? '⚙️ جاري مراجعة وتحليل لوائح السياسات...' : '🧠 مراجع السياسات المسترجعة'}
            </span>
          </div>

          {isThinkingExpanded && (
            <div className="thinking-process-content" style={{ marginTop: '0.4rem', padding: '0.6rem 0.8rem', borderRadius: '8px', background: 'rgba(0, 0, 0, 0.12)', border: '1px solid rgba(255,255,255,0.03)' }}>
              {/* Simulated typing status */}
              <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', opacity: 0.9, fontStyle: 'italic', marginBottom: '0.5rem', direction: 'rtl', textAlign: 'right' }}>
                {thinkingText}
                {!isThinkingDone && <span className="cursor-blink"></span>}
              </div>

              {/* Citations references */}
              {isThinkingDone && msg.citations.map((cit, cIdx) => (
                <div key={cIdx} className="citation-block" style={{ padding: '0.5rem 0', borderBottom: cIdx < msg.citations.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none' }}>
                  <div className="citation-text" style={{ fontSize: '0.8rem', opacity: 0.85, marginBottom: '0.25rem', direction: 'rtl', textAlign: 'right' }}>
                    "{cit.text}"
                  </div>
                  <div className="citation-meta" style={{ display: 'flex', justifyContent: 'flex-start' }}>
                    <a
                      href={`http://127.0.0.1:8081/policies-files/${cit.category}/${cit.source}#page=${cit.page_number}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="citation-link"
                      style={{ fontSize: '0.75rem', color: 'var(--hsa-gold)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}
                    >
                      <i className="fa-solid fa-file-pdf"></i>
                      <span>{cit.source} (صفحة {cit.page_number})</span>
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 💬 Actual Bot Message Text */}
      {inquiryShowText && (displayedText || isThinkingDone) && (
        <div style={{ whiteSpace: 'pre-line', fontSize: '0.92rem', lineHeight: '1.7', textAlign: 'right', direction: 'rtl' }} className={isInquiry ? 'animate-fade-in' : ''}>
          {displayedText}
          {!isTypingCompleted && isThinkingDone && <span className="cursor-blink"></span>}
        </div>
      )}

      {/* Render TRANSACTIONAL Action Confirmation Card */}
      {isTransaction && isTypingCompleted && (
        <div className="action-confirmation-card animate-fade-in" style={{ marginTop: '0.75rem' }}>
          <div className="action-card-header">
            <i className="fa-solid fa-clipboard-check action-card-icon"></i>
            <span className="action-card-title">{msg.actionWidget.title_ar}</span>
          </div>
          <div className="action-card-summary">{msg.actionWidget.summary_ar}</div>
          <div className="action-card-fields">
            {msg.actionWidget.fields.map((f, fIdx) => (
              <div key={fIdx} className="action-card-field-row">
                <span className="action-field-label">{f.label_ar}</span>
                <span className="action-field-value">{f.value}</span>
              </div>
            ))}
          </div>
          {activePendingAction && activePendingAction.action_id === msg.actionWidget.action_id && (
            <div className="action-card-actions">
              <button 
                className="action-btn-confirm"
                onClick={() => executePendingAction(msg.actionWidget.action_id)}
              >
                <i className="fa-solid fa-check"></i>
                تأكيد وإرسال (Submit)
              </button>
              <button 
                className="action-btn-cancel"
                onClick={() => {
                  useChatStore.setState({ activePendingAction: null });
                  sendQuery('إلغاء المعاملة');
                }}
              >
                إلغاء
              </button>
            </div>
          )}
        </div>
      )}

      {/* 🔧 Action Buttons (Copy) */}
      {isTypingCompleted && (
        <div className="message-actions" style={{ display: 'flex', gap: '0.5rem', marginTop: '0.6rem', borderTop: '1px solid rgba(255,255,255,0.04)', paddingTop: '0.4rem', justifyContent: 'flex-start', direction: 'rtl' }}>
          <button 
            onClick={handleCopy} 
            className="action-icon-btn action-icon-btn-copy" 
            title="نسخ الرد"
            style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.75rem', padding: '0.25rem 0.5rem', borderRadius: '4px' }}
          >
            <i className={`fa-solid ${copied ? 'fa-check' : 'fa-copy'}`} style={{ color: copied ? 'var(--success)' : '' }} />
            <span>{copied ? 'تم النسخ' : 'نسخ'}</span>
          </button>
        </div>
      )}
    </div>
  );
}

function UserMessageBubble({ msg, index, setInputValue }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(msg.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleEdit = () => {
    setInputValue(msg.text);
    const inputEl = document.getElementById('chat-input');
    if (inputEl) {
      inputEl.focus();
    }
  };

  return (
    <div className="message-bubble">
      <div style={{ whiteSpace: 'pre-line', fontSize: '0.92rem', lineHeight: '1.7', textAlign: 'right', direction: 'rtl' }}>
        {msg.text}
      </div>
      <div className="message-actions" style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '0.4rem', justifyContent: 'flex-end', direction: 'rtl' }}>
        <button 
          onClick={handleEdit} 
          className="action-icon-btn" 
          title="تعديل الرسالة"
          style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', background: 'none', border: 'none', color: 'rgba(255,255,255,0.4)', cursor: 'pointer', fontSize: '0.75rem', padding: '0.25rem 0.5rem', borderRadius: '4px' }}
        >
          <i className="fa-solid fa-pen-to-square" />
          <span>تعديل</span>
        </button>
        <button 
          onClick={handleCopy} 
          className="action-icon-btn" 
          title="نسخ الرسالة"
          style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', background: 'none', border: 'none', color: 'rgba(255,255,255,0.4)', cursor: 'pointer', fontSize: '0.75rem', padding: '0.25rem 0.5rem', borderRadius: '4px' }}
        >
          <i className={`fa-solid ${copied ? 'fa-check' : 'fa-copy'}`} style={{ color: copied ? 'var(--success)' : '' }} />
          <span>{copied ? 'تم النسخ' : 'نسخ'}</span>
        </button>
      </div>
    </div>
  );
}

export default function AssistantView() {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef(null);

  const messages = useChatStore((state) => state.messages);
  const isWaitingResponse = useChatStore((state) => state.isWaitingResponse);
  const sendQuery = useChatStore((state) => state.sendQuery);
  const executePendingAction = useChatStore((state) => state.executePendingAction);
  const activePendingAction = useChatStore((state) => state.activePendingAction);

  const handleSend = () => {
    const query = inputValue.trim();
    if (!query) return;
    setInputValue('');
    sendQuery(query);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      if (isWaitingResponse || !inputValue.trim()) {
        e.preventDefault();
        return;
      }
      handleSend();
    }
  };

  // Scroll to bottom on new messages or when waiting state changes
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isWaitingResponse]);

  const isEmpty = messages.length === 0;

  const suggestedQuestions = [
    { icon: 'fa-solid fa-calendar-check', text: 'ما هي سياسة الإجازة السنوية؟' },
    { icon: 'fa-solid fa-plane-departure', text: 'أريد تقديم طلب إجازة سنوية' },
    { icon: 'fa-solid fa-house-chimney', text: 'ما هي تفاصيل بدل السكن؟' },
    { icon: 'fa-solid fa-file-invoice-dollar', text: 'أريد كشف الراتب لشهر مايو' },
  ];

  return (
    <div id="view-assistant" className="view-panel active">
      <main className="glass-card chat-container">
        <div className="chat-messages" id="chat-messages">
          {isEmpty ? (
            <div className="empty-state" id="empty-state">
              <div className="empty-state-hero">
                <div className="empty-icon-ring">
                  <div className="empty-icon-ring-inner">
                    <i className="fa-robot fa-solid"></i>
                  </div>
                </div>
                <h2 className="empty-title">مرحباً بك في نظام AskHR الذكي</h2>
                <p className="empty-subtitle">
                  المحرك الآلي للموارد البشرية لمجموعة هائل سعيد أنعم
                </p>
              </div>

              <div className="suggested-grid">
                {suggestedQuestions.map((q, i) => (
                  <div
                    key={i}
                    className="suggested-card"
                    onClick={() => sendQuery(q.text)}
                    style={{ animationDelay: `${i * 0.08}s` }}
                  >
                    <div className="suggested-card-icon">
                      <i className={q.icon}></i>
                    </div>
                    <span>{q.text}</span>
                    <i className="fa-solid fa-arrow-left suggested-card-arrow"></i>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, index) => (
              <div key={index} className={`message-wrapper ${msg.sender}`}>
                <div className="message-bubble-container" style={{ width: '100%' }}>
                  {msg.sender === 'user' ? (
                    <UserMessageBubble 
                      msg={msg} 
                      index={index} 
                      setInputValue={setInputValue} 
                    />
                  ) : (
                    <BotMessageBubble 
                      msg={msg} 
                      index={index}
                      activePendingAction={activePendingAction}
                      executePendingAction={executePendingAction}
                      sendQuery={sendQuery}
                    />
                  )}
                  <div className="message-meta">
                    <span>{msg.time}</span>
                  </div>
                </div>
              </div>
            ))
          )}

          {isWaitingResponse && (
            <div className="message-wrapper bot">
              <div className="message-bubble-container" style={{ width: '100%' }}>
                <div className="message-bubble">
                  <div className="typing-indicator">يفكر
                    <div className="typing-dot"></div>
                    <div className="typing-dot"></div>
                    <div className="typing-dot"></div>
                  </div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-panel">
          <div className="chat-input-wrapper">
            <input
              type="text"
              className="chat-input"
              id="chat-input"
              placeholder={activePendingAction ? "بانتظار تأكيد الإجراء من البطاقة أعلاه..." : "اكتب استفسارك هنا..."}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={activePendingAction !== null || isWaitingResponse}
            />
            <button
              className={`send-btn ${(isWaitingResponse || !inputValue.trim() || activePendingAction) ? 'disabled' : ''} ${inputValue.trim() && !isWaitingResponse && !activePendingAction ? 'has-text' : ''}`}
              onClick={handleSend}
              id="send-btn"
              disabled={isWaitingResponse || !inputValue.trim() || activePendingAction !== null}
            >
              <i className="fa-solid fa-paper-plane" style={{ transform: 'rotate(180deg)' }} id="send-icon"></i>
            </button>
          </div>
          <div className="chat-input-hint">
            <i className="fa-solid fa-shield-halved"></i>
            <span>محادثاتك محمية ومؤمّنة بالكامل عبر SharePoint SSO</span>
          </div>
        </div>
      </main>
    </div>
  );
}

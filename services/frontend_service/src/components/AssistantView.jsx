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

export default function AssistantView() {
  const [inputValue, setInputValue] = useState('');
  const [expandedThinking, setExpandedThinking] = useState({});
  const [completedInquiries, setCompletedInquiries] = useState({}); // Keep track of completed inquiry animations by msgIndex
  const messagesEndRef = useRef(null);

  const messages = useChatStore((state) => state.messages);
  const isWaitingResponse = useChatStore((state) => state.isWaitingResponse);
  const sendQuery = useChatStore((state) => state.sendQuery);
  const executePendingAction = useChatStore((state) => state.executePendingAction);
  const activePendingAction = useChatStore((state) => state.activePendingAction);

  const toggleThinking = (idx) => {
    setExpandedThinking((prev) => ({
      ...prev,
      [idx]: !prev[idx],
    }));
  };

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
            messages.map((msg, index) => {
              const hasWidget = msg.actionWidget !== undefined && msg.actionWidget !== null;
              const isTransaction = hasWidget && msg.actionWidget.action_type === 'TRANSACTIONAL';
              const isInquiry = hasWidget && msg.actionWidget.action_type === 'INQUIRY';
              
              // Determine whether to display the text yet for inquiry actions
              const inquiryShowText = !isInquiry || completedInquiries[index] === true;

              return (
                <div key={index} className={`message-wrapper ${msg.sender}`}>
                  <div className="message-bubble-container" style={{ width: '100%' }}>
                    <div className="message-bubble">
                      
                      {/* Inquiry Animation Handling */}
                      {isInquiry && !completedInquiries[index] && (
                        <InquiryLoadingCard 
                          steps={msg.actionWidget.status_steps_ar || []} 
                          onComplete={() => {
                            setCompletedInquiries(prev => ({ ...prev, [index]: true }));
                          }}
                        />
                      )}

                      {/* Display response text (fades in for inquiry after animation) */}
                      {inquiryShowText && (
                        <div style={{ whiteSpace: 'pre-line' }} className={isInquiry ? 'animate-fade-in' : ''}>
                          {msg.text}
                        </div>
                      )}

                      {/* Render TRANSACTIONAL Action Confirmation Card */}
                      {isTransaction && (
                        <div className="action-confirmation-card">
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
                          {/* Only show buttons if this is the active pending action in store */}
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

                      {/* Citations / References Section */}
                      {msg.sender === 'bot' && inquiryShowText && msg.responseData && msg.responseData.execution_details && msg.responseData.execution_details.citations && msg.responseData.execution_details.citations.length > 0 && (
                        <div className="thinking-process-container">
                          <button
                            className="thinking-process-toggle"
                            onClick={() => toggleThinking(index)}
                          >
                            <i className={`fa-solid ${expandedThinking[index] ? 'fa-chevron-up' : 'fa-chevron-down'}`} style={{ marginLeft: '0.4rem' }}></i>
                            <span>🧠 عرض مراجع السياسات المسترجعة</span>
                          </button>

                          {expandedThinking[index] && (
                            <div className="thinking-process-content">
                              {msg.responseData.execution_details.citations.map((cit, cIdx) => (
                                <div key={cIdx} className="citation-block">
                                  <div className="citation-text">
                                    "{cit.text}"
                                  </div>
                                  <div className="citation-meta">
                                    <a
                                      href={`http://127.0.0.1:8081/policies-files/${cit.category}/${cit.source}#page=${cit.page_number}`}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="citation-link"
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
                    </div>

                    <div className="message-meta">
                      <span>{msg.time}</span>
                    </div>
                  </div>
                </div>
              );
            })
          )}

          {isWaitingResponse && (
            <div className="message-wrapper bot">
              <div className="message-bubble">
                <div className="typing-indicator">يفكر
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
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

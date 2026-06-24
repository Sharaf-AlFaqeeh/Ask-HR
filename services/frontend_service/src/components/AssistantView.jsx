import React, { useState, useEffect, useRef } from 'react';
import { useChatStore } from '../store/useChatStore';

export default function AssistantView() {
  const [inputValue, setInputValue] = useState('');
  const [expandedThinking, setExpandedThinking] = useState({});
  const messagesEndRef = useRef(null);

  const messages = useChatStore((state) => state.messages);
  const isWaitingResponse = useChatStore((state) => state.isWaitingResponse);
  const sendQuery = useChatStore((state) => state.sendQuery);

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
    { icon: 'fa-solid fa-file-contract', text: 'كيف أطلب شهادة خبرة؟' },
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
                    <i className="fa-solid fa-robot"></i>
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
                <div className="message-bubble-container">
                  <div className="message-bubble">
                    <div style={{ whiteSpace: 'pre-line' }}>{msg.text}</div>
                    
                    {msg.sender === 'bot' && msg.responseData && msg.responseData.execution_details && msg.responseData.execution_details.citations && msg.responseData.execution_details.citations.length > 0 && (
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

                  {msg.sender === 'bot' && msg.responseData && (
                    <div className="engine-pills">
                      {msg.responseData.intent && (
                        <div className="engine-pill intent">
                          <i className="fa-solid fa-bullseye"></i>
                          {msg.responseData.intent}
                        </div>
                      )}
                      {msg.responseData.context_used && (
                        <div className="engine-pill rag">
                          <i className="fa-solid fa-database"></i>
                          RAG
                        </div>
                      )}
                      {msg.responseData.sap_executed && (
                        <div className="engine-pill sap">
                          <i className="fa-solid fa-check-double"></i>
                          SAP SuccessFactors
                        </div>
                      )}
                      {msg.responseData.confidence != null && (
                        <div className="engine-pill confidence">
                          <i className="fa-solid fa-gauge-high"></i>
                          {Math.round(msg.responseData.confidence * 100)}%
                        </div>
                      )}
                    </div>
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
              <div className="message-bubble">
                <div className="typing-indicator">
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
              placeholder="اكتب استفسارك هنا..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <button
              className={`send-btn ${(isWaitingResponse || !inputValue.trim()) ? 'disabled' : ''} ${inputValue.trim() && !isWaitingResponse ? 'has-text' : ''}`}
              onClick={handleSend}
              id="send-btn"
              disabled={isWaitingResponse || !inputValue.trim()}
            >
              <i className="fa-solid fa-paper-plane" style={{ transform: 'rotate(180deg)' }} id="send-icon"></i>
            </button>
          </div>
          <div className="chat-input-hint">
            <i className="fa-solid fa-shield-halved"></i>
            <span>محادثاتك محمية ومؤمّنة بالكامل</span>
          </div>
        </div>
      </main>
    </div>
  );
}

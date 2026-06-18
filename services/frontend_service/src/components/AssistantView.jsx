import React, { useState, useEffect, useRef } from 'react';
import { useChatStore } from '../store/useChatStore';

export default function AssistantView() {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef(null);

  const messages = useChatStore((state) => state.messages);
  const isWaitingResponse = useChatStore((state) => state.isWaitingResponse);
  const sendQuery = useChatStore((state) => state.sendQuery);

  const handleSend = () => {
    const query = inputValue.trim();
    if (!query) return;
    setInputValue('');
    sendQuery(query);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
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

  return (
    <div id="view-assistant" className="view-panel active">
      <main className="glass-card chat-container">
        <div className="chat-messages" id="chat-messages">
          {isEmpty ? (
            <div className="empty-state" id="empty-state">
              <div className="empty-icon">
                <i className="fa-solid fa-comments"></i>
              </div>
              <h2>مرحباً بك في نظام AskHR  الذكي</h2>
              <p style={{ color: 'var(--text-secondary)', maxWidth: '450px', margin: '0.5rem 0 1.5rem' }}>
                المحرك الآلي للموارد البشرية لمجموعة هائل سعيد أنعم (HSA Group)
              </p>
              <div className="suggested-chips">
                <div className="suggested-chip" onClick={() => sendQuery('ما هي سياسة الإجازة السنوية؟')}>
                  ما هي سياسة الإجازة السنوية؟
                </div>
                <div className="suggested-chip" onClick={() => sendQuery('أريد تقديم طلب إجازة سنوية')}>
                  أريد تقديم طلب إجازة سنوية
                </div>
                <div className="suggested-chip" onClick={() => sendQuery('ما هي تفاصيل بدل السكن؟')}>
                  ما هي تفاصيل بدل السكن؟
                </div>
              </div>
            </div>
          ) : (
            messages.map((msg, index) => (

              <div key={index} className={`message-wrapper ${msg.sender}`}>
                {/* <div className={`message-avatar ${msg.sender}`}>
                  {msg.sender === 'user' ? (
                    <i className="fa-solid fa-user"></i>
                  ) : (
                    <i className="fa-solid fa-brain"></i>
                  )}
                </div> */}
                <div className="message-bubble-container">
                  <div className="message-bubble" style={{ whiteSpace: 'pre-line' }}>
                    {msg.text}
                  </div>

                  {msg.sender === 'bot' && msg.responseData && (
                    <div className="engine-pills">
                      {msg.responseData.intent && (
                        <div className="engine-pill rag">
                          {/* <i className="fa-solid fa-wand-magic-sparkles"></i>{msg.responseData.intent} */}
                        </div>
                      )}
                      {msg.responseData.context_used && (
                        <div className="engine-pill rag">
                          <i className="fa-solid fa-database"></i>
                        </div>
                      )}
                      {msg.responseData.sap_executed && (
                        <div className="engine-pill sap">
                          <i className="fa-solid fa-check-double"></i> SAP SuccessFactors
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
              {/* <div className="message-avatar bot">
                <i className="fa-solid fa-brain"></i>
              </div> */}
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
          <input
            type="text"
            className="chat-input"
            id="chat-input"
            placeholder="اكتب استفسارك هنا..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isWaitingResponse}
          />
          <button
            className="send-btn"
            onClick={handleSend}
            id="send-btn"
            style={{ opacity: isWaitingResponse ? 0.5 : 1 }}
            disabled={isWaitingResponse}
          >
            <i className="fa-solid fa-paper-plane" style={{ transform: 'rotate(180deg)' }} id="send-icon"></i>
          </button>
        </div>
      </main>
    </div>
  );
}

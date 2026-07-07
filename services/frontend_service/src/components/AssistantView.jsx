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

// Leave Request Form — Professional structured form for leave details
function LeaveRequestForm({ formData, onSubmit, onCancel }) {
  const [leaveType, setLeaveType] = useState(formData?.fields?.leave_type?.value || '');
  const [startDate, setStartDate] = useState(formData?.fields?.start_date?.value || '');
  const [endDate, setEndDate] = useState(formData?.fields?.end_date?.value || '');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const leaveOptions = formData?.fields?.leave_type?.options || [];
  const startInferred = formData?.fields?.start_date?.inferred || false;
  const endInferred = formData?.fields?.end_date?.inferred || false;

  // Calculate duration
  const calcDays = () => {
    if (!startDate || !endDate) return null;
    try {
      const s = new Date(startDate);
      const e = new Date(endDate);
      if (isNaN(s) || isNaN(e)) return null;
      const diff = Math.floor((e - s) / (1000 * 60 * 60 * 24)) + 1;
      return diff > 0 ? diff : null;
    } catch { return null; }
  };
  const totalDays = calcDays();

  const handleSubmit = async () => {
    if (!leaveType || !startDate || !endDate) return;
    setIsSubmitting(true);
    await onSubmit({ leave_type: leaveType, start_date: startDate, end_date: endDate });
    setIsSubmitting(false);
  };

  const isValid = leaveType && startDate && endDate && totalDays && totalDays > 0;

  return (
    <div className="leave-form-card animate-fade-in" style={{ direction: 'rtl', marginTop: '10px' }}>
      <div className="leave-form-header" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
        <i className="fa-solid fa-calendar-plus leave-form-icon" style={{ color: 'var(--hsa-gold)' }}></i>
        <span className="leave-form-title" style={{ fontWeight: 'bold', fontSize: '0.95rem' }}>{formData?.title_ar || '📋 تفاصيل طلب الإجازة'}</span>
      </div>
      <div className="leave-form-description" style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>{formData?.description_ar}</div>

      {/* Leave Type Select */}
      <div className="leave-form-field" style={{ marginBottom: '12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <label className="leave-form-label" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          نوع الإجازة
        </label>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <select
            className="leave-form-select"
            value={leaveType}
            onChange={(e) => setLeaveType(e.target.value)}
            style={{
              flex: 1,
              backgroundColor: 'var(--hsa-navy-input)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: '8px',
              padding: '8px',
              color: '#fff',
              outline: 'none'
            }}
          >
            <option value="">— اختر نوع الإجازة —</option>
            {leaveOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label_ar}</option>
            ))}
          </select>
          {leaveType && formData?.fields?.leave_type?.value === leaveType && (
            <span className="leave-form-inferred-badge" style={{ fontSize: '0.7rem', color: 'var(--hsa-gold)', backgroundColor: 'rgba(212,175,55,0.1)', padding: '4px 8px', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '4px', whiteSpace: 'nowrap' }}>
              <i className="fa-solid fa-wand-magic-sparkles"></i>
              مُستنتج
            </span>
          )}
        </div>
      </div>

      {/* Start Date */}
      <div className="leave-form-field" style={{ marginBottom: '12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <label className="leave-form-label" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          تاريخ البداية
        </label>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <input
            type="date"
            className="leave-form-date-input"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            style={{
              flex: 1,
              backgroundColor: 'var(--hsa-navy-input)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: '8px',
              padding: '8px',
              color: '#fff',
              outline: 'none'
            }}
          />
          {startInferred && startDate && formData?.fields?.start_date?.value === startDate && (
            <span className="leave-form-inferred-badge" style={{ fontSize: '0.7rem', color: 'var(--hsa-gold)', backgroundColor: 'rgba(212,175,55,0.1)', padding: '4px 8px', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '4px', whiteSpace: 'nowrap' }}>
              <i className="fa-solid fa-wand-magic-sparkles"></i>
              مُستنتج
            </span>
          )}
        </div>
      </div>

      {/* End Date */}
      <div className="leave-form-field" style={{ marginBottom: '12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <label className="leave-form-label" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          تاريخ النهاية
        </label>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <input
            type="date"
            className="leave-form-date-input"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            style={{
              flex: 1,
              backgroundColor: 'var(--hsa-navy-input)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: '8px',
              padding: '8px',
              color: '#fff',
              outline: 'none'
            }}
          />
          {endInferred && endDate && formData?.fields?.end_date?.value === endDate && (
            <span className="leave-form-inferred-badge" style={{ fontSize: '0.7rem', color: 'var(--hsa-gold)', backgroundColor: 'rgba(212,175,55,0.1)', padding: '4px 8px', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '4px', whiteSpace: 'nowrap' }}>
              <i className="fa-solid fa-wand-magic-sparkles"></i>
              مُستنتج
            </span>
          )}
        </div>
      </div>

      {/* Dynamic Summary */}
      {totalDays !== null && totalDays > 0 && (
        <div className="leave-form-summary" style={{ fontSize: '0.85rem', color: 'var(--success)', backgroundColor: 'rgba(16,185,129,0.08)', padding: '8px', borderRadius: '8px', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <i className="fa-solid fa-clock"></i>
          <span>مدة الإجازة: <strong>{totalDays} {totalDays === 1 ? 'يوم' : totalDays === 2 ? 'يومان' : totalDays <= 10 ? 'أيام' : 'يوماً'}</strong></span>
        </div>
      )}

      {/* Validation Message */}
      {!isValid && (leaveType || startDate || endDate) && (
        <div className="leave-form-validation" style={{ fontSize: '0.8rem', color: 'var(--danger)', marginBottom: '12px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {!leaveType && <span>⚠️ يرجى اختيار نوع الإجازة</span>}
          {!startDate && <span>⚠️ يرجى تحديد تاريخ البداية</span>}
          {!endDate && <span>⚠️ يرجى تحديد تاريخ النهاية</span>}
          {startDate && endDate && totalDays !== null && totalDays <= 0 && (
            <span>⚠️ تاريخ النهاية يجب أن يكون بعد تاريخ البداية</span>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="leave-form-actions" style={{ display: 'flex', gap: '8px' }}>
        <button
          className="leave-form-submit"
          onClick={handleSubmit}
          disabled={!isValid || isSubmitting}
          style={{
            flex: 1.5,
            background: (!isValid || isSubmitting) ? 'rgba(255,255,255,0.05)' : 'linear-gradient(135deg, var(--hsa-gold), var(--hsa-gold-dark))',
            color: (!isValid || isSubmitting) ? 'var(--text-muted)' : '#1a1204',
            border: 'none',
            borderRadius: '8px',
            padding: '8px 12px',
            fontSize: '0.85rem',
            fontWeight: 'bold',
            cursor: (!isValid || isSubmitting) ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px'
          }}
        >
          {isSubmitting ? 'جاري الإرسال...' : 'إرسال الطلب'}
        </button>
      <button
        className="leave-form-cancel"
        onClick={onCancel}
        disabled={isSubmitting}
        style={{
          flex: 1,
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid rgba(255,255,255,0.08)',
          color: 'var(--text-secondary)',
          borderRadius: '8px',
          padding: '8px 12px',
          fontSize: '0.85rem',
          cursor: 'pointer'
        }}
      >
        إلغاء
      </button>
    </div>
    </div >
  );
}

function BotMessageBubble({ msg, index, activePendingAction, executePendingAction, sendQuery, activeLeaveForm, submitLeaveForm }) {
  const [displayedText, setDisplayedText] = useState('');
  const [thinkingText, setThinkingText] = useState('');
  const [isThinkingDone, setIsThinkingDone] = useState(false);
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(true); // default expanded while thinking
  const [isTypingCompleted, setIsTypingCompleted] = useState(false);
  const [copied, setCopied] = useState(false);
  const [inquiryCompleted, setInquiryCompleted] = useState(false);

  const isHistory = !msg.rawTextBuffer && !msg.rawTextTarget && msg.text;

  const [typedCitations, setTypedCitations] = useState(
    isHistory ? (msg.citations || []).map(c => c.text) : []
  );

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
    let currentCitIdx = 0;
    let citWordIdx = 0;
    let citationWordTick = 0;
    let targetThinkingText = '';
    let hasInitializedThinkingText = false;
    let localTypedCitations = [];

    const interval = setInterval(() => {
      const state = stateRef.current;

      // 1. Check if LLM response has started arriving
      const hasResponseArrived = (state.rawTextBuffer && state.rawTextBuffer.length > 0) || (state.rawTextTarget && state.rawTextTarget.length > 0);

      if (hasResponseArrived) {
        // If LLM response has arrived, we want to immediately display all citations fully,
        // collapse the thinking container, set isThinkingDone to true, and type the response.
        if (!state.isThinkingDone) {
          state.isThinkingDone = true;
          setIsThinkingDone(true);
          setIsThinkingExpanded(false);
          setTypedCitations(state.citations.map(c => c.text));
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
        return;
      }

      // 2. If LLM response has NOT arrived yet, we proceed with thinking animations
      if (!state.isThinkingDone) {
        // Wait if citations haven't loaded yet
        if (state.citations.length === 0) {
          return;
        }

        // 2a. Type the initial thinking header
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
          return;
        }

        // 2b. After header is done, type citation text word-by-word
        if (currentCitIdx < state.citations.length) {
          const currentCit = state.citations[currentCitIdx];
          const words = currentCit.text.split(/\s+/);

          // We only type a word every 10 ticks (approx 120ms) to look natural and buy time
          citationWordTick++;
          if (citationWordTick >= 10) {
            citationWordTick = 0;

            if (citWordIdx < words.length) {
              const nextCitText = words.slice(0, citWordIdx + 1).join(' ');
              localTypedCitations[currentCitIdx] = nextCitText;
              setTypedCitations([...localTypedCitations]);
              citWordIdx++;
            } else {
              // Finished current citation, move to the next one
              localTypedCitations[currentCitIdx] = currentCit.text;
              setTypedCitations([...localTypedCitations]);
              currentCitIdx++;
              citWordIdx = 0;
            }
          }
        } else {
          // All citations fully typed, but response still hasn't arrived
          state.isThinkingDone = true;
          setIsThinkingDone(true);
        }
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
              ⚙️ جاري مراجعة وتحليل لوائح السياسات...
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
              {msg.citations.map((cit, cIdx) => {
                const typedText = typedCitations[cIdx] || '';
                if (!typedText) return null; // Don't render if we haven't started typing this citation yet
                return (
                  <div key={cIdx} className="citation-block" style={{ padding: '0.5rem 0', borderBottom: cIdx < msg.citations.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none' }}>
                    <div className="citation-text" style={{ fontSize: '0.8rem', opacity: 0.85, marginBottom: '0.25rem', direction: 'rtl', textAlign: 'right' }}>
                      "{typedText}"
                      {cIdx === typedCitations.length - 1 && !isThinkingDone && <span className="cursor-blink"></span>}
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
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* 💬 Actual Bot Message Text */}
      {inquiryShowText && (displayedText || isThinkingDone) && (
        <div style={{ whiteSpace: 'pre-line', fontSize: '0.92rem', lineHeight: '1.7', textAlign: 'right', direction: 'rtl' }} className={isInquiry ? 'animate-fade-in' : ''}>
          {displayedText ? (
            <>
              {displayedText}
              {!isTypingCompleted && <span className="cursor-blink"></span>}
            </>
          ) : (
            !isTypingCompleted && (
              <div className="typing-indicator" style={{ padding: '0.5rem 0', justifyContent: 'flex-start', direction: 'rtl', height: 'auto' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>جاري التحليل وصياغة الرد</span>
                <div className="typing-dot" style={{ width: '6px', height: '6px', margin: '0 2px' }}></div>
                <div className="typing-dot" style={{ width: '6px', height: '6px', margin: '0 2px' }}></div>
                <div className="typing-dot" style={{ width: '6px', height: '6px', margin: '0 2px' }}></div>
              </div>
            )
          )}
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

      {/* Render Leave Request Form */}
      {msg.leaveForm && activeLeaveForm && isTypingCompleted && (
        <LeaveRequestForm
          formData={msg.leaveForm}
          onSubmit={submitLeaveForm}
          onCancel={() => {
            useChatStore.setState({ activeLeaveForm: null });
            sendQuery('إلغاء طلب الإجازة');
          }}
        />
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
    <div className="message-bubble user-bubble-wrapper">
      <div style={{ whiteSpace: 'pre-line', fontSize: '0.92rem', lineHeight: '1.7', textAlign: 'right', direction: 'rtl' }}>
        {msg.text}
      </div>
      <div className="user-message-actions">
        <button
          onClick={handleEdit}
          className="user-action-btn"
          title="تعديل الرسالة"
        >
          <i className="fa-solid fa-pen-to-square" />
        </button>
        <button
          onClick={handleCopy}
          className="user-action-btn"
          title={copied ? "تم نسخ النص" : "نسخ الرسالة"}
        >
          <i className={`fa-solid ${copied ? 'fa-check' : 'fa-copy'}`} style={{ color: copied ? 'var(--success)' : '' }} />
        </button>
      </div>
    </div>
  );
}

export default function AssistantView() {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const messages = useChatStore((state) => state.messages);
  const isWaitingResponse = useChatStore((state) => state.isWaitingResponse);
  const abortController = useChatStore((state) => state.abortController);
  const sendQuery = useChatStore((state) => state.sendQuery);
  const stopResponse = useChatStore((state) => state.stopResponse);
  const executePendingAction = useChatStore((state) => state.executePendingAction);
  const activePendingAction = useChatStore((state) => state.activePendingAction);
  const activeLeaveForm = useChatStore((state) => state.activeLeaveForm);
  const submitLeaveForm = useChatStore((state) => state.submitLeaveForm);

  const isGenerating = isWaitingResponse || abortController !== null;

  const handleSend = () => {
    if (isGenerating) {
      stopResponse();
      setTimeout(() => {
        if (inputRef.current) inputRef.current.focus();
      }, 50);
      return;
    }
    const query = inputValue.trim();
    if (!query) return;
    setInputValue('');
    sendQuery(query);
    setTimeout(() => {
      if (inputRef.current) inputRef.current.focus();
    }, 50);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      if (isGenerating) {
        e.preventDefault();
        return;
      }
      if (!inputValue.trim() || activePendingAction) {
        e.preventDefault();
        return;
      }
      handleSend();
    }
  };

  // Auto focus input field on mount
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  // Maintain focus when response state changes and input is not disabled
  useEffect(() => {
    if (!isGenerating && activePendingAction === null) {
      if (inputRef.current) {
        inputRef.current.focus();
      }
    }
  }, [isGenerating, activePendingAction]);

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
                    onClick={() => {
                      sendQuery(q.text);
                      setTimeout(() => {
                        if (inputRef.current) inputRef.current.focus();
                      }, 50);
                    }}
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
                      activeLeaveForm={activeLeaveForm}
                      submitLeaveForm={submitLeaveForm}
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
              ref={inputRef}
              type="text"
              className="chat-input"
              id="chat-input"
              placeholder={activePendingAction ? "بانتظار تأكيد الإجراء من البطاقة أعلاه..." : "اكتب استفسارك هنا..."}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={activePendingAction !== null}
            />
            <button
              className={`send-btn ${isGenerating ? 'stop-active has-text' : ((!inputValue.trim() || activePendingAction) ? 'disabled' : '')} ${inputValue.trim() && !isGenerating && !activePendingAction ? 'has-text' : ''}`}
              onClick={handleSend}
              id="send-btn"
              disabled={activePendingAction !== null || (!isGenerating && !inputValue.trim())}
            >
              {isGenerating ? (
                <i className="fa-solid fa-stop" id="send-icon" style={{ fontSize: '0.95rem' }}></i>
              ) : (
                <i className="fa-solid fa-paper-plane" style={{ transform: 'rotate(180deg)' }} id="send-icon"></i>
              )}
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

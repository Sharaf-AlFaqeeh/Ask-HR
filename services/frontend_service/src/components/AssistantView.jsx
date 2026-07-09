import React, { useState, useEffect, useRef } from 'react';
import { useChatStore } from '../store/useChatStore';
import { useAppStore } from '../store/useAppStore';

// Helper to detect if text is predominantly English
function isEnglishText(text) {
  if (!text) return false;
  const hasArabic = /[\u0600-\u06FF]/.test(text);
  return !hasArabic;
}

// Helper to parse inline markdown patterns (bold, italic, code, links)
function parseInlineMarkdown(text) {
  if (!text) return '';

  const pattern = /(\*\*([^*]+)\*\*)|(\*([^*]+)\*)|(`([^`]+)`)|(\[([^\]]+)\]\(([^)]+)\))/g;
  const tokens = [];
  let lastIndex = 0;
  let key = 0;

  let match;
  while ((match = pattern.exec(text)) !== null) {
    const matchIndex = match.index;

    if (matchIndex > lastIndex) {
      tokens.push(text.substring(lastIndex, matchIndex));
    }

    if (match[1]) {
      tokens.push(<strong key={key++} className="md-bold">{match[2]}</strong>);
    } else if (match[3]) {
      tokens.push(<em key={key++} className="md-italic">{match[4]}</em>);
    } else if (match[5]) {
      tokens.push(<code key={key++} className="md-code">{match[6]}</code>);
    } else if (match[7]) {
      tokens.push(
        <a key={key++} href={match[9]} target="_blank" rel="noopener noreferrer" className="md-link">
          {match[8]}
        </a>
      );
    }

    lastIndex = pattern.lastIndex;
  }

  if (lastIndex < text.length) {
    tokens.push(text.substring(lastIndex));
  }

  return tokens.length > 0 ? tokens : text;
}

// Render markdown blocks: tables, lists, headers, blockquotes, paragraphs
function renderMarkdown(text) {
  if (!text) return null;

  const lines = text.split('\n');
  const blocks = [];
  let currentTable = null;
  let currentList = null; // { type: 'ul' | 'ol', items: [] }
  let currentParagraph = [];

  const flushParagraph = (key) => {
    if (currentParagraph.length > 0) {
      blocks.push(
        <p key={key} className="md-paragraph">
          {currentParagraph.map((line, idx) => (
            <React.Fragment key={idx}>
              {idx > 0 && <br />}
              {parseInlineMarkdown(line)}
            </React.Fragment>
          ))}
        </p>
      );
      currentParagraph = [];
    }
  };

  const flushTable = (key) => {
    if (currentTable) {
      const rows = currentTable.map(line => {
        const cells = line.split('|').map(c => c.trim());
        if (cells[0] === '') cells.shift();
        if (cells[cells.length - 1] === '') cells.pop();
        return cells;
      });

      let hasHeader = true;
      let headerRow = rows[0] || [];
      let bodyRows = rows.slice(1);

      const isSeparator = (row) => row.every(cell => /^:?-+:?$/.test(cell));
      if (rows[1] && isSeparator(rows[1])) {
        bodyRows = rows.slice(2);
      } else if (rows[0] && isSeparator(rows[0])) {
        hasHeader = false;
        bodyRows = rows.slice(1);
      }

      blocks.push(
        <div key={key} className="md-table-container">
          <table className="md-table">
            {hasHeader && (
              <thead>
                <tr>
                  {headerRow.map((cell, idx) => (
                    <th key={idx}>{parseInlineMarkdown(cell)}</th>
                  ))}
                </tr>
              </thead>
            )}
            <tbody>
              {bodyRows.map((row, rowIdx) => (
                <tr key={rowIdx}>
                  {row.map((cell, cellIdx) => (
                    <td key={cellIdx}>{parseInlineMarkdown(cell)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      currentTable = null;
    }
  };

  const flushList = (key) => {
    if (currentList) {
      const Tag = currentList.type;
      blocks.push(
        <Tag key={key} className={currentList.type === 'ul' ? 'md-ul' : 'md-ol'}>
          {currentList.items.map((item, idx) => (
            <li key={idx} className="md-li">
              {parseInlineMarkdown(item)}
            </li>
          ))}
        </Tag>
      );
      currentList = null;
    }
  };

  const flushAll = (key) => {
    flushParagraph(key + '-p');
    flushTable(key + '-t');
    flushList(key + '-l');
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // 1. Table Row
    const isTableRow = trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.length > 1;
    if (isTableRow) {
      flushParagraph(i);
      flushList(i);
      if (!currentTable) currentTable = [];
      currentTable.push(trimmed);
      continue;
    } else {
      flushTable(i);
    }

    // 2. Unordered List Item
    const ulMatch = line.match(/^(\s*)[-*]\s+(.*)$/);
    if (ulMatch) {
      flushParagraph(i);
      flushTable(i);
      if (!currentList || currentList.type !== 'ul') {
        flushList(i);
        currentList = { type: 'ul', items: [] };
      }
      currentList.items.push(ulMatch[2]);
      continue;
    }

    // 3. Ordered List Item
    const olMatch = line.match(/^(\s*)\d+\.\s+(.*)$/);
    if (olMatch) {
      flushParagraph(i);
      flushTable(i);
      if (!currentList || currentList.type !== 'ol') {
        flushList(i);
        currentList = { type: 'ol', items: [] };
      }
      currentList.items.push(olMatch[2]);
      continue;
    }

    flushList(i);

    // 4. Headers
    const headerMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
    if (headerMatch) {
      flushParagraph(i);
      const level = headerMatch[1].length;
      const content = headerMatch[2];
      const Tag = `h${Math.min(level + 2, 6)}`;
      blocks.push(
        <Tag key={i} className={`md-header md-h${level}`}>
          {parseInlineMarkdown(content)}
        </Tag>
      );
      continue;
    }

    // 5. Blockquotes
    if (trimmed.startsWith('>')) {
      flushParagraph(i);
      const content = trimmed.substring(1).trim();
      blocks.push(
        <blockquote key={i} className="md-blockquote">
          {parseInlineMarkdown(content)}
        </blockquote>
      );
      continue;
    }

    // 6. Empty Line
    if (trimmed === '') {
      flushParagraph(i);
      continue;
    }

    currentParagraph.push(line);
  }

  flushAll(lines.length);

  return blocks;
}

// Appends typing cursor to the last text node in the parsed block structure
function appendCursor(blocks, cursorKey) {
  if (!blocks || blocks.length === 0) {
    return [<span key={cursorKey} className="cursor-blink"></span>];
  }

  const lastIndex = blocks.length - 1;
  const lastBlock = blocks[lastIndex];
  const cursor = <span key={cursorKey} className="cursor-blink"></span>;

  if (React.isValidElement(lastBlock)) {
    const children = lastBlock.props.children;
    let newChildren;

    if (children === undefined || children === null) {
      newChildren = cursor;
    } else if (Array.isArray(children)) {
      if (children.length > 0) {
        const lastChild = children[children.length - 1];
        newChildren = [
          ...children.slice(0, -1),
          <React.Fragment key="last-with-cursor">
            {lastChild}
            {cursor}
          </React.Fragment>
        ];
      } else {
        newChildren = [cursor];
      }
    } else {
      newChildren = (
        <React.Fragment key="last-with-cursor">
          {children}
          {cursor}
        </React.Fragment>
      );
    }

    const clonedBlock = React.cloneElement(lastBlock, {}, newChildren);
    const updatedBlocks = [...blocks];
    updatedBlocks[lastIndex] = clonedBlock;
    return updatedBlocks;
  }

  return [...blocks, cursor];
}

// Reusable Thinking & Analyzing Indicator Component
function ThinkingIndicator({ text, color = 'gold', showIcon = true }) {
  const indicatorDirection = useAppStore((state) => state.indicatorDirection || 'rtl');
  const isRtl = indicatorDirection === 'auto' ? !isEnglishText(text) : indicatorDirection === 'rtl';

  let dotBg = 'linear-gradient(135deg, var(--hsa-gold), var(--hsa-gold-dark))';
  let textColor = 'var(--text-muted)';
  let iconClass = 'fa-solid fa-wand-magic-sparkles';
  let iconStyle = { color: 'var(--hsa-gold)', fontSize: '0.85rem' };
  let indicatorStyle = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '8px',
    padding: '0.4rem 0.8rem',
    borderRadius: '12px',
    background: 'rgba(255, 255, 255, 0.03)',
    border: '1px solid rgba(255, 255, 255, 0.05)',
    direction: isRtl ? 'rtl' : 'ltr',
    height: 'auto',
    marginBottom: '0.5rem'
  };

  if (color === 'blue') {
    dotBg = 'linear-gradient(135deg, #38bdf8, #0284c7)';
    textColor = '#38bdf8';
    iconClass = 'fa-solid fa-gears fa-spin';
    iconStyle = { color: '#38bdf8', fontSize: '0.85rem' };
    indicatorStyle.background = 'rgba(56, 189, 248, 0.04)';
    indicatorStyle.borderColor = 'rgba(56, 189, 248, 0.12)';
  } else if (color === 'gold') {
    dotBg = 'linear-gradient(135deg, var(--hsa-gold), var(--hsa-gold-dark))';
    textColor = 'var(--hsa-gold)';
    iconClass = 'fa-solid fa-wand-magic-sparkles fa-bounce';
    iconStyle = { color: 'var(--hsa-gold)', fontSize: '0.85rem' };
    indicatorStyle.background = 'rgba(212, 175, 55, 0.04)';
    indicatorStyle.borderColor = 'rgba(212, 175, 55, 0.12)';
  } else {
    dotBg = color;
    textColor = color;
    iconClass = 'fa-solid fa-spinner fa-spin';
    iconStyle = { color: color, fontSize: '0.85rem' };
  }

  return (
    <div className="typing-indicator animate-fade-in" style={indicatorStyle}>
      {showIcon && <i className={iconClass} style={iconStyle} />}
      <span style={{ fontSize: '0.82rem', color: textColor, fontWeight: '600' }}>
        {text}
      </span>
      <div style={{ display: 'flex', gap: '4px', [isRtl ? 'marginRight' : 'marginLeft']: '4px' }}>
        <div className="typing-dot" style={{ background: dotBg, width: '6px', height: '6px' }} />
        <div className="typing-dot" style={{ background: dotBg, width: '6px', height: '6px' }} />
        <div className="typing-dot" style={{ background: dotBg, width: '6px', height: '6px' }} />
      </div>
    </div>
  );
}

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
  const indicatorDirection = useAppStore((state) => state.indicatorDirection || 'rtl');
  
  const [displayedText, setDisplayedText] = useState('');
  const [thinkingText, setThinkingText] = useState('');
  const [isThinkingDone, setIsThinkingDone] = useState(false);
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(true); // default expanded while thinking
  const [isTypingCompleted, setIsTypingCompleted] = useState(false);
  const [copied, setCopied] = useState(false);
  const [inquiryCompleted, setInquiryCompleted] = useState(false);

  const isBubbleRtl = indicatorDirection === 'auto' ? !isEnglishText(displayedText || msg.text || msg.rawTextTarget) : indicatorDirection === 'rtl';

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
          setIsThinkingDone(true);
          setIsThinkingExpanded(false); // Auto collapse thinking on completion
        }
        return;
      }

      // 2. If LLM response has NOT arrived yet, we proceed with thinking animations
      if (!state.isThinkingDone) {
        // If citations haven't loaded yet, type a default thinking message
        if (state.citations.length === 0) {
          if (!hasInitializedThinkingText) {
            targetThinkingText = `جاري البحث والتحليل في لوائح الموارد البشرية...`;
            hasInitializedThinkingText = true;
            thinkingCharIdx = 0;
          }

          if (thinkingCharIdx < targetThinkingText.length) {
            const nextText = targetThinkingText.substring(0, thinkingCharIdx + 1);
            setThinkingText(nextText);
            state.thinkingText = nextText;
            thinkingCharIdx++;
          }
          return;
        }

        // 2a. If citations exist, format and type the detailed thinking header
        const docSources = Array.from(new Set(state.citations.map(c => c.source)));
        // const expectedDetailedText = `جاري مراجعة وتحليل لوائح السياسات المسترجعة من مستند [${docSources.join(', ')}]...`;
        const expectedDetailedText = `Analyzing`;

        if (!hasInitializedThinkingText || targetThinkingText !== expectedDetailedText) {
          targetThinkingText = expectedDetailedText;
          hasInitializedThinkingText = true;
          thinkingCharIdx = 0; // Reset detailed header typing
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
      {inquiryShowText && (!isThinkingDone || (msg.citations && msg.citations.length > 0)) && (
        <div className="thinking-process-container animate-fade-in" style={{ marginBottom: '0.6rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', direction: isBubbleRtl ? 'rtl' : 'ltr', justifyContent: 'flex-start' }}>
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

            {/* <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 600 }}>
              ⚙️ جاري مراجعة وتحليل لوائح السياسات...
            </span> */}
          </div>

          {isThinkingExpanded && (
            <div className="thinking-process-content" style={{ marginTop: '0.4rem', padding: '0.6rem 0.8rem', borderRadius: '8px', background: 'rgba(0, 0, 0, 0.12)', border: '1px solid rgba(255,255,255,0.03)' }}>
              {/* Simulated typing status */}
              <div style={{ display: 'flex', justifyContent: 'flex-start', width: '100%', direction: isBubbleRtl ? 'rtl' : 'ltr' }}>
                {!isThinkingDone ? (
                  <ThinkingIndicator text={thinkingText} color="blue" />
                ) : (
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', opacity: 0.7, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <i className="fa-solid fa-circle-check" style={{ color: 'var(--success)', fontSize: '0.85rem' }} />
                    <span>{thinkingText}</span>
                  </div>
                )}
              </div>

              {/* Citations references */}
              {msg.citations && msg.citations.length > 0 && msg.citations.map((cit, cIdx) => {
                const typedText = typedCitations[cIdx] || '';
                if (!typedText) return null; // Don't render if we haven't started typing this citation yet
                return (
                  <div key={cIdx} className="citation-block" style={{ padding: '0.5rem 0', borderBottom: cIdx < msg.citations.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none' }}>
                    <div className="citation-text" style={{ fontSize: '0.8rem', opacity: 0.85, marginBottom: '0.25rem', direction: isBubbleRtl ? 'rtl' : 'ltr', textAlign: isBubbleRtl ? 'right' : 'left' }}>
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
        <div
          style={{
            fontSize: '0.92rem',
            lineHeight: '1.7',
            textAlign: (displayedText ? isEnglishText(displayedText) : !isBubbleRtl) ? 'left' : 'right',
            direction: (displayedText ? isEnglishText(displayedText) : !isBubbleRtl) ? 'ltr' : 'rtl'
          }}
          className={`${isInquiry ? 'animate-fade-in' : ''} ${(displayedText ? isEnglishText(displayedText) : !isBubbleRtl) ? 'md-ltr' : ''}`}
        >
          {displayedText ? (
            isTypingCompleted ? (
              renderMarkdown(displayedText)
            ) : (
              appendCursor(renderMarkdown(displayedText), 'bot-cursor')
            )
          ) : (
            !isTypingCompleted && (
              <ThinkingIndicator text="Thinking" color="gold" />
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
  const chatMessagesRef = useRef(null);
  const messagesInnerRef = useRef(null);

  const messages = useChatStore((state) => state.messages);
  const sessionId = useChatStore((state) => state.sessionId);
  const isWaitingResponse = useChatStore((state) => state.isWaitingResponse);
  const abortController = useChatStore((state) => state.abortController);
  const sendQuery = useChatStore((state) => state.sendQuery);
  const stopResponse = useChatStore((state) => state.stopResponse);
  const executePendingAction = useChatStore((state) => state.executePendingAction);
  const activePendingAction = useChatStore((state) => state.activePendingAction);
  const activeLeaveForm = useChatStore((state) => state.activeLeaveForm);
  const submitLeaveForm = useChatStore((state) => state.submitLeaveForm);

  const isGenerating = isWaitingResponse || abortController !== null;
  const messagesRef = useRef(messages);

  const handleSend = (overrideQuery) => {
    if (isGenerating) {
      stopResponse();
      setTimeout(() => {
        if (inputRef.current) inputRef.current.focus();
      }, 50);
      return;
    }
    const query = typeof overrideQuery === 'string' ? overrideQuery.trim() : inputValue.trim();
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

  // Keep messages ref up to date for scroll observer callback
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  // Auto-scroll logic during typing/streaming using ResizeObserver
  useEffect(() => {
    const container = chatMessagesRef.current;
    const inner = messagesInnerRef.current;
    if (!container || !inner) return;

    // Scroll to bottom immediately on session change or new message
    container.scrollTo({ top: container.scrollHeight, behavior: 'auto' });

    let lastScrollTop = container.scrollTop;
    let lastScrollHeight = container.scrollHeight;

    const handleScroll = () => {
      lastScrollTop = container.scrollTop;
      lastScrollHeight = container.scrollHeight;
    };
    container.addEventListener('scroll', handleScroll);

    const observer = new ResizeObserver(() => {
      const newScrollHeight = container.scrollHeight;
      const clientHeight = container.clientHeight;

      // Check if user was scrolled to the bottom (within threshold of 150px)
      const isAtBottom = lastScrollTop + clientHeight >= lastScrollHeight - 150;
      
      const currentMessages = messagesRef.current;
      const lastMessage = currentMessages[currentMessages.length - 1];
      const isLastMessageUser = lastMessage && lastMessage.sender === 'user';

      if (isAtBottom || isLastMessageUser) {
        container.scrollTo({ top: newScrollHeight, behavior: 'auto' });
      }

      lastScrollHeight = newScrollHeight;
      lastScrollTop = container.scrollTop;
    });

    observer.observe(inner);

    return () => {
      observer.disconnect();
      container.removeEventListener('scroll', handleScroll);
    };
  }, [sessionId]);

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
        <div className="chat-messages" id="chat-messages" ref={chatMessagesRef}>
          <div ref={messagesInnerRef} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', width: '100%' }}>
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
                      handleSend(q.text);
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

          {isWaitingResponse && messages[messages.length - 1]?.sender !== 'bot' && (
            <div className="message-wrapper bot">
              <div className="message-bubble-container" style={{ width: '100%' }}>
                <div className="message-bubble">
                  <ThinkingIndicator text="يفكر" color="gold" />
                </div>
              </div>
            </div>
          )}
          </div>
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

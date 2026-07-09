import React, { useState, useEffect, useRef } from 'react';
import { useAppStore } from '../store/useAppStore';
import { useChatStore } from '../store/useChatStore';

export default function SettingsView() {
  const { authToken, setAuthToken, consoleLogs, clearConsoleLogs, indicatorDirection, setIndicatorDirection } = useAppStore();
  const { sessionId, triggerIngest, isIngesting, clearSessionById } = useChatStore();

  const [clearId, setClearId] = useState('');
  const consoleEndRef = useRef(null);

  // Sync clear ID input with active session ID if available
  useEffect(() => {
    if (sessionId) {
      setClearId(sessionId);
    }
  }, [sessionId]);

  // Auto scroll console logs to bottom
  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [consoleLogs]);

  return (
    <div id="view-settings" className="view-panel active">
      <div className="settings-container">
        {/* Access Token settings */}
        <div className="settings-card">
          <h3 className="settings-title">المصادقة والتحقق من الوصول</h3>
          <p className="settings-desc">إعدادات كلمات المرور ومفاتيح التوثيق الخاصة بالاتصال بخوادم أوركسترا الموارد البشرية.</p>

          <div className="form-group">
            <label>رمزBearer للمطور (Static Authorization Key)</label>
            <input 
              type="text" 
              id="auth-token" 
              value={authToken}
              onChange={(e) => setAuthToken(e.target.value)}
            />
          </div>
        </div>

        {/* UI Customization settings */}
        <div className="settings-card">
          <h3 className="settings-title">تخصيص واجهة المستخدم والتفاعل</h3>
          <p className="settings-desc">تعديل سلوك واتجاه حركة مؤشرات التفكير والتحليل في النظام.</p>

          <div className="form-group">
            <label>اتجاه مؤشر التفكير والتحليل (Thinking & Analyzing Direction)</label>
            <select
              className="select-style"
              value={indicatorDirection}
              onChange={(e) => setIndicatorDirection(e.target.value)}
            >
              <option value="rtl">من اليمين إلى اليسار (RTL) - للغة العربية</option>
              <option value="ltr">من اليسار إلى اليمين (LTR) - للغة الإنجليزية</option>
              <option value="auto">تلقائي (Auto) - بناءً على لغة النص</option>
            </select>
          </div>
        </div>

        {/* Admin controls panel */}
        <div className="settings-card">
          <h3 className="settings-title">إجراءات المدير والعمليات الخلفية</h3>
          <p className="settings-desc">أدوات إدارية خاصة بتهيئة قاعدة البيانات Vector DB وحذف جلسات الذاكرة المؤقتة.</p>

          <div className="action-group">
            <button 
              className="btn-card btn-admin" 
              onClick={triggerIngest} 
              id="btn-ingest"
              disabled={isIngesting}
              style={{ backgroundColor: 'var(--accent-admin)', width: '100%', justifyContent: 'center', color: 'white', opacity: isIngesting ? 0.6 : 1 }}
            >
              <i className={`fa-solid ${isIngesting ? 'fa-sync fa-spin' : 'fa-sync'}`}></i>
              {isIngesting ? ' جاري تحديث الفهرس...' : ' إعادة بناء فهرس المستندات (Ingest Vector DB)'}
            </button>

            <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.05)', marginTop: '1rem', paddingTop: '1rem' }}>
              <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', display: 'block', fontWeight: 600 }}>
                مسح بيانات جلسة محددة من الذاكرة:
              </label>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <input 
                  type="text" 
                  className="input-style" 
                  id="session-clear-id"
                  placeholder="أدخل معرف الجلسة Session ID" 
                  style={{ flex: 1, backgroundColor: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '4px', padding: '0 0.75rem', outline: 'none' }}
                  value={clearId}
                  onChange={(e) => setClearId(e.target.value)}
                />
                <button 
                  className="btn-card btn-danger" 
                  onClick={() => clearSessionById(clearId)}
                  style={{ backgroundColor: 'var(--danger)', border: 'none', color: 'white' }}
                >
                  حذف الجلسة
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Live Terminal Output */}
        <div className="settings-card" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: '250px' }}>
          <div className="split-card-header" style={{ marginBottom: '0.75rem' }}>
            <div>
              <h3 className="settings-title">سجل الأحداث والعمليات الفوري (Console Logs)</h3>
            </div>
            <button 
              className="new-chat-btn" 
              onClick={clearConsoleLogs}
              style={{ fontSize: '0.75rem', padding: '0.2rem 0.6rem', border: 'none', cursor: 'pointer' }}
            >
              مسح السجل
            </button>
          </div>

          <div className="console-output" id="console-output" style={{ overflowY: 'auto', maxHeight: '180px' }}>
            {consoleLogs.map((log, idx) => {
              let badgeClass = 'console-type-info';
              let badgeText = '[INFO]';
              if (log.type === 'success') {
                badgeClass = 'console-type-success';
                badgeText = '[SUCCESS]';
              } else if (log.type === 'warn') {
                badgeClass = 'console-type-warn';
                badgeText = '[WARN]';
              } else if (log.type === 'error') {
                badgeClass = 'console-type-error';
                badgeText = '[ERROR]';
              }

              return (
                <div key={idx} className="console-line">
                  <span className="console-time">[{log.time}]</span>
                  <span className={badgeClass}>{badgeText}</span>
                  <span>{log.message}</span>
                </div>
              );
            })}
            <div ref={consoleEndRef} />
          </div>
        </div>
      </div>
    </div>
  );
}

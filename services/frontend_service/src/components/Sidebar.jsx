import React from 'react';
import { useAppStore } from '../store/useAppStore';
import { useChatStore } from '../store/useChatStore';

export default function Sidebar() {
  const toggleSidebar = useAppStore((state) => state.toggleSidebar);
  const startNewSession = useChatStore((state) => state.startNewSession);
  const sessions = useChatStore((state) => state.sessions);
  const sessionId = useChatStore((state) => state.sessionId);
  const loadSession = useChatStore((state) => state.loadSession);
  const clearSessionById = useChatStore((state) => state.clearSessionById);
  const switchView = useAppStore((state) => state.switchView);

  return (
    <aside className="sidebar">
      <div className="sidebar-inner">
        <div className="sidebar-header">
          <div className="sidebar-logo-row">
            <div className="logo-wrapper">
              <svg className="hsa-logo-svg" viewBox="0 0 120 40" width="120" height="40">
                <defs>
                  <linearGradient id="gold-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#FFE082" />
                    <stop offset="50%" stopColor="#D4AF37" />
                    <stop offset="100%" stopColor="#B38F24" />
                  </linearGradient>
                </defs>
                <text x="5" y="28" fontFamily="'Outfit', sans-serif" fontWeight="900" fontSize="26"
                  fill="url(#gold-grad)" letterSpacing="-1">HSA</text>
                <path d="M 5 32 Q 55 38 105 32" fill="none" stroke="#0056b3" strokeWidth="3.5"
                  strokeLinecap="round" />
                <path d="M 45 32 Q 75 35 105 32" fill="none" stroke="url(#gold-grad)" strokeWidth="2.5"
                  strokeLinecap="round" />
              </svg>
              <span className="logo-divider">|</span>
            </div>
            <button 
              className="sidebar-close-btn"
              onClick={toggleSidebar}
              title="إخفاء القائمة الجانبية"
            >
              <i className="fa-solid fa-bars"></i>
            </button>
          </div>
          <div className="sidebar-subtitle">HSA GROUP CORPORATE AI SUITE</div>
        </div>

        {/* Persistent Chat Sessions History Manager */}
        <div className="sidebar-sessions-title">محادثاتك السابقة</div>
        <div style={{ padding: '0 0.5rem', marginBottom: '0.75rem' }}>
          <button 
            className="sidebar-new-chat-btn" 
            onClick={() => {
              startNewSession();
              if (window.innerWidth <= 768) {
                toggleSidebar();
              }
            }}
          >
            <i className="fa-solid fa-plus"></i>
            محادثة جديدة
          </button>
        </div>

        <div className="sidebar-session-list">
          {sessions.length === 0 ? (
            <div style={{ textAlign: 'center', fontSize: '0.72rem', color: 'var(--text-muted)', padding: '1rem 0' }}>
              لا توجد محادثات سابقة.
            </div>
          ) : (
            sessions.map((s) => (
              <div 
                key={s.session_id} 
                className={`sidebar-session-item ${sessionId === s.session_id ? 'active' : ''}`}
                onClick={() => {
                  if (sessionId !== s.session_id) {
                    loadSession(s.session_id);
                    switchView('assistant');
                    if (window.innerWidth <= 768) {
                      toggleSidebar();
                    }
                  }
                }}
              >
                <div className="session-item-content">
                  <i className="fa-regular fa-comment"></i>
                  <span className="session-item-preview" title={s.preview}>{s.preview}</span>
                </div>
                <button 
                  className="session-delete-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm('هل أنت متأكد من حذف هذه المحادثة؟')) {
                      clearSessionById(s.session_id);
                    }
                  }}
                  title="حذف المحادثة"
                >
                  <i className="fa-solid fa-trash-can"></i>
                </button>
              </div>
            ))
          )}
        </div>

        <div className="sidebar-footer">
          <div className="footer-link">
            <i className="fa-solid fa-circle-question"></i>
            <span>مركز المساعدة</span>
          </div>
          <div 
            className="footer-link" 
            onClick={() => {
              if (confirm('هل أنت متأكد من تسجيل الخروج؟')) {
                localStorage.removeItem('authToken');
                localStorage.removeItem('userProfile');
                useAppStore.setState({ authToken: null, loggedInUser: null });
                useChatStore.getState().startNewSession();
              }
            }}
          >
            <i className="fa-solid fa-arrow-right-from-bracket"></i>
            <span>تسجيل الخروج</span>
          </div>
        </div>
      </div>
    </aside>
  );
}

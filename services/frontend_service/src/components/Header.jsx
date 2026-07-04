import React, { useEffect } from 'react';
import { useAppStore } from '../store/useAppStore';
import { useChatStore } from '../store/useChatStore';

export default function Header() {
  const { activeView, switchView, theme, toggleTheme, serverStatus, serverStatusText, checkServerHealth, loggedInUser, sidebarCollapsed, toggleSidebar } = useAppStore();
  const triggerIngest = useChatStore((state) => state.triggerIngest);
  const isIngesting = useChatStore((state) => state.isIngesting);

  useEffect(() => {
    // Initial check
    checkServerHealth();
    
    // Check health every 15 seconds
    const interval = setInterval(checkServerHealth, 15000);
    return () => clearInterval(interval);
  }, [checkServerHealth]);

  return (
    <header className="top-header">
      {sidebarCollapsed && (
        <button 
          className="header-sidebar-toggle" 
          onClick={toggleSidebar}
          title="عرض القائمة الجانبية"
        >
          <i className="fa-solid fa-bars"></i>
        </button>
      )}

      <div className="logo-area">
        <div className="logo-wrapper">
          <span className="header-brand">AskHR</span>
          <span className="logo-divider">|</span>
          <span className="logo-hsa-text">HSA</span>
        </div>
      </div>

      <div className="search-container">
        <input type="text" className="search-input" placeholder="البحث عن مصادر وسياسات..." />
        <i className="fa-solid fa-magnifying-glass search-icon"></i>
      </div>

      <div className="header-tabs">
        <div 
          className={`header-tab ${activeView === 'dashboard' ? 'active' : ''}`} 
          id="header-tab-overview" 
          onClick={() => switchView('dashboard')}
        >
          نظرة عامة
        </div>
        <div 
          className={`header-tab ${activeView === 'assistant' ? 'active' : ''}`} 
          id="header-tab-assistant" 
          onClick={() => switchView('assistant')}
        >
          المساعد الذكي
        </div>
        <div 
          className={`header-tab ${activeView === 'settings' ? 'active' : ''}`} 
          onClick={() => switchView('settings')}
        >
          الإعدادات والتفويض
        </div>
      </div>

      <button 
        className="header-action-btn" 
        onClick={triggerIngest}
        disabled={isIngesting}
      >
        {isIngesting ? <i className="fa-solid fa-sync fa-spin" style={{ marginLeft: '0.25rem' }}></i> : '+ '}
        تحديث الفهرس
      </button>

      <div className="header-controls">
        {/* Premium Theme Toggle Pill Switch */}
        <div 
          className="theme-toggle-pill" 
          id="theme-toggle-pill" 
          onClick={toggleTheme}
          title="تبديل المظهر (Light/Dark Mode)"
        >
          <div className="theme-pill-active-bg" style={{ transform: theme === 'light' ? 'translateX(-50%)' : 'translateX(0)' }}></div>
          <span className={`theme-pill-btn ${theme === 'dark' ? 'active' : ''}`} id="theme-pill-dark">
            <i className="fa-solid fa-moon"></i>
            <span>داكن</span>
          </span>
          <span className={`theme-pill-btn ${theme === 'light' ? 'active' : ''}`} id="theme-pill-light">
            <i className="fa-solid fa-sun"></i>
            <span>فاتح</span>
          </span>
        </div>

        <div className="control-icon">
          <i className="fa-solid fa-bell"></i>
          <div className="control-badge"></div>
        </div>

        <div className="control-icon">
          <i className="fa-solid fa-keyboard"></i>
        </div>

        <div className="server-status">
          <div className={`status-dot ${serverStatus === 'offline' || serverStatus === 'warning' ? 'offline' : ''}`} id="server-status-dot"></div>
          <span id="server-status-text">{serverStatusText}</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <div className="user-info-text" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', fontSize: '0.75rem', lineStyle: 'none' }}>
            <span style={{ fontWeight: 700, color: '#fff' }}>
              {loggedInUser ? `${loggedInUser.first_name} ${loggedInUser.last_name}` : 'زائر'}
            </span>
            <span style={{ color: 'var(--text-secondary)', fontSize: '0.68rem', direction: 'rtl' }}>
              {loggedInUser ? loggedInUser.department : 'شير بونت SSO'}
            </span>
          </div>
          <div 
            className="user-cell-avatar" 
            style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }} 
            onClick={() => switchView('settings')}
            title={loggedInUser ? `الموظف: ${loggedInUser.first_name}` : 'المستخدم'}
          >
            {loggedInUser ? `${loggedInUser.first_name[0]}${loggedInUser.last_name[0]}`.toUpperCase() : 'HR'}
          </div>
        </div>
      </div>
    </header>
  );
}

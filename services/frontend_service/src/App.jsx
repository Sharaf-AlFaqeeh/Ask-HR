import React, { useEffect } from 'react';
import { useAppStore, baseUrl } from './store/useAppStore';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import DashboardView from './components/DashboardView';
import AssistantView from './components/AssistantView';
import SettingsView from './components/SettingsView';
import SharepointLogin from './components/SharepointLogin';
import { useChatStore } from './store/useChatStore';
import { hasPermission } from './utils/permissions';

export default function App() {
  const activeView = useAppStore((state) => state.activeView);
  const switchView = useAppStore((state) => state.switchView);
  const loggedInUser = useAppStore((state) => state.loggedInUser);
  const theme = useAppStore((state) => state.theme);
  const sidebarCollapsed = useAppStore((state) => state.sidebarCollapsed);
  const toggleSidebar = useAppStore((state) => state.toggleSidebar);
  const authToken = useAppStore((state) => state.authToken);
  const fetchSessions = useChatStore((state) => state.fetchSessions);

  // Apply theme class to body element when theme state changes
  useEffect(() => {
    if (theme === 'light') {
      document.body.classList.add('light-theme');
    } else {
      document.body.classList.remove('light-theme');
    }
  }, [theme]);

  // Fetch previous chats and latest user profile when user is authenticated
  useEffect(() => {
    if (authToken) {
      fetchSessions();
      
      // Fetch latest profile to ensure roles/permissions are up to date
      fetch(`${baseUrl}/api/v1/auth/me`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      })
      .then(res => {
        if (res.ok) return res.json();
        throw new Error('Unauthorized');
      })
      .then(profile => {
        localStorage.setItem('userProfile', JSON.stringify(profile));
        useAppStore.setState({ loggedInUser: profile });
      })
      .catch(err => {
        // If unauthorized/expired, clear token and log out
        localStorage.removeItem('authToken');
        localStorage.removeItem('userProfile');
        useAppStore.setState({ authToken: null, loggedInUser: null });
      });
    }
  }, [authToken, fetchSessions]);

  // Guard views: redirect user if they try to access a view they don't have permission for
  useEffect(() => {
    if (loggedInUser) {
      if (activeView === 'dashboard' && !hasPermission(loggedInUser, 'view_overview')) {
        switchView('assistant');
      } else if (activeView === 'settings' && !hasPermission(loggedInUser, 'view_settings')) {
        switchView('assistant');
      }
    }
  }, [loggedInUser, activeView, switchView]);

  if (!authToken) {
    return (
      <>
        <div className="ambient-glow-container" style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none', zIndex: 0 }}>
          <div className="ambient-glow-1"></div>
          <div className="ambient-glow-2"></div>
        </div>
        <SharepointLogin onLoginSuccess={() => fetchSessions()} />
      </>
    );
  }

  return (
    <>
      <div className="ambient-glow-container" style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none', zIndex: 0 }}>
        <div className="ambient-glow-1"></div>
        <div className="ambient-glow-2"></div>
      </div>

      <div className={`app-layout ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        {!sidebarCollapsed && (
          <div className="sidebar-backdrop" onClick={toggleSidebar}></div>
        )}
        <Sidebar />

        <div className="main-content">
          <Header />

          {activeView === 'dashboard' && hasPermission(loggedInUser, 'view_overview') && <DashboardView />}
          {activeView === 'assistant' && <AssistantView />}
          {activeView === 'settings' && hasPermission(loggedInUser, 'view_settings') && <SettingsView />}
        </div>
      </div>
    </>
  );
}

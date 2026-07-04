import React, { useEffect } from 'react';
import { useAppStore } from './store/useAppStore';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import DashboardView from './components/DashboardView';
import AssistantView from './components/AssistantView';
import SettingsView from './components/SettingsView';
import SharepointLogin from './components/SharepointLogin';
import { useChatStore } from './store/useChatStore';

export default function App() {
  const activeView = useAppStore((state) => state.activeView);
  const theme = useAppStore((state) => state.theme);
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

  // Fetch previous chats when user is authenticated
  useEffect(() => {
    if (authToken) {
      fetchSessions();
    }
  }, [authToken, fetchSessions]);

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

      <div className="app-layout">
        <Sidebar />

        <div className="main-content">
          <Header />

          {activeView === 'dashboard' && <DashboardView />}
          {activeView === 'assistant' && <AssistantView />}
          {activeView === 'settings' && <SettingsView />}
        </div>
      </div>
    </>
  );
}

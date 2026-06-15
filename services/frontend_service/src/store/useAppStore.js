import { create } from 'zustand';

export const baseUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
  ? 'http://127.0.0.1:8081' 
  : window.location.origin.replace(':8082', ':8081');

export const useAppStore = create((set, get) => ({
  theme: localStorage.getItem('theme') || 'dark',
  activeView: 'dashboard',
  authToken: 'askhr_super_secret_token_2026',
  serverStatus: 'checking',
  serverStatusText: 'جاري الفحص...',
  consoleLogs: [
    {
      time: new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      type: 'info',
      message: 'تم بدء تهيئة لوحة التحكم...'
    },
    {
      time: new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      type: 'success',
      message: 'تم تفعيل ملف التنسيق المطور بنجاح.'
    }
  ],

  setAuthToken: (token) => {
    set({ authToken: token });
    get().addConsoleLog('تم تحديث مفتاح الوصول Authentication Token', 'info');
  },

  switchView: (viewName) => {
    set({ activeView: viewName });
    const viewLabels = {
      dashboard: 'لوحة الإحصائيات',
      assistant: 'المساعد الذكي',
      settings: 'إعدادات النظام'
    };
    get().addConsoleLog(`تم الانتقال بنجاح إلى واجهة: ${viewLabels[viewName] || viewName}`, 'info');
  },

  toggleTheme: () => {
    const nextTheme = get().theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('theme', nextTheme);
    set({ theme: nextTheme });
    get().addConsoleLog(`تم التحويل إلى المظهر ${nextTheme === 'dark' ? 'الداكن' : 'الفاتح'}.`, 'info');
  },

  addConsoleLog: (message, type = 'info') => {
    const time = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    set((state) => ({
      consoleLogs: [...state.consoleLogs, { time, type, message }]
    }));
  },

  clearConsoleLogs: () => {
    set({ consoleLogs: [] });
    get().addConsoleLog('تم مسح سجل الكونسول.', 'info');
  },

  checkServerHealth: async () => {
    try {
      const response = await fetch(`${baseUrl}/health`);
      if (response.ok) {
        set({
          serverStatus: 'healthy',
          serverStatusText: 'متصل'
        });
      } else {
        set({
          serverStatus: 'warning',
          serverStatusText: 'استجابة خاطئة'
        });
      }
    } catch (e) {
      set({
        serverStatus: 'offline',
        serverStatusText: 'غير متصل'
      });
    }
  }
}));

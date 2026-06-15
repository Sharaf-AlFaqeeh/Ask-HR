import { create } from 'zustand';
import { baseUrl, useAppStore } from './useAppStore';
import { useAgentStore } from './useAgentStore';
import { useMetricsStore } from './useMetricsStore';

export const useChatStore = create((set, get) => ({
  messages: [],
  sessionId: null,
  isWaitingResponse: false,
  isIngesting: false,

  startNewSession: () => {
    set({ sessionId: null, messages: [] });
    useMetricsStore.getState().resetActiveSessions();
    useAgentStore.getState().resetAgentState();
    useAppStore.getState().addConsoleLog('تم إنهاء الجلسة القديمة وبدء جلسة جديدة بنجاح.', 'success');
  },

  sendQuery: async (query) => {
    if (get().isWaitingResponse) return;

    const startTime = performance.now();
    const appStore = useAppStore.getState();
    const metricsStore = useMetricsStore.getState();
    const agentStore = useAgentStore.getState();

    // Add User Message
    const userTime = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    set((state) => ({
      messages: [...state.messages, { sender: 'user', text: query, time: userTime }]
    }));

    set({ isWaitingResponse: true });
    appStore.addConsoleLog(`إرسال طلب محادثة: "${query}" إلى خادم الأوركسترا...`, 'info');

    try {
      const payload = { query };
      if (get().sessionId) {
        payload.session_id = get().sessionId;
      }

      const response = await fetch(`${baseUrl}/api/v1/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${appStore.authToken}`
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        const errMsg = errData?.error?.message || errData?.detail || 'فشل الاتصال بالخادم الداخلي.';
        
        const botTime = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        set((state) => ({
          messages: [...state.messages, { sender: 'bot', text: `⚠️ خطأ: ${errMsg}`, time: botTime }]
        }));
        
        appStore.addConsoleLog(`خطأ معالجة الطلب: ${errMsg}`, 'error');
        set({ isWaitingResponse: false });
        return;
      }

      const result = await response.json();
      
      // Update session ID if returned
      if (result.session_id) {
        set({ sessionId: result.session_id });
        metricsStore.setActiveSessions(1);
      }

      const endTime = performance.now();
      const latency = Math.round(endTime - startTime);

      // Update metrics & charts
      metricsStore.updateMetrics(latency, result.sap_executed, result.intent);

      // Append bot message
      const botTime = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      set((state) => ({
        messages: [...state.messages, { sender: 'bot', text: result.response, responseData: result, time: botTime }]
      }));

      // Update state tracker panel
      agentStore.updateAgentState(result);

      appStore.addConsoleLog(`تم الاستلام. نية المستخدم: '${result.intent}' (الثقة: ${Math.round(result.confidence * 100)}%) خلال ${latency}ms`, 'success');

    } catch (err) {
      const botTime = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      set((state) => ({
        messages: [...state.messages, { sender: 'bot', text: `⚠️ فشل إرسال الطلب: تأكد من تشغيل الخادم على المنفذ الصحيح. (${err.message})`, time: botTime }]
      }));
      appStore.addConsoleLog(`خطأ شبكة: ${err.message}`, 'error');
    } finally {
      set({ isWaitingResponse: false });
    }
  },

  triggerIngest: async () => {
    const appStore = useAppStore.getState();
    set({ isIngesting: true });
    appStore.addConsoleLog('جاري إرسال طلب إعادة الفهرسة لمستندات السياسات...', 'info');

    try {
      const response = await fetch(`${baseUrl}/api/v1/admin/ingest`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${appStore.authToken}`
        }
      });

      const data = await response.json();
      if (response.ok && data.success) {
        appStore.addConsoleLog('نجاح: تم بناء متجهات Qdrant لسياسات الموارد البشرية وإعادة تحميل الكوليكشن.', 'success');
        alert('تمت إعادة الفهرسة بنجاح!');
      } else {
        const err = data?.error?.message || data?.detail || 'فشل بناء الفهرس.';
        appStore.addConsoleLog(`فشل تحديث الفهرس: ${err}`, 'error');
        alert(`خطأ: ${err}`);
      }
    } catch (e) {
      appStore.addConsoleLog(`خطأ اتصال: ${e.message}`, 'error');
      alert(`خطأ شبكة: ${e.message}`);
    } finally {
      set({ isIngesting: false });
    }
  },

  clearSessionById: async (targetSessionId) => {
    if (!targetSessionId) {
      alert('يرجى إدخال معرف الجلسة Session ID.');
      return;
    }

    const appStore = useAppStore.getState();
    appStore.addConsoleLog(`جاري إرسال طلب حذف الجلسة: ${targetSessionId}...`, 'info');

    try {
      const response = await fetch(`${baseUrl}/api/v1/admin/sessions/${targetSessionId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${appStore.authToken}`
        }
      });

      const data = await response.json();
      if (response.ok && data.success) {
        appStore.addConsoleLog(`نجاح: تم مسح الجلسة ${targetSessionId} بالكامل وتفريغ ذاكرتها.`, 'success');
        alert(`تم مسح الجلسة بنجاح.`);
        if (targetSessionId === get().sessionId) {
          get().startNewSession();
        }
      } else {
        const err = data?.error?.message || data?.detail || 'الجلسة غير موجودة.';
        appStore.addConsoleLog(`فشل مسح الجلسة: ${err}`, 'error');
        alert(`خطأ: ${err}`);
      }
    } catch (e) {
      appStore.addConsoleLog(`خطأ اتصال: ${e.message}`, 'error');
      alert(`خطأ شبكة: ${e.message}`);
    }
  }
}));

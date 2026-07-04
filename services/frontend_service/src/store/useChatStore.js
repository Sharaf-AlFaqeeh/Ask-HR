import { create } from 'zustand';
import { baseUrl, useAppStore } from './useAppStore';
import { useAgentStore } from './useAgentStore';
import { useMetricsStore } from './useMetricsStore';

export const useChatStore = create((set, get) => ({
  messages: [],
  sessions: [],
  sessionId: null,
  isWaitingResponse: false,
  isIngesting: false,
  activePendingAction: null, // Holds currently pending TRANSACTIONAL action template

  fetchSessions: async () => {
    const appStore = useAppStore.getState();
    if (!appStore.authToken) return;

    try {
      const response = await fetch(`${baseUrl}/api/v1/chats`, {
        headers: {
          'Authorization': `Bearer ${appStore.authToken}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        set({ sessions: data });
      }
    } catch (e) {
      console.error('Failed to fetch past chat sessions:', e);
    }
  },

  startNewSession: () => {
    set({ sessionId: null, messages: [], activePendingAction: null });
    useMetricsStore.getState().resetActiveSessions();
    useAgentStore.getState().resetAgentState();
    useAppStore.getState().addConsoleLog('تم بدء جلسة محادثة جديدة.', 'success');
  },

  loadSession: async (targetSessionId) => {
    const appStore = useAppStore.getState();
    if (!appStore.authToken) return;

    set({ isWaitingResponse: true });
    appStore.addConsoleLog(`جاري استرجاع سجل المحادثة للجلسة: ${targetSessionId}...`, 'info');

    try {
      const response = await fetch(`${baseUrl}/api/v1/chats/${targetSessionId}`, {
        headers: {
          'Authorization': `Bearer ${appStore.authToken}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        
        // Map backend history (role: 'user' | 'assistant') to frontend (sender: 'user' | 'bot')
        const mappedMessages = data.history.map(m => {
          const time = new Date(m.timestamp * 1000).toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
          return {
            sender: m.role === 'user' ? 'user' : 'bot',
            text: m.content,
            time: time,
            // If it's a success confirmation card, we can attach response data
            responseData: m.role === 'assistant' ? { intent: 'SAP', response: m.content } : null
          };
        });

        // Set active pending action if any
        let pendingAction = null;
        if (data.pending_action) {
          // Re-generate template or fetch it. To be safe, we can trigger the state
          // but usually it will be prompted on next query. For UI convenience,
          // we can store the basic details.
          pendingAction = data.pending_action;
        }

        set({
          sessionId: data.session_id,
          messages: mappedMessages,
          activePendingAction: null // Clear on load, will re-trigger if they query again
        });

        useMetricsStore.getState().setActiveSessions(1);
        appStore.addConsoleLog(`تم استرجاع سجل الجلسة ${targetSessionId} بنجاح.`, 'success');
      } else {
        appStore.addConsoleLog(`فشل استرجاع الجلسة ${targetSessionId}.`, 'error');
      }
    } catch (e) {
      appStore.addConsoleLog(`خطأ اتصال أثناء استرجاع الجلسة: ${e.message}`, 'error');
    } finally {
      set({ isWaitingResponse: false });
    }
  },

  sendQuery: async (query) => {
    if (get().isWaitingResponse) return;

    const startTime = performance.now();
    const appStore = useAppStore.getState();
    const metricsStore = useMetricsStore.getState();
    const agentStore = useAgentStore.getState();

    // Add User Message
    const userTime = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
    set((state) => ({
      messages: [...state.messages, { sender: 'user', text: query, time: userTime }],
      activePendingAction: null // Clear any pending action since user wrote a new query
    }));

    set({ isWaitingResponse: true });
    appStore.addConsoleLog(`إرسال طلب محادثة: "${query}"...`, 'info');

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
        
        const botTime = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
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
      const botTime = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
      
      // Check if response contains action payload (UI widget for confirmation/loading)
      let pendingAction = null;
      if (result.action_payload) {
        pendingAction = result.action_payload;
        appStore.addConsoleLog(`تم تلقي قالب واجهة إجراء تفاعلي: ${result.action_payload.action_id} (${result.action_payload.action_type})`, 'info');
      }

      set((state) => ({
        messages: [...state.messages, { sender: 'bot', text: result.response, responseData: result, time: botTime, actionWidget: pendingAction }],
        activePendingAction: pendingAction
      }));

      // Update state tracker panel
      agentStore.updateAgentState(result);

      appStore.addConsoleLog(`تم الاستلام بنجاح. نية المستخدم: '${result.intent}' خلال ${latency}ms`, 'success');
      
      // Refresh sidebar list
      get().fetchSessions();

    } catch (err) {
      const botTime = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
      set((state) => ({
        messages: [...state.messages, { sender: 'bot', text: `⚠️ فشل إرسال الطلب: تأكد من تشغيل الخادم. (${err.message})`, time: botTime }]
      }));
      appStore.addConsoleLog(`خطأ شبكة: ${err.message}`, 'error');
    } finally {
      set({ isWaitingResponse: false });
    }
  },

  executePendingAction: async (actionId) => {
    const appStore = useAppStore.getState();
    const sessionId = get().sessionId;
    if (!sessionId || !appStore.authToken) return;

    set({ isWaitingResponse: true, activePendingAction: null });
    appStore.addConsoleLog(`جاري إرسال تأكيد تنفيذ الإجراء ${actionId} لـ SAP SuccessFactors...`, 'info');

    try {
      const response = await fetch(`${baseUrl}/api/v1/chats/execute-action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${appStore.authToken}`
        },
        body: JSON.stringify({
          session_id: sessionId,
          action_id: actionId
        })
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        const errMsg = errData?.detail || 'فشل تنفيذ الإجراء في نظام SAP.';
        alert(`خطأ: ${errMsg}`);
        appStore.addConsoleLog(`فشل تنفيذ الإجراء: ${errMsg}`, 'error');
        set({ isWaitingResponse: false });
        return;
      }

      const result = await response.json();
      
      // Append bot success message
      const botTime = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
      set((state) => ({
        messages: [...state.messages, { sender: 'bot', text: result.response, time: botTime }]
      }));

      // Update metrics store to count successful SAP execution
      useMetricsStore.getState().updateMetrics(100, true, 'SAP');
      appStore.addConsoleLog(`تم تنفيذ الإجراء بنجاح في SAP SF.`, 'success');
      
      // Refresh sidebar list
      get().fetchSessions();

    } catch (e) {
      appStore.addConsoleLog(`خطأ اتصال أثناء تأكيد الإجراء: ${e.message}`, 'error');
      alert(`خطأ اتصال: ${e.message}`);
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
      const response = await fetch(`${baseUrl}/api/v1/chats/${targetSessionId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${appStore.authToken}`
        }
      });

      const data = await response.json();
      if (response.ok && data.success) {
        appStore.addConsoleLog(`نجاح: تم مسح الجلسة ${targetSessionId} بالكامل وتفريغ ذاكرتها.`, 'success');
        
        // Remove from local list
        set((state) => ({
          sessions: state.sessions.filter(s => s.session_id !== targetSessionId)
        }));

        if (targetSessionId === get().sessionId) {
          get().startNewSession();
        }
      } else {
        const err = data?.detail || 'الجلسة غير موجودة.';
        appStore.addConsoleLog(`فشل مسح الجلسة: ${err}`, 'error');
        alert(`خطأ: ${err}`);
      }
    } catch (e) {
      appStore.addConsoleLog(`خطأ اتصال: ${e.message}`, 'error');
      alert(`خطأ شبكة: ${e.message}`);
    }
  }
}));

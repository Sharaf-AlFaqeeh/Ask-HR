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
  activeLeaveForm: null, // Holds currently active leave request form data
  abortController: null,

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

    // Add User Message and an initial Bot Message immediately with default thinking state
    const userTime = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
    const botTime = userTime;
    set((state) => ({
      messages: [
        ...state.messages,
        { sender: 'user', text: query, time: userTime },
        { 
          sender: 'bot', 
          text: '', 
          rawTextBuffer: '', 
          rawTextTarget: '', 
          isStreamClosed: false,
          citations: [],
          time: botTime 
        }
      ],
      activePendingAction: null, // Clear any pending action since user wrote a new query
      activeLeaveForm: null // Clear any active leave form
    }));

    const controller = new AbortController();
    set({ isWaitingResponse: true, abortController: controller });
    appStore.addConsoleLog(`إرسال طلب محادثة بث (Streaming): "${query}"...`, 'info');

    const botMessageIndex = get().messages.length - 1;

    try {
      const payload = { query };
      if (get().sessionId) {
        payload.session_id = get().sessionId;
      }

      const response = await fetch(`${baseUrl}/api/v1/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${appStore.authToken}`
        },
        body: JSON.stringify(payload),
        signal: controller.signal
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        const errMsg = errData?.error?.message || errData?.detail || 'فشل الاتصال بالخادم الداخلي.';
        
        set((state) => {
          const nextMessages = [...state.messages];
          nextMessages[botMessageIndex] = {
            sender: 'bot',
            text: `⚠️ خطأ: ${errMsg}`,
            rawTextTarget: `⚠️ خطأ: ${errMsg}`,
            isStreamClosed: true,
            time: botTime
          };
          return { messages: nextMessages };
        });
        
        appStore.addConsoleLog(`خطأ معالجة الطلب: ${errMsg}`, 'error');
        set({ isWaitingResponse: false });
        return;
      }

      // Initialize reader for text/event-stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      // Hide loading spinner as stream starts arriving
      set({ isWaitingResponse: false });

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Split buffer by SSE event boundaries (\n\n)
        const parts = buffer.split('\n\n');
        // Keep the last partial event in the buffer
        buffer = parts.pop();

        for (const part of parts) {
          const trimmedPart = part.trim();
          if (!trimmedPart || !trimmedPart.startsWith('data: ')) continue;

          const dataStr = trimmedPart.substring(5).trim();
          if (!dataStr) continue;

          try {
            const data = JSON.parse(dataStr);
            if (data.error) {
              set((state) => {
                const nextMessages = [...state.messages];
                nextMessages[botMessageIndex].text = `⚠️ خطأ: ${data.error.message}`;
                nextMessages[botMessageIndex].rawTextTarget = `⚠️ خطأ: ${data.error.message}`;
                nextMessages[botMessageIndex].isStreamClosed = true;
                return { messages: nextMessages };
              });
              appStore.addConsoleLog(`خطأ في البث: ${data.error.message}`, 'error');
              break;
            }

            if (data.is_thinking) {
              set((state) => {
                const nextMessages = [...state.messages];
                const currentMsg = nextMessages[botMessageIndex];
                if (currentMsg) {
                  currentMsg.citations = data.execution_details?.citations || [];
                }
                return { messages: nextMessages };
              });
              appStore.addConsoleLog(`بدء تفكير الوكيل وقراءة لوائح الموارد البشرية...`, 'info');
              continue;
            }

            if (data.response !== undefined) {
              set((state) => {
                const nextMessages = [...state.messages];
                const currentMsg = nextMessages[botMessageIndex];

                if (currentMsg) {
                  if (data.is_chunk) {
                    // Append chunks to rawTextBuffer
                    currentMsg.rawTextBuffer = (currentMsg.rawTextBuffer || '') + data.response;
                    currentMsg.text = currentMsg.rawTextBuffer;
                  } else {
                    // Final non-chunk message: override with full text, attach metadata
                    currentMsg.text = data.response;
                    currentMsg.rawTextTarget = data.response;
                    currentMsg.isStreamClosed = true;
                    currentMsg.responseData = data;

                    let pendingAction = null;
                    if (data.action_payload) {
                      pendingAction = data.action_payload;
                      currentMsg.actionWidget = pendingAction;
                      if (pendingAction.action_type === 'TRANSACTIONAL') {
                        set({ activePendingAction: pendingAction });
                      }
                      appStore.addConsoleLog(`تم تلقي قالب واجهة تفاعلي: ${pendingAction.action_id}`, 'info');
                    }

                    // Handle leave form payload
                    if (data.leave_form) {
                      currentMsg.leaveForm = data.leave_form;
                      set({ activeLeaveForm: data.leave_form });
                      appStore.addConsoleLog(`تم تلقي نموذج طلب إجازة مع تواريخ مستنتجة`, 'info');
                    }

                    // Update session ID
                    if (data.session_id) {
                      set({ sessionId: data.session_id });
                      metricsStore.setActiveSessions(1);
                    }

                    // Update metrics
                    const endTime = performance.now();
                    const latency = Math.round(endTime - startTime);
                    metricsStore.updateMetrics(latency, data.sap_executed, data.intent);
                    agentStore.updateAgentState(data);

                    appStore.addConsoleLog(`تم اكتمال استقبال البث بنجاح. نية المستخدم: '${data.intent}' خلال ${latency}ms`, 'success');
                  }
                }

                return { messages: nextMessages };
              });
            }
          } catch (jsonErr) {
            console.error('Error parsing SSE data chunk:', jsonErr, dataStr);
          }
        }
      }

      // Refresh sidebar sessions list
      get().fetchSessions();

    } catch (err) {
      const isAbort = err.name === 'AbortError';
      if (isAbort) {
        set((state) => {
          const nextMessages = [...state.messages];
          if (botMessageIndex >= 0 && nextMessages[botMessageIndex]) {
            nextMessages[botMessageIndex].isStreamClosed = true;
            nextMessages[botMessageIndex].rawTextTarget = nextMessages[botMessageIndex].rawTextBuffer || 'تم إيقاف الاستجابة من قِبل المستخدم.';
          }
          return { messages: nextMessages };
        });
        appStore.addConsoleLog('تم إيقاف استجابة البث من قِبل المستخدم.', 'info');
      } else {
        const botTime = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
        set((state) => {
          const nextMessages = [...state.messages];
          if (botMessageIndex >= 0 && nextMessages[botMessageIndex]) {
            nextMessages[botMessageIndex].text = `⚠️ فشل إرسال الطلب: تأكد من تشغيل الخادم. (${err.message})`;
            nextMessages[botMessageIndex].rawTextTarget = `⚠️ فشل إرسال الطلب: تأكد من تشغيل الخادم. (${err.message})`;
            nextMessages[botMessageIndex].isStreamClosed = true;
          } else {
            nextMessages.push({ sender: 'bot', text: `⚠️ فشل إرسال الطلب: تأكد من تشغيل الخادم. (${err.message})`, rawTextTarget: `⚠️ فشل إرسال الطلب: تأكد من تشغيل الخادم. (${err.message})`, isStreamClosed: true, time: botTime });
          }
          return { messages: nextMessages };
        });
        appStore.addConsoleLog(`خطأ اتصال: ${err.message}`, 'error');
      }
    } finally {
      set({ isWaitingResponse: false, abortController: null });
    }
  },

  stopResponse: () => {
    const { abortController } = get();
    if (abortController) {
      abortController.abort();
      set({ abortController: null, isWaitingResponse: false });
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

  submitLeaveForm: async (formData) => {
    const appStore = useAppStore.getState();
    const sessionId = get().sessionId;
    if (!sessionId || !appStore.authToken) return;

    set({ isWaitingResponse: true, activeLeaveForm: null });
    appStore.addConsoleLog(`جاري إرسال نموذج طلب الإجازة...`, 'info');

    try {
      const response = await fetch(`${baseUrl}/api/v1/chats/submit-leave-form`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${appStore.authToken}`
        },
        body: JSON.stringify({
          session_id: sessionId,
          leave_type: formData.leave_type,
          start_date: formData.start_date,
          end_date: formData.end_date
        })
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        const errMsg = errData?.detail || 'فشل إرسال نموذج طلب الإجازة.';
        alert(`خطأ: ${errMsg}`);
        appStore.addConsoleLog(`فشل إرسال نموذج الإجازة: ${errMsg}`, 'error');
        set({ isWaitingResponse: false });
        return;
      }

      const result = await response.json();
      
      // Append bot confirmation message with action widget
      const botTime = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
      const actionPayload = result.action_payload || null;
      
      set((state) => ({
        messages: [...state.messages, { 
          sender: 'bot', 
          text: result.response, 
          time: botTime,
          actionWidget: actionPayload
        }],
        activePendingAction: actionPayload
      }));

      appStore.addConsoleLog(`تم تقديم نموذج الإجازة بنجاح — بانتظار التأكيد.`, 'success');
      
    } catch (e) {
      appStore.addConsoleLog(`خطأ اتصال أثناء إرسال نموذج الإجازة: ${e.message}`, 'error');
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

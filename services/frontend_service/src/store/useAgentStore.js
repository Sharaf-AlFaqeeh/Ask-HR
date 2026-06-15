import { create } from 'zustand';

const initialSessionState = {
  sessionId: 'لا توجد جلسة نشطة',
  intent: 'غير محدد',
  confidence: '-',
  tenant: 'HSAGroup'
};

const initialSlots = {
  employee_id: null,
  leave_type: null,
  start_date: null,
  end_date: null
};

const initialOperations = {
  rag_completed: false,
  sap_completed: false
};

export const useAgentStore = create((set) => ({
  sessionState: { ...initialSessionState },
  slots: { ...initialSlots },
  operations: { ...initialOperations },

  resetAgentState: () => {
    set({
      sessionState: { ...initialSessionState },
      slots: { ...initialSlots },
      operations: { ...initialOperations }
    });
  },

  updateAgentState: (result) => {
    set({
      sessionState: {
        sessionId: result.session_id || 'لا توجد جلسة نشطة',
        intent: result.intent || 'غير محدد',
        confidence: result.confidence ? `${Math.round(result.confidence * 100)}%` : '-',
        tenant: 'HSAGroup'
      },
      slots: {
        employee_id: result.entities?.employee_id || null,
        leave_type: result.entities?.leave_type || null,
        start_date: result.entities?.start_date || null,
        end_date: result.entities?.end_date || null
      },
      operations: {
        rag_completed: !!result.context_used,
        sap_completed: !!result.sap_executed
      }
    });
  }
}));

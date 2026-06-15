import { create } from 'zustand';

const initialRecentActivities = [
  { user: 'خالد', activity: 'طلب إجازة سنوية عبر بوابة SAP SuccessFactors', time: '08:52 ص', latency: '0.45s', status: 'ONLINE' },
  { user: 'م. طه', activity: 'استعلم عن "بدل السكن وتذاكر السفر للمستشارين" (Qdrant RAG)', time: '08:48 ص', latency: '0.22s', status: 'ONLINE' },
  { user: 'أحمد', activity: 'استعلم عن "شروط الترقية الاستثنائية لشركات المجموعة"', time: '08:41 ص', latency: '0.18s', status: 'ONLINE' }
];

export const useMetricsStore = create((set, get) => ({
  totalQueries: 24892,
  activeSessionsCount: 1,
  avgLatency: 34,
  latencySum: 340,
  queryCount: 10,
  chartLabels: [],
  chartData: [],
  recentActivities: [...initialRecentActivities],

  initChartData: () => {
    // Generate initial time metrics
    const labels = [];
    const data = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setSeconds(d.getSeconds() - i * 30);
      labels.push(d.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
      data.push(Math.floor(Math.random() * 15) + 20); // base simulated latency
    }
    set({ chartLabels: labels, chartData: data });
  },

  setActiveSessions: (count) => {
    set({ activeSessionsCount: count });
  },

  resetActiveSessions: () => {
    set({ activeSessionsCount: 0 });
  },

  updateMetrics: (latencyVal, sapExecuted, intent) => {
    const { totalQueries, queryCount, latencySum, chartLabels, chartData, recentActivities } = get();
    
    // Add point to chart data
    const now = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const newLabels = [...chartLabels, now];
    const newData = [...chartData, latencyVal];

    if (newLabels.length > 8) {
      newLabels.shift();
      newData.shift();
    }

    const newQueryCount = queryCount + 1;
    const newLatencySum = latencySum + latencyVal;
    const newAvg = Math.round(newLatencySum / newQueryCount);

    // Add activity row
    const time = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
    const latencySec = `${(latencyVal / 1000).toFixed(2)}s`;
    
    const newActivity = {
      user: 'موظف HSA',
      activity: `أجرى استعلاماً بنوع النية '${intent || 'غير محدد'}'`,
      time,
      latency: latencySec,
      status: 'ONLINE'
    };

    const newActivities = [newActivity, ...recentActivities];
    if (newActivities.length > 5) {
      newActivities.pop();
    }

    set({
      totalQueries: totalQueries + 1,
      queryCount: newQueryCount,
      latencySum: newLatencySum,
      avgLatency: newAvg,
      chartLabels: newLabels,
      chartData: newData,
      recentActivities: newActivities
    });
  }
}));

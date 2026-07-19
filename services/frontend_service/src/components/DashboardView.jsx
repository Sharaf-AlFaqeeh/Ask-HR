import React, { useEffect, useRef } from 'react';
import Chart from 'chart.js/auto';
import { useAppStore } from '../store/useAppStore';
import { useChatStore } from '../store/useChatStore';
import { useMetricsStore } from '../store/useMetricsStore';
import { useAgentStore } from '../store/useAgentStore';
import { hasPermission } from '../utils/permissions';

export default function DashboardView() {
  const chartRef = useRef(null);
  const chartInstanceRef = useRef(null);

  const { theme, serverStatus, loggedInUser } = useAppStore();
  const triggerIngest = useChatStore((state) => state.triggerIngest);
  const startNewSession = useChatStore((state) => state.startNewSession);

  // Metrics state
  const { totalQueries, activeSessionsCount, avgLatency, chartLabels, chartData, recentActivities, initChartData } = useMetricsStore();

  // Agent State Tracker state
  const { sessionState, slots, operations } = useAgentStore();

  useEffect(() => {
    // Initialize chart data if empty
    if (chartLabels.length === 0) {
      initChartData();
    }
  }, [chartLabels, initChartData]);

  // Chart Rendering
  useEffect(() => {
    if (!chartRef.current || chartLabels.length === 0) return;
    const ctx = chartRef.current.getContext('2d');

    if (chartInstanceRef.current) {
      chartInstanceRef.current.destroy();
    }

    const isLight = theme === 'light';
    const textColor = isLight ? '#475569' : '#a3b1c6';
    const gridColor = isLight ? 'rgba(0, 0, 0, 0.05)' : 'rgba(255, 255, 255, 0.03)';

    chartInstanceRef.current = new Chart(ctx, {
      type: 'line',
      data: {
        labels: chartLabels,
        datasets: [{
          label: 'زمن المعالجة (ملي ثانية)',
          data: chartData,
          borderColor: '#d4af37',
          backgroundColor: 'rgba(212, 175, 55, 0.08)',
          fill: true,
          tension: 0.4,
          borderWidth: 2,
          pointBackgroundColor: '#d4af37',
          pointBorderColor: '#fff',
          pointRadius: 4,
          pointHoverRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          y: {
            grid: { color: gridColor },
            ticks: { color: textColor, font: { family: 'Outfit', size: 10 } }
          },
          x: {
            grid: { display: false },
            ticks: { color: textColor, font: { family: 'Outfit', size: 9 } }
          }
        }
      }
    });

    return () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.destroy();
      }
    };
  }, [chartLabels, chartData, theme]);

  // Helper values for server health card
  const isHealthy = serverStatus === 'healthy';
  const isOffline = serverStatus === 'offline';
  const isWarning = serverStatus === 'warning';

  let statusBadgeText = 'STABLE';
  let statusBadgeClass = 'trend-stable trend-up';
  let uptimeStatusText = 'Healthy';

  if (isOffline) {
    statusBadgeText = 'DOWN';
    statusBadgeClass = 'trend-stable trend-danger';
    uptimeStatusText = 'Offline';
  } else if (isWarning) {
    statusBadgeText = 'ERROR';
    statusBadgeClass = 'trend-stable trend-danger';
    uptimeStatusText = 'Warning';
  }

  return (
    <div id="view-dashboard" className="view-panel active">
      <div className="page-section-header">
        <div>
          <h2 className="page-title">مراقبة النظام والأداء العام</h2>
          <span className="page-subtitle">أداء محرك أوركسترا الذكاء الاصطناعي ومعدلات طلبات الموظفين الفورية.</span>
        </div>
        <div className="page-actions">
          {hasPermission(loggedInUser, 'update_index') && (
            <button className="btn-card" onClick={triggerIngest}>
              <i className="fa-solid fa-arrows-rotate"></i>
              <span>تحديث الفهرس</span>
            </button>
          )}
          {hasPermission(loggedInUser, 'delete_session') && (
            <button className="btn-card" onClick={startNewSession}>
              <i className="fa-solid fa-trash-can"></i>
              <span>تصفير الجلسات</span>
            </button>
          )}
        </div>
      </div>

      {/* Bento Metrics Grid */}
      <div className="bento-grid-3">
        {/* Card 1: Active Users */}
        <div className="dashboard-card">
          <div className="card-top">
            <div className="card-icon-wrapper">
              <i className="fa-solid fa-users"></i>
            </div>
            <div className="card-trend trend-up">
              <i className="fa-solid fa-arrow-trend-up"></i>
              <span>+12.5%</span>
            </div>
          </div>
          <div>
            <div className="card-value" id="metrics-sessions">{activeSessionsCount}</div>
            <div className="card-label">الجلسات النشطة</div>
          </div>
          <div className="mini-chart">
            <div className="mini-bar" style={{ height: '40%' }}></div>
            <div className="mini-bar" style={{ height: '55%' }}></div>
            <div className="mini-bar" style={{ height: '45%' }}></div>
            <div className="mini-bar" style={{ height: '60%' }}></div>
            <div className="mini-bar" style={{ height: '75%' }}></div>
            <div className="mini-bar active" style={{ height: '90%' }}></div>
          </div>
        </div>

        {/* Card 2: Total API Queries */}
        <div className="dashboard-card">
          <div className="card-top teal-theme">
            <div className="card-icon-wrapper">
              <i className="fa-solid fa-terminal"></i>
            </div>
            <div className="card-trend trend-up" style={{ color: '#2dd4bf' }}>
              <i className="fa-solid fa-arrow-trend-up"></i>
              <span>+8.2%</span>
            </div>
          </div>
          <div>
            <div className="card-value" id="metrics-queries">{totalQueries.toLocaleString()}</div>
            <div className="card-label">إجمالي الطلبات (API Queries)</div>
          </div>
          <div>
            <div className="progress-bar-wrapper">
              <div className="progress-bar-fill" style={{ width: `${Math.min((totalQueries / 30000) * 100, 100)}%` }}></div>
            </div>
            <div className="progress-goal-text">
              <span>الهدف: 30,000</span>
              <span>{((totalQueries / 30000) * 100).toFixed(1)}%</span>
            </div>
          </div>
        </div>

        {/* Card 3: Uptime & Health */}
        <div className="dashboard-card">
          <div className="card-top green-theme">
            <div className="card-icon-wrapper">
              <i className="fa-solid fa-heart-pulse"></i>
            </div>
            <div id="metrics-status-badge" className={statusBadgeClass}>{statusBadgeText}</div>
          </div>
          <div className="uptime-ring-container">
            <div className="uptime-ring">
              <svg width="50" height="50">
                <circle className="bg" cx="25" cy="25" r="21" />
                <circle className="bar" cx="25" cy="25" r="21" strokeDasharray="132" strokeDashoffset={isOffline ? 132 : 0.13} />
              </svg>
              <span className="uptime-value">{isOffline ? '0%' : '99.9%'}</span>
            </div>
            <div>
              <div className="card-value" id="metrics-status">{uptimeStatusText}</div>
              <div className="card-label">حالة اتصال الخادم</div>
            </div>
          </div>
          <div className="card-subtext">
            <span>زمن الاستجابة: </span>
            <strong id="metrics-latency-val" style={{ color: '#fff', fontFamily: 'var(--font-numeric)' }}>{avgLatency}ms</strong>
            <span style={{ margin: '0 0.5rem' }}>|</span>
            <span>الضغط: </span>
            <strong style={{ color: '#fff', fontFamily: 'var(--font-numeric)' }}>{isOffline ? '0%' : '12%'}</strong>
          </div>
        </div>
      </div>

      {/* Charts & Distributions Grid */}
      <div className="bento-grid-split">
        {/* Left: Real-time Line Graph */}
        <div className="split-card">
          <div className="split-card-header">
            <div>
              <h3 className="split-card-title">حجم حركة مرور البيانات (Traffic Volume)</h3>
              <span className="split-card-subtitle">مراقبة فورية لمعدلات زمن معالجة الطلبات بالملي ثانية.</span>
            </div>
            <div className="swapper-pills">
              <button className="swapper-pill active">يومي</button>
              <button className="swapper-pill">أسبوعي</button>
            </div>
          </div>
          <div className="chart-container-wrapper">
            <canvas ref={chartRef} id="latencyChart"></canvas>
          </div>
        </div>

        {/* Right: Intent Distributions Progress bars */}
        <div className="split-card">
          <div className="split-card-header">
            <div>
              <h3 className="split-card-title">توزيع قصد المستخدمين (Intents)</h3>
              <span className="split-card-subtitle">النسبة المئوية لنوايا الطلبات الواردة للمحرك.</span>
            </div>
          </div>
          <div className="progress-rows">
            {/* RAG Queries */}
            <div className="progress-row-item">
              <div className="progress-row-header">
                <span className="progress-row-label">استعلامات السياسات (RAG)</span>
                <span className="progress-row-val">55%</span>
              </div>
              <div className="progress-row-bar-bg">
                <div className="progress-row-bar-fill purple" style={{ width: '55%' }}></div>
              </div>
            </div>
            {/* SAP Actions */}
            <div className="progress-row-item">
              <div className="progress-row-header">
                <span className="progress-row-label">إجراءات الموارد البشرية (SAP)</span>
                <span className="progress-row-val">30%</span>
              </div>
              <div className="progress-row-bar-bg">
                <div className="progress-row-bar-fill teal" style={{ width: '30%' }}></div>
              </div>
            </div>
            {/* General Chats */}
            <div className="progress-row-item">
              <div className="progress-row-header">
                <span className="progress-row-label">محادثات عامة ترحيبية</span>
                <span className="progress-row-val">10%</span>
              </div>
              <div className="progress-row-bar-bg">
                <div className="progress-row-bar-fill blue" style={{ width: '10%' }}></div>
              </div>
            </div>
            {/* Errors / Unrecognized */}
            <div className="progress-row-item">
              <div className="progress-row-header">
                <span className="progress-row-label">طلبات غير مفهومة / أخطاء</span>
                <span className="progress-row-val">5%</span>
              </div>
              <div className="progress-row-bar-bg">
                <div className="progress-row-bar-fill grey" style={{ width: '5%' }}></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity list */}
      <div className="activity-card">
        <div className="split-card-header">
          <div>
            <h3 className="split-card-title">آخر العمليات والتفاعلات الجارية</h3>
            <span className="split-card-subtitle">تفاصيل استدعاءات الموظفين المباشرة لخدمة الاسترجاع RAG ونظام SAP.</span>
          </div>
        </div>
        <div className="activity-table-wrapper">
          <table className="activity-table">
            <thead>
              <tr>
                <th>المستخدم</th>
                <th>العملية / الاستعلام</th>
                <th>الوقت</th>
                <th>سرعة المعالجة</th>
                <th>الحالة</th>
              </tr>
            </thead>
            <tbody id="activity-table-body">
              {recentActivities.map((act, idx) => (
                <tr key={idx}>
                  <td className="user-profile-cell">
                    <div className="user-cell-avatar">HSA</div>
                    <div className="user-cell-name">{act.user}</div>
                  </td>
                  <td>{act.activity}</td>
                  <td style={{ fontFamily: 'var(--font-numeric)' }}>{act.time}</td>
                  <td style={{ fontFamily: 'var(--font-numeric)' }}>{act.latency}</td>
                  <td>
                    <span className={`activity-badge ${act.status.toLowerCase() === 'online' ? 'online' : 'completed'}`}>
                      {act.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* State Tracker & Slot Filling Section */}
      <div className="bento-grid-split" style={{ marginTop: '1.5rem' }}>
        {/* State Tracker Card */}
        <div className="split-card">
          <div className="split-card-header">
            <div>
              <h3 className="split-card-title">
                <i className="fa-solid fa-microchip" style={{ marginLeft: '0.5rem', color: '#a5b4fc' }}></i>
                مراقب الحالة (State Tracker)
              </h3>
              <span className="split-card-subtitle">حالة الجلسة الحالية ونتائج تحليل النية والكيانات المستخرجة.</span>
            </div>
          </div>
          <div className="state-tracker-grid">
            <div className="state-row">
              <span className="state-label">Session ID</span>
              <span className={`state-value ${sessionState.sessionId === 'لا توجد جلسة نشطة' ? 'empty' : ''}`} id="state-session-id">
                {sessionState.sessionId}
              </span>
            </div>
            <div className="state-row">
              <span className="state-label">قصد المستخدم (Intent)</span>
              <span className={`state-value ${sessionState.intent === 'غير محدد' ? 'empty' : 'badge-intent'}`} id="state-intent">
                {sessionState.intent}
              </span>
            </div>
            <div className="state-row">
              <span className="state-label">نسبة الثقة (Confidence)</span>
              <span className={`state-value ${sessionState.confidence === '-' ? 'empty' : ''}`} id="state-confidence">
                {sessionState.confidence}
              </span>
            </div>
            <div className="state-row">
              <span className="state-label">المستأجر (Tenant ID)</span>
              <span className="state-value" id="state-tenant">{sessionState.tenant}</span>
            </div>
          </div>
          <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
            <h4 style={{ fontSize: '0.85rem', color: '#a5b4fc', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <i className="fa-solid fa-database" style={{ fontSize: '0.75rem' }}></i>
              العمليات الحالية
            </h4>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <span 
                id="op-rag" 
                className={`badge ${operations.rag_completed ? 'badge-completed' : 'badge-none'}`}
                style={{ flex: 1, textAlign: 'center', fontSize: '0.7rem', padding: '0.35rem' }}
              >
                RAG Retriever
              </span>
              <span 
                id="op-sap" 
                className={`badge ${operations.sap_completed ? 'badge-completed' : 'badge-none'}`}
                style={{ flex: 1, textAlign: 'center', fontSize: '0.7rem', padding: '0.35rem' }}
              >
                SAP SF Gateway
              </span>
            </div>
          </div>
        </div>

        {/* Slot Filling Card */}
        <div className="split-card">
          <div className="split-card-header">
            <div>
              <h3 className="split-card-title">
                <i className="fa-solid fa-list-check" style={{ marginLeft: '0.5rem', color: '#a5b4fc' }}></i>
                تعبئة البيانات (Slot Filling)
              </h3>
              <span className="split-card-subtitle">حالة تعبئة حقول البيانات المطلوبة لتنفيذ إجراءات SAP.</span>
            </div>
          </div>
          <div className="slot-filling-grid">
            <div className="slot-row">
              <div className="slot-info">
                <i className="fa-solid fa-id-badge slot-icon"></i>
                <span className="state-label">الرقم الوظيفي (Employee ID)</span>
              </div>
              <span id="slot-employee-id" className={`badge ${slots.employee_id ? 'badge-completed' : 'badge-none'}`}>
                {slots.employee_id || 'مفقود'}
              </span>
            </div>
            <div className="slot-row">
              <div className="slot-info">
                <i className="fa-solid fa-umbrella-beach slot-icon"></i>
                <span className="state-label">نوع الإجازة (Leave Type)</span>
              </div>
              <span id="slot-leave-type" className={`badge ${slots.leave_type ? 'badge-completed' : 'badge-none'}`}>
                {slots.leave_type || 'مفقود'}
              </span>
            </div>
            <div className="slot-row">
              <div className="slot-info">
                <i className="fa-solid fa-calendar-day slot-icon"></i>
                <span className="state-label">تاريخ البدء (Start Date)</span>
              </div>
              <span id="slot-start-date" className={`badge ${slots.start_date ? 'badge-completed' : 'badge-none'}`}>
                {slots.start_date || 'مفقود'}
              </span>
            </div>
            <div className="slot-row">
              <div className="slot-info">
                <i className="fa-solid fa-calendar-check slot-icon"></i>
                <span className="state-label">تاريخ الانتهاء (End Date)</span>
              </div>
              <span id="slot-end-date" className={`badge ${slots.end_date ? 'badge-completed' : 'badge-none'}`}>
                {slots.end_date || 'مفقود'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

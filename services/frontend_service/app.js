// AskHR Enterprise AI Orchestration Suite - Frontend Engine (app.js)

const baseUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? 'http://127.0.0.1:8081' 
    : window.location.origin.replace(':8082', ':8081');

let currentSessionId = null;
let isWaitingResponse = false;
let totalQueries = 24892; // Seeded value from design image
let activeSessionsCount = 1;
let latencyChart = null;
let totalLatencySum = 34 * 10; // Seeded average latency
let queryCount = 10;

// Chart history arrays
let chartLabels = [];
let chartData = [];

// Event Listeners
window.addEventListener('load', () => {
    checkServerHealth();
    initChart();
    loadSavedTheme();
    addConsoleLog('تم تشغيل لوحة التحكم ومكتبة الرسوم البيانية بنجاح.', 'success');
    addConsoleLog('نظام أوركسترا AskHR نشط وجاهز لاستقبال الاتصالات.', 'info');
    
    // Check health every 15 seconds
    setInterval(checkServerHealth, 15000);
});

// Switch view tabs in Sidebar
function switchView(viewName) {
    // Hide all views
    document.querySelectorAll('.view-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    
    // Deactivate all nav links
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });

    // Show selected view and activate sidebar item
    const targetPanel = document.getElementById(`view-${viewName}`);
    const targetLink = document.getElementById(`nav-${viewName}`);
    
    if (targetPanel && targetLink) {
        targetPanel.classList.add('active');
        targetLink.classList.add('active');
        addConsoleLog(`تم الانتقال بنجاح إلى واجهة: ${targetLink.innerText.trim()}`, 'info');
    }
    
    // Switch header tabs highlighting if viewing dashboard/assistant
    const headerTabs = document.querySelectorAll('.header-tab');
    headerTabs.forEach(tab => {
        tab.classList.remove('active');
    });
    
    if (viewName === 'dashboard') {
        const tab = document.getElementById('header-tab-overview');
        if (tab) tab.classList.add('active');
        // Force chart refresh to prevent size issues on hidden layouts
        setTimeout(() => { if (latencyChart) latencyChart.resize(); }, 50);
    } else if (viewName === 'assistant') {
        const tab = document.getElementById('header-tab-assistant');
        if (tab) tab.classList.add('active');
    }
}

// Check api health status
async function checkServerHealth() {
    try {
        const response = await fetch(`${baseUrl}/health`);
        const dot = document.getElementById('server-status-dot');
        const text = document.getElementById('server-status-text');
        
        if (response.ok) {
            dot.className = 'status-dot';
            text.innerText = 'متصل';
            document.getElementById('metrics-status').innerText = 'Healthy';
            document.getElementById('metrics-status-badge').innerText = 'STABLE';
            document.getElementById('metrics-status-badge').className = 'trend-stable trend-up';
        } else {
            dot.className = 'status-dot offline';
            text.innerText = 'استجابة خاطئة';
            document.getElementById('metrics-status').innerText = 'Warning';
            document.getElementById('metrics-status-badge').innerText = 'ERROR';
            document.getElementById('metrics-status-badge').className = 'trend-stable trend-danger';
        }
    } catch (e) {
        const dot = document.getElementById('server-status-dot');
        const text = document.getElementById('server-status-text');
        dot.className = 'status-dot offline';
        text.innerText = 'غير متصل';
        document.getElementById('metrics-status').innerText = 'Offline';
        document.getElementById('metrics-status-badge').innerText = 'DOWN';
        document.getElementById('metrics-status-badge').className = 'trend-stable trend-danger';
    }
}

// Initialize Latency Chart
function initChart() {
    const ctx = document.getElementById('latencyChart');
    if (!ctx) return;
    
    // Generate initial time metrics
    for (let i = 6; i >= 0; i--) {
        const d = new Date();
        d.setSeconds(d.getSeconds() - i * 30);
        chartLabels.push(d.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
        chartData.push(Math.floor(Math.random() * 15) + 20); // base simulated latency
    }

    latencyChart = new Chart(ctx.getContext('2d'), {
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
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: { color: '#8c8fa7', font: { family: 'Outfit', size: 10 } }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#8c8fa7', font: { family: 'Outfit', size: 9 } }
                }
            }
        }
    });
}

// Add point to chart
function updateChart(latencyVal) {
    if (!latencyChart) return;
    
    const now = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    
    latencyChart.data.labels.push(now);
    latencyChart.data.datasets[0].data.push(latencyVal);
    
    if (latencyChart.data.labels.length > 8) {
        latencyChart.data.labels.shift();
        latencyChart.data.datasets[0].data.shift();
    }
    
    latencyChart.update();
    
    // Update metric cards
    queryCount++;
    totalLatencySum += latencyVal;
    const avg = Math.round(totalLatencySum / queryCount);
    document.getElementById('metrics-latency-val').innerText = `${avg}ms`;
}

// Console trace log system
function addConsoleLog(message, type = 'info') {
    const consoleBox = document.getElementById('console-output');
    if (!consoleBox) return;
    
    const logLine = document.createElement('div');
    logLine.className = 'console-line';
    
    const time = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    
    let typeBadge = '<span class="console-type-info">[INFO]</span>';
    if (type === 'success') typeBadge = '<span class="console-type-success">[SUCCESS]</span>';
    if (type === 'warn') typeBadge = '<span class="console-type-warn">[WARN]</span>';
    if (type === 'error') typeBadge = '<span class="console-type-error">[ERROR]</span>';

    logLine.innerHTML = `<span class="console-time">[${time}]</span> ${typeBadge} <span>${message}</span>`;
    consoleBox.appendChild(logLine);
    consoleBox.scrollTop = consoleBox.scrollHeight;
}

function clearConsoleLogs() {
    const consoleBox = document.getElementById('console-output');
    if (consoleBox) consoleBox.innerHTML = '';
    addConsoleLog('تم مسح سجل الكونسول.', 'info');
}

// Reset chat session state
function startNewSession() {
    currentSessionId = null;
    document.getElementById('metrics-sessions').innerText = '0';
    activeSessionsCount = 0;
    
    const messagesContainer = document.getElementById('chat-messages');
    messagesContainer.innerHTML = `
        <div class="empty-state" id="empty-state">
            <div class="empty-icon">
                <i class="fa-solid fa-comments"></i>
            </div>
            <h2>تم بدء جلسة محادثة جديدة</h2>
            <p style="color: var(--text-secondary); max-width: 450px; margin: 0.5rem 0 1.5rem;">
                اطرح أي استفسار لبدء دورة المحادثة مجدداً.
            </p>
            <div class="suggested-chips">
                <div class="suggested-chip" onclick="sendQuery('ما هي سياسة الإجازة السنوية؟')">ما هي سياسة الإجازة السنوية؟</div>
                <div class="suggested-chip" onclick="sendQuery('أريد تقديم طلب إجازة سنوية')">أريد تقديم طلب إجازة سنوية</div>
                <div class="suggested-chip" onclick="sendQuery('ما هي تفاصيل بدل السكن؟')">ما هي تفاصيل بدل السكن؟</div>
            </div>
        </div>
    `;
    
    // Reset tracker panel
    document.getElementById('state-session-id').innerText = 'لا توجد جلسة نشطة';
    document.getElementById('state-session-id').classList.add('empty');
    
    document.getElementById('state-intent').innerText = 'غير مححدد';
    document.getElementById('state-intent').className = 'state-value empty';
    
    document.getElementById('state-confidence').innerText = '-';
    document.getElementById('state-confidence').classList.add('empty');

    const slots = ['slot-employee-id', 'slot-leave-type', 'slot-start-date', 'slot-end-date'];
    slots.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.className = 'badge badge-none';
            el.innerText = 'مفقود';
        }
    });

    document.getElementById('op-rag').className = 'badge badge-none';
    document.getElementById('op-sap').className = 'badge badge-none';

    addConsoleLog('تم إنهاء الجلسة القديمة وبدء جلسة جديدة بنجاح.', 'success');
}

function handleSend() {
    const input = document.getElementById('chat-input');
    const query = input.value.trim();
    if (!query) return;

    input.value = '';
    sendQuery(query);
}

// Send user text to API endpoints
async function sendQuery(query) {
    if (isWaitingResponse) return;
    
    const startTime = performance.now();
    const messagesContainer = document.getElementById('chat-messages');
    
    // Remove empty screen
    const emptyState = document.getElementById('empty-state');
    if (emptyState) {
        messagesContainer.innerHTML = '';
    }

    // Render User Message
    appendMessage('user', query);
    
    // Render Loading Dots
    const typingIndicator = appendTypingIndicator();
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    isWaitingResponse = true;
    document.getElementById('send-btn').style.opacity = '0.5';

    const token = document.getElementById('auth-token').value.trim();
    addConsoleLog(`إرسال طلب محادثة: "${query}" إلى خادم الأوركسترا...`, 'info');

    try {
        const payload = { query: query };
        if (currentSessionId) {
            payload.session_id = currentSessionId;
        }

        const response = await fetch(`${baseUrl}/api/v1/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });

        typingIndicator.remove();

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            const errMsg = errData?.error?.message || errData?.detail || 'فشل الاتصال بالخادم الداخلي.';
            appendMessage('bot', `⚠️ خطأ: ${errMsg}`);
            addConsoleLog(`خطأ معالجة الطلب: ${errMsg}`, 'error');
            return;
        }

        const result = await response.json();
        
        // Track session state
        if (result.session_id) {
            if (currentSessionId !== result.session_id) {
                currentSessionId = result.session_id;
                activeSessionsCount = 1;
                document.getElementById('metrics-sessions').innerText = '1';
            }
        }

        const endTime = performance.now();
        const latency = Math.round(endTime - startTime);

        // Update dynamic charts & metrics
        updateChart(latency);
        totalQueries++;
        document.getElementById('metrics-queries').innerText = totalQueries.toLocaleString();
        
        // Append log to Table Activity Stream
        addActivityRow('موظف HSA', `أجرى استعلاماً بنوع النية '${result.intent}'`, result.sap_executed ? 'ONLINE' : 'ONLINE', latency);
        
        addConsoleLog(`تم الاستلام. نية المستخدم: '${result.intent}' (الثقة: ${Math.round(result.confidence * 100)}%) خلال ${latency}ms`, 'success');

        // Append Bot Reply
        appendMessage('bot', result.response, result);
        
        // Refresh States panel UI
        updateStateTracker(result);

    } catch (err) {
        typingIndicator.remove();
        appendMessage('bot', `⚠️ فشل إرسال الطلب: تأكد من تشغيل الخادم على المنفذ الصحيح. (${err.message})`);
        addConsoleLog(`خطأ شبكة: ${err.message}`, 'error');
    } finally {
        isWaitingResponse = false;
        document.getElementById('send-btn').style.opacity = '1';
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

// Append messages bubbles
function appendMessage(sender, text, responseData = null) {
    const messagesContainer = document.getElementById('chat-messages');
    const wrapper = document.createElement('div');
    wrapper.className = `message-wrapper ${sender}`;

    const avatar = document.createElement('div');
    avatar.className = `message-avatar ${sender}`;
    avatar.innerHTML = sender === 'user' ? '<i class="fa-solid fa-user"></i>' : '<i class="fa-solid fa-brain"></i>';

    const container = document.createElement('div');
    container.className = 'message-bubble-container';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = text.replace(/\n/g, '<br>');

    container.appendChild(bubble);

    if (sender === 'bot' && responseData) {
        const pills = document.createElement('div');
        pills.className = 'engine-pills';

        if (responseData.intent) {
            const intentPill = document.createElement('div');
            intentPill.className = 'engine-pill rag';
            intentPill.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> Intent: ${responseData.intent}`;
            pills.appendChild(intentPill);
        }

        if (responseData.context_used) {
            const ragPill = document.createElement('div');
            ragPill.className = 'engine-pill rag';
            ragPill.innerHTML = '<i class="fa-solid fa-database"></i> RAG Context';
            pills.appendChild(ragPill);
        }

        if (responseData.sap_executed) {
            const sapPill = document.createElement('div');
            sapPill.className = 'engine-pill sap';
            sapPill.innerHTML = '<i class="fa-solid fa-check-double"></i> SAP SuccessFactors';
            pills.appendChild(sapPill);
        }

        if (pills.childNodes.length > 0) {
            container.appendChild(pills);
        }
    }

    const meta = document.createElement('div');
    meta.className = 'message-meta';
    const time = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    meta.innerHTML = `<span>${time}</span>`;
    container.appendChild(meta);

    wrapper.appendChild(avatar);
    wrapper.appendChild(container);
    messagesContainer.appendChild(wrapper);
}

// Append Typing indicator bubble
function appendTypingIndicator() {
    const messagesContainer = document.getElementById('chat-messages');
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper bot';

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar bot';
    avatar.innerHTML = '<i class="fa-solid fa-brain"></i>';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    
    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
    
    bubble.appendChild(indicator);
    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
    messagesContainer.appendChild(wrapper);

    return wrapper;
}

// Update State Tracker on User panel
function updateStateTracker(result) {
    const sessionIdEl = document.getElementById('state-session-id');
    sessionIdEl.innerText = result.session_id;
    sessionIdEl.classList.remove('empty');
    
    // Propagate session id to admin forms
    document.getElementById('session-clear-id').value = result.session_id;

    const intentEl = document.getElementById('state-intent');
    intentEl.innerText = result.intent;
    intentEl.className = 'state-value badge-intent';

    const confidenceEl = document.getElementById('state-confidence');
    confidenceEl.innerText = `${Math.round(result.confidence * 100)}%`;
    confidenceEl.classList.remove('empty');

    const opRag = document.getElementById('op-rag');
    opRag.className = result.context_used ? 'badge badge-completed' : 'badge badge-none';

    const opSap = document.getElementById('op-sap');
    opSap.className = result.sap_executed ? 'badge badge-completed' : 'badge badge-none';

    updateSlotBadge('slot-employee-id', result.entities?.employee_id);
    updateSlotBadge('slot-leave-type', result.entities?.leave_type);
    updateSlotBadge('slot-start-date', result.entities?.start_date);
    updateSlotBadge('slot-end-date', result.entities?.end_date);
}

function updateSlotBadge(badgeId, value) {
    const el = document.getElementById(badgeId);
    if (!el) return;
    if (value) {
        el.className = 'badge badge-completed';
        el.innerText = value;
    } else {
        el.className = 'badge badge-none';
        el.innerText = 'مفقود';
    }
}

// -------------------- ADMIN DASHBOARD API LOGIC --------------------

// POST /api/v1/admin/ingest
async function triggerIngest() {
    const token = document.getElementById('auth-token').value.trim();
    const btn = document.getElementById('btn-ingest');
    
    addConsoleLog('جاري إرسال طلب إعادة الفهرسة والـ chunking لمستندات السياسات...', 'info');
    btn.style.opacity = '0.6';
    btn.innerHTML = '<i class="fa-solid fa-sync fa-spin"></i> جاري تحديث الفهرس...';

    try {
        const response = await fetch(`${baseUrl}/api/v1/admin/ingest`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();
        if (response.ok && data.success) {
            addConsoleLog('نجاح: تم بناء متجهات Qdrant لسياسات الموارد البشرية وإعادة تحميل الكوليكشن.', 'success');
            alert('تمت إعادة الفهرسة بنجاح!');
        } else {
            const err = data?.error?.message || data?.detail || 'فشل بناء الفهرس.';
            addConsoleLog(`فشل تحديث الفهرس: ${err}`, 'error');
            alert(`خطأ: ${err}`);
        }
    } catch(e) {
        addConsoleLog(`خطأ اتصال: ${e.message}`, 'error');
        alert(`خطأ شبكة: ${e.message}`);
    } finally {
        btn.style.opacity = '1';
        btn.innerHTML = '<i class="fa-solid fa-sync"></i> إعادة فهرسة مستندات السياسات (Ingest)';
    }
}

// DELETE /api/v1/admin/sessions/{session_id}
async function clearSessionById() {
    const token = document.getElementById('auth-token').value.trim();
    const sessionInput = document.getElementById('session-clear-id');
    const targetSessionId = sessionInput.value.trim();

    if (!targetSessionId) {
        alert('يرجى إدخال معرف الجلسة Session ID.');
        return;
    }

    addConsoleLog(`جاري إرسال طلب حذف الجلسة: ${targetSessionId}...`, 'info');

    try {
        const response = await fetch(`${baseUrl}/api/v1/admin/sessions/${targetSessionId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();
        if (response.ok && data.success) {
            addConsoleLog(`نجاح: تم مسح الجلسة ${targetSessionId} بالكامل وتفريغ ذاكرتها.`, 'success');
            alert(`تم مسح الجلسة بنجاح.`);
            sessionInput.value = '';
            if (targetSessionId === currentSessionId) {
                startNewSession();
            }
        } else {
            const err = data?.error?.message || data?.detail || 'الجلسة غير موجودة.';
            addConsoleLog(`فشل مسح الجلسة: ${err}`, 'error');
            alert(`خطأ: ${err}`);
        }
    } catch(e) {
        addConsoleLog(`خطأ اتصال: ${e.message}`, 'error');
        alert(`خطأ شبكة: ${e.message}`);
    }
}

// Helper to add row to Dashboard Activity Stream
function addActivityRow(user, activityText, status, latency) {
    const tableBody = document.getElementById('activity-table-body');
    if (!tableBody) return;
    
    const row = document.createElement('tr');
    
    const time = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
    const latencySec = (latency / 1000).toFixed(2);
    
    const statusBadge = status.toLowerCase() === 'online' ? 
        '<span class="activity-badge online">ONLINE</span>' : 
        '<span class="activity-badge offline">COMPLETED</span>';

    row.innerHTML = `
        <td class="user-profile-cell">
            <div class="user-cell-avatar">HSA</div>
            <div class="user-cell-name">${user}</div>
        </td>
        <td>${activityText}</td>
        <td>${time}</td>
        <td>${latencySec}s</td>
        <td>${statusBadge}</td>
    `;
    
    // Prepend to top of table
    tableBody.insertBefore(row, tableBody.firstChild);
    
    // Keep max 5 rows in activity stream
    if (tableBody.childNodes.length > 5) {
        tableBody.removeChild(tableBody.lastChild);
    }
}

// -------------------- THEME TOGGLE LOGIC --------------------
function toggleTheme() {
    const body = document.body;
    const icon = document.getElementById('theme-toggle-icon');
    
    if (body.classList.contains('light-theme')) {
        body.classList.remove('light-theme');
        if (icon) {
            icon.className = 'fa-solid fa-sun';
        }
        localStorage.setItem('theme', 'dark');
        addConsoleLog('تم التحويل إلى المظهر الداكن.', 'info');
        updateChartTheme(false);
    } else {
        body.classList.add('light-theme');
        if (icon) {
            icon.className = 'fa-solid fa-moon';
        }
        localStorage.setItem('theme', 'light');
        addConsoleLog('تم التحويل إلى المظهر الفاتح.', 'info');
        updateChartTheme(true);
    }
}

function loadSavedTheme() {
    const savedTheme = localStorage.getItem('theme');
    const body = document.body;
    const icon = document.getElementById('theme-toggle-icon');
    
    if (savedTheme === 'light') {
        body.classList.add('light-theme');
        if (icon) {
            icon.className = 'fa-solid fa-moon';
        }
        setTimeout(() => updateChartTheme(true), 200);
    }
}

function updateChartTheme(isLight) {
    if (!latencyChart) return;
    
    const textColor = isLight ? '#475569' : '#a3b1c6';
    const gridColor = isLight ? 'rgba(0, 0, 0, 0.05)' : 'rgba(255, 255, 255, 0.03)';
    
    latencyChart.options.scales.y.ticks.color = textColor;
    latencyChart.options.scales.y.grid.color = gridColor;
    latencyChart.options.scales.x.ticks.color = textColor;
    
    latencyChart.update();
}


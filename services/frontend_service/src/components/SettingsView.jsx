import React, { useState, useEffect, useRef } from 'react';
import { useAppStore, baseUrl } from '../store/useAppStore';
import { useChatStore } from '../store/useChatStore';
import { hasPermission } from '../utils/permissions';

export default function SettingsView() {
  const { authToken, setAuthToken, consoleLogs, clearConsoleLogs, indicatorDirection, setIndicatorDirection, loggedInUser, addConsoleLog } = useAppStore();
  const { sessionId, triggerIngest, isIngesting, clearSessionById } = useChatStore();

  const [clearId, setClearId] = useState('');
  const consoleEndRef = useRef(null);

  // Sync clear ID input with active session ID if available
  useEffect(() => {
    if (sessionId) {
      setClearId(sessionId);
    }
  }, [sessionId]);

  // Auto scroll console logs to bottom
  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [consoleLogs]);

  // User Permissions States & Handlers
  const [users, setUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [savingUserId, setSavingUserId] = useState(null);

  const fetchUsers = async () => {
    setLoadingUsers(true);
    try {
      const response = await fetch(`${baseUrl}/api/v1/permissions/users`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (response.ok) {
        const data = await response.json();
        setUsers(data.users);
      } else {
        const errData = await response.json().catch(() => ({}));
        addConsoleLog(`فشل استرجاع مستخدمي الصلاحيات: ${errData?.detail || 'خطأ غير معروف'}`, 'error');
      }
    } catch (err) {
      addConsoleLog(`فشل استرجاع مستخدمي الصلاحيات: ${err.message}`, 'error');
    } finally {
      setLoadingUsers(false);
    }
  };

  useEffect(() => {
    if (hasPermission(loggedInUser, 'manage_permissions')) {
      fetchUsers();
    }
  }, [loggedInUser]);

  const handleRoleChange = async (employeeId, newRoles) => {
    setSavingUserId(employeeId);
    try {
      const response = await fetch(`${baseUrl}/api/v1/permissions/update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({ employee_id: employeeId, roles: newRoles })
      });
      if (response.ok) {
        addConsoleLog(`تم تحديث صلاحيات الموظف ${employeeId} بنجاح.`, 'success');
        fetchUsers();
        
        // If updating the logged-in user themselves, refresh the local profile state
        if (employeeId === loggedInUser.employee_id) {
          addConsoleLog('تم تحديث أدوارك الحالية بالخلفية. جاري استرجاع البيانات المحدثة...', 'info');
          const meResponse = await fetch(`${baseUrl}/api/v1/auth/me`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
          });
          if (meResponse.ok) {
            const meData = await meResponse.json();
            localStorage.setItem('userProfile', JSON.stringify(meData));
            useAppStore.setState({ loggedInUser: meData });
            addConsoleLog('تم تحديث الصلاحيات الحالية لجلسة العمل بنجاح.', 'success');
          }
        }
      } else {
        const errData = await response.json().catch(() => ({}));
        addConsoleLog(`فشل تحديث الصلاحيات: ${errData?.detail || 'خطأ غير معروف'}`, 'error');
      }
    } catch (err) {
      addConsoleLog(`فشل تحديث الصلاحيات: ${err.message}`, 'error');
    } finally {
      setSavingUserId(null);
    }
  };

  return (
    <div id="view-settings" className="view-panel active">
      <div className="settings-container">
        {/* Access Token settings */}
        <div className="settings-card">
          <h3 className="settings-title">المصادقة والتحقق من الوصول</h3>
          <p className="settings-desc">إعدادات كلمات المرور ومفاتيح التوثيق الخاصة بالاتصال بخوادم أوركسترا الموارد البشرية.</p>

          <div className="form-group">
            <label>رمزBearer للمطور (Static Authorization Key)</label>
            <input 
              type="text" 
              id="auth-token" 
              value={authToken}
              onChange={(e) => setAuthToken(e.target.value)}
            />
          </div>
        </div>

        {/* UI Customization settings */}
        <div className="settings-card">
          <h3 className="settings-title">تخصيص واجهة المستخدم والتفاعل</h3>
          <p className="settings-desc">تعديل سلوك واتجاه حركة مؤشرات التفكير والتحليل في النظام.</p>

          <div className="form-group">
            <label>اتجاه مؤشر التفكير والتحليل (Thinking & Analyzing Direction)</label>
            <select
              className="select-style"
              value={indicatorDirection}
              onChange={(e) => setIndicatorDirection(e.target.value)}
            >
              <option value="rtl">من اليمين إلى اليسار (RTL) - للغة العربية</option>
              <option value="ltr">من اليسار إلى اليمين (LTR) - للغة الإنجليزية</option>
              <option value="auto">تلقائي (Auto) - بناءً على لغة النص</option>
            </select>
          </div>
        </div>

        {/* Admin controls panel */}
        <div className="settings-card">
          <h3 className="settings-title">إجراءات المدير والعمليات الخلفية</h3>
          <p className="settings-desc">أدوات إدارية خاصة بتهيئة قاعدة البيانات Vector DB وحذف جلسات الذاكرة المؤقتة.</p>

          <div className="action-group">
            <button 
              className="btn-card btn-admin" 
              onClick={triggerIngest} 
              id="btn-ingest"
              disabled={isIngesting}
              style={{ backgroundColor: 'var(--accent-admin)', width: '100%', justifyContent: 'center', color: 'white', opacity: isIngesting ? 0.6 : 1 }}
            >
              <i className={`fa-solid ${isIngesting ? 'fa-sync fa-spin' : 'fa-sync'}`}></i>
              {isIngesting ? ' جاري تحديث الفهرس...' : ' إعادة بناء فهرس المستندات (Ingest Vector DB)'}
            </button>

            <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.05)', marginTop: '1rem', paddingTop: '1rem' }}>
              <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', display: 'block', fontWeight: 600 }}>
                مسح بيانات جلسة محددة من الذاكرة:
              </label>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <input 
                  type="text" 
                  className="input-style" 
                  id="session-clear-id"
                  placeholder="أدخل معرف الجلسة Session ID" 
                  style={{ flex: 1, backgroundColor: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '4px', padding: '0 0.75rem', outline: 'none' }}
                  value={clearId}
                  onChange={(e) => setClearId(e.target.value)}
                />
                <button 
                  className="btn-card btn-danger" 
                  onClick={() => clearSessionById(clearId)}
                  style={{ backgroundColor: 'var(--danger)', border: 'none', color: 'white' }}
                >
                  حذف الجلسة
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* User Permissions Management Panel (General Manager only) */}
        {hasPermission(loggedInUser, 'manage_permissions') && (
          <div className="settings-card permissions-card" style={{ animation: 'fadeIn 0.3s ease' }}>
            <h3 className="settings-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <i className="fa-solid fa-user-shield" style={{ color: 'var(--accent-gold)' }}></i>
              إدارة صلاحيات النظام والتحكم في الوصول (Access Control)
            </h3>
            <p className="settings-desc">بصفتك المدير العام للنظام، يمكنك إدارة وتعديل أدوار الموظفين وتوزيع صلاحيات الاستخدام.</p>
            
            {loadingUsers ? (
              <div style={{ textAlign: 'center', padding: '2rem' }}>
                <i className="fa-solid fa-spinner fa-spin" style={{ fontSize: '1.5rem', color: 'var(--accent-gold)' }}></i>
                <p style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>جاري تحميل الموظفين وصلاحياتهم...</p>
              </div>
            ) : (
              <div className="permissions-table-wrapper" style={{ marginTop: '1rem', overflowX: 'auto' }}>
                <table className="activity-table" style={{ width: '100%' }}>
                  <thead>
                    <tr>
                      <th>الموظف</th>
                      <th>القسم / المسمى الوظيفي</th>
                      <th>الدور الوظيفي (Role)</th>
                      <th>الصلاحيات المكتسبة (Permissions)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map(user => (
                      <tr key={user.employee_id}>
                        <td className="user-profile-cell">
                          <div className="user-cell-avatar" style={{ backgroundColor: 'var(--accent-gold)', color: '#000', fontWeight: 'bold' }}>
                            {user.first_name[0] || ''}{user.last_name ? user.last_name[0] : ''}
                          </div>
                          <div>
                            <div className="user-cell-name">{user.first_name} {user.last_name}</div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{user.email}</div>
                          </div>
                        </td>
                        <td>
                          <div>{user.department}</div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{user.position}</div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <select
                              className="select-style"
                              style={{ fontSize: '0.8rem', padding: '0.25rem 0.5rem', width: 'auto', minWidth: '160px', backgroundColor: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '4px', outline: 'none' }}
                              value={user.roles[0] || 'employee'}
                              disabled={savingUserId === user.employee_id}
                              onChange={(e) => handleRoleChange(user.employee_id, [e.target.value])}
                            >
                              <option value="employee" style={{ backgroundColor: '#1e293b' }}>مستخدم عادي (Employee)</option>
                              <option value="manager" style={{ backgroundColor: '#1e293b' }}>مدير (Manager)</option>
                              <option value="hr_admin" style={{ backgroundColor: '#1e293b' }}>مسؤول موارد بشرية (HR Admin)</option>
                              <option value="general_manager" style={{ backgroundColor: '#1e293b' }}>مدير عام للنظام (General Manager)</option>
                            </select>
                            {savingUserId === user.employee_id && (
                              <i className="fa-solid fa-spinner fa-spin" style={{ color: 'var(--accent-gold)' }}></i>
                            )}
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                            {(user.roles || []).map(role => {
                              const labelMap = {
                                'view_overview': 'نظرة عامة',
                                'update_index': 'تحديث الفهرس',
                                'view_settings': 'الإعدادات',
                                'manage_permissions': 'إدارة الصلاحيات',
                                'delete_session': 'حذف الجلسات'
                              };
                              const rolePerms = {
                                general_manager: ['view_overview', 'update_index', 'view_settings', 'manage_permissions', 'delete_session'],
                                hr_admin: ['view_overview', 'update_index', 'view_settings', 'delete_session'],
                                manager: ['view_overview'],
                                employee: []
                              };
                              const perms = rolePerms[role] || [];
                              if (perms.length === 0) {
                                return <span key={role} className="badge badge-none" style={{ fontSize: '0.65rem', backgroundColor: 'rgba(255,255,255,0.05)', color: 'var(--text-muted)' }}>لا توجد صلاحيات خاصة</span>;
                              }
                              return perms.map(p => (
                                <span 
                                  key={p} 
                                  className="badge" 
                                  style={{ 
                                    fontSize: '0.65rem', 
                                    backgroundColor: 'rgba(212, 175, 55, 0.1)', 
                                    color: 'var(--accent-gold)', 
                                    border: '1px solid rgba(212, 175, 55, 0.2)',
                                    borderRadius: '4px',
                                    padding: '0.15rem 0.35rem'
                                  }}
                                >
                                  {labelMap[p] || p}
                                </span>
                              ));
                            })}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Live Terminal Output */}
        <div className="settings-card" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: '250px' }}>
          <div className="split-card-header" style={{ marginBottom: '0.75rem' }}>
            <div>
              <h3 className="settings-title">سجل الأحداث والعمليات الفوري (Console Logs)</h3>
            </div>
            <button 
              className="new-chat-btn" 
              onClick={clearConsoleLogs}
              style={{ fontSize: '0.75rem', padding: '0.2rem 0.6rem', border: 'none', cursor: 'pointer' }}
            >
              مسح السجل
            </button>
          </div>

          <div className="console-output" id="console-output" style={{ overflowY: 'auto', maxHeight: '180px' }}>
            {consoleLogs.map((log, idx) => {
              let badgeClass = 'console-type-info';
              let badgeText = '[INFO]';
              if (log.type === 'success') {
                badgeClass = 'console-type-success';
                badgeText = '[SUCCESS]';
              } else if (log.type === 'warn') {
                badgeClass = 'console-type-warn';
                badgeText = '[WARN]';
              } else if (log.type === 'error') {
                badgeClass = 'console-type-error';
                badgeText = '[ERROR]';
              }

              return (
                <div key={idx} className="console-line">
                  <span className="console-time">[{log.time}]</span>
                  <span className={badgeClass}>{badgeText}</span>
                  <span>{log.message}</span>
                </div>
              );
            })}
            <div ref={consoleEndRef} />
          </div>
        </div>
      </div>
    </div>
  );
}

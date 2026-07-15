import React, { useState } from 'react';
import { useAppStore, baseUrl } from '../store/useAppStore';

export default function SharepointLogin({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const addConsoleLog = useAppStore((state) => state.addConsoleLog);

  // Quick profiles for simulation
  const mockProfiles = [
    { name: 'Sharaf', email: 'sharaf@hsagroup.com', role: 'الذكاء الاصطناعي (AI)', empId: 'EMP101' },
    { name: 'Testing User 2', email: 'khaled.mutahar@hsagroup.com', role: 'الذكاء الاصطناعي (AI Lead)', empId: 'EMP102' },
    { name: 'Testing User 3', email: 'sarah.jamil@hsagroup.com', role: 'المالية (Financial Analyst)', empId: 'EMP103' },
    { name: 'علي منصور', email: 'ali.mansoor@hsagroup.com', role: 'المبيعات (Sales Rep)', empId: 'EMP104' }
  ];

  const handleLogin = async (e, customEmail = null, customPass = null) => {
    if (e) e.preventDefault();
    setErrorMsg('');
    setLoading(true);

    const emailToUse = customEmail || username;
    const passToUse = customPass || password;

    if (!emailToUse || !passToUse) {
      setErrorMsg('يرجى إدخال اسم المستخدم وكلمة المرور.');
      setLoading(false);
      return;
    }

    addConsoleLog(`محاولة تسجيل دخول للمستخدم: ${emailToUse}...`, 'info');

    try {
      const response = await fetch(`${baseUrl}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username_or_email: emailToUse,
          password: passToUse
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const msg = errorData?.detail || 'فشل تسجيل الدخول. يرجى التحقق من المدخلات.';
        setErrorMsg(msg);
        addConsoleLog(`فشل تسجيل الدخول للمستخدم ${emailToUse}: ${msg}`, 'error');
        setLoading(false);
        return;
      }

      const result = await response.json();

      // Save to localStorage and store
      localStorage.setItem('authToken', result.access_token);
      localStorage.setItem('userProfile', JSON.stringify(result.user));

      useAppStore.getState().setAuthToken(result.access_token);
      useAppStore.setState({ loggedInUser: result.user });

      addConsoleLog(`تم تسجيل الدخول بنجاح للموظف: ${result.user.first_name} ${result.user.last_name} (${result.user.employee_id})`, 'success');

      if (onLoginSuccess) {
        onLoginSuccess();
      }
    } catch (err) {
      setErrorMsg('خطأ في الاتصال بالخادم. يرجى التأكد من تشغيل خادم الأوركسترا.');
      addConsoleLog(`خطأ اتصال بالشبكة أثناء تسجيل الدخول: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = (email) => {
    setUsername(email);
    setPassword('password123');
    handleLogin(null, email, 'password123');
  };

  return (
    <div className="login-page-container">
      <div className="login-card-glass">

        {/* HSA Corporate SVG Logo */}
        <div className="login-logo-header">
          <svg className="hsa-logo-svg" viewBox="0 0 120 40" width="150" height="50" style={{ margin: '0 auto 0.5rem auto', display: 'block' }}>
            <text x="5" y="28" fontFamily="'Outfit', sans-serif" fontWeight="900" fontSize="28"
              fill="url(#gold-grad)" letterSpacing="-1">HSA</text>
            <path d="M 5 32 Q 55 38 105 32" fill="none" stroke="#0056b3" strokeWidth="4" strokeLinecap="round" />
            <path d="M 45 32 Q 75 35 105 32" fill="none" stroke="url(#gold-grad)" strokeWidth="3" strokeLinecap="round" />
          </svg>
          <div className="login-subtitle">بوابة تسجيل الدخول الموحد (SharePoint SSO Portal)</div>
        </div>

        {errorMsg && (
          <div className="login-error-alert animate-fade-in">
            <i className="fa-solid fa-triangle-exclamation" style={{ marginLeft: '0.5rem' }}></i>
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={(e) => handleLogin(e)} className="login-form">
          <div className="form-group">
            <label className="form-label">البريد الإلكتروني أو اسم المستخدم المؤسسي</label>
            <div className="input-with-icon">
              <i className="fa-solid fa-envelope input-icon-inner"></i>
              <input
                type="text"
                placeholder="username@hsagroup.com"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={loading}
                className="login-input"
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">كلمة المرور في نظام SAP / Active Directory</label>
            <div className="input-with-icon">
              <i className="fa-solid fa-lock input-icon-inner"></i>
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                className="login-input"
              />
            </div>
          </div>

          <button
            type="submit"
            className={`login-submit-btn ${loading ? 'loading' : ''}`}
            disabled={loading}
          >
            {loading ? (
              <>
                <i className="fa-solid fa-spinner fa-spin" style={{ marginLeft: '0.5rem' }}></i>
                جاري التحقق والمصادقة...
              </>
            ) : (
              <>
                <i className="fa-solid fa-right-to-bracket" style={{ marginLeft: '0.5rem' }}></i>
                تسجيل الدخول الموحد
              </>
            )}
          </button>
        </form>

        <div className="login-divider-text">أو قم بمحاكاة حساب موظف نشط مباشرة</div>

        <div className="quick-profiles-grid">
          {mockProfiles.map((profile, idx) => (
            <div
              key={idx}
              className="quick-profile-card"
              onClick={() => !loading && handleQuickLogin(profile.email)}
              title={`تسجيل دخول سريع كـ ${profile.name}`}
            >
              <div className="quick-profile-avatar">
                {profile.name.substring(0, 2)}
              </div>
              <div className="quick-profile-info">
                <div className="quick-profile-name">{profile.name}</div>
                <div className="quick-profile-role">{profile.role}</div>
                <div className="quick-profile-id">كود: {profile.empId}</div>
              </div>
              <i className="fa-solid fa-chevron-left quick-profile-arrow"></i>
            </div>
          ))}
        </div>

        <div className="login-footer">
          <i className="fa-solid fa-lock-keyhole" style={{ marginLeft: '0.25rem' }}></i>
          جميع جلسات الاتصال مشفرة عبر خوادم بوابة SharePoint ومربوطة بأمان بنظام SAP SuccessFactors.
        </div>

      </div>
    </div>
  );
}

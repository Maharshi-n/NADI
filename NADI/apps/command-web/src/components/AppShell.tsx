import React, { useState } from 'react';

const ROLES = [
  { id: 'cmho', label: 'CMHO / District Officer' },
  { id: 'bmo', label: 'Block Medical Officer' },
  { id: 'mo', label: 'Medical Officer (PHC)' },
  { id: 'pharmacist', label: 'PHC Pharmacist' },
  { id: 'state', label: 'State Officer' },
] as const;

/**
 * App shell — header with NADI logo and role switcher stub.
 * Demo mode: no auth, role switcher in header (per CONTEXT.md).
 */
type Role = typeof ROLES[number];

export function AppShell({ 
  children,
  currentView = 'dashboard',
  onViewChange
}: { 
  children: React.ReactNode,
  currentView?: string,
  onViewChange?: (view: any) => void 
}) {
  const [currentRole, setCurrentRole] = useState<Role>(ROLES[0]);
  const [showRoles, setShowRoles] = useState(false);

  return (
    <>
      <header className="app-header" id="app-header">
        <div className="app-header__logo">
          <div className="app-header__logo-icon">⚡</div>
          <span>NADI</span>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400, marginLeft: '4px' }}>
            District Command
          </span>
        </div>

        <nav style={{ display: 'flex', gap: '24px', flex: 1, marginLeft: '40px' }}>
          <div 
            onClick={() => onViewChange?.('dashboard')}
            style={{ 
              cursor: 'pointer',
              color: currentView === 'dashboard' ? 'var(--text-primary)' : 'var(--text-secondary)',
              fontWeight: currentView === 'dashboard' ? 500 : 400,
              borderBottom: currentView === 'dashboard' ? '2px solid var(--accent-glow)' : '2px solid transparent',
              padding: '16px 0',
              transition: 'all 0.2s'
            }}
          >
            Dashboard
          </div>
          <div 
            onClick={() => onViewChange?.('planner')}
            style={{ 
              cursor: 'pointer',
              color: currentView === 'planner' ? 'var(--text-primary)' : 'var(--text-secondary)',
              fontWeight: currentView === 'planner' ? 500 : 400,
              borderBottom: currentView === 'planner' ? '2px solid var(--accent-glow)' : '2px solid transparent',
              padding: '16px 0',
              transition: 'all 0.2s'
            }}
          >
            Transfer Planner
          </div>
        </nav>

        <div className="app-header__right">
          <div
            className="role-switcher"
            id="role-switcher"
            onClick={() => setShowRoles(!showRoles)}
            style={{ position: 'relative' }}
          >
            <span className="role-switcher__dot" />
            <span>{currentRole.label}</span>
            <span style={{ fontSize: '0.65rem', opacity: 0.6 }}>▼</span>

            {showRoles && (
              <div
                style={{
                  position: 'absolute',
                  top: '100%',
                  right: 0,
                  marginTop: '6px',
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--bg-glass-border)',
                  borderRadius: 'var(--radius-md)',
                  boxShadow: 'var(--shadow-lg)',
                  zIndex: 200,
                  minWidth: '220px',
                  overflow: 'hidden',
                }}
              >
                {ROLES.map((role) => (
                  <div
                    key={role.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      setCurrentRole(role);
                      setShowRoles(false);
                    }}
                    style={{
                      padding: '10px 16px',
                      fontSize: '0.8rem',
                      cursor: 'pointer',
                      background: role.id === currentRole.id ? 'var(--accent-glow)' : 'transparent',
                      color: role.id === currentRole.id ? 'var(--accent-hover)' : 'var(--text-secondary)',
                      transition: 'background var(--transition-fast)',
                    }}
                    onMouseEnter={(e) => {
                      if (role.id !== currentRole.id) {
                        (e.target as HTMLElement).style.background = 'rgba(255,255,255,0.03)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (role.id !== currentRole.id) {
                        (e.target as HTMLElement).style.background = 'transparent';
                      }
                    }}
                  >
                    {role.label}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </header>
      {children}
    </>
  );
}

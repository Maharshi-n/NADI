import { useState } from 'react';
import './index.css';
import { AppShell } from './components/AppShell';
import { Dashboard } from './pages/Dashboard';
import { TransferPlanner } from './pages/TransferPlanner';
import { FederationDashboard } from './pages/FederationDashboard';
import { DataTrust } from './pages/DataTrust';

export type ViewState = 'dashboard' | 'planner' | 'federation' | 'trust';

function App() {
  const [currentView, setCurrentView] = useState<ViewState>('dashboard');

  return (
    <AppShell currentView={currentView} onViewChange={setCurrentView}>
      {currentView === 'dashboard' && <Dashboard />}
      {currentView === 'planner' && <TransferPlanner />}
      {currentView === 'federation' && <FederationDashboard />}
      {currentView === 'trust' && <DataTrust />}
    </AppShell>
  );
}

export default App;

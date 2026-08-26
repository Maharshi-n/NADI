import { useState } from 'react';
import './index.css';
import { AppShell } from './components/AppShell';
import { Dashboard } from './pages/Dashboard';
import { TransferPlanner } from './pages/TransferPlanner';

export type ViewState = 'dashboard' | 'planner';

function App() {
  const [currentView, setCurrentView] = useState<ViewState>('dashboard');

  return (
    <AppShell currentView={currentView} onViewChange={setCurrentView}>
      {currentView === 'dashboard' ? <Dashboard /> : <TransferPlanner />}
    </AppShell>
  );
}

export default App;

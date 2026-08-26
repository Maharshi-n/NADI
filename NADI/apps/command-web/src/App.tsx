import './index.css';
import { AppShell } from './components/AppShell';
import { Dashboard } from './pages/Dashboard';

function App() {
  return (
    <AppShell>
      <Dashboard />
    </AppShell>
  );
}

export default App;

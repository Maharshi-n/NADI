import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { HomeTab } from './pages/HomeTab';
import { StockTab } from './pages/StockTab';
import { ScanTab } from './pages/ScanTab';
import { TransfersTab } from './pages/TransfersTab';
import { useEffect } from 'react';
import { syncMutations } from './services/sync';

function App() {
  // Try to sync when coming back online
  useEffect(() => {
    const handleOnline = () => {
      console.log('Back online, syncing mutations...');
      syncMutations().catch(console.error);
    };
    
    window.addEventListener('online', handleOnline);
    return () => window.removeEventListener('online', handleOnline);
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomeTab />} />
          <Route path="stock" element={<StockTab />} />
          <Route path="scan" element={<ScanTab />} />
          <Route path="transfers" element={<TransfersTab />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;

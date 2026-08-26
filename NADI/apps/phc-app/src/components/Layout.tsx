import { Link, Outlet, useLocation } from 'react-router-dom';
import { Home, Package, Camera, ArrowRightLeft } from 'lucide-react';
import { useLiveQuery } from 'dexie-react-hooks';
import { db } from '../db/db';

export function Layout() {
  const location = useLocation();
  const pendingCount = useLiveQuery(() => db.mutations.where('synced').equals('false').count(), []) || 0;

  const navItems = [
    { path: '/', label: 'Home', icon: Home },
    { path: '/stock', label: 'Stock', icon: Package },
    { path: '/scan', label: 'Scan', icon: Camera },
    { path: '/transfers', label: 'Transfers', icon: ArrowRightLeft },
  ];

  return (
    <div className="flex flex-col h-screen bg-background text-gray-100">
      {/* Header */}
      <header className="flex items-center justify-between p-4 bg-surface border-b border-gray-800">
        <h1 className="text-xl font-bold text-primary">NADI PHC</h1>
        {pendingCount > 0 && (
          <div className="flex items-center space-x-2">
            <span className="flex h-3 w-3 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-warning opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-warning"></span>
            </span>
            <span className="text-sm text-gray-400">{pendingCount} pending</span>
          </div>
        )}
      </header>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto p-4">
        <Outlet />
      </main>

      {/* Bottom Navigation */}
      <nav className="flex items-center justify-around p-3 bg-surface border-t border-gray-800">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex flex-col items-center space-y-1 p-2 rounded-lg transition-colors ${
                isActive ? 'text-primary' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <Icon className="w-6 h-6" />
              <span className="text-xs">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

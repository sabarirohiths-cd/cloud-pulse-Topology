import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { Toaster, toast } from 'sonner';
import { Cloud, Zap, Server, Settings, Activity, Boxes, CloudCog } from 'lucide-react';
import InventoryPage from './pages/inventory/InventoryPage';
import ConfigPage from './pages/config/ConfigPage';
import ControlPage from './pages/control/ControlPage';

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" theme="dark" richColors duration={2500} />
      <div className="flex h-screen" onClick={() => toast.dismiss()}>
        {/* Sidebar */}
        <aside className="w-56 bg-[#0e1015] border-r border-[#1e232b] flex flex-col p-3">
          <div className="flex items-center gap-2.5 mb-6 px-3 pt-2">
            <div className="relative flex items-center justify-center">
              <Cloud className="h-6 w-6 text-white" strokeWidth={1.5} />
              <Activity className="h-3 w-3 text-white absolute" strokeWidth={3} />
            </div>
            <span className="text-white font-bold tracking-tight text-[15px]">Cloud Pulse Agent</span>
          </div>
          <nav className="space-y-1">
            <NavLink to="/control" className={({isActive}) => `flex items-center gap-3 px-3 py-2.5 rounded-md text-[13px] font-medium transition-colors ${isActive ? 'bg-[#1a1d24] text-white' : 'text-[#8b949e] hover:text-white hover:bg-[#1a1d24]'}`}>
              {({isActive}) => (
                <>
                  <Activity className="h-4 w-4 text-purple-400" /> Control
                </>
              )}
            </NavLink>
            <NavLink to="/inventory" className={({isActive}) => `flex items-center gap-3 px-3 py-2.5 rounded-md text-[13px] font-medium transition-colors ${isActive ? 'bg-[#1a1d24] text-white' : 'text-[#8b949e] hover:text-white hover:bg-[#1a1d24]'}`}>
              {({isActive}) => (
                <>
                  <Boxes className="h-4 w-4 text-teal-400" /> Inventory
                </>
              )}
            </NavLink>
            <NavLink to="/config" className={({isActive}) => `flex items-center gap-3 px-3 py-2.5 rounded-md text-[13px] font-medium transition-colors ${isActive ? 'bg-[#1a1d24] text-white' : 'text-[#8b949e] hover:text-white hover:bg-[#1a1d24]'}`}>
              {({isActive}) => (
                <>
                  <CloudCog className="h-4 w-4 text-cyan-400" /> Configuration
                </>
              )}
            </NavLink>
          </nav>
        </aside>
        {/* Main content */}
        <main id="main-scroll-container" className="flex-1 overflow-y-auto p-6 bg-[#0a0a0f]">
          <Routes>
            <Route path="/" element={<Navigate to="/control" replace />} />
            <Route path="/control" element={<ControlPage />} />
            <Route path="/inventory" element={<InventoryPage />} />
            <Route path="/config" element={<ConfigPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { Toaster, toast } from 'sonner';
import { Cloud, Activity, Boxes, Settings, PanelLeftClose, PanelLeft } from 'lucide-react';
import TopologyPage from './pages/topology/TopologyPage';
import ConfigPage from './pages/config/ConfigPage';
import DiagnosticDetailPage from './pages/diagnostics/DiagnosticDetailPage';

export default function App() {
  const [isSidebarMinimized, setIsSidebarMinimized] = useState(false);

  useEffect(() => {
    // Trigger window resize event after transition completes to force visualizations to re-center
    const timer = setTimeout(() => {
      window.dispatchEvent(new Event('resize'));
    }, 300);
    return () => clearTimeout(timer);
  }, [isSidebarMinimized]);

  return (
    <BrowserRouter>
      <Toaster position="top-right" theme="dark" richColors duration={2500} />
      <div className="flex h-screen bg-[#0a0a0f]" onClick={() => toast.dismiss()}>
        {/* Sidebar */}
        <aside className={`${isSidebarMinimized ? 'w-[72px]' : 'w-56'} transition-all duration-300 ease-in-out bg-[#0e1015] border-r border-[#1e232b] flex flex-col p-3 z-20 relative shrink-0`}>
          
          <div 
            className={`flex items-center ${isSidebarMinimized ? 'justify-center group cursor-pointer' : 'justify-between'} mb-6 pt-2 min-h-8`}
            onClick={() => { if (isSidebarMinimized) setIsSidebarMinimized(false); }}
            title={isSidebarMinimized ? "Expand Sidebar" : ""}
          >
            <div className={`flex items-center gap-2.5 ${isSidebarMinimized ? 'px-0 relative' : 'px-1'}`}>
              <div className={`relative flex items-center justify-center shrink-0 transition-opacity duration-300 ${isSidebarMinimized ? 'group-hover:opacity-0' : ''}`}>
                <Cloud className="h-6 w-6 text-white" strokeWidth={1.5} />
                <Activity className="h-3 w-3 text-white absolute" strokeWidth={3} />
              </div>
              
              {isSidebarMinimized && (
                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300 text-white">
                  <PanelLeft size={20} />
                </div>
              )}

              {!isSidebarMinimized && (
                <span className="text-white font-bold tracking-tight text-sm whitespace-nowrap overflow-hidden ml-1">
                  Cloud Pulse Agent
                </span>
              )}
            </div>
            
            {!isSidebarMinimized && (
              <button 
                onClick={(e) => { e.stopPropagation(); setIsSidebarMinimized(true); }}
                className="text-gray-400 hover:text-white transition-colors p-1"
                title="Minimize Sidebar"
              >
                <PanelLeftClose size={16} />
              </button>
            )}
          </div>
          <nav className="space-y-1">
            <NavLink to="/topology" title={isSidebarMinimized ? "Topology" : ""} className={({isActive}) => `flex items-center gap-3 ${isSidebarMinimized ? 'px-3 justify-center' : 'px-3'} py-2.5 rounded-md text-sm font-medium transition-colors ${isActive ? 'bg-[#1a1d24] text-white' : 'text-[#8b949e] hover:text-white hover:bg-[#1a1d24]'}`}>
              {({isActive}) => (
                <>
                  <Boxes className="h-4 w-4 text-purple-400 shrink-0" /> 
                  {!isSidebarMinimized && <span className="whitespace-nowrap overflow-hidden">Topology</span>}
                </>
              )}
            </NavLink>
            <NavLink to="/config" title={isSidebarMinimized ? "Configuration" : ""} className={({isActive}) => `flex items-center gap-3 ${isSidebarMinimized ? 'px-3 justify-center' : 'px-3'} py-2.5 rounded-md text-sm font-medium transition-colors ${isActive ? 'bg-[#1a1d24] text-white' : 'text-[#8b949e] hover:text-white hover:bg-[#1a1d24]'}`}>
              {({isActive}) => (
                <>
                  <Settings className="h-4 w-4 text-gray-400 shrink-0" /> 
                  {!isSidebarMinimized && <span className="whitespace-nowrap overflow-hidden">Configuration</span>}
                </>
              )}
            </NavLink>
          </nav>
        </aside>
        {/* Main content */}
        <main id="main-scroll-container" className="flex-1 bg-[#0a0a0f] flex flex-col min-h-0 relative">
          <Routes>
            <Route path="/" element={<Navigate to="/topology" replace />} />
            <Route path="/topology" element={<TopologyPage />} />
            <Route path="/config" element={<ConfigPage />} />
            <Route path="/diagnostics/:nodeId" element={<DiagnosticDetailPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

import React, { useState, useCallback, useEffect } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';
import { scanTopology, getSampleTopology } from '../../api/topology';
import { listConfigs } from '../../api/config';
import TopologyDetailModal from '../../components/topology/TopologyDetailModal';
import ScanConfigurationModal from '../../components/topology/ScanConfigurationModal';
import InfrastructureTreeView from '../../components/topology/InfrastructureTreeView';
import TopologyDashboard from '../../components/topology/TopologyDashboard'; // Trigger rebuild

export default function TopologyPage() {
  const [loading, setLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [globals, setGlobals] = useState(null);
  
  const [viewRegion, setViewRegion] = useState('');
  const [viewProvider, setViewProvider] = useState('');
  const [availableProviders, setAvailableProviders] = useState([]);
  const [viewAccount, setViewAccount] = useState('');
  const [availableAccounts, setAvailableAccounts] = useState([]);
  const [configs, setConfigs] = useState([]);
  const [showScanModal, setShowScanModal] = useState(false);
  const [availableRegions, setAvailableRegions] = useState([]);
  const [rawTopologyData, setRawTopologyData] = useState(null);
  
  const [focusedNodeId, setFocusedNodeId] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const loadData = useCallback(async (isLive = false, regions = ['ap-south-1']) => {
    setLoading(true);
    try {
      const response = isLive ? await scanTopology(regions) : await getSampleTopology();
      const topologyData = response.data || {};
      
      const extractedRegions = topologyData.Regions ? Object.keys(topologyData.Regions) : [];
      setAvailableRegions(extractedRegions);
      if (extractedRegions.length > 0) {
        setViewRegion(prev => extractedRegions.includes(prev) ? prev : extractedRegions[0]);
      }
      
      setRawTopologyData(topologyData);
      
      toast.success(isLive ? 'Live scan complete!' : 'Loaded sample topology.');
    } catch (error) {
      toast.error('Failed to load topology: ' + error.message);
    } finally {
      setLoading(false);
      setShowScanModal(false);
    }
  }, []);

  useEffect(() => {
    async function fetchConfigs() {
      try {
        const res = await listConfigs();
        const confs = res.data?.configs || [];
        setConfigs(confs);
        
        const providers = [...new Set(confs.map(c => c.provider.toUpperCase()))];
        if (providers.length > 0) {
          setAvailableProviders(providers);
          setViewProvider(providers[0]);
        }
      } catch (error) {
        console.error("Failed to load configs", error);
      }
    }
    fetchConfigs();
  }, []);

  useEffect(() => {
    if (configs.length > 0 && viewProvider) {
      const accountsForProvider = configs
        .filter(c => c.provider.toUpperCase() === viewProvider)
        .map(c => c.account_name);
      
      setAvailableAccounts(accountsForProvider);
      if (accountsForProvider.length > 0) {
        setViewAccount(accountsForProvider[0]);
      } else {
        setViewAccount('');
      }
    } else {
      setAvailableAccounts([]);
      setViewAccount('');
    }
  }, [viewProvider, configs]);

  useEffect(() => {
    if (rawTopologyData) {
      setGlobals(rawTopologyData.GlobalResources || null);
    }
  }, [rawTopologyData]);

  useEffect(() => {
    loadData(false);
  }, [loadData]);

  return (
    <div className="flex flex-col h-full w-full bg-[#0a0a0f] text-gray-200 overflow-hidden relative">
      
      {/* Global Page Header */}
      <div className="px-6 py-5 border-b border-[#1e232b] bg-[#0a0a0f] flex items-center justify-between z-30 flex-shrink-0 shadow-sm">
        <div>
          <h1 className="text-2xl font-bold text-[#e4e4e7] tracking-tight">AWS Infrastructure Topology</h1>
          <p className="text-sm text-zinc-500 mt-1">Interactive visual map of your cloud environment</p>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex items-center space-x-4">
            
            <div className="flex items-center space-x-2">
              <label className="text-zinc-500 text-xs uppercase tracking-wider font-medium">Provider:</label>
              <select 
                value={viewProvider} 
                onChange={(e) => setViewProvider(e.target.value)}
                className="bg-[#1a1d24] text-white border border-[#2d333b] rounded-lg py-1.5 px-3 text-xs outline-none focus:border-blue-500 transition-colors"
              >
                {availableProviders.map(p => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center space-x-2">
              <label className="text-zinc-500 text-xs uppercase tracking-wider font-medium">Account:</label>
              <select 
                value={viewAccount} 
                onChange={(e) => setViewAccount(e.target.value)}
                className="bg-[#1a1d24] text-white border border-[#2d333b] rounded-lg py-1.5 px-3 text-xs outline-none focus:border-blue-500 transition-colors"
              >
                {availableAccounts.map(a => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
            </div>

            {availableRegions.length > 0 && (
              <div className="flex items-center space-x-2">
                <label className="text-zinc-500 text-xs uppercase tracking-wider font-medium">Region:</label>
                <select 
                  value={viewRegion} 
                  onChange={(e) => setViewRegion(e.target.value)}
                  className="bg-[#1a1d24] text-white border border-[#2d333b] rounded-lg py-1.5 px-3 text-xs outline-none focus:border-blue-500 transition-colors"
                >
                  {availableRegions.map(r => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div className="h-6 w-px bg-[#2d333b] mx-1"></div>

          <button 
            onClick={() => loadData(false)}
            disabled={loading}
            className="px-4 py-2 bg-[#1a1d24] text-zinc-300 rounded-lg text-xs font-medium hover:bg-[#2d333b] hover:text-white transition-colors border border-[#2d333b]"
          >
            Load Mock Data
          </button>
          <button 
            onClick={() => setShowScanModal(true)}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-500 transition-colors flex items-center gap-2 shadow-lg shadow-blue-900/20"
          >
            {loading ? (
              <>
                <svg className="animate-spin h-3.5 w-3.5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Scanning...
              </>
            ) : (
              'Live Scan'
            )}
          </button>
        </div>
      </div>

      {/* Workspace Area */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Left Sidebar: Infrastructure Tree View */}
        <aside 
          className={`border-r border-[#1e232b] bg-[#0e1015] flex flex-col z-20 shadow-[2px_0_10px_rgba(0,0,0,0.5)] transition-all duration-300 ease-in-out ${
            isSidebarOpen ? 'w-72 translate-x-0' : 'w-0 -translate-x-full opacity-0 overflow-hidden border-none'
          }`}
        >
          <div className="w-72 h-full flex flex-col">
            <InfrastructureTreeView data={rawTopologyData} onNodeSelect={setFocusedNodeId} />
          </div>
        </aside>

        {/* Right Main Area: React Flow Canvas */}
        <main className={`flex flex-col relative transition-all duration-300 ease-in-out flex-1 bg-[#0a0a0f]`}>
          
          {/* Floating Sidebar Toggle on the Canvas */}
          <div className="absolute top-4 left-4 z-10">
            <button 
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-2 text-gray-400 hover:text-white hover:bg-[#2d333b] bg-[#1a1d24]/80 backdrop-blur border border-[#2d333b] rounded-lg transition-colors flex items-center justify-center focus:outline-none shadow-md"
              title={isSidebarOpen ? "Hide Sidebar" : "Show Sidebar"}
            >
              {isSidebarOpen ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
            </button>
          </div>
        
        {showScanModal && (
          <ScanConfigurationModal 
            onClose={() => setShowScanModal(false)}
            onStartScan={(regions) => loadData(true, regions)}
          />
        )}

        <div className="flex-1 relative min-h-0">
          <TopologyDashboard 
            data={rawTopologyData} 
            viewRegion={viewRegion} 
            onNodeClick={(node) => {
              setSelectedNode(node);
              setFocusedNodeId(node.id);
            }} 
          />
          {loading && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#0a0a0f] bg-opacity-80 backdrop-blur-sm">
              <div className="flex flex-col items-center gap-4">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
                <div className="text-white font-medium">Scanning AWS Infrastructure...</div>
              </div>
            </div>
          )}
        </div>
        </main>
      </div>

      {/* Render Modal Outside Flex to overlay everything */}
      {selectedNode && (
        <TopologyDetailModal 
          node={selectedNode} 
          onClose={() => setSelectedNode(null)} 
          globalResources={globals}
        />
      )}
    </div>
  );
}

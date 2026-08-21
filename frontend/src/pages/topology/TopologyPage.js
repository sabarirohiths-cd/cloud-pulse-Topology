import React, { useState, useCallback, useEffect } from 'react';
import { ChevronLeft, ChevronRight, Zap } from 'lucide-react';
import { toast } from 'sonner';
import { getGlowColors } from '../../utils/iconMap';
import { scanTopology, getTopologyByAccount } from '../../api/topology';
import { listConfigs } from '../../api/config';
import TopologyDetailModal from './components/TopologyDetailModal';
import ScanConfigurationModal from './components/ScanConfigurationModal';
import InfrastructureTreeView from './components/InfrastructureTreeView';
import TopologyDashboard from './components/TopologyDashboard';
import { FilterBar } from '../../components/ui/FilterBar';

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
  const [drillDownState, setDrillDownState] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [currentVpcIndex, setCurrentVpcIndex] = useState(0);

  const handleSidebarSelect = (payload) => {
    if (!payload || typeof payload !== 'object') {
      setFocusedNodeId(payload);
      return;
    }
    
    if (payload.drillParent) {
      // It's a VPC resource: auto drill-down and glow, but DON'T open the modal
      setDrillDownState(payload.drillParent);
      setSelectedNode(null);
    } else {
      // It's a Global resource (not on canvas): close drill-down, open the modal
      setDrillDownState(null);
      setSelectedNode(payload.node);
    }
    
    setTimeout(() => {
      setFocusedNodeId({ id: payload.node.id, type: payload.node.data?.type || payload.node.type || 'Unknown' });
    }, 100);
  };

  useEffect(() => {
    setCurrentVpcIndex(0);
    setDrillDownState(null);
    setSelectedNode(null);
  }, [viewRegion]);

  // Reset scroll position when entering/exiting drill-down
  useEffect(() => {
    const container = document.getElementById('dashboard-scroll-container');
    if (container) {
      container.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [drillDownState]);

  // Scroll into view and flash when a node is focused via the sidebar
  useEffect(() => {
    if (focusedNodeId) {
      // Small delay to ensure the DOM has updated (if switching VPCs)
      setTimeout(() => {
        const id = typeof focusedNodeId === 'object' ? focusedNodeId.id : focusedNodeId;
        const type = typeof focusedNodeId === 'object' ? focusedNodeId.type : 'Unknown';
        
        const el = document.getElementById(id);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          
          const [c1, c2] = getGlowColors(type);
          
          el.style.setProperty('--glow-c1', c1);
          el.style.setProperty('--glow-c2', c2);
          el.classList.add('premium-spin-glow');
          
          setTimeout(() => {
            el.classList.remove('premium-spin-glow');
            el.style.removeProperty('--glow-c1');
            el.style.removeProperty('--glow-c2');
            setFocusedNodeId(null);
          }, 2000);
        } else {
          // In case it wasn't found, still reset it so we can try again later
          setFocusedNodeId(null);
        }
      }, 50);
    }
  }, [focusedNodeId, currentVpcIndex]);

  let filteredDataForTree = { GlobalResources: null, Regions: {} };
  if (rawTopologyData) {
    filteredDataForTree.GlobalResources = rawTopologyData.GlobalResources;
    if (rawTopologyData.Regions) {
      let targetRegions = viewRegion === 'ALL' ? Object.values(rawTopologyData.Regions) : (rawTopologyData.Regions[viewRegion] ? [rawTopologyData.Regions[viewRegion]] : []);
      const allVpcs = targetRegions.flat();
      if (allVpcs.length > currentVpcIndex) {
        const activeVpc = allVpcs[currentVpcIndex];
        filteredDataForTree.Regions[viewRegion === 'ALL' ? 'Selected Region' : viewRegion] = [activeVpc];
      }
    }
  }

  const loadData = useCallback(async (isLive = false, regions = ['ap-south-1'], accountToFetch = null) => {
    setLoading(true);
    try {
      const targetAccount = accountToFetch || viewAccount;
      if (!targetAccount && !isLive) {
        setLoading(false);
        return;
      }
      
      const response = isLive 
          ? await scanTopology(targetAccount, regions) 
          : await getTopologyByAccount(targetAccount);
          
      const topologyData = response.data || {};

      const extractedRegions = topologyData.Regions ? Object.keys(topologyData.Regions) : [];
      setAvailableRegions(extractedRegions);
      if (extractedRegions.length > 0) {
        setViewRegion(prev => extractedRegions.includes(prev) ? prev : extractedRegions[0]);
      }

      setRawTopologyData(topologyData);
      if (isLive) {
        toast.success('Live scan complete!');
      }
    } catch (error) {
      toast.error('Failed to load topology: ' + error.message);
    } finally {
      setLoading(false);
      setShowScanModal(false);
    }
  }, [viewAccount]);

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
    // Initial load will just fetch the default account via API
    loadData(false);
  }, [loadData]);

  useEffect(() => {
    if (viewAccount) {
      loadData(false, ['ap-south-1'], viewAccount);
    }
  }, [viewAccount, loadData]);

  return (
    <div className="flex flex-col h-full w-full bg-[#0a0a0f] text-gray-200 overflow-hidden relative">

      {/* Global Page Header */}
      <div className="px-6 py-5 border-b border-[#1e232b] bg-[#0a0a0f] flex flex-col z-30 flex-shrink-0 shadow-sm gap-5">

        {/* Title Row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {viewProvider && (
              <img src={`/${viewProvider.toLowerCase()}-logo.svg`} alt="" className="h-10 w-10 object-contain shrink-0" />
            )}
            <div>
              <h1 className="text-xl font-semibold flex items-center gap-3 text-[#e4e4e7] tracking-tight">
                {viewProvider || 'Cloud'} - Infrastructure Topology ({viewAccount || 'None'})
              </h1>
              <p className="text-[11px] text-[#a1a1aa] mt-1">Interactive visual map of your cloud environment</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={() => setShowScanModal(true)}
              disabled={loading}
              className="flex items-center gap-2 px-3 py-1.5 text-[11px] uppercase tracking-wider font-semibold bg-transparent border border-zinc-700 text-zinc-300 rounded-md hover:bg-zinc-800 disabled:opacity-50 transition-colors"
            >
              {loading ? (
                <svg className="animate-spin h-3 w-3 text-zinc-300" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : (
                <Zap className="h-3 w-3" />
              )}
              {loading ? 'Scanning...' : 'Scan Now'}
            </button>
          </div>
        </div>

        {/* Filter Bar */}
        <FilterBar
          filters={[
            {
              label: "Provider:",
              value: viewProvider,
              onChange: setViewProvider,
              options: availableProviders.map(p => ({ label: p, value: p })),
              width: "max-w-[110px]"
            },
            {
              label: "Account:",
              value: viewAccount,
              onChange: setViewAccount,
              options: availableAccounts.map(a => ({ label: a, value: a })),
              width: "max-w-[150px]"
            },
            ...(availableRegions.length > 0 ? [{
              label: "Region:",
              value: viewRegion,
              onChange: setViewRegion,
              options: availableRegions.map(r => ({ label: r, value: r })),
              width: "max-w-[120px]"
            }] : [])
          ]}
        />
      </div>

      {/* Workspace Area */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Left Sidebar: Infrastructure Tree View */}
        <aside
          className={`bg-[#0e1015] flex flex-col z-20 shadow-[2px_0_10px_rgba(0,0,0,0.5)] transition-all duration-300 ease-[cubic-bezier(0.4,0,0.2,1)] overflow-hidden shrink-0 ${
            isSidebarOpen ? 'w-60 border-r border-[#1e232b]' : 'w-0 border-r-0 border-transparent'
          }`}
        >
          <div className="w-60 h-full flex flex-col">
            <InfrastructureTreeView data={filteredDataForTree} onNodeSelect={handleSidebarSelect} selectedNodeId={selectedNode?.id} />
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
              currentVpcIndex={currentVpcIndex}
              setCurrentVpcIndex={setCurrentVpcIndex}
              drillDownState={drillDownState}
              setDrillDownState={setDrillDownState}
              onNodeClick={(node) => {
                setSelectedNode(node);
              }}
            />
            {loading && (
              <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#0a0a0f] bg-opacity-80 backdrop-blur-sm">
                <div className="flex flex-col items-center gap-4">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-sky-500"></div>
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
          edges={rawTopologyData?.Edges || []}
          onClose={() => setSelectedNode(null)}
          globalResources={globals}
        />
      )}
    </div>
  );
}

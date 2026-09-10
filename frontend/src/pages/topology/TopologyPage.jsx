import React, { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft, ChevronRight, Zap, List, RefreshCw, Activity, Database, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { getComputeResources, scanComputeFlow, getCachedRegions, getLocalComputeFlow, getLocalComputeResources, getLocalTrace, getSupportedComputeTypes, getCachedAccounts, tempResetMockData, tempClearAllTopology } from '../../api/topology';
import { listConfigs } from '../../api/config';
import ResourceDetailModal from './components/ResourceDetailModal';
import ScanConfigurationModal from './components/ScanConfigurationModal';
import ComputeResourcesSidebar from './components/ComputeResourcesSidebar';
import ApplicationFlowVisualizer from './components/ApplicationFlowVisualizer';
import { FilterBar } from '../../components/ui/FilterBar';
import DiagnosticDetailPage from './diagnostics/DiagnosticDetailPage';

export default function TopologyPage() {
  const [loading, setLoading] = useState(false);
  const [tracing, setTracing] = useState(false);

  // Two-Step State
  const [resources, setResources] = useState([]);
  const [flowData, setFlowData] = useState(null); // { nodes, edges }

  const [selectedNode, setSelectedNode] = useState(null);
  const [diagnosticsNodeId, setDiagnosticsNodeId] = useState(null);

  // Available regions dynamically populated from cached files
  const [availableRegions, setAvailableRegions] = useState([]);
  const [cachedAccounts, setCachedAccounts] = useState([]);

  // Selection State
  const [viewRegions, setViewRegions] = useState([]);
  const [viewProvider, setViewProvider] = useState('');
  const [availableProviders, setAvailableProviders] = useState([]);
  const [viewAccount, setViewAccount] = useState('');
  const [availableAccounts, setAvailableAccounts] = useState([]);
  const [configs, setConfigs] = useState([]);

  const [supportedComputeTypes, setSupportedComputeTypes] = useState(['EC2']);
  const [viewComputeType, setViewComputeType] = useState('EC2');

  const [activeResourceId, setActiveResourceId] = useState(null);
  const [focusNodeId, setFocusNodeId] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const [showScanModal, setShowScanModal] = useState(false);

  // Observability State
  const [observabilityOptions, setObservabilityOptions] = useState([]);
  const [lookbackMinutes, setLookbackMinutes] = useState(15);
  const [showDiagnosticsMenu, setShowDiagnosticsMenu] = useState(false);
  
  // Animation state for Diagnostics button
  const [showDiagnosticsLabel, setShowDiagnosticsLabel] = useState(false);

  useEffect(() => {
    if (activeResourceId) {
      setShowDiagnosticsLabel(true);
      const timer = setTimeout(() => {
        setShowDiagnosticsLabel(false);
      }, 2000); 
      return () => clearTimeout(timer);
    }
  }, [activeResourceId]);

  const toggleObservability = (opt) => {
    setObservabilityOptions(prev =>
      prev.includes(opt) ? prev.filter(o => o !== opt) : [...prev, opt]
    );
  };

  const loadRegionsAndAccounts = useCallback(async (preserveView = false) => {
    try {
      const [regions, accounts] = await Promise.all([
        getCachedRegions(viewAccount).catch(() => []),
        getCachedAccounts().catch(() => [])
      ]);
      
      if (regions && regions.length > 0) {
        setAvailableRegions(regions);
        if (!preserveView && (!viewRegions[0] || !regions.includes(viewRegions[0]))) {
          setViewRegions([regions[0]]);
        }
      } else {
        setAvailableRegions([]);
        if (!preserveView && viewRegions.length > 0) {
          setViewRegions([]);
        }
      }
      
      if (accounts && accounts.length > 0) {
        setCachedAccounts(accounts);
      }
    } catch (e) {
      // ignore
    }
  }, [viewRegions, viewAccount]);

  useEffect(() => {
    loadRegionsAndAccounts();
  }, [loadRegionsAndAccounts]);

  useEffect(() => {
    async function loadComputeTypes() {
      try {
        const types = await getSupportedComputeTypes();
        if (types && types.length > 0) {
          setSupportedComputeTypes(types);
          // Default to EC2 if available, otherwise first
          setViewComputeType(types.includes('EC2') ? 'EC2' : types[0]);
        }
      } catch (e) {
        console.warn("Failed to load compute types");
      }
    }
    loadComputeTypes();
  }, []);


  // Load Cloud Configs
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
    let accountNames = [];
    let defaultRegion = null;
    
    if (configs.length > 0 && viewProvider) {
      const accountsForProvider = configs.filter(c => c.provider.toUpperCase() === viewProvider);
      accountNames = accountsForProvider.map(c => c.account_name);
      if (accountsForProvider.length > 0) {
        defaultRegion = accountsForProvider[0].default_region;
      }
    }
    
    // Only merge 'mock-data' from the dynamically discovered accounts
    if (cachedAccounts.length > 0) {
      const validCached = cachedAccounts.filter(a => a === 'mock-data');
      accountNames = [...new Set([...accountNames, ...validCached])];
    }
    
    setAvailableAccounts(accountNames);
    
    if (accountNames.length > 0) {
      if (!accountNames.includes(viewAccount)) {
        setViewAccount(accountNames[0]);
      }
      if (defaultRegion && (!viewRegions[0] || !availableRegions.includes(viewRegions[0]))) {
        setViewRegions([defaultRegion]);
      }
    } else {
      setViewAccount('');
    }
  }, [viewProvider, configs, cachedAccounts, viewAccount, viewRegions, availableRegions]);

  // Step 1: Global Fetch (Load Resources)
  const fetchResources = useCallback(async (regionsToFetch = viewRegions) => {
    if (!viewAccount) return;

    setLoading(true);
    setFlowData(null);
    setActiveResourceId(null);

    try {
      const response = await getComputeResources(viewAccount, regionsToFetch, viewComputeType);
      
      if (response && response.resources) {
        setResources(response.resources);
      } else {
        setResources([]);
      }

      if (response && response.summaries) {
        if (response.summaries.length === 1) {
          const summary = response.summaries[0];
          if (summary.error) {
             if (summary.error.includes("AuthFailure") || summary.error.includes("UnauthorizedOperation") || summary.error.includes("validate the provided access credentials")) {
                toast.error(`Region ${summary.region} blocked: Access Denied`);
             } else {
                toast.error(`Failed scanning ${summary.region}: ${summary.error}`);
             }
          } else if (summary.count === 0) {
             toast.info(`No instances found in ${summary.region}`);
          } else {
             toast.success(`Found ${summary.count} instances in ${summary.region}`);
          }
        } else {
          const hasSuccess = response.summaries.some(s => !s.error && s.count > 0);
          const hasError = response.summaries.some(s => s.error);
          
          let toastFn = toast.info;
          if (hasError && !hasSuccess) toastFn = toast.error;
          else if (hasSuccess) toastFn = toast.success;

          toastFn(
            <div className="flex flex-col gap-1.5 w-full">
              <div className="font-bold text-sm mb-1">Scan completed ({response.summaries.length} regions)</div>
              <ul className="text-xs space-y-2 max-h-40 overflow-y-auto pr-1" style={{ scrollbarWidth: 'thin' }}>
                {response.summaries.map(s => {
                  if (s.error) {
                    let reason = s.error;
                    if (s.error.includes("RequestExpired")) {
                        reason = "AWS Credentials Expired (Update Config)";
                    } else if (s.error.includes("AuthFailure") || s.error.includes("validate the provided access credentials")) {
                        reason = "Opt-In Required / Invalid STS";
                    } else if (s.error.includes("UnauthorizedOperation") || s.error.includes("service control policy")) {
                        reason = "Blocked by AWS Service Control Policy (SCP)";
                    }
                    return (
                      <li key={s.region} className="flex flex-col">
                        <div className="flex justify-between text-red-400 font-medium"><span>{s.region}:</span> <span>Blocked</span></div>
                        <span className="text-[10.5px] text-red-400/80 mt-0.5 leading-snug">{reason}</span>
                      </li>
                    );
                  } else if (s.count === 0) {
                    return <li key={s.region} className="text-blue-400 flex justify-between font-medium"><span>{s.region}:</span> <span>0 instances</span></li>;
                  } else {
                    return <li key={s.region} className="text-emerald-400 flex justify-between font-medium"><span>{s.region}:</span> <span>{s.count} instances</span></li>;
                  }
                })}
              </ul>
            </div>,
            { duration: 7000 }
          );
        }
      }
    } catch (error) {
      toast.error('Failed to load resources: ' + (error.response?.data?.detail || error.message));
      setResources([]);
    } finally {
      setLoading(false);
      setShowScanModal(false);
      loadRegionsAndAccounts(true); // Auto-refresh region and accounts dropdown
    }
  }, [viewAccount, viewRegions, loadRegionsAndAccounts]);

  // Auto-load previously saved trace and resources when region changes or on page load
  useEffect(() => {
    async function loadLocal() {
      if (!viewRegions[0] || !viewAccount) return;
      try {
        const resourcesResponse = await getLocalComputeResources(viewRegions[0], viewComputeType, viewAccount).catch(() => []);

        let traceResponse = null;
        let activeId = null;

        if (resourcesResponse && resourcesResponse.length > 0) {
          setResources(resourcesResponse);
          activeId = resourcesResponse[0].id;
          traceResponse = await getLocalTrace(activeId).catch(() => null);
        } else {
          setResources([]);
        }

        if (traceResponse && traceResponse.nodes && traceResponse.nodes.length > 0) {
          setFlowData({
            ...traceResponse,
            compute_id: activeId
          });
          setActiveResourceId(activeId);
        } else {
          setFlowData(null);
          setActiveResourceId(null);
        }
      } catch (e) {
        setFlowData(null);
        setActiveResourceId(null);
      }
    }
    loadLocal();
  }, [viewRegions, viewComputeType, viewAccount]);

  // Step 2: Deep Trace
  const handleResourceSelect = async (resource, force = false) => {
    if (tracing) return; // Prevent concurrent duplicate fetches
    if (!force && activeResourceId === resource.id) return; // Prevent fetch if already selected

    setFocusNodeId(null);
    setActiveResourceId(resource.id);
    setTracing(true);

    if (!force) {
      try {
        const localTrace = await getLocalTrace(resource.id);
        if (localTrace && localTrace.nodes && localTrace.nodes.length > 0) {
          setFlowData({
            ...localTrace,
            compute_id: resource.id
          });
          setTracing(false);
          return; // Fast cache hit, no need to hit AWS
        }
      } catch (e) {
        // Not in cache, proceed to scan
      }
    }

    try {
      const response = await scanComputeFlow(viewAccount, resource.region || viewRegions[0], viewComputeType, resource.id, observabilityOptions, lookbackMinutes);
      if (response && response.nodes) {
        setFlowData({
          compute_id: resource.id,
          nodes: response.nodes,
          edges: response.edges || []
        });
        toast.success(`Traced flow for ${resource.name || resource.id}`);
      }
    } catch (error) {
      toast.error('Failed to trace flow: ' + (error.response?.data?.detail || error.message));
      setFlowData(null);
    } finally {
      setTracing(false);
    }
  };

  const handleStartScan = (regions) => {
    const targetRegions = regions.length > 0 ? regions : viewRegions;
    setViewRegions(targetRegions);
    fetchResources(targetRegions);
  };

  return (
    <div className="flex flex-col h-full w-full bg-[#0a0a0f] text-gray-200 overflow-hidden relative">

      {/* Global Page Header */}
      <div className="px-6 py-5 border-b border-[#1e232b] bg-[#0a0a0f] flex flex-col z-30 flex-shrink-0 shadow-sm gap-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {viewProvider && (
              <img src={`/${viewProvider.toLowerCase()}-logo.svg`} alt="" className="h-10 w-10 object-contain shrink-0" />
            )}
            <div className="min-w-0">
              <h1 className="text-lg font-semibold flex items-center gap-3 text-[#e4e4e7] tracking-tight whitespace-nowrap truncate">
                {viewProvider || 'Cloud'} - Compute Flow Topology ({viewAccount || 'None'})
              </h1>
              <p className="text-xs text-[#a1a1aa] mt-1">Select a compute resource to trace its end-to-end flow.</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {(() => {
              const hasMockData = availableAccounts.includes('mock-data');
              return (
                <div className="flex flex-col items-center gap-1">
                  <button
                    onClick={async () => {
                      try {
                        toast.loading(`${hasMockData ? "Deleting" : "Inserting"} mock data...`);
                        await tempResetMockData();
                        toast.success(`Mock data ${hasMockData ? "deleted" : "inserted"} successfully!`);
                        window.location.reload();
                      } catch (e) {
                        toast.error(`Failed to ${hasMockData ? "delete" : "insert"} mock data`);
                      }
                    }}
                    title={hasMockData ? "[TEMP] Delete Mock Data" : "[TEMP] Insert Mock Data"}
                    className={`flex items-center justify-center w-8 h-8 rounded-md transition-colors ${
                      hasMockData 
                        ? "bg-red-500/20 text-red-400 border border-red-500/50 hover:bg-red-500/30" 
                        : "bg-orange-500/20 text-orange-400 border border-orange-500/50 hover:bg-orange-500/30"
                    }`}
                  >
                    <Database size={16} />
                  </button>
                  <span className="text-[9px] text-zinc-500 uppercase tracking-wider font-bold">Mock</span>
                </div>
              );
            })()}
            <div className="flex flex-col items-center gap-1">
              <button
                onClick={async () => {
                  if (window.confirm("Are you sure you want to clear ALL topology data? This will not delete your cloud credentials.")) {
                    try {
                      toast.loading("Clearing all topology data...");
                      await tempClearAllTopology();
                      toast.success("All topology data cleared successfully!");
                      window.location.reload();
                    } catch (e) {
                      toast.error("Failed to clear topology data");
                    }
                  }
                }}
                title="[TEMP] Clear All Topology DB"
                className="flex items-center justify-center w-8 h-8 bg-red-500/20 text-red-400 border border-red-500/50 rounded-md hover:bg-red-500/30 transition-colors"
              >
                <Trash2 size={16} />
              </button>
              <span className="text-[9px] text-zinc-500 uppercase tracking-wider font-bold">Clear</span>
            </div>
            <button
              onClick={() => setShowScanModal(true)}
              disabled={loading || !viewAccount}
              className="flex items-center gap-2 px-3 py-1.5 text-xs uppercase tracking-wider font-semibold bg-transparent border border-zinc-700 text-zinc-300 rounded-md hover:bg-zinc-800 disabled:opacity-50 transition-colors"
            >
              <Zap size={14} className={loading ? "animate-pulse text-emerald-400" : "text-emerald-500"} />
              {loading ? "Scanning..." : "Scan Now"}
            </button>
          </div>
        </div>

        {/* Global Filters */}
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
            {
              label: "Region:",
              value: availableRegions.length > 0 ? (viewRegions[0] || availableRegions[0]) : 'None',
              onChange: (val) => {
                if (val !== 'None') setViewRegions([val]);
              },
              options: availableRegions.length > 0 ? availableRegions.map(r => ({ label: r, value: r })) : [{ label: 'No Scanned Regions', value: 'None' }],
              width: "max-w-[150px]"
            },
            {
              label: "Compute Type:",
              value: viewComputeType,
              onChange: setViewComputeType,
              options: supportedComputeTypes.map(t => ({ label: t, value: t })),
              width: "max-w-[130px]"
            }
          ]}
        />
      </div>

      {/* Workspace Area */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Left Sidebar */}
        <aside
          className={`bg-[#0e1015] flex flex-col z-20 shadow-[2px_0_10px_rgba(0,0,0,0.5)] transition-all duration-300 ease-[cubic-bezier(0.4,0,0.2,1)] overflow-hidden shrink-0 ${isSidebarOpen ? 'w-64 border-r border-[#1e232b]' : 'w-0 border-r-0 border-transparent'
            }`}
        >
          <div className="w-64 h-full flex flex-col relative">
            {loading && (
              <div className="absolute inset-0 z-10 bg-[#0e1015]/80 backdrop-blur-sm flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-500"></div>
              </div>
            )}
            <ComputeResourcesSidebar
              data={resources}
              onNodeSelect={handleResourceSelect}
              selectedNodeId={activeResourceId}
              flowData={flowData}
              onNodeFocus={setFocusNodeId}
              onClearTrace={() => {
                setFlowData(null);
                setActiveResourceId(null);
                setFocusNodeId(null);
              }}
              onCloseSidebar={() => setIsSidebarOpen(false)}
            />
          </div>
        </aside>

        {/* Right Main Area */}
        <main className={`flex flex-col relative transition-all duration-300 ease-in-out flex-1 bg-[#0a0a0f]`}>
          <div className="absolute top-4 left-4 z-20 flex flex-col items-start gap-2">
            {!isSidebarOpen && (
              <button
                onClick={() => setIsSidebarOpen(true)}
                className="p-1.5 text-zinc-400 hover:text-white hover:bg-[#2d333b] bg-[#1a1d24]/90 backdrop-blur border border-[#2d333b] rounded transition-colors flex items-center justify-center focus:outline-none shadow-md"
                title="Show Global Resources"
              >
                <List size={16} />
              </button>
            )}

            {activeResourceId && (
              <button
                onClick={() => {
                  setDiagnosticsNodeId(activeResourceId);
                }}
                title="Deep Diagnostics Dashboard"
                className="text-purple-400 hover:text-purple-300 hover:bg-[#2d333b] bg-[#1a1d24]/90 backdrop-blur border border-[#2d333b] rounded transition-colors flex items-center justify-center focus:outline-none shadow-md overflow-hidden"
                style={{ padding: '6px' }}
              >
                <div className="flex items-center">
                  <Activity size={16} />
                  <AnimatePresence>
                    {showDiagnosticsLabel && (
                      <motion.span
                        initial={{ width: 0, opacity: 0, marginLeft: 0 }}
                        animate={{ width: "auto", opacity: 1, marginLeft: 8 }}
                        exit={{ width: 0, opacity: 0, marginLeft: 0 }}
                        className="text-[10px] font-bold uppercase tracking-wider whitespace-nowrap overflow-hidden"
                      >
                        Deep Diagnostics Report
                      </motion.span>
                    )}
                  </AnimatePresence>
                </div>
              </button>
            )}
          </div>

          {activeResourceId && (
            <div className="absolute top-4 right-4 z-20 flex flex-col items-end gap-2">
              <div className="flex items-center gap-1 bg-[#1a1d24]/90 backdrop-blur border border-[#2d333b] rounded p-1 shadow-md">
                <div className="relative">
                  <button
                    onClick={() => setShowDiagnosticsMenu(!showDiagnosticsMenu)}
                    className={`flex items-center gap-1.5 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider rounded transition-colors ${observabilityOptions.length > 0
                        ? 'bg-indigo-500/20 text-indigo-400'
                        : 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200'
                      }`}
                  >
                    Trace Config {observabilityOptions.length > 0 && `(${observabilityOptions.length})`}
                  </button>

                  {showDiagnosticsMenu && (
                    <div className="absolute top-full right-0 mt-2 w-56 bg-[#161b22] border border-zinc-700 rounded shadow-xl z-50 p-3 text-left">
                      <div className="text-[11px] uppercase tracking-wider font-semibold text-zinc-400 mb-2">Diagnostic Tracers</div>

                      <div className="flex flex-col gap-1.5 mb-3">
                        {['INFRASTRUCTURE', 'NETWORK_FLOW', 'METRICS', 'LOGS', 'XRAY'].map(opt => (
                          <label key={opt} className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={observabilityOptions.includes(opt)}
                              onChange={() => toggleObservability(opt)}
                              className="rounded border-zinc-600 bg-[#0e1015] text-indigo-500 focus:ring-indigo-500 w-3 h-3"
                            />
                            <span className="text-[11px] text-zinc-300">{opt}</span>
                          </label>
                        ))}
                      </div>

                      <div className="text-[11px] uppercase tracking-wider font-semibold text-zinc-400 mb-2 mt-2 pt-2 border-t border-zinc-700/50">Lookback Window</div>
                      <select
                        value={lookbackMinutes}
                        onChange={(e) => setLookbackMinutes(Number(e.target.value))}
                        className="w-full bg-[#0e1015] border border-zinc-700 text-zinc-300 text-[11px] rounded px-1.5 py-1 outline-none focus:border-indigo-500"
                      >
                        <option value={15}>15 Minutes</option>
                        <option value={60}>1 Hour</option>
                        <option value={1440}>24 Hours</option>
                        <option value={10080}>7 Days</option>
                      </select>
                    </div>
                  )}
                </div>

                <div className="w-px h-3.5 bg-zinc-700 mx-0.5"></div>

                <button
                  onClick={() => {
                    const res = resources.find(r => r.id === activeResourceId);
                    if (res) handleResourceSelect(res, true);
                  }}
                  disabled={tracing || !viewAccount}
                  title="Re-Run Trace"
                  className="p-1.5 bg-blue-500/10 text-blue-400 rounded hover:bg-blue-500/20 transition-colors"
                >
                  <RefreshCw size={14} className={tracing ? "animate-spin" : ""} />
                </button>
              </div>
            </div>
          )}

          {showScanModal && (
            <ScanConfigurationModal
              onClose={() => setShowScanModal(false)}
              onStartScan={handleStartScan}
              initialRegions={viewRegions}
            />
          )}

          {diagnosticsNodeId && (
            <DiagnosticDetailPage 
              nodeId={diagnosticsNodeId} 
              activeTraceId={activeResourceId}
              onClose={() => setDiagnosticsNodeId(null)} 
            />
          )}


          <div className="flex-1 relative min-h-0">
            {tracing ? (
              <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#0a0a0f]">
                <div className="flex flex-col items-center gap-4">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500"></div>
                  <div className="text-white font-medium animate-pulse">Tracing compute flow architecture...</div>
                </div>
              </div>
            ) : flowData ? (
              <ApplicationFlowVisualizer
                data={flowData}
                focusNodeId={focusNodeId}
                isSidebarOpen={isSidebarOpen}
                onNodeClick={(node) => {
                  setSelectedNode(node);
                }}
              />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center flex-col text-gray-500 gap-4">
                <Zap size={48} className="opacity-20" />
                <p>Select a compute resource from the sidebar to trace its flow.</p>
              </div>
            )}
          </div>
        </main>
      </div>

      {/* Detail Modal */}
      {selectedNode && (
        <ResourceDetailModal
          node={selectedNode}
          edges={flowData?.edges || []}
          allNodes={flowData?.nodes || []}
          onClose={() => setSelectedNode(null)}
          globalResources={null}
          onShowDiagnostics={(id) => {
            setSelectedNode(null);
            setDiagnosticsNodeId(id);
          }}
        />
      )}
    </div>
  );
}

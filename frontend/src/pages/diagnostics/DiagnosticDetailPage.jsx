import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Activity, ShieldAlert, Wifi, Server, Database, CloudRain, AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';
import { getLocalTrace } from '../../api/topology';

export default function DiagnosticDetailPage({ nodeId: propNodeId, onClose }) {
  const params = useParams();
  const navigate = useNavigate();
  const nodeId = propNodeId || params.nodeId;
  const [nodeData, setNodeData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    const fetchTrace = async () => {
      try {
        setLoading(true);
        // We fetch the latest local trace graph to find the node's rich diagnostic_details
        const traceResponse = await getLocalTrace(nodeId);
        if (traceResponse && traceResponse.nodes) {
          const targetNode = traceResponse.nodes.find(n => n.id === nodeId);
          if (targetNode) {
            setNodeData(targetNode);
          } else {
            // fallback: maybe the nodeId passed isn't the root computeId, just a child node.
            // Still we have the whole graph.
            const anyNode = traceResponse.nodes.find(n => n.id === nodeId);
            if (anyNode) setNodeData(anyNode);
            else setError("Node not found in the current trace.");
          }
        } else {
            setError("No trace data found. Please run a deep diagnostic trace from the Topology page first.");
        }
      } catch (err) {
        setError(err.message || "Failed to load trace data.");
      } finally {
        setLoading(false);
      }
    };
    
    if (nodeId) fetchTrace();
  }, [nodeId]);

  const handleClose = () => {
    if (onClose) onClose();
    else navigate(-1);
  };

  if (loading) {
    return (
      <div className="fixed inset-0 z-[9999] bg-black/70 backdrop-blur-sm flex items-center justify-center">
        <div className="bg-[#0a0a0f] border border-zinc-800 rounded-2xl p-12 flex flex-col items-center gap-4 shadow-2xl">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
          <div className="text-zinc-400 font-medium">Loading Diagnostic Data...</div>
        </div>
      </div>
    );
  }

  if (error || !nodeData) {
    return (
      <div className="fixed inset-0 z-[9999] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
        <div className="bg-[#0a0a0f] border border-zinc-800 rounded-2xl p-8 max-w-lg w-full shadow-2xl relative">
          <button onClick={handleClose} className="absolute top-4 right-4 text-zinc-500 hover:text-white transition-colors">
            <X size={20} />
          </button>
          <div className="bg-red-950/20 border border-red-500/30 p-6 rounded-xl flex items-center gap-4 text-red-400">
            <AlertTriangle size={32} />
            <div>
              <h2 className="text-lg font-bold">Failed to Load Diagnostics</h2>
              <p className="text-sm opacity-80 mt-1">{error || "Node not found."}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const details = nodeData.diagnostic_details || {};
  const infra = details.infrastructure || {};
  const network = details.network_flow || {};
  const app = details.application || {};
  
  const healthColor = nodeData.health_state === 'CRITICAL' ? 'text-red-500' : (nodeData.health_state === 'DEGRADED' ? 'text-amber-500' : 'text-emerald-500');

  const getStatusIcon = (status) => {
      if (status === 'HEALTHY') return <CheckCircle2 size={18} className="text-emerald-500" />;
      if (status === 'CRITICAL') return <ShieldAlert size={18} className="text-red-500 animate-pulse" />;
      if (status === 'DEGRADED') return <AlertTriangle size={18} className="text-amber-500" />;
      return <Info size={18} className="text-zinc-500" />;
  };

  return (
    <div className="fixed inset-0 z-[9999] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 md:p-6">
      <div className="bg-[#0a0a0f] text-zinc-200 w-full max-w-[1100px] h-[90vh] rounded-2xl border border-zinc-800 shadow-2xl relative overflow-hidden">
        {/* Header */}
        <div className="absolute top-0 left-0 right-0 h-[74px] bg-[#131315] border-b border-zinc-800/80 p-4 px-6 flex items-center justify-between z-10">
          <div className="flex items-center gap-4">
            <button onClick={handleClose} className="p-1.5 bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-white transition-colors" title="Close Diagnostics">
              <X size={18} />
            </button>
            <div className="w-px h-6 bg-zinc-800 mx-1"></div>
            <div className="p-2 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
              <Activity size={20} className={healthColor} />
            </div>
            <div>
              <h1 className="text-base font-bold flex items-center gap-3">
                Deep Diagnostics Report 
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider border ${nodeData.health_state === 'CRITICAL' ? 'bg-red-500/10 text-red-500 border-red-500/20' : (nodeData.health_state === 'DEGRADED' ? 'bg-amber-500/10 text-amber-500 border-amber-500/20' : 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20')}`}>
                  {nodeData.health_state}
                </span>
              </h1>
              <p className="text-[11px] text-zinc-500 mt-0.5 font-mono">{nodeData.id} • {nodeData.type}</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
              <div className="bg-[#161b22] px-3 py-1.5 rounded-lg border border-zinc-800 flex items-center gap-2">
                  <Activity size={14} className={healthColor} />
                  <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-400">Cloud Pulse</span>
              </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="absolute top-[74px] left-0 right-0 h-[50px] bg-[#131315] border-b border-zinc-800/80 px-6 flex items-center gap-6 z-10">
            <button 
                onClick={() => setActiveTab('overview')}
                className={`h-full px-2 text-xs font-bold uppercase tracking-wider flex items-center gap-2 border-b-2 transition-colors ${activeTab === 'overview' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-zinc-500 hover:text-zinc-300'}`}
            >
                <Activity size={14} />
                Overview
            </button>
            <button 
                onClick={() => setActiveTab('infrastructure')}
                className={`h-full px-2 text-xs font-bold uppercase tracking-wider flex items-center gap-2 border-b-2 transition-colors ${activeTab === 'infrastructure' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-zinc-500 hover:text-zinc-300'}`}
            >
                <Server size={14} />
                Infrastructure
                {infra.status && getStatusIcon(infra.status)}
            </button>
            <button 
                onClick={() => setActiveTab('network')}
                className={`h-full px-2 text-xs font-bold uppercase tracking-wider flex items-center gap-2 border-b-2 transition-colors ${activeTab === 'network' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-zinc-500 hover:text-zinc-300'}`}
            >
                <Wifi size={14} />
                Network Flow
                {network.status && getStatusIcon(network.status)}
            </button>
            <button 
                onClick={() => setActiveTab('application')}
                className={`h-full px-2 text-xs font-bold uppercase tracking-wider flex items-center gap-2 border-b-2 transition-colors ${activeTab === 'application' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-zinc-500 hover:text-zinc-300'}`}
            >
                <CloudRain size={14} />
                Application
                {app.status && getStatusIcon(app.status)}
            </button>
        </div>

        {/* Scrollable Content */}
        <div className="absolute top-[124px] left-0 right-0 bottom-0 overflow-y-auto custom-scrollbar p-5 md:p-6 bg-[#0a0a0f]">
            <div className="flex flex-col gap-5 w-full h-auto">
          
        {(!details || Object.keys(details).length === 0) && (
            <div className="bg-amber-950/20 border border-amber-500/30 p-6 rounded-xl flex items-center gap-4 text-amber-400">
                <Info size={32} />
                <div>
                <h2 className="text-lg font-bold">No Deep Diagnostics Found</h2>
                <p className="text-sm opacity-80 mt-1">This resource has not been scanned with the Deep Diagnostics tracers yet, or the scan returned no detailed layers. Go back and select "Re-Run Trace" with diagnostic options checked.</p>
                </div>
            </div>
        )}

        {/* 0. Overview / Root Cause Synthesis */}
        {activeTab === 'overview' && details.synthesis && (
            <div className="bg-[#131315] border border-indigo-500/30 rounded-xl overflow-hidden shadow-xl animate-in fade-in slide-in-from-bottom-4 duration-300">
                <div className="bg-indigo-950/20 px-5 py-3 border-b border-indigo-500/20 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Activity className="text-indigo-400" size={16} />
                        <h2 className="text-[11px] font-bold uppercase tracking-widest text-indigo-300">Root Cause Synthesis</h2>
                    </div>
                </div>
                <div className="p-6 flex flex-col gap-5">
                    <p className="text-lg font-medium text-zinc-200">
                        {details.synthesis.synthesis_statement}
                    </p>
                    
                    {details.synthesis.error_classification_tags?.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                            {details.synthesis.error_classification_tags.map(tag => (
                                <span key={tag} className="px-2.5 py-1 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded-md text-[10px] font-bold tracking-wider uppercase">
                                    {tag}
                                </span>
                            ))}
                        </div>
                    )}

                    {details.synthesis.why_analysis_reasoning && (
                        <div className="bg-black/30 p-4 rounded-xl border border-zinc-800">
                            <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-2">Analysis Reasoning</h4>
                            <p className="text-sm text-zinc-300 leading-relaxed">{details.synthesis.why_analysis_reasoning}</p>
                        </div>
                    )}

                    {details.synthesis.extracted_code_locations?.length > 0 && (
                        <div className="bg-black/30 p-4 rounded-xl border border-zinc-800">
                            <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-2">Extracted Code Locations</h4>
                            <div className="flex flex-wrap gap-2">
                                {details.synthesis.extracted_code_locations.map(loc => (
                                    <span key={loc} className="font-mono text-[11px] px-2 py-1 bg-red-950/30 text-red-400 border border-red-500/20 rounded">
                                        {loc}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        )}
        
        {activeTab === 'overview' && !details.synthesis && (
            <div className="text-center py-12 text-zinc-500">No synthesis data available for this resource.</div>
        )}

        {/* 1. Infrastructure Layer */}
        {activeTab === 'infrastructure' && infra.status && (
            <div className="bg-[#131315] border border-zinc-800/80 rounded-xl overflow-hidden shadow-xl animate-in fade-in slide-in-from-bottom-4 duration-300">
                <div className="bg-[#1c2128] px-5 py-3 border-b border-zinc-800/80 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Server className="text-blue-400" size={16} />
                        <h2 className="text-[11px] font-bold uppercase tracking-widest text-zinc-300">Infrastructure Pre-Checks</h2>
                    </div>
                    {getStatusIcon(infra.status)}
                </div>
                <div className="p-5 grid grid-cols-1 md:grid-cols-3 gap-5">
                    <div className="col-span-full">
                        <p className="text-xs text-zinc-400 bg-black/20 p-2.5 rounded-lg border border-zinc-800">{infra.summary}</p>
                    </div>
                    
                    {/* EC2 Checks */}
                    <div className="bg-[#0a0a0f] p-3.5 rounded-xl border border-zinc-800/50 flex flex-col gap-3">
                        <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider pb-2 border-b border-zinc-800/80 flex justify-between items-center">
                            AWS Status Checks
                            {getStatusIcon(infra.details?.ec2_status_checks?.summary === "3/3 checks passed" ? 'HEALTHY' : (infra.details?.ec2_status_checks ? 'CRITICAL' : 'UNKNOWN'))}
                        </h3>
                        {infra.details?.ec2_status_checks?.summary ? (
                            <div className="flex flex-col gap-2.5">
                                <div className="flex justify-between items-center text-[11px]">
                                    <span className="text-zinc-400">System</span>
                                    <span className={infra.details.ec2_status_checks.system_status === 'ok' ? 'text-emerald-400 font-mono' : 'text-red-400 font-mono'}>{infra.details.ec2_status_checks.system_status || 'N/A'}</span>
                                </div>
                                <div className="flex justify-between items-center text-[11px]">
                                    <span className="text-zinc-400">Instance</span>
                                    <span className={infra.details.ec2_status_checks.instance_status === 'ok' ? 'text-emerald-400 font-mono' : 'text-red-400 font-mono'}>{infra.details.ec2_status_checks.instance_status || 'N/A'}</span>
                                </div>
                                <div className="flex justify-between items-center text-[11px]">
                                    <span className="text-zinc-400">EBS Vol</span>
                                    <span className={infra.details.ec2_status_checks.ebs_status === 'ok' ? 'text-emerald-400 font-mono' : 'text-red-400 font-mono'}>{infra.details.ec2_status_checks.ebs_status || 'N/A'}</span>
                                </div>
                            </div>
                        ) : <span className="text-[11px] text-zinc-600">No status checks available.</span>}
                    </div>

                    {/* Security Groups */}
                    <div className="bg-[#0a0a0f] p-3.5 rounded-xl border border-zinc-800/50 flex flex-col gap-3">
                        <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider pb-2 border-b border-zinc-800/80 flex justify-between items-center">
                            Security Groups
                            {getStatusIcon('HEALTHY')}
                        </h3>
                        {infra.details?.security_groups?.length > 0 ? (
                            <div className="flex flex-col gap-2">
                                {infra.details.security_groups.map(sg => (
                                    <div key={sg.id} className="text-[11px] flex flex-col gap-1 pb-2 border-b border-zinc-800/50 last:border-0 last:pb-0">
                                        <span className="text-zinc-300 font-mono">{sg.id}</span>
                                        <span className="text-zinc-500">Inbound: <span className="text-emerald-400/70 font-mono">{sg.inbound_rules_count}</span> | Outbound: <span className="text-blue-400/70 font-mono">{sg.outbound_rules_count}</span></span>
                                    </div>
                                ))}
                            </div>
                        ) : <span className="text-[11px] text-zinc-600">No attached Security Groups.</span>}
                    </div>

                    {/* Subnet / Routing */}
                    <div className="bg-[#0a0a0f] p-3.5 rounded-xl border border-zinc-800/50 flex flex-col gap-3">
                        <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider pb-2 border-b border-zinc-800/80 flex justify-between items-center">
                            Subnet & Routing
                            {getStatusIcon(infra.details?.subnet ? 'HEALTHY' : 'UNKNOWN')}
                        </h3>
                        {infra.details?.subnet ? (
                            <div className="flex flex-col gap-2.5 text-[11px]">
                                <div className="flex flex-col gap-0.5">
                                    <span className="text-zinc-500">Subnet</span>
                                    <span className="text-zinc-300 font-mono">{infra.details.subnet.id || 'N/A'}</span>
                                </div>
                                <div className="flex flex-col gap-0.5">
                                    <span className="text-zinc-500">NACL</span>
                                    <span className="text-zinc-300 font-mono">{infra.details.subnet.nacl?.id || 'N/A'}</span>
                                </div>
                                <div className="flex flex-col gap-0.5">
                                    <span className="text-zinc-500">Route Table</span>
                                    <span className="text-zinc-300 font-mono">{infra.details.subnet.route_table?.id || 'N/A'}</span>
                                </div>
                            </div>
                        ) : <span className="text-[11px] text-zinc-600">No Subnet association.</span>}
                    </div>
                </div>
            </div>
        )}
        
        {activeTab === 'infrastructure' && !infra.status && (
            <div className="text-center py-12 text-zinc-500">No Infrastructure diagnostic data available for this resource.</div>
        )}

        {/* 2. Network Flow Layer */}
        {activeTab === 'network' && network.status && (
            <div className="bg-[#131315] border border-zinc-800/80 rounded-xl overflow-hidden shadow-xl animate-in fade-in slide-in-from-bottom-4 duration-300">
                <div className="bg-[#1c2128] px-5 py-3 border-b border-zinc-800/80 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Wifi className="text-purple-400" size={16} />
                        <h2 className="text-[11px] font-bold uppercase tracking-widest text-zinc-300">Network Flow Telemetry</h2>
                    </div>
                    {getStatusIcon(network.status)}
                </div>
                <div className="p-5 flex flex-col gap-4">
                    <p className="text-xs text-zinc-400 bg-black/20 p-2.5 rounded-lg border border-zinc-800">{network.summary}</p>
                    
                    {network.details?.sample_logs && network.details.sample_logs.length > 0 && (
                        <div className="bg-[#0a0a0f] rounded-xl border border-zinc-800/50 overflow-hidden flex flex-col">
                            <div className="px-4 py-2.5 bg-[#161b22] border-b border-zinc-800 flex items-center justify-between">
                                <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Rejected Packets (VPC Flow Logs)</span>
                                {getStatusIcon('CRITICAL')}
                            </div>
                            <div className="p-3 text-[11px] font-mono text-red-400 overflow-x-auto overflow-y-auto max-h-[400px] custom-scrollbar whitespace-pre bg-red-950/5">
                                {network.details.sample_logs.map((log, i) => (
                                    <div key={i} className="mb-1 opacity-90 hover:opacity-100">{log}</div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        )}
        
        {activeTab === 'network' && !network.status && (
            <div className="text-center py-12 text-zinc-500">No Network Flow diagnostic data available. Enable "Flow Logs" option in trace settings.</div>
        )}

        {/* 3. Application Layer */}
        {activeTab === 'application' && app.status && (
            <div className="bg-[#131315] border border-zinc-800/80 rounded-xl overflow-hidden shadow-xl animate-in fade-in slide-in-from-bottom-4 duration-300">
                <div className="bg-[#1c2128] px-5 py-3 border-b border-zinc-800/80 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <CloudRain className="text-emerald-400" size={16} />
                        <h2 className="text-[11px] font-bold uppercase tracking-widest text-zinc-300">Application Telemetry</h2>
                    </div>
                    {getStatusIcon(app.status)}
                </div>
                <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div className="col-span-full">
                        <p className="text-xs text-zinc-400 bg-black/20 p-2.5 rounded-lg border border-zinc-800">{app.summary}</p>
                    </div>

                    {/* Metrics */}
                    {app.details?.metrics && (
                        <div className="bg-[#0a0a0f] p-3.5 rounded-xl border border-zinc-800/50 flex flex-col gap-3">
                            <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider pb-2 border-b border-zinc-800/80 flex justify-between items-center">
                                CloudWatch Metrics
                                {getStatusIcon(app.details.metrics.status)}
                            </h3>
                            <div className="flex justify-between items-center text-[11px]">
                                <span className="text-zinc-400">Max CPU</span>
                                <span className={`font-mono ${app.details.metrics.cpu_max > 80 ? 'text-amber-400' : 'text-zinc-200'}`}>{app.details.metrics.cpu_max?.toFixed(1) || 0}%</span>
                            </div>
                            <div className="flex justify-between items-center text-[11px]">
                                <span className="text-zinc-400">HTTP 5XX Errors</span>
                                <span className={`font-mono ${app.details.metrics.errors_5xx > 0 ? 'text-red-400' : 'text-zinc-200'}`}>{app.details.metrics.errors_5xx || 0}</span>
                            </div>
                        </div>
                    )}

                    {/* X-Ray */}
                    {app.details?.xray && (
                        <div className="bg-[#0a0a0f] p-3.5 rounded-xl border border-zinc-800/50 flex flex-col gap-3">
                            <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider pb-2 border-b border-zinc-800/80 flex justify-between items-center">
                                AWS X-Ray
                                {getStatusIcon(app.details.xray.issues?.length > 0 ? 'DEGRADED' : 'HEALTHY')}
                            </h3>
                            <div className="flex justify-between items-center text-[11px]">
                                <span className="text-zinc-400">Faulty/Slow Traces</span>
                                <span className={`font-mono ${app.details.xray.faulty_trace_count > 0 ? 'text-amber-400' : 'text-zinc-200'}`}>{app.details.xray.faulty_trace_count || 0}</span>
                            </div>
                        </div>
                    )}

                    {/* Logs */}
                    {app.details?.logs && (
                        <div className="col-span-full bg-[#0a0a0f] rounded-xl border border-zinc-800/50 overflow-hidden flex flex-col">
                            <div className="px-4 py-2.5 bg-[#161b22] border-b border-zinc-800 flex items-center justify-between">
                                <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">CloudWatch Logs Insights</span>
                                {getStatusIcon(app.details.logs.issues?.length > 0 ? 'CRITICAL' : 'HEALTHY')}
                            </div>
                            <div className="p-4 text-[11px] font-mono overflow-x-auto overflow-y-auto max-h-[400px] custom-scrollbar whitespace-pre bg-red-950/5">
                                {app.details.logs.traces?.length > 0 ? (
                                    app.details.logs.traces.map((trace, i) => (
                                        <div key={i} className="mb-2 text-red-400 border-l-2 border-red-500/50 pl-3 py-0.5 opacity-90 hover:opacity-100">{trace}</div>
                                    ))
                                ) : (
                                    <span className="text-zinc-600">No error traces found in log group {app.details.logs.log_group}.</span>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        )}
        
        {activeTab === 'application' && !app.status && (
            <div className="text-center py-12 text-zinc-500">No Application diagnostic data available. Enable "Metrics, Logs, or X-Ray" options in trace settings.</div>
        )}

        {/* End of content */}
            </div>
        </div>
      </div>
    </div>
  );
}

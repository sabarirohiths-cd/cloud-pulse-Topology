import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Layers, AlertTriangle, Activity } from 'lucide-react';
import { getIcon, getColorClasses } from '../../../utils/iconMap';

const colorizeJson = (jsonObj) => {
  if (!jsonObj) return '';
  const cleanObj = { ...jsonObj };
  delete cleanObj.label;
  delete cleanObj.type;
  
  const jsonStr = JSON.stringify(cleanObj, null, 2);
  return jsonStr.split('\n').map((line, i) => {
    let coloredLine = line;
    coloredLine = coloredLine.replace(/"([^"]+)":/g, '<span class="text-sky-300">"$1"</span>:');
    coloredLine = coloredLine.replace(/: "([^"]*)"/g, ': <span class="text-zinc-100">"$1"</span>');
    coloredLine = coloredLine.replace(/: (-?\d+\.?\d*)/g, ': <span class="text-emerald-300">$1</span>');
    coloredLine = coloredLine.replace(/: (true|false|null)/g, ': <span class="text-sky-400 font-medium">$1</span>');

    return (
      <div key={i} className="table-row">
        <span className="table-cell text-zinc-600 select-none pr-4 text-right border-r border-zinc-800">{i + 1}</span>
        <span className="table-cell pl-4 break-words whitespace-pre-wrap" dangerouslySetInnerHTML={{ __html: coloredLine }} />
      </div>
    );
  });
};

export default function ResourceDetailModal({ node, edges, allNodes, onClose, globalResources }) {
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    setActiveTab('overview');
  }, [node]);

  React.useEffect(() => {
    const handleWheel = (e) => {
      const container = e.target.closest('.overflow-x-auto');
      if (container) {
        const isScrollable = container.scrollWidth > container.clientWidth;
        if (isScrollable && e.deltaY !== 0) {
          e.preventDefault();
          container.scrollLeft += e.deltaY;
        }
      }
    };

    window.addEventListener('wheel', handleWheel, { passive: false });
    return () => window.removeEventListener('wheel', handleWheel);
  }, []);

  if (!node) return null;
  const data = node.data || {};
  const type = data.type || 'Resource';
  const colors = getColorClasses(type);

  const formatKey = (key) => key.replace(/([A-Z])/g, ' $1').trim();
  
  const renderValue = (key, value) => {
    if (value === null || value === undefined) return <span className="text-gray-500 italic">None</span>;
    if (typeof value === 'boolean') return <span className={value ? "text-green-400" : "text-red-400"}>{value ? 'Yes' : 'No'}</span>;
    
    if (typeof value === 'object') {
      if (Array.isArray(value)) {
        if (value.length === 0) return <span className="text-gray-500 italic">Empty</span>;
        
        if (key === 'InboundRules' || key === 'OutboundRules' || key === 'Routes') {
           return (
              <div className="flex flex-col gap-1.5 mt-2">
                 {value.map((rule, idx) => {
                    const isDeny = String(rule).toLowerCase().includes('deny');
                    const dotColor = isDeny ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]' : (key === 'InboundRules' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]' : key === 'OutboundRules' ? 'bg-sky-500 shadow-[0_0_8px_rgba(14,165,233,0.6)]' : 'bg-purple-500 shadow-[0_0_8px_rgba(168,85,247,0.6)]');
                    return (
                        <div key={idx} className="bg-[#0a0a0f] border border-[#26262b] rounded-lg p-2.5 flex items-center gap-3 hover:border-[#3d444d] transition-colors">
                           <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotColor}`}></div>
                           <span className={`text-[11px] font-mono break-all ${isDeny ? 'text-red-300' : 'text-zinc-300'}`}>{String(rule)}</span>
                        </div>
                    );
                 })}
              </div>
           );
        }

        if (typeof value[0] === 'object' && value[0] !== null) {
          const allKeys = Array.from(new Set(value.flatMap(item => Object.keys(item))));
          const displayKeys = allKeys.filter(k => typeof value[0][k] !== 'object' || Array.isArray(value[0][k]));
          
          return (
            <div className="overflow-x-auto mt-2 border border-[#2d333b] rounded-lg">
              <table className="w-full text-left border-collapse">
                <thead className="bg-[#1c2128]">
                  <tr>
                    {displayKeys.map(k => (
                      <th key={k} className="p-2 text-xs font-semibold text-zinc-400 border-b border-[#2d333b] whitespace-nowrap">{formatKey(k)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-[#161b22]">
                  {value.map((item, idx) => (
                    <tr key={idx} className="border-b border-[#2d333b] last:border-0 hover:bg-[#1c2128] transition-colors">
                      {displayKeys.map(k => (
                        <td key={k} className="p-2 text-xs text-zinc-300">
                          {typeof item[k] === 'object' ? JSON.stringify(item[k]) : String(item[k] ?? '-')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
        
        return (
          <div className="flex flex-wrap gap-2 mt-1">
            {value.map((item, idx) => (
              <span key={idx} className="bg-[#1c2128] px-2 py-1 rounded text-xs border border-[#2d333b] text-zinc-300">
                {String(item)}
              </span>
            ))}
          </div>
        );
      }
      
      return (
        <div className="bg-[#1a1d24] p-2 rounded border border-[#2d333b] text-xs mt-1">
          {Object.entries(value).map(([k, v]) => (
            <div key={k} className="flex flex-col mb-1 last:mb-0">
              <span className="text-gray-400 font-medium">{formatKey(k)}:</span>
              <span className="text-white break-all">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
            </div>
          ))}
        </div>
      );
    }
    return <span className="text-white break-all">{String(value)}</span>;
  };

  const tabs = ['overview', 'flow', 'diagnostics', 'raw json'];

  return createPortal(
    <AnimatePresence>
      {node && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 z-[9999] flex items-center justify-center w-screen h-screen bg-black/70 backdrop-blur-sm"
        >
          <motion.div 
            initial={{ opacity: 0, scale: 0.98, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.98, y: 8 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="bg-[#131315] border border-[#26262b] rounded-xl w-full max-w-[480px] shadow-2xl overflow-hidden flex flex-col h-[700px] max-h-[85vh]"
          >
            <div className="px-4 py-3 bg-[#131315] flex items-center justify-between shrink-0 border-b border-[#26262b]">
              <div className="flex items-center gap-3">
                <div className="bg-[#1c2128] p-2 rounded-lg border border-[#26262b]">
                  {getIcon(type, 24)}
                </div>
                <div>
                  <h2 className="text-[15px] font-bold text-zinc-100 truncate max-w-[350px]">
                    {data.label || 'Resource Details'}
                  </h2>
                  <div className="flex items-center gap-2 mt-1">
                    <p className={`text-[11px] ${colors.text} opacity-90 uppercase tracking-wider font-bold`}>
                      {type}
                    </p>
                    <span className="text-zinc-600 text-[10px]">•</span>
                    <p className={`text-[11px] font-mono tracking-wider ${data.status === 'running' || data.status === 'available' ? 'text-emerald-400' : 'text-amber-400'}`}>
                      {data.status || 'UNKNOWN'}
                    </p>
                  </div>
                </div>
              </div>
              <motion.button 
                whileHover={{ scale: 1.05, backgroundColor: '#26262b' }}
                whileTap={{ scale: 0.95 }}
                onClick={onClose}
                className="p-1.5 text-zinc-500 rounded-md transition-colors"
              >
                <X className="h-5 w-5" />
              </motion.button>
            </div>
            
            <div className="px-4 py-2 border-b border-[#26262b] bg-[#1a1d24] shrink-0">
              <div className="flex items-center gap-1 bg-[#0a0a0f] p-1 rounded-lg w-fit border border-[#26262b]">
                {tabs.map((tab) => (
                  <button 
                    key={tab}
                    onClick={() => setActiveTab(tab)} 
                    className={`px-3 py-1 text-[11px] font-bold rounded-md transition-colors relative z-10 capitalize ${
                      activeTab === tab 
                      ? (tab === 'diagnostics' && ['CRITICAL', 'BLOCKED'].includes(data.health_state)) ? 'text-red-400' : 'text-white' 
                      : (tab === 'diagnostics' && ['CRITICAL', 'BLOCKED'].includes(data.health_state)) ? 'text-red-500/70 hover:text-red-400' : 'text-zinc-500 hover:text-zinc-300'
                    }`}
                  >
                    {activeTab === tab && <motion.div layoutId="detailTab" className="absolute inset-0 bg-[#26262b] rounded-md z-[-1]" />}
                    {tab}
                    {tab === 'diagnostics' && ['CRITICAL', 'BLOCKED'].includes(data.health_state) && (
                      <span className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full animate-ping"></span>
                    )}
                  </button>
                ))}
              </div>
            </div>

            <div className="p-4 overflow-y-auto custom-scrollbar bg-[#0a0a0f] flex-1 min-h-0">
              {activeTab === 'raw json' ? (
                <div 
                  className="border border-[#26262b] rounded-lg shadow-sm bg-[#0a0a0f] overflow-x-auto custom-scrollbar"
                >
                  <div className="p-3 m-0 text-[11px] font-mono table w-full">
                    {colorizeJson(data)}
                  </div>
                </div>
              ) : activeTab === 'diagnostics' ? (
                <div className="flex flex-col gap-3">
                    {['CRITICAL', 'BLOCKED'].includes(data.health_state) ? (
                        <div className="p-4 bg-red-950/20 border border-red-500/30 rounded-xl flex flex-col gap-2">
                            <div className="flex items-center gap-2 text-red-400">
                                <AlertTriangle size={18} className="animate-pulse" />
                                <h3 className="font-bold text-xs uppercase tracking-wider">Root Cause Detected</h3>
                            </div>
                            <p className="text-red-200/90 text-[12px] leading-relaxed border-t border-red-500/20 pt-2">
                                {typeof data.diagnostic === 'object' && data.diagnostic !== null 
                                  ? (data.diagnostic.message || JSON.stringify(data.diagnostic))
                                  : (data.diagnostic || 'Critical system failure detected in this resource.')}
                            </p>
                        </div>
                    ) : (
                        <div className="p-4 bg-emerald-950/20 border border-emerald-500/30 rounded-xl flex flex-col items-center justify-center py-8 gap-2 text-center">
                            <Activity size={28} className="text-emerald-500/50" />
                            <h3 className="font-bold text-xs text-emerald-400 uppercase tracking-wider">System Healthy</h3>
                            <p className="text-emerald-200/70 text-[11px]">No critical issues or blocked connections detected.</p>
                        </div>
                    )}
                    
                    {data.metadata?.status_checks && (
                        <div className="mt-2">
                            <h3 className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest mb-2 flex items-center gap-2">
                                AWS Status Checks
                                <span className="h-px bg-zinc-800 flex-1"></span>
                            </h3>
                            <div className="bg-[#161b22] border border-[#26262b] rounded-xl p-3 flex flex-col gap-3 shadow-sm">
                                <div className="flex items-center justify-between">
                                    <span className="text-[12px] font-bold text-zinc-300">Total Summary</span>
                                    <span className={`text-[11px] font-mono px-2 py-1 rounded-md font-bold ${data.metadata.status_checks.summary.startsWith('3/3') || data.metadata.status_checks.summary.startsWith('2/2') ? 'bg-emerald-900/40 text-emerald-400 border border-emerald-800' : 'bg-red-900/40 text-red-400 border border-red-800'}`}>
                                        {data.metadata.status_checks.summary}
                                    </span>
                                </div>
                                <div className="grid grid-cols-3 gap-2 mt-1">
                                    {[
                                        { label: 'System Check', value: data.metadata.status_checks.system_status },
                                        { label: 'Instance Check', value: data.metadata.status_checks.instance_status },
                                        { label: 'EBS Storage', value: data.metadata.status_checks.ebs_status }
                                    ].map((check, idx) => (
                                        <div key={idx} className="bg-[#0a0a0f] border border-[#2d333b] rounded-lg p-2.5 flex flex-col items-center justify-center text-center gap-2">
                                            <span className="text-[9px] text-zinc-400 uppercase font-bold tracking-wider">{check.label}</span>
                                            <div className="flex items-center gap-1.5">
                                                <div className={`w-1.5 h-1.5 rounded-full ${check.value === 'ok' || check.value === 'passed' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]' : check.value === 'not-applicable' ? 'bg-zinc-500' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]'}`}></div>
                                                <span className={`text-[11px] font-bold uppercase tracking-wider ${check.value === 'ok' || check.value === 'passed' ? 'text-emerald-400' : check.value === 'not-applicable' ? 'text-zinc-400' : 'text-red-400'}`}>
                                                    {check.value || 'N/A'}
                                                </span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
              ) : activeTab === 'flow' ? (
                <div className="flex flex-col gap-4">
                  {(() => {
                    const nodeEdges = edges.filter(e => e.source === node.id || e.target === node.id);
                    if (nodeEdges.length === 0) {
                      return <div className="text-zinc-500 text-xs italic text-center p-4">No connected nodes found in application flow.</div>;
                    }
                    
                    const inboundEdges = nodeEdges.filter(e => e.target === node.id);
                    const outboundEdges = nodeEdges.filter(e => e.source === node.id);

                    const renderEdgeGroup = (title, groupEdges, isInbound) => {
                      if (groupEdges.length === 0) return null;
                      return (
                        <div className="border border-[#2d333b] rounded-lg overflow-hidden bg-[#161b22]">
                          <div className={`p-2 px-3 text-[11px] font-bold uppercase tracking-wider border-b border-[#2d333b] flex items-center justify-between ${isInbound ? 'bg-emerald-900/20 text-emerald-400' : 'bg-blue-900/20 text-blue-400'}`}>
                            {title}
                            <span className="px-1.5 py-0.5 rounded-full bg-[#0a0a0f] text-zinc-400 text-[10px]">{groupEdges.length}</span>
                          </div>
                          <div className="flex flex-col">
                            {groupEdges.map((edge, idx) => {
                              const connectedNodeId = isInbound ? edge.source : edge.target;
                              const connectedNode = allNodes?.find(n => n.id === connectedNodeId);
                              const connectedType = connectedNode?.type || 'RESOURCE';
                              const connectedLabel = connectedNode?.label && connectedNode.label !== connectedNodeId ? `${connectedNode.label} (${connectedNodeId})` : connectedNodeId;
                              const isCriticalEdge = edge.health_state === 'CRITICAL' || edge.health_state === 'BLOCKED';
                              return (
                                <div key={idx} className={`p-3 border-b border-[#2d333b] last:border-0 flex items-center justify-between hover:bg-[#1c2128] transition-colors ${isCriticalEdge ? 'bg-red-950/10' : ''}`}>
                                  <div className="flex flex-col max-w-[65%]">
                                    <div className="flex items-center gap-2 mb-1.5">
                                      <span className="px-1.5 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-[9px] font-bold text-sky-400 uppercase tracking-wider shadow-sm">{connectedType}</span>
                                      <span className="text-xs font-mono text-zinc-300 truncate" title={connectedLabel}>{connectedLabel}</span>
                                    </div>
                                    <span className="text-[10px] text-purple-400 font-bold uppercase tracking-wider">{edge.relation}</span>
                                  </div>
                                  <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase shrink-0 ${isCriticalEdge ? 'bg-red-900/40 text-red-400 border border-red-800' : 'bg-green-900/40 text-green-400 border border-green-800'}`}>
                                    {edge.health_state || 'HEALTHY'}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      );
                    };

                    return (
                      <>
                        {renderEdgeGroup('Incoming (Upstream)', inboundEdges, true)}
                        {renderEdgeGroup('Outgoing (Downstream)', outboundEdges, false)}
                      </>
                    );
                  })()}
                </div>
              ) : (
                <div className="flex flex-col gap-4">
                  {(() => {
                      const containsEdges = edges.filter(e => e.source === node.id && e.relation === 'CONTAINS');
                      if (containsEdges.length === 0) return null;
                      
                      const counts = {};
                      containsEdges.forEach(e => {
                          let prefix = 'RESOURCE';
                          if (e.target.startsWith('subnet-')) prefix = 'SUBNET';
                          else if (e.target.startsWith('vpc-')) prefix = 'VPC';
                          else if (e.target.startsWith('i-')) prefix = 'EC2';
                          else if (e.target.startsWith('vol-')) prefix = 'EBS';
                          else if (e.target.startsWith('igw-')) prefix = 'IGW';
                          else if (e.target.startsWith('nat-')) prefix = 'NAT';
                          else if (e.target.includes('targetgroup')) prefix = 'TARGET GROUP';
                          else if (e.target.includes('loadbalancer')) prefix = 'ALB';
                          
                          counts[prefix] = (counts[prefix] || 0) + 1;
                      });
                      
                      return (
                          <div>
                              <h3 className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest mb-2 flex items-center gap-2">
                                  Contained Resources (Analytics)
                                  <span className="h-px bg-zinc-800 flex-1"></span>
                              </h3>
                              <div className="flex flex-wrap gap-2">
                                  {Object.entries(counts).map(([type, count]) => (
                                      <div key={type} className="bg-purple-900/20 px-3 py-2 rounded-lg border border-purple-500/30 flex items-center gap-2">
                                          <span className="text-[10px] font-bold text-purple-400 uppercase tracking-wider">{type}</span>
                                          <span className="bg-purple-500/20 text-purple-300 text-[10px] px-1.5 py-0.5 rounded-md font-mono">{count}</span>
                                      </div>
                                  ))}
                                  <div className="bg-emerald-900/20 px-3 py-2 rounded-lg border border-emerald-500/30 flex items-center gap-2 ml-auto">
                                      <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">TOTAL CONNECTED</span>
                                      <span className="bg-emerald-500/20 text-emerald-300 text-[10px] px-1.5 py-0.5 rounded-md font-mono">{containsEdges.length}</span>
                                  </div>
                              </div>
                          </div>
                      );
                  })()}
                    
                    {data.Tags && data.Tags.length > 0 && (
                        <div>
                            <h3 className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest mb-2 flex items-center gap-2">
                                Resource Tags
                                <span className="h-px bg-zinc-800 flex-1"></span>
                            </h3>
                            <div className="grid grid-cols-2 gap-2">
                                {data.Tags.map((tag, idx) => (
                                    <div key={idx} className="bg-[#161b22] px-2 py-1.5 rounded-lg border border-[#26262b] flex items-center justify-between">
                                        <span className="text-[9px] font-bold text-zinc-500 uppercase">{tag.Key}</span>
                                        <span className="text-[11px] text-zinc-300 font-medium truncate ml-2" title={tag.Value}>{tag.Value}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                  <div>
                      <h3 className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest mb-2 flex items-center gap-2">
                          Configuration & Networking
                          <span className="h-px bg-zinc-800 flex-1"></span>
                      </h3>
                      <div className="grid grid-cols-2 gap-2">
                        {(() => {
                            const metadata = data.metadata || {};
                            const entries = Object.entries(metadata).filter(([k, v]) => k !== 'status_checks' && v !== null && v !== undefined && v !== '' && !(Array.isArray(v) && v.length === 0));
                            
                            if (entries.length === 0) {
                                return <div className="text-zinc-500 text-xs italic col-span-2">No configuration metadata available.</div>;
                            }
                            
                            return entries.map(([key, value]) => {
                                const isComplex = typeof value === 'object' && value !== null;
                                return (
                                <div key={key} className={`bg-[#161b22] p-3 rounded-xl border border-[#26262b] shadow-sm ${isComplex ? 'col-span-2' : 'col-span-1'}`}>
                                    <label className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold mb-1 block">{formatKey(key)}</label>
                                    <div className="text-[12px] font-bold text-zinc-200">
                                    {renderValue(key, value)}
                                    </div>
                                </div>
                                );
                            })
                        })()}
                      </div>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  );
}

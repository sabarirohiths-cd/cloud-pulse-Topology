import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Layers } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
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

export default function TopologyDetailModal({ node, edges = [], onClose }) {
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    if (node?.data?.type === 'VPC') {
      setActiveTab('analytics');
    } else {
      setActiveTab('overview');
    }
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
        
        if (typeof value[0] === 'object' && value[0] !== null) {
          if (type === 'VPC') {
            return (
              <div className="flex items-center gap-2 mt-1">
                <span className="bg-[#1c2128] px-2 py-1 rounded text-xs border border-[#2d333b] text-purple-400 font-bold">
                  {value.length} Resources
                </span>
                <span className="text-gray-500 text-[10px] italic">View in Dashboard</span>
              </div>
            );
          }
          
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

  const renderVpcAnalytics = () => {
    const vpcData = node.data;
    
    const chartData = [
      { name: 'Subnets', value: vpcData.Subnets?.length || 0, color: '#3b82f6' },
      { name: 'EC2 Instances', value: vpcData.EC2Instances?.length || 0, color: '#f59e0b' },
      { name: 'RDS Clusters', value: vpcData.RDSClusters?.length || 0, color: '#10b981' },
      { name: 'Load Balancers', value: vpcData.LoadBalancers?.length || 0, color: '#8b5cf6' },
      { name: 'Security Groups', value: vpcData.SecurityGroups?.length || 0, color: '#ef4444' },
      { name: 'NAT Gateways', value: vpcData.NatGateways?.length || 0, color: '#06b6d4' },
      { name: 'Internet Gateways', value: vpcData.InternetGateways?.length || 0, color: '#f97316' },
    ].filter(d => d.value > 0);

    if (chartData.length === 0) {
      return <div className="text-zinc-500 text-sm mt-8 text-center italic">No resources found in this VPC.</div>;
    }

    return (
      <div className="flex flex-col h-full bg-[#0e1015]">
        <div className="p-4 border-b border-[#1e232b]">
          <h3 className="text-white font-medium text-sm flex items-center gap-2">
            <Layers className="w-4 h-4 text-purple-400" />
            Resource Distribution Analytics
          </h3>
          <p className="text-xs text-zinc-500 mt-1">A visual breakdown of all resources deployed within {node.data.label}</p>
        </div>
        
        <div className="flex-1 min-h-[350px] p-4 relative">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={80}
                outerRadius={120}
                paddingAngle={4}
                dataKey="value"
                stroke="none"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ backgroundColor: '#161b22', border: '1px solid #2d333b', borderRadius: '8px', color: '#fff' }}
                itemStyle={{ color: '#fff', fontSize: '12px' }}
                labelStyle={{ display: 'none' }}
              />
              <Legend 
                verticalAlign="bottom" 
                height={36} 
                iconType="circle"
                wrapperStyle={{ fontSize: '12px', color: '#a1a1aa' }}
              />
            </PieChart>
          </ResponsiveContainer>
          
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center pointer-events-none mt-[-18px]">
            <span className="text-3xl font-bold text-white tracking-tighter">
              {chartData.reduce((acc, curr) => acc + curr.value, 0)}
            </span>
            <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-semibold">Total</span>
          </div>
        </div>
      </div>
    );
  };

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
            className="bg-[#131315] border border-[#26262b] rounded-xl w-full max-w-[500px] shadow-2xl overflow-hidden flex flex-col h-[650px] max-h-[85vh]"
          >
            <div className="px-4 py-3 bg-[#131315] flex items-center justify-between shrink-0">
              <div className="flex items-center gap-3">
                <div className="bg-[#1c2128] p-2 rounded-lg border border-[#26262b]">
                  {getIcon(type, 20)}
                </div>
                <div>
                  <h2 className="text-[13px] font-bold text-zinc-100 truncate max-w-[300px]">
                    {data.label || 'Resource Details'}
                  </h2>
                  <p className={`text-[11px] ${colors.text} opacity-80 mt-0.5 uppercase tracking-wider font-semibold`}>
                    {type}
                  </p>
                </div>
              </div>
              <motion.button 
                whileHover={{ scale: 1.05, backgroundColor: '#26262b' }}
                whileTap={{ scale: 0.95 }}
                onClick={onClose}
                className="p-1.5 text-zinc-500 rounded-md transition-colors"
              >
                <X className="h-4 w-4" />
              </motion.button>
            </div>

            <div className="px-4 pb-3 border-b border-[#26262b] bg-[#131315] shrink-0">
              <div className="flex items-center gap-1 bg-[#0a0a0f] p-1 rounded-lg w-fit border border-[#26262b]">
                {type === 'VPC' ? ['overview', 'analytics', 'networking', 'connections', 'tags', 'raw json'].map((tab) => (
                  <button 
                    key={tab}
                    onClick={() => setActiveTab(tab)} 
                    className={`px-3 py-1 text-[11px] font-bold rounded-md transition-colors relative z-10 capitalize ${activeTab === tab ? 'text-white' : 'text-zinc-500 hover:text-zinc-300'}`}
                  >
                    {activeTab === tab && <motion.div layoutId="detailTab" className="absolute inset-0 bg-[#26262b] rounded-md z-[-1]" />}
                    {tab}
                  </button>
                )) : ['overview', 'networking', 'connections', 'tags', 'raw json'].map((tab) => (
                  <button 
                    key={tab}
                    onClick={() => setActiveTab(tab)} 
                    className={`px-3 py-1 text-[11px] font-bold rounded-md transition-colors relative z-10 capitalize ${activeTab === tab ? 'text-white' : 'text-zinc-500 hover:text-zinc-300'}`}
                  >
                    {activeTab === tab && <motion.div layoutId="detailTab" className="absolute inset-0 bg-[#26262b] rounded-md z-[-1]" />}
                    {tab}
                  </button>
                ))}
              </div>
            </div>

            <div className="p-4 overflow-y-auto custom-scrollbar bg-[#0a0a0f] flex-1 min-h-0">
              {activeTab === 'analytics' ? renderVpcAnalytics() : activeTab === 'raw json' ? (
                <div 
                  className="border border-[#26262b] rounded-lg shadow-sm bg-[#0a0a0f] overflow-x-auto custom-scrollbar"
                  onWheel={(e) => {
                    if (e.currentTarget.scrollWidth > e.currentTarget.clientWidth) {
                      e.currentTarget.scrollLeft += e.deltaY;
                    }
                  }}
                >
                  <div className="p-4 m-0 text-[11px] font-mono table w-full">
                    {colorizeJson(data)}
                  </div>
                </div>
              ) : activeTab === 'tags' ? (
                <div className="grid grid-cols-1 gap-3">
                  {!data.Tags || data.Tags.length === 0 ? (
                    <div className="text-zinc-500 text-sm italic">No tags assigned to this resource.</div>
                  ) : (
                    data.Tags.map((tag, idx) => (
                      <div key={idx} className="bg-[#161b22] px-4 py-3 rounded-xl border border-[#26262b] shadow-sm flex items-center justify-between">
                        <span className="text-[11px] font-bold text-zinc-400">{tag.Key}</span>
                        <span className="text-[12px] text-zinc-100">{tag.Value}</span>
                      </div>
                    ))
                  )}

                </div>
              ) : activeTab === 'connections' ? (
                <div 
                  className="overflow-x-auto custom-scrollbar border border-[#2d333b] rounded-lg"
                  onWheel={(e) => {
                    if (e.currentTarget.scrollWidth > e.currentTarget.clientWidth) {
                      e.currentTarget.scrollLeft += e.deltaY;
                    }
                  }}
                >
                  <table className="w-full text-left border-collapse">
                    <thead className="bg-[#1c2128]">
                      <tr>
                        <th className="p-2 text-xs font-semibold text-zinc-400 border-b border-[#2d333b]">Direction</th>
                        <th className="p-2 text-xs font-semibold text-zinc-400 border-b border-[#2d333b]">Connected Node ID</th>
                        <th className="p-2 text-xs font-semibold text-zinc-400 border-b border-[#2d333b]">Connection Type</th>
                      </tr>
                    </thead>
                    <tbody className="bg-[#161b22]">
                      {edges.filter(e => e.source === node.id || e.target === node.id).map((edge, idx) => {
                        const isOutbound = edge.source === node.id;
                        return (
                          <tr key={idx} className="border-b border-[#2d333b] last:border-0 hover:bg-[#1c2128] transition-colors">
                            <td className="p-2 text-xs">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${isOutbound ? 'bg-blue-900/40 text-blue-400 border border-blue-800' : 'bg-emerald-900/40 text-emerald-400 border border-emerald-800'}`}>
                                {isOutbound ? 'OUTBOUND' : 'INBOUND'}
                              </span>
                            </td>
                            <td className="p-2 text-xs font-mono text-zinc-300">{isOutbound ? edge.target : edge.source}</td>
                            <td className="p-2 text-xs text-purple-400">{edge.type}</td>
                          </tr>
                        );
                      })}
                      {edges.filter(e => e.source === node.id || e.target === node.id).length === 0 && (
                        <tr>
                          <td colSpan="3" className="p-4 text-xs text-zinc-500 text-center italic">No connected nodes found in graph flow.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  {(() => {
                    const networkingKeys = ['VpcId', 'SubnetId', 'PrivateIpAddress', 'PublicIpAddress', 'CidrBlock', 'SecurityGroups', 'NetworkInterfaces', 'MacAddress', 'IpAddress', 'Port', 'Endpoint', 'VpcSecurityGroups', 'SubnetIds', 'AvailabilityZones'];
                    
                    return Object.entries(data)
                      .filter(([key, value]) => {
                        if (['label', 'type', 'Id', 'Tags'].includes(key)) return false;
                        if (value === null || value === undefined || value === '') return false;
                        if (Array.isArray(value) && value.length === 0) return false;
                        
                        const isNetworking = networkingKeys.some(nk => key.includes(nk) || nk.includes(key));
                        if (activeTab === 'networking' && !isNetworking) return false;
                        if (activeTab === 'overview' && isNetworking) return false;
                        return true;
                      })
                      .map(([key, value]) => {
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
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  );
}

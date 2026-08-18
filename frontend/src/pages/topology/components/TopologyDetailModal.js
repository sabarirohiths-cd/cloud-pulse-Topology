import React from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Server, Database, Zap, Activity, Cloud, Network } from 'lucide-react';
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

export default function TopologyDetailModal({ node, onClose }) {
  const [activeTab, setActiveTab] = React.useState('overview');

  React.useEffect(() => {
    if (node) setActiveTab('overview');
  }, [node]);

  if (!node) return null;
  const data = node.data || {};
  const type = data.type || 'Resource';
  const colors = getColorClasses(type);

  const formatKey = (key) => key.replace(/([A-Z])/g, ' $1').trim();
  
  const getLayer = (key) => {
    if (['Subnets', 'RouteTables', 'InternetGateways', 'NatGateways', 'TransitGatewayAttachments', 'CustomerGateways', 'VpnConnections'].includes(key)) return 'Network & Edge Layer';
    if (['RDSInstances', 'ElastiCacheNodes', 'DynamoDBTables', 'RedshiftClusters', 'NeptuneClusters'].includes(key)) return 'Data Layer';
    if (['SecurityGroups', 'NetworkAcls', 'NetworkFirewalls'].includes(key)) return 'Security Layer';
    if (['Name', 'CidrBlock', 'State', 'IsDefault', 'InstanceTenancy', 'DhcpOptionsId'].includes(key)) return 'VPC Configuration';
    return 'Other Resources';
  };
  
  
  const renderValue = (key, value) => {
    if (value === null || value === undefined) return <span className="text-gray-500 italic">None</span>;
    if (typeof value === 'boolean') return <span className={value ? "text-green-400" : "text-red-400"}>{value ? 'Yes' : 'No'}</span>;
    
    if (typeof value === 'object') {
      // Arrays
      if (Array.isArray(value)) {
        if (value.length === 0) return <span className="text-gray-500 italic">Empty</span>;
        
        // If it's an array of objects (like SecurityGroups, Rules, Subnets)
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
          
          // Render as a table for everything else
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
        
        // Array of primitives (Strings, numbers)
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
      
      // Standard Object Map
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
                <button 
                  onClick={() => setActiveTab('overview')} 
                  className={`px-3 py-1 text-[11px] font-bold rounded-md transition-colors relative z-10 ${activeTab === 'overview' ? 'text-white' : 'text-zinc-500 hover:text-zinc-300'}`}
                >
                  {activeTab === 'overview' && <motion.div layoutId="detailTab" className="absolute inset-0 bg-[#26262b] rounded-md z-[-1]" />}
                  Overview
                </button>
                <button 
                  onClick={() => setActiveTab('json')} 
                  className={`px-3 py-1 text-[11px] font-bold rounded-md transition-colors relative z-10 ${activeTab === 'json' ? 'text-white' : 'text-zinc-500 hover:text-zinc-300'}`}
                >
                  {activeTab === 'json' && <motion.div layoutId="detailTab" className="absolute inset-0 bg-[#26262b] rounded-md z-[-1]" />}
                  Raw JSON
                </button>
              </div>
            </div>

            <div className="p-4 overflow-y-auto bg-[#0a0a0f] flex-1 min-h-0">
              {activeTab === 'overview' ? (
                <div className="grid grid-cols-2 gap-3">
                  {type === 'VPC' ? (
                    (() => {
                      const layers = {};
                      Object.entries(data).forEach(([key, value]) => {
                        if (['label', 'type', 'Id', 'VpcId', 'SubnetId', 'Tags'].includes(key)) return;
                        if (value === null || value === undefined || value === '') return;
                        if (Array.isArray(value) && value.length === 0) return;
                        
                        const layerName = getLayer(key);
                        if (!layers[layerName]) layers[layerName] = [];
                        layers[layerName].push({ key, value });
                      });
                      
                      return Object.entries(layers)
                        .sort(([a], [b]) => a.localeCompare(b))
                        .map(([layerName, items]) => (
                          <div key={layerName} className="col-span-2 mb-2">
                            <h3 className="text-purple-400 text-[11px] uppercase tracking-wider font-bold mb-3 border-b border-zinc-800 pb-1">{layerName}</h3>
                            <div className="grid grid-cols-2 gap-3">
                              {items.map(({key, value}) => {
                                const isComplex = typeof value === 'object' && value !== null;
                                return (
                                  <div key={key} className={`bg-[#161b22] p-3 rounded-xl border border-[#26262b] shadow-sm ${isComplex ? 'col-span-2' : 'col-span-1'}`}>
                                    <label className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold mb-1 block">{formatKey(key)}</label>
                                    <div className="text-[12px] font-bold text-zinc-200">
                                      {renderValue(key, value)}
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                      ));
                    })()
                  ) : (
                    Object.entries(data)
                      .filter(([key, value]) => {
                        if (['label', 'type', 'Id', 'VpcId', 'SubnetId'].includes(key)) return false;
                        if (value === null || value === undefined || value === '') return false;
                        if (Array.isArray(value) && value.length === 0) return false;
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
                  )}
                </div>
              ) : (
                <div className="border border-[#26262b] rounded-lg shadow-sm bg-[#0a0a0f]">
                  <div className="p-4 m-0 text-[11px] font-mono table w-full">
                    {colorizeJson(data)}
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

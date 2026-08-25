import React, { useState } from 'react';
import { getIcon } from '../../../utils/iconMap';
import { Search, Server, ChevronRight, ChevronDown, Globe } from 'lucide-react';

const TreeNode = ({ label, id, type, icon, children, onNodeClick, isSelected = false, defaultExpanded = true, rightElement }) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const hasChildren = children && children.length > 0;

  const handleClick = (e) => {
    e.stopPropagation();
    if (hasChildren) {
      setIsExpanded(!isExpanded);
    }
    if (onNodeClick) {
      onNodeClick(id);
    }
  };

  return (
    <div className="select-none">
      <div
        onClick={handleClick}
        className={`flex items-center gap-2 py-1 px-1.5 rounded cursor-pointer transition-all ${
            isSelected 
              ? 'bg-sky-500/30 ring-1 ring-sky-400 text-sky-300 font-bold shadow-[0_0_8px_rgba(14,165,233,0.3)]' 
              : 'hover:bg-[#1f242e] text-zinc-400 hover:text-sky-300'
        }`}
        title={`Click to focus on ${label || id}`}
      >
        <div className="w-4 h-4 flex items-center justify-center flex-shrink-0 text-zinc-500">
          {hasChildren ? (
            isExpanded ? <ChevronDown size={14} className="hover:text-white" /> : <ChevronRight size={14} className="hover:text-white" />
          ) : null}
        </div>

        <div className="flex items-center justify-center flex-shrink-0 w-4 h-4">
          {icon || getIcon(type, 14)}
        </div>

        <div className="flex flex-col flex-1 overflow-hidden justify-center gap-0.5">
          <span className="text-[13px] font-medium truncate leading-tight text-zinc-200">
            {label}
          </span>
          {type && (
            <span className="text-[10px] font-bold uppercase tracking-wider text-sky-400">
                {type}
            </span>
          )}
        </div>
        
        {rightElement && (
            <div className="flex-shrink-0 ml-2">
                {rightElement}
            </div>
        )}
      </div>

      {hasChildren && isExpanded && (
        <div className="ml-4 pl-2 border-l border-[#2d333b] mt-0.5 flex flex-col gap-0.5">
          {children.map((child, index) => (
            <React.Fragment key={`${child.id}-${index}`}>
              {child.node}
            </React.Fragment>
          ))}
        </div>
      )}
    </div>
  );
};

export default function ComputeResourcesSidebar({ data, onNodeSelect, selectedNodeId, flowData, onNodeFocus }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedRoots, setExpandedRoots] = useState({});
  
  if (!data || !Array.isArray(data)) {
    return (
      <div className="p-4 w-full h-full text-gray-300 flex flex-col">
        <h3 className="font-semibold text-white mb-4 uppercase tracking-wider text-[11px] border-b border-[#2d333b] pb-2">
          Global Resources
        </h3>
        <div className="text-sm italic text-gray-500 bg-[#1a1d24] p-3 rounded border border-[#2d333b]">
          No resources available. Run a scan to populate the list.
        </div>
      </div>
    );
  }

  const filteredResources = data.filter(res => {
    const term = searchTerm.toLowerCase();
    return (
      (res.name && res.name.toLowerCase().includes(term)) ||
      (res.id && res.id.toLowerCase().includes(term))
    );
  });



  // Flat Trace List
  const buildTraceTreeElements = (selectedId) => {
    if (!flowData || !flowData.nodes || flowData.nodes.length === 0 || flowData.compute_id !== selectedId) return null;

    // Filter out the selected instance itself to avoid duplicating it in the sub-list
    const nodes = flowData.nodes.filter(n => n.id !== selectedId);
    const edges = flowData.edges || [];
    
    // Dynamic Topological Sorting (Layer computation)
    // We calculate the "depth" of each node based on relations (e.g. CONTAINS, PROTECTS)
    const adj = {};
    const inDegree = {};
    
    flowData.nodes.forEach(n => {
        adj[n.id] = [];
        inDegree[n.id] = 0;
    });
    
    edges.forEach(e => {
        if (adj[e.source] && inDegree[e.target] !== undefined) {
            adj[e.source].push(e.target);
            inDegree[e.target]++;
        }
    });
    
    const depths = {};
    flowData.nodes.forEach(n => { depths[n.id] = 0; });
    
    const queue = [];
    flowData.nodes.forEach(n => {
        if (inDegree[n.id] === 0) queue.push(n.id);
    });
    
    while (queue.length > 0) {
        const current = queue.shift();
        const currentDepth = depths[current];
        
        adj[current].forEach(neighbor => {
            if (currentDepth + 1 > depths[neighbor]) {
                depths[neighbor] = currentDepth + 1;
            }
            inDegree[neighbor]--;
            if (inDegree[neighbor] === 0) {
                queue.push(neighbor);
            }
        });
    }
    
    // Sort nodes dynamically by their computed layer depth in the graph architecture
    const sortedNodes = [...nodes].sort((a, b) => {
        const depthA = depths[a.id] || 0;
        const depthB = depths[b.id] || 0;
        
        if (depthA !== depthB) {
            return depthA - depthB;
        }
        
        // Alphabetical fallback for items in the same layer
        return (a.label || a.id).localeCompare(b.label || b.id);
    });
    
    return (
        <div className="mt-0.5 flex flex-col gap-0 pb-1 ml-2 border-l border-[#2d333b] pl-1">
            {sortedNodes.map(node => (
                <TreeNode 
                    key={node.id}
                    label={node.label || node.id} 
                    id={node.id} 
                    type={node.type}
                    onNodeClick={() => onNodeFocus && onNodeFocus(node.id)}
                    children={[]} // No nested subfolders inside subfolders
                />
            ))}
        </div>
    );
  };

  return (
    <div className="p-3 w-full h-full text-gray-300 flex flex-col">
      <div className="px-1 mb-3 shrink-0">
        <h3 className="font-semibold text-white mb-3 uppercase tracking-wider text-[11px] border-b border-[#2d333b] pb-2 flex-shrink-0">
          Global Resources
        </h3>
        <div className="relative">
          <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            placeholder="Search by ID or Name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#1a1d24] border border-[#2d333b] rounded py-1.5 pl-8 pr-2 text-xs text-white focus:outline-none focus:border-sky-500 transition-colors"
          />
        </div>
      </div>
      <div className="overflow-y-auto flex-1 pr-2 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-zinc-700/50 hover:[&::-webkit-scrollbar-thumb]:bg-zinc-600 [&::-webkit-scrollbar-thumb]:rounded-full transition-colors">
        <div className="flex flex-col gap-1.5">
          {filteredResources.length === 0 ? (
            <div className="text-xs text-gray-500 p-2">No resources match your search.</div>
          ) : (
            filteredResources.map((res) => {
              const isSelected = selectedNodeId === res.id;
              const isRunning = res.state === 'running';
              
              return (
                <div key={res.id} className="flex flex-col">
                  <div
                    onClick={() => {
                        if (selectedNodeId !== res.id) {
                            onNodeSelect(res);
                            setExpandedRoots(prev => ({ ...prev, [res.id]: true }));
                        } else {
                            setExpandedRoots(prev => ({ ...prev, [res.id]: !prev[res.id] }));
                        }
                    }}
                    className={`flex items-center justify-between p-2 rounded cursor-pointer transition-all border ${
                      isSelected
                        ? 'bg-sky-500/10 border-sky-500/30 text-sky-100 shadow-[0_0_10px_rgba(14,165,233,0.1)]'
                        : 'bg-[#161a22] border-[#2d333b] text-gray-300 hover:bg-[#1f242e] hover:border-[#3d444d]'
                    }`}
                  >
                    <div className="flex items-center gap-2 overflow-hidden">
                      <div className="flex items-center justify-center text-zinc-500 hover:text-white transition-colors">
                        {isSelected && expandedRoots[res.id] ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      </div>
                      <div className={`p-1.5 rounded bg-black/40 ${isSelected ? 'text-sky-400' : 'text-gray-400'}`}>
                        <Server size={14} />
                      </div>
                      <div className="flex flex-col overflow-hidden">
                        <span className="text-[13px] font-medium truncate">
                          {res.name || res.id}
                        </span>
                        {res.name && (
                          <span className="text-[10px] text-gray-500 font-mono truncate">
                            {res.id}
                          </span>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex items-center justify-center pl-2 shrink-0 gap-3">
                      <div 
                        className={`h-2 w-2 rounded-full ${isRunning ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-red-500'}`}
                        title={`State: ${res.state}`}
                      />
                    </div>
                  </div>
                  
                  {isSelected && expandedRoots[res.id] && buildTraceTreeElements(res.id)}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}


import React, { useState } from 'react';
import { getIcon } from '../../../utils/iconMap';
import { getResourceId, getResourceLabel } from '../../../utils/resourceUtils';
import {
  ChevronRight,
  ChevronDown,
  FolderOpen,
  Globe,
  Search
} from 'lucide-react';

// Recursive Tree Node Component
const TreeNode = ({ label, id, icon, children, onNodeSelect, defaultExpanded = false, isResource = false, fullNodeData, forceExpand, selectedNodeId }) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  
  React.useEffect(() => {
    if (forceExpand) setIsExpanded(true);
  }, [forceExpand]);

  const hasChildren = children && children.length > 0;
  const isSelected = selectedNodeId && selectedNodeId === id;

  const handleClick = (e) => {
    e.stopPropagation();
    if (hasChildren && !isResource) {
      setIsExpanded(!isExpanded);
    }
    if (isResource && onNodeSelect && fullNodeData) {
      onNodeSelect(fullNodeData);
    } else if (isResource && onNodeSelect && id) {
      onNodeSelect(id);
    }
  };

  return (
    <div className="select-none">
      <div
        onClick={handleClick}
        className={`flex items-center gap-2 py-1.5 px-2 rounded cursor-pointer transition-all ${
            isSelected 
              ? 'bg-sky-500/30 ring-1 ring-sky-400 text-sky-300 font-bold shadow-[0_0_8px_rgba(14,165,233,0.3)]' 
              : isResource 
                ? 'hover:bg-[#2d333b] text-gray-300' 
                : 'hover:bg-[#1a1d24] text-gray-200 font-medium'
          }`}
      >
        <div className="w-4 h-4 flex items-center justify-center flex-shrink-0 text-gray-500">
          {hasChildren && !isResource ? (
            isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />
          ) : null}
        </div>

        {icon && <div className="flex items-center justify-center flex-shrink-0 w-4 h-4">{icon}</div>}

        <span className={`text-sm truncate leading-tight ${isResource && !isSelected ? 'opacity-90' : ''}`}>
          {label}
        </span>
      </div>

      {hasChildren && isExpanded && (
        <div className="ml-4 pl-2 border-l border-[#2d333b] mt-1 flex flex-col gap-0.5">
          {children.map((child, index) => (
            <React.Fragment key={`${child.id || child.label}-${index}`}>
              {child.node}
            </React.Fragment>
          ))}
        </div>
      )}
    </div>
  );
};

export default function InfrastructureTreeView({ data, onNodeSelect, selectedNodeId }) {
  const [searchTerm, setSearchTerm] = useState('');
  if (!data || (!data.Regions && !data.GlobalResources)) {
    return (
      <div className="p-4 w-full h-full text-gray-300">
        <h3 className="font-semibold text-white mb-4 uppercase tracking-wider text-xs border-b border-[#2d333b] pb-2">
          Infrastructure Explorer
        </h3>
        <div className="text-sm italic text-gray-500 bg-[#1a1d24] p-3 rounded border border-[#2d333b]">
          No infrastructure data available. Run a scan to populate the tree.
        </div>
      </div>
    );
  }

  // Parse Global Resources
  const renderGlobalResources = () => {
    if (!data.GlobalResources) return null;
    const globalGroups = Object.keys(data.GlobalResources).filter(k => data.GlobalResources[k].length > 0);
    if (globalGroups.length === 0) return null;

    const children = globalGroups.map(key => {
      const resources = data.GlobalResources[key];
      const resourceNodes = resources.map(res => {
        const id = getResourceId(res, key);
        const name = getResourceLabel(res, key);
        
        const term = searchTerm.toLowerCase();
        if (searchTerm && !name.toLowerCase().includes(term) && !id.toLowerCase().includes(term) && !key.toLowerCase().includes(term)) return null;

        return {
          id,
          node: <TreeNode 
                  label={name} 
                  id={id} 
                  isResource={true} 
                  icon={getIcon(key)} 
                  onNodeSelect={onNodeSelect} 
                  selectedNodeId={selectedNodeId}
                  forceExpand={!!searchTerm}
                  fullNodeData={{
                    drillParent: null,
                    node: { id, data: { label: name, type: key.replace(/s$/, ''), ...res } }
                  }}
                />
        };
      }).filter(Boolean);

      if (searchTerm && resourceNodes.length === 0) return null;

      return {
        label: key,
        node: <TreeNode label={key} icon={<FolderOpen size={14} className="text-yellow-500" />} children={resourceNodes} forceExpand={!!searchTerm} selectedNodeId={selectedNodeId} />
      };
    }).filter(Boolean);

    if (children.length === 0) return null;

    return <TreeNode label="Global Resources" icon={<Globe size={14} className="text-sky-300" />} defaultExpanded={true} children={children} forceExpand={!!searchTerm} selectedNodeId={selectedNodeId} />;
  };

  // Parse Regions and VPCs
  const renderRegions = () => {
    if (!data.Regions) return null;
    return Object.keys(data.Regions).map(regionName => {
      const vpcs = data.Regions[regionName] || [];

      const vpcChildren = vpcs.map(vpc => {
        const vpcId = vpc.VpcId || 'Unknown VPC';
        const vpcName = vpc.Name || vpcId;

        // 1. VPC Level Configurations (Security Groups, IGWs, Route Tables)
        const vpcConfigKeys = Object.keys(vpc).filter(k => Array.isArray(vpc[k]) && k !== 'Subnets' && vpc[k].length > 0);
        const configNodes = vpcConfigKeys.map(key => {
          const resNodes = vpc[key].map(res => {
            const id = getResourceId(res, key);
            const name = getResourceLabel(res, key);
            
            const term = searchTerm.toLowerCase();
            if (searchTerm && !name.toLowerCase().includes(term) && !id.toLowerCase().includes(term) && !key.toLowerCase().includes(term)) return null;
            return {
              id,
              node: <TreeNode 
                      label={name} 
                      id={id} 
                      isResource={true} 
                      icon={getIcon(key)} 
                      onNodeSelect={onNodeSelect} 
                      selectedNodeId={selectedNodeId}
                      forceExpand={!!searchTerm}
                      fullNodeData={{
                        drillParent: { type: key, title: key, drillData: vpc[key] },
                        node: { id, data: { label: name, type: key.replace(/s$/, ''), ...res } }
                      }}
                    />
            };
          }).filter(Boolean);
          if (searchTerm && resNodes.length === 0) return null;
          return {
            label: key,
            node: <TreeNode label={key} icon={<FolderOpen size={14} className="text-yellow-600" />} children={resNodes} forceExpand={!!searchTerm} selectedNodeId={selectedNodeId} />
          };
        }).filter(Boolean);

        // 2. Subnets and their contained resources
        const subnets = vpc.Subnets || [];
        const subnetNodes = subnets.map(subnet => {
          const subnetId = subnet.SubnetId || 'Unknown Subnet';
          const subnetResKeys = Object.keys(subnet).filter(k => Array.isArray(subnet[k]) && subnet[k].length > 0);
          
          const resNodes = subnetResKeys.map(key => {
            const leafNodes = subnet[key].map(res => {
              const id = getResourceId(res, key);
              const name = res.Name || res.GroupName || res.AutoScalingGroupName || res.ClusterName || res.InstanceId || res.DBInstanceIdentifier || res.CacheClusterId || id;
              
              const term = searchTerm.toLowerCase();
              if (searchTerm && !name.toLowerCase().includes(term) && !id.toLowerCase().includes(term) && !key.toLowerCase().includes(term)) return null;
              return {
                id,
                node: <TreeNode 
                        label={name} 
                        id={id} 
                        isResource={true} 
                        icon={getIcon(key)} 
                        onNodeSelect={onNodeSelect} 
                        selectedNodeId={selectedNodeId}
                        forceExpand={!!searchTerm}
                        fullNodeData={{
                          drillParent: { type: 'Subnet', title: subnet.Name || subnetId, drillData: subnet },
                          node: { id, data: { label: name, type: key.replace(/s$/, ''), ...res } }
                        }}
                      />
              };
            }).filter(Boolean);
            if (searchTerm && leafNodes.length === 0) return null;
            return {
              label: key,
              node: <TreeNode label={key} icon={<FolderOpen size={14} className="text-yellow-500" />} children={leafNodes} forceExpand={!!searchTerm} selectedNodeId={selectedNodeId} />
            };
          }).filter(Boolean);

          const subnetNameMatches = (subnet.Name || subnetId).toLowerCase().includes(searchTerm.toLowerCase());
          if (searchTerm && resNodes.length === 0 && !subnetNameMatches) return null;

          return {
            id: subnetId,
            node: <TreeNode label={subnet.Name || subnetId} id={subnetId} icon={getIcon('Subnets')} children={resNodes} forceExpand={!!searchTerm} selectedNodeId={selectedNodeId} />
          };
        }).filter(Boolean);

        const vpcNameMatches = vpcName.toLowerCase().includes(searchTerm.toLowerCase());
        if (searchTerm && configNodes.length === 0 && subnetNodes.length === 0 && !vpcNameMatches) return null;

        return {
          id: vpcId,
          node: <TreeNode label={vpcName} id={vpcId} icon={getIcon('VPCs')} defaultExpanded={true} children={[...configNodes, ...subnetNodes]} forceExpand={!!searchTerm} selectedNodeId={selectedNodeId} />
        };
      }).filter(Boolean);

      if (searchTerm && vpcChildren.length === 0) return null;

      return <TreeNode key={regionName} label={regionName} icon={<Globe size={14} className="text-green-400" />} defaultExpanded={true} children={vpcChildren} forceExpand={!!searchTerm} selectedNodeId={selectedNodeId} />;
    }).filter(Boolean);
  };

  return (
    <div className="p-3 w-full h-full text-gray-300 flex flex-col">
      <div className="px-1 mb-3 shrink-0">
        <h3 className="font-semibold text-white mb-3 uppercase tracking-wider text-[11px] border-b border-[#2d333b] pb-2 flex-shrink-0">
          Infrastructure Explorer
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
        <div className="flex flex-col gap-2">
          {renderGlobalResources()}
          {renderRegions()}
        </div>
      </div>
    </div>
  );
}

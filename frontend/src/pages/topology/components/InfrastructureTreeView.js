import React, { useState } from 'react';
import { getIcon } from '../../../utils/iconMap';
import {
  ChevronRight,
  ChevronDown,
  FolderOpen,
  Globe
} from 'lucide-react';

// Reusable ID extractor to guarantee sync with Canvas
const getResourceId = (resource, key) => {
  if (resource.Id) return resource.Id;
  const overrides = {
    'SecurityGroups': resource.GroupId,
    'DhcpOptions': resource.DhcpOptionsId,
    'ElasticIps': resource.AllocationId || resource.PublicIp,
    'GatewayLoadBalancers': resource.LoadBalancerArn,
    'MemoryDBClusters': resource.Name,
    'EMRClusters': resource.Id,
    'DirectoryServices': resource.DirectoryId,
    'AppRunnerVpcConnectors': resource.VpcConnectorArn,
    'GlueConnections': resource.Name,
    'BatchComputeEnvironments': resource.ComputeEnvironmentArn,
    'SecurityAndCompliance': `sec-comp-${resource.GuardDutyStatus || 'none'}`,
    'HybridConnectivity': resource.ConnectionId || resource.CoreNetworkId,
    'AutoScalingGroups': resource.AutoScalingGroupName || resource.AutoScalingGroupARN,
    'EKSClusters': resource.Name || resource.Arn,
    'ECSClusters': resource.ClusterName || resource.ClusterArn,
  };
  if (overrides[key]) return overrides[key];
  const singularId = resource[`${key.slice(0, -1)}Id`];
  if (singularId) return singularId;
  if (resource.Name) return resource.Name;
  if (resource.Arn) return resource.Arn;
  return `res-${Math.random()}`;
};

// Recursive Tree Node Component
const TreeNode = ({ label, id, icon, children, onNodeSelect, defaultExpanded = false, isResource = false, fullNodeData }) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const hasChildren = children && children.length > 0;

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
        className={`flex items-center gap-2 py-1.5 px-2 rounded cursor-pointer transition-colors ${isResource ? 'hover:bg-[#2d333b] text-gray-300' : 'hover:bg-[#1a1d24] text-gray-200 font-medium'
          }`}
      >
        <div className="w-4 h-4 flex items-center justify-center flex-shrink-0 text-gray-500">
          {hasChildren && !isResource ? (
            isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />
          ) : null}
        </div>

        {icon && <div className="flex items-center justify-center flex-shrink-0 w-4 h-4">{icon}</div>}

        <span className={`text-sm truncate leading-tight ${isResource ? 'opacity-90' : ''}`}>
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

export default function InfrastructureTreeView({ data, onNodeSelect }) {
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
        const name = res.Name || res.GroupName || res.AutoScalingGroupName || res.ClusterName || res.RoleName || res.DistributionId || res.BucketName || id;
        return {
          id,
          node: <TreeNode 
                  label={name} 
                  id={id} 
                  isResource={true} 
                  icon={getIcon(key)} 
                  onNodeSelect={onNodeSelect} 
                  fullNodeData={{
                    drillParent: null,
                    node: { id, data: { label: name, type: key.replace(/s$/, ''), ...res } }
                  }}
                />
        };
      });

      return {
        label: key,
        node: <TreeNode label={key} icon={<FolderOpen size={14} className="text-yellow-500" />} children={resourceNodes} />
      };
    });

    return <TreeNode label="Global Resources" icon={<Globe size={14} className="text-sky-300" />} defaultExpanded={true} children={children} />;
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
            const name = res.Name || res.GroupName || res.AutoScalingGroupName || res.ClusterName || res.GroupId || res.RouteTableId || id;
            return {
              id,
              node: <TreeNode 
                      label={name} 
                      id={id} 
                      isResource={true} 
                      icon={getIcon(key)} 
                      onNodeSelect={onNodeSelect} 
                      fullNodeData={{
                        drillParent: { type: key, title: key, drillData: vpc[key] },
                        node: { id, data: { label: name, type: key.replace(/s$/, ''), ...res } }
                      }}
                    />
            };
          });
          return {
            label: key,
            node: <TreeNode label={key} icon={<FolderOpen size={14} className="text-yellow-600" />} children={resNodes} />
          };
        });

        // 2. Subnets and their contained resources
        const subnets = vpc.Subnets || [];
        const subnetNodes = subnets.map(subnet => {
          const subnetId = subnet.SubnetId || 'Unknown Subnet';

          const subnetResKeys = Object.keys(subnet).filter(k => Array.isArray(subnet[k]) && subnet[k].length > 0);
          const resNodes = subnetResKeys.map(key => {
            const leafNodes = subnet[key].map(res => {
              const id = getResourceId(res, key);
              const name = res.Name || res.GroupName || res.AutoScalingGroupName || res.ClusterName || res.InstanceId || res.DBInstanceIdentifier || res.CacheClusterId || id;
              return {
                id,
                node: <TreeNode 
                        label={name} 
                        id={id} 
                        isResource={true} 
                        icon={getIcon(key)} 
                        onNodeSelect={onNodeSelect} 
                        fullNodeData={{
                          drillParent: { type: 'Subnet', title: subnet.Name || subnetId, drillData: subnet },
                          node: { id, data: { label: name, type: key.replace(/s$/, ''), ...res } }
                        }}
                      />
              };
            });
            return {
              label: key,
              node: <TreeNode label={key} icon={<FolderOpen size={14} className="text-yellow-500" />} children={leafNodes} />
            };
          });

          return {
            id: subnetId,
            node: <TreeNode label={subnet.Name || subnetId} id={subnetId} icon={getIcon('Subnets')} children={resNodes} />
          };
        });

        return {
          id: vpcId,
          node: <TreeNode label={vpcName} id={vpcId} icon={getIcon('VPCs')} defaultExpanded={true} children={[...configNodes, ...subnetNodes]} />
        };
      });

      return <TreeNode key={regionName} label={regionName} icon={<Globe size={14} className="text-green-400" />} defaultExpanded={true} children={vpcChildren} />;
    });
  };

  return (
    <div className="p-3 w-full h-full text-gray-300 flex flex-col">
      <h3 className="font-semibold text-white mb-3 uppercase tracking-wider text-[11px] border-b border-[#2d333b] pb-2 flex-shrink-0">
        Infrastructure Explorer
      </h3>
      <div className="overflow-y-auto flex-1 pr-1 custom-scrollbar">
        <div className="flex flex-col gap-2">
          {renderGlobalResources()}
          {renderRegions()}
        </div>
      </div>
    </div>
  );
}

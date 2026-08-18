import React, { useState, useEffect } from 'react';
import { Cloud, Network, Server, Database, Zap, Activity, Shield, Box, Lock, ChevronLeft, ChevronRight } from 'lucide-react';

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

const getLabel = (resource, key) => {
  return resource.Name || resource.GroupName || resource.AutoScalingGroupName || resource.ClusterName || resource.DBInstanceIdentifier || resource.DBClusterIdentifier || resource.FunctionName || resource.CacheClusterId || resource.InstanceId || resource.GroupId || resource.RouteTableId || resource.LoadBalancerName || resource.DistributionId || resource.BucketName || 'Resource';
};

const getIcon = (type) => {
  switch (type) {
    case 'EC2': case 'Instance': return <Server className="w-4 h-4 text-green-400" />;
    case 'RDS': case 'RDSInstance': return <Database className="w-4 h-4 text-blue-400" />;
    case 'Lambda': case 'LambdaFunction': return <Zap className="w-4 h-4 text-orange-400" />;
    case 'SecurityGroup': return <Shield className="w-4 h-4 text-red-400" />;
    case 'NetworkAcl': return <Lock className="w-4 h-4 text-red-300" />;
    case 'RouteTable': return <Network className="w-4 h-4 text-cyan-400" />;
    case 'InternetGateway': return <Cloud className="w-4 h-4 text-indigo-400" />;
    case 'Subnet': return <Network className="w-4 h-4 text-blue-400" />;
    case 'VPC': return <Cloud className="w-4 h-4 text-purple-400" />;
    default: return <Activity className="w-4 h-4 text-gray-400" />;
  }
};

const MicroCard = ({ resource, resourceKey, onClick }) => {
  const label = getLabel(resource, resourceKey);
  const type = resourceKey.replace(/s$/, ''); // singularize
  
  return (
    <div 
      onClick={() => onClick({ id: getResourceId(resource, resourceKey), data: { label, type, ...resource } })}
      className="bg-[#1a1d24] border border-[#2d333b] rounded-md p-2 flex items-center gap-3 shadow-sm hover:border-gray-400 transition-colors cursor-pointer w-full"
    >
      <div className="p-1.5 bg-[#0a0a0f] rounded border border-[#2d333b] shrink-0">
        {getIcon(type)}
      </div>
      <div className="flex flex-col min-w-0 flex-1">
        <span className="text-white text-[11px] font-medium truncate w-full block">{label}</span>
        <span className="text-gray-500 text-[9px] uppercase tracking-wider truncate w-full block">{type}</span>
      </div>
    </div>
  );
};

const Badge = ({ resource, resourceKey, onClick }) => {
  const label = getLabel(resource, resourceKey);
  const type = resourceKey.replace(/s$/, '');
  return (
    <div 
      onClick={() => onClick({ id: getResourceId(resource, resourceKey), data: { label, type, ...resource } })}
      className="bg-[#1a1d24] border border-[#2d333b] rounded-full px-3 py-1 flex items-center gap-2 shadow-sm hover:border-gray-400 transition-colors cursor-pointer shrink-0"
    >
      {getIcon(type)}
      <span className="text-white text-[10px] font-bold whitespace-nowrap">{label}</span>
      <span className="text-zinc-500 text-[9px] uppercase tracking-wider whitespace-nowrap hidden sm:inline ml-1 border-l border-[#2d333b] pl-2">{type}</span>
    </div>
  );
};

export default function TopologyDashboard({ data, viewRegion, onNodeClick }) {
  const [currentVpcIndex, setCurrentVpcIndex] = useState(0);

  // Reset index when region changes
  useEffect(() => {
    setCurrentVpcIndex(0);
  }, [viewRegion]);

  if (!data || !data.Regions) {
    return (
      <div className="w-full h-full flex items-center justify-center text-gray-500 italic bg-[#0a0a0f]">
        No infrastructure data available. Run a scan to populate the dashboard.
      </div>
    );
  }

  let targetRegions = [];
  if (viewRegion === 'ALL') {
    targetRegions = Object.values(data.Regions);
  } else {
    targetRegions = data.Regions[viewRegion] ? [data.Regions[viewRegion]] : [];
  }

  // Flatten all VPCs from the selected region(s) into a single array
  const allVpcs = targetRegions.flat();

  const vpcConfigKeys = [
    'RouteTables', 'InternetGateways', 'NetworkAcls', 'SecurityGroups', 
    'DhcpOptions', 'FlowLogs', 'ElasticIps'
  ];
  
  const vpcResourceKeys = [
    'LoadBalancers', 'RDSInstances', 'PeeringConnections', 'TransitGatewayAttachments', 
    'VpnGateways', 'VpnConnections', 'RegionalQueues', 'NetworkFirewalls', 
    'EgressOnlyInternetGateways', 'CarrierGateways', 'HybridConnectivity'
  ];

  if (allVpcs.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center text-gray-500 italic bg-[#0a0a0f]">
        No VPCs found in the selected region.
      </div>
    );
  }

  const vpc = allVpcs[currentVpcIndex];
  const vpcId = vpc.Id || vpc.VpcId;
  
  const hasConfigs = vpcConfigKeys.some(key => vpc[key] && vpc[key].length > 0);
  const hasVpcResources = vpcResourceKeys.some(key => vpc[key] && vpc[key].length > 0);
  const hasSubnets = vpc.Subnets && vpc.Subnets.length > 0;

  return (
    <div className="flex flex-col gap-6 p-6 pb-24 overflow-y-auto w-full h-full custom-scrollbar bg-[#0a0a0f]">
      
      {/* Pagination Navigation Bar */}
      {allVpcs.length > 1 && (
        <div className="flex items-center justify-between bg-[#161b22] border border-[#2d333b] rounded-xl p-3 shadow-md shrink-0">
          <button 
            onClick={() => setCurrentVpcIndex(prev => Math.max(0, prev - 1))}
            disabled={currentVpcIndex === 0}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-zinc-300 hover:bg-[#2d333b] hover:text-white"
          >
            <ChevronLeft className="w-4 h-4" /> Previous VPC
          </button>
          
          <div className="flex flex-col items-center">
            <span className="text-white font-bold text-sm">VPC {currentVpcIndex + 1} of {allVpcs.length}</span>
            <span className="text-zinc-500 text-[10px] uppercase tracking-wider">{vpc.Name || vpcId}</span>
          </div>

          <button 
            onClick={() => setCurrentVpcIndex(prev => Math.min(allVpcs.length - 1, prev + 1))}
            disabled={currentVpcIndex === allVpcs.length - 1}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-zinc-300 hover:bg-[#2d333b] hover:text-white"
          >
            Next VPC <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Active VPC Card */}
      <div className="bg-[#0e1015]/80 backdrop-blur border-[2px] border-purple-500/30 border-dashed rounded-xl flex flex-col p-5 relative shadow-xl">
        
        {/* VPC Header */}
        <div 
          className="flex items-center gap-3 bg-[#0a0a0f] p-3 pr-6 rounded-lg border border-[#2d333b] shadow-md w-fit cursor-pointer hover:border-purple-400 transition-colors"
          onClick={() => onNodeClick({ id: vpcId, data: { label: vpc.Name || vpcId, type: 'VPC', ...vpc } })}
        >
          <Cloud className="w-6 h-6 text-purple-400" />
          <div>
            <div className="text-white text-base font-bold truncate">{vpc.Name || vpcId}</div>
            <div className="text-gray-400 text-[10px] uppercase tracking-wider font-semibold">Virtual Private Cloud</div>
          </div>
        </div>

        {/* VPC Network Config Badges */}
        {hasConfigs && (
          <div className="mt-5">
            <h3 className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold mb-2">Network Control Plane</h3>
            <div className="flex flex-wrap gap-2">
              {vpcConfigKeys.map(key => {
                const resources = vpc[key] || [];
                return resources.map(res => (
                  <Badge key={getResourceId(res, key)} resource={res} resourceKey={key} onClick={onNodeClick} />
                ));
              })}
            </div>
          </div>
        )}

        {/* VPC Infrastructure Resources */}
        {hasVpcResources && (
          <div className="mt-5">
            <h3 className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold mb-2">VPC Edge Resources</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
              {vpcResourceKeys.map(key => {
                const resources = vpc[key] || [];
                return resources.map(res => (
                  <MicroCard key={getResourceId(res, key)} resource={res} resourceKey={key} onClick={onNodeClick} />
                ));
              })}
            </div>
          </div>
        )}

        {/* Subnets Grid */}
        {hasSubnets && (
          <div className="mt-6">
            <h3 className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold mb-3">Subnets</h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {(vpc.Subnets || []).map(subnet => {
                const subnetId = subnet.Id || subnet.SubnetId;
                const subnetResourceKeys = Object.keys(subnet).filter(k => Array.isArray(subnet[k]) && subnet[k].length > 0 && k !== 'Tags');
                const hasSubnetResources = subnetResourceKeys.length > 0;
                
                return (
                  <div key={subnetId} className="bg-[#161b22] border border-blue-500/30 rounded-lg flex flex-col p-4 shadow-lg relative pt-10">
                    
                    {/* Subnet Header placed cleanly over the grid */}
                    <div 
                      className="absolute top-3 left-3 flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity w-fit z-10"
                      onClick={() => onNodeClick({ id: subnetId, data: { label: subnet.Name || subnetId, type: 'Subnet', ...subnet } })}
                    >
                      <Network className="w-4 h-4 text-blue-400" />
                      <div className="flex flex-col">
                        <div className="text-white text-sm font-bold truncate max-w-[200px] leading-tight">{subnet.Name || subnetId}</div>
                        <div className="text-blue-400/70 text-[9px] uppercase tracking-wider font-semibold">Subnet</div>
                      </div>
                    </div>

                    {/* Subnet Children */}
                    {hasSubnetResources ? (
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-2 mt-2">
                        {subnetResourceKeys.map(key => {
                          const resources = subnet[key] || [];
                          return resources.map(res => (
                            <MicroCard key={getResourceId(res, key)} resource={res} resourceKey={key} onClick={onNodeClick} />
                          ));
                        })}
                      </div>
                    ) : (
                      <div className="text-gray-500 italic text-xs mt-2">Empty Subnet</div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

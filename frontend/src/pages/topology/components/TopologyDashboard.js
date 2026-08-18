import React, { useState } from 'react';
import { Cloud, ChevronLeft, ChevronRight } from 'lucide-react';

import { getIcon, getColorClasses } from '../../../utils/iconMap';

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

const MicroCard = ({ resource, resourceKey, onClick }) => {
  const label = getLabel(resource, resourceKey);
  const type = resourceKey.replace(/s$/, ''); // singularize
  const colors = getColorClasses(type);
  
  return (
    <div
      id={getResourceId(resource, resourceKey)}
      onClick={() => onClick({ id: getResourceId(resource, resourceKey), data: { label, type, ...resource } })}
      className={`bg-[#1e232b] hover:bg-[#2a313c] border border-zinc-700/50 ${colors.border} transition-all duration-300 rounded-md p-2.5 flex items-center gap-3 cursor-pointer group shadow-md`}
    >
      <div className="bg-[#2d333b] p-1.5 rounded-md group-hover:scale-110 transition-transform duration-300 shadow-sm border border-black/20">
        {getIcon(type)}
      </div>
      <div className="flex flex-col overflow-hidden w-full">
        <span className="text-[11px] font-bold text-gray-200 truncate leading-tight group-hover:text-white transition-colors">{label}</span>
        <span className={`text-[9px] ${colors.text} opacity-80 font-semibold truncate mt-0.5`}>{type}</span>
      </div>
    </div>
  );
};

const SummaryCard = ({ title, count, type, onClick }) => {
  const colors = getColorClasses(type);
  
  return (
    <div 
      className={`bg-[#161b22] hover:bg-[#1f2630] border ${colors.borderStatic} ${colors.border} rounded-lg p-2.5 flex items-center gap-3 shadow-sm hover:shadow-md cursor-pointer transition-all duration-300 group`}
      onClick={onClick}
    >
      <div className="bg-[#2d333b] p-2 rounded-md group-hover:scale-110 transition-transform duration-300 shadow-sm border border-black/20">
        {getIcon(type, 16)}
      </div>
      <div className="flex flex-col overflow-hidden w-full">
        <span className="text-[11px] font-bold text-gray-200 truncate leading-tight group-hover:text-white transition-colors">{title}</span>
        <span className={`text-[9px] ${colors.text} opacity-80 font-semibold truncate mt-0.5`}>{count} Resources</span>
      </div>
    </div>
  );
};

const SubnetSummaryCard = ({ subnet, onClick }) => {
  const subnetId = subnet.Id || subnet.SubnetId;
  const subnetResourceKeys = Object.keys(subnet).filter(k => Array.isArray(subnet[k]) && subnet[k].length > 0 && k !== 'Tags');
  const resourceCount = subnetResourceKeys.reduce((acc, key) => acc + (subnet[key]?.length || 0), 0);
  const colors = getColorClasses('Subnet');
  
  return (
    <div 
      className={`bg-[#161b22] hover:bg-[#1f2630] border ${colors.borderStatic} ${colors.border} rounded-lg p-3 flex flex-col shadow-sm hover:shadow-md cursor-pointer transition-all duration-300 group min-h-[90px]`}
      onClick={() => onClick(subnet)}
    >
      <div className="flex items-center gap-2 mb-3">
        <div className="bg-[#2d333b] p-1.5 rounded-md group-hover:scale-110 transition-transform duration-300 border border-black/20">
          {getIcon('Subnet', 14)}
        </div>
        <div className="flex flex-col overflow-hidden">
          <div className="text-[12px] text-gray-200 font-bold truncate leading-tight group-hover:text-white transition-colors">{subnet.Name || subnetId}</div>
          <div className={`${colors.text} opacity-70 text-[9px] uppercase tracking-wider font-semibold`}>Subnet</div>
        </div>
      </div>
      <div className="mt-auto flex items-end justify-between border-t border-zinc-800/50 pt-2">
        <div className="text-gray-400 text-[9px] uppercase tracking-wider">Resources</div>
        <div className={`${colors.text} text-[14px] font-bold leading-none`}>{resourceCount}</div>
      </div>
    </div>
  );
};

const Badge = ({ resource, resourceKey, onClick }) => {
  const label = getLabel(resource, resourceKey);
  const type = resourceKey.replace(/s$/, '');
  return (
    <div
      id={getResourceId(resource, resourceKey)}
      onClick={() => onClick({ id: getResourceId(resource, resourceKey), data: { label, type, ...resource } })}
      className="bg-[#1a1d24] border border-[#2d333b] rounded-full px-3 py-1 flex items-center gap-2 shadow-sm hover:border-gray-400 transition-colors cursor-pointer shrink-0 transition-shadow duration-500"
    >
      {getIcon(type)}
      <span className="text-white text-[10px] font-bold whitespace-nowrap">{label}</span>
      <span className="text-zinc-500 text-[9px] uppercase tracking-wider whitespace-nowrap hidden sm:inline ml-1 border-l border-[#2d333b] pl-2">{type}</span>
    </div>
  );
};

export default function TopologyDashboard({ data, viewRegion, currentVpcIndex, setCurrentVpcIndex, onNodeClick, drillDownState, setDrillDownState }) {

  if (!data || !data.Regions) {
    return (
      <div className="w-full h-full flex items-center justify-center text-gray-500 italic bg-[#0a0a0f]">
        No infrastructure data available. Run a scan to populate the dashboard.
      </div>
    );
  }

  const vpcConfigKeys = [
    'RouteTables', 'InternetGateways', 'NetworkAcls', 'SecurityGroups',
    'DhcpOptions', 'FlowLogs', 'ElasticIps'
  ];

  const vpcResourceKeys = [
    'LoadBalancers', 'PeeringConnections', 'TransitGatewayAttachments',
    'VpnGateways', 'VpnConnections', 'NetworkFirewalls',
    'EgressOnlyInternetGateways', 'CarrierGateways', 'HybridConnectivity'
  ];

  const vpcDataKeys = [
    'RDSInstances', 'ElastiCacheNodes', 'RegionalQueues', 'RedshiftClusters', 
    'DocumentDBClusters', 'MemoryDBClusters', 'OpenSearchDomains', 
    'NeptuneClusters', 'AmazonMQBrokers', 'MSKClusters'
  ];

  const targetRegions = viewRegion === 'Global' 
    ? Object.values(data.Regions || {}) 
    : [data.Regions[viewRegion] || []];
  
  const allVpcs = targetRegions.flat();

  // Handle empty state if no VPCs exist
  if (allVpcs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-zinc-500 gap-4">
        <Cloud size={48} className="opacity-20" />
        <p>No VPCs found in {viewRegion === 'Global' ? 'any region' : viewRegion}</p>
      </div>
    );
  }

  const vpc = allVpcs[currentVpcIndex] || allVpcs[0];
  const vpcId = vpc.Id || vpc.VpcId;

  const hasConfigs = vpcConfigKeys.some(key => vpc[key] && vpc[key].length > 0);
  const hasVpcResources = vpcResourceKeys.some(key => vpc[key] && vpc[key].length > 0);
  const hasDataResources = vpcDataKeys.some(key => vpc[key] && vpc[key].length > 0);
  const hasSubnets = vpc.Subnets && vpc.Subnets.length > 0;

  // Render Drill Down View if active
  if (drillDownState) {
    const { type, title, drillData } = drillDownState;
    return (
      <div id="dashboard-scroll-container" className="flex flex-col gap-6 p-6 pb-24 overflow-y-auto w-full h-full custom-scrollbar bg-[#0a0a0f]">
        <button 
          onClick={() => setDrillDownState(null)}
          className="flex items-center gap-2 text-zinc-400 hover:text-white transition-colors w-fit mb-2 mt-12 bg-[#161b22] px-4 py-2 rounded-lg border border-zinc-800 shadow-lg relative z-10"
        >
          <ChevronLeft className="w-4 h-4" /> Back to Topology Overview
        </button>
        
        <div className={`bg-[#0e1015]/80 backdrop-blur border-[2px] ${getColorClasses(type).borderStatic} border-dashed rounded-xl flex flex-col p-6 pb-12 shadow-xl relative min-h-[500px] shrink-0`}>
           <div className="flex items-center gap-3 mb-6 border-b border-zinc-800 pb-4">
             {getIcon(type, 28)}
             <div>
               <h2 className="text-white text-2xl font-bold">{title}</h2>
               <p className={`text-xs uppercase tracking-wider font-semibold ${getColorClasses(type).text}`}>{type} Detailed View</p>
             </div>
           </div>
           
           {/* If Subnet, we map through its keys and render MicroCards */}
           {type === 'Subnet' && (
             <div className="flex flex-col gap-6">
               {Object.keys(drillData).filter(k => Array.isArray(drillData[k]) && drillData[k].length > 0 && k !== 'Tags').map(key => (
                 <div key={key}>
                   <h3 className="text-zinc-400 text-sm font-bold mb-3">{key}</h3>
                   <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
                     {drillData[key].map(res => (
                       <MicroCard key={getResourceId(res, key)} resource={res} resourceKey={key} onClick={onNodeClick} />
                     ))}
                   </div>
                 </div>
               ))}
             </div>
           )}
           
           {/* If Layer Group, we map through its resources directly */}
           {type !== 'Subnet' && (
             <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
               {drillData.map(res => (
                 <MicroCard key={getResourceId(res, type)} resource={res} resourceKey={type} onClick={onNodeClick} />
               ))}
             </div>
           )}
        </div>
      </div>
    );
  }

  return (
    <div id="dashboard-scroll-container" className="flex flex-col gap-6 p-6 pb-24 overflow-y-auto w-full h-full custom-scrollbar bg-[#0a0a0f]">

      {/* Active VPC Card */}
      <div className="bg-[#0e1015]/80 backdrop-blur border-[2px] border-purple-500/30 border-dashed rounded-xl flex flex-col p-5 pt-12 relative shadow-xl mt-12">

        {/* Unified Centered VPC Header & Navigation (Straddling the top border) */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 flex items-center justify-center gap-3 w-max z-10">

          {/* Left Arrow */}
          {allVpcs.length > 1 && (
            <button
              onClick={() => setCurrentVpcIndex(prev => Math.max(0, prev - 1))}
              disabled={currentVpcIndex === 0}
              className="p-1.5 bg-[#0a0a0f] border-2 border-[#2d333b] rounded-full hover:border-purple-500 hover:text-purple-400 disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-zinc-400 shadow-lg"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          )}

          <div className="flex flex-col items-center relative">
            {/* Clickable VPC Title */}
            <div
              id={vpcId}
              className="flex items-center gap-3 bg-[#0a0a0f] py-2 px-5 rounded-xl border-[2px] border-purple-500/80 shadow-2xl shadow-purple-900/20 cursor-pointer hover:border-purple-400 transition-all duration-500"
              onClick={() => onNodeClick({ id: vpcId, data: { label: vpc.Name || vpcId, type: 'VPC', ...vpc } })}
            >
              <Cloud className="w-5 h-5 text-purple-400" />
              <div className="flex flex-col items-start">
                <div className="text-white text-sm font-bold truncate max-w-[250px] leading-tight">{vpc.Name || vpcId}</div>
                <div className="text-purple-400/80 text-[9px] uppercase tracking-wider font-bold">Virtual Private Cloud</div>
              </div>
            </div>

            {/* Subtle Counter */}
            {allVpcs.length > 1 && (
              <div className="absolute -bottom-2 text-zinc-400 text-[8px] uppercase tracking-widest font-bold bg-[#0a0a0f] border border-[#2d333b] px-2 py-0.5 rounded-full z-20">
                VPC {currentVpcIndex + 1} of {allVpcs.length}
              </div>
            )}
          </div>

          {/* Right Arrow */}
          {allVpcs.length > 1 && (
            <button
              onClick={() => setCurrentVpcIndex(prev => Math.min(allVpcs.length - 1, prev + 1))}
              disabled={currentVpcIndex === allVpcs.length - 1}
              className="p-1.5 bg-[#0a0a0f] border-2 border-[#2d333b] rounded-full hover:border-sky-500 hover:text-sky-400 disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-zinc-400 shadow-lg"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* VPC Network Config Badges */}
        {hasConfigs && (
          <div className="mt-5">
            <h3 className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold mb-2">Network Control Plane</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {vpcConfigKeys.map(key => {
                const resources = vpc[key] || [];
                if (resources.length === 0) return null;
                return (
                  <SummaryCard 
                    key={key} 
                    title={key} 
                    count={resources.length} 
                    type={key.replace(/s$/, '')}
                    onClick={() => setDrillDownState({ type: key, title: key, drillData: resources })} 
                  />
                );
              })}
            </div>
          </div>
        )}

        {/* VPC Infrastructure Resources */}
        {hasVpcResources && (
          <div className="mt-5">
            <h3 className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold mb-2">VPC Edge Resources</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {vpcResourceKeys.map(key => {
                const resources = vpc[key] || [];
                if (resources.length === 0) return null;
                return (
                  <SummaryCard 
                    key={key} 
                    title={key} 
                    count={resources.length} 
                    type={key.replace(/s$/, '')}
                    onClick={() => setDrillDownState({ type: key, title: key, drillData: resources })} 
                  />
                );
              })}
            </div>
          </div>
        )}

        {/* Data & Messaging Layer */}
        {hasDataResources && (
          <div className="mt-5">
            <h3 className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold mb-2">Data & Messaging Layer</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {vpcDataKeys.map(key => {
                const resources = vpc[key] || [];
                if (resources.length === 0) return null;
                return (
                  <SummaryCard 
                    key={key} 
                    title={key} 
                    count={resources.length} 
                    type={key.replace(/s$/, '')}
                    onClick={() => setDrillDownState({ type: key, title: key, drillData: resources })} 
                  />
                );
              })}
            </div>
          </div>
        )}

        {/* Subnets Grid */}
        {hasSubnets && (
          <div className="mt-6">
            <h3 className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold mb-3">
              Subnets ({vpc.Subnets.length})
            </h3>
            
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {vpc.Subnets.map(subnet => (
                <SubnetSummaryCard 
                  key={subnet.Id || subnet.SubnetId} 
                  subnet={subnet} 
                  onClick={(s) => setDrillDownState({ type: 'Subnet', title: s.Name || s.SubnetId, drillData: s })} 
                />
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

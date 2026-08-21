import React, { useState } from 'react';
import {
  Cloud, ChevronLeft, ChevronRight, ChevronDown, Info, BarChart2
} from 'lucide-react';

import { getIcon, getColorClasses } from '../../../utils/iconMap';
import { getResourceId, getResourceLabel, RESOURCE_CATEGORIES } from '../../../utils/resourceUtils';

const MicroCard = ({ resource, resourceKey, onClick }) => {
  const label = getResourceLabel(resource, resourceKey);
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

const SubnetSummaryCard = ({ subnet, onClick, onNodeClick }) => {
  const subnetId = subnet.Id || subnet.SubnetId;
  const subnetResourceKeys = Object.keys(subnet).filter(k => Array.isArray(subnet[k]) && subnet[k].length > 0 && k !== 'Tags');
  const resourceCount = subnetResourceKeys.reduce((acc, key) => acc + (subnet[key]?.length || 0), 0);
  const colors = getColorClasses('Subnet');

  return (
    <div
      className={`bg-[#161b22] hover:bg-[#1f2630] border ${colors.borderStatic} ${colors.border} rounded-lg p-3 flex flex-col shadow-sm hover:shadow-md cursor-pointer transition-all duration-300 group min-h-[90px] relative overflow-hidden`}
      onClick={() => onClick(subnet)}
    >
      <button
        onClick={(e) => {
          e.stopPropagation();
          onNodeClick({ id: subnetId, data: { label: subnet.Name || subnetId, type: 'Subnet', ...subnet } });
        }}
        className="absolute top-2 right-2 p-1.5 rounded-md bg-[#2d333b]/80 text-zinc-400 hover:text-white hover:bg-sky-500/80 opacity-0 group-hover:opacity-100 transition-all duration-300 shadow-sm backdrop-blur-sm z-10 translate-x-2 group-hover:translate-x-0"
        title="View Subnet JSON Details"
      >
        <Info size={14} />
      </button>

      <div className="flex items-center gap-2 mb-3 w-[85%]">
        <div className="bg-[#2d333b] p-1.5 rounded-md group-hover:scale-110 transition-transform duration-300 border border-black/20 shrink-0">
          {getIcon('Subnet', 14)}
        </div>
        <div className="flex flex-col overflow-hidden w-full">
          <div className="text-[12px] text-gray-200 font-bold truncate leading-tight group-hover:text-white transition-colors" title={subnet.Name || subnetId}>{subnet.Name || subnetId}</div>
          <div className={`${colors.text} opacity-70 text-[9px] uppercase tracking-wider font-semibold mt-0.5`}>Subnet</div>
        </div>
      </div>
      <div className="mt-auto flex items-end justify-between border-t border-zinc-800/50 pt-2">
        <div className="text-gray-400 text-[9px] uppercase tracking-wider">Resources</div>
        <div className={`${colors.text} text-[14px] font-bold leading-none`}>{resourceCount}</div>
      </div>
    </div>
  );
};



export default function TopologyDashboard({ data, viewRegion, currentVpcIndex, setCurrentVpcIndex, onNodeClick, drillDownState, setDrillDownState }) {
  const [showVpcDropdown, setShowVpcDropdown] = useState(false);

  if (!data || !data.Regions) {
    return (
      <div className="w-full h-full flex items-center justify-center text-gray-500 italic bg-[#0a0a0f]">
        No infrastructure data available. Run a scan to populate the dashboard.
      </div>
    );
  }

  const { vpcConfigKeys, vpcResourceKeys, vpcDataKeys, subnetEdgeKeys, subnetComputeKeys, subnetDataKeys } = RESOURCE_CATEGORIES;

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
        <div className="flex items-center gap-2 text-sm font-medium w-fit mb-2 mt-12 bg-[#161b22] px-4 py-2 rounded-lg border border-zinc-800 shadow-lg relative z-10">
          <button
            onClick={() => setDrillDownState(null)}
            className="flex items-center gap-1.5 text-zinc-400 hover:text-white transition-colors"
          >
            <Cloud className="w-4 h-4" />
            <span className="truncate max-w-[150px]">{vpc.Name || vpcId}</span>
          </button>
          <span className="text-zinc-600">/</span>
          <div className={`flex items-center gap-1.5 ${getColorClasses(type).text}`}>
            <span className="w-4 h-4 flex items-center justify-center">{getIcon(type, 14)}</span>
            <span className="truncate max-w-[200px]">{title}</span>
          </div>
        </div>

        <div className={`bg-[#0e1015]/80 backdrop-blur border-[2px] ${getColorClasses(type).borderStatic} border-dashed rounded-xl flex flex-col p-6 pb-12 shadow-xl relative min-h-[500px] shrink-0`}>
          <div className="flex items-center gap-3 mb-6 border-b border-zinc-800 pb-4">
            {getIcon(type, 28)}
            <div>
              <h2 className="text-white text-2xl font-bold">{title}</h2>
              <p className={`text-xs uppercase tracking-wider font-semibold ${getColorClasses(type).text}`}>{type} Detailed View</p>
            </div>
          </div>

          {/* If Subnet, we map through keys by Layer to show Application Flow */}
          {type === 'Subnet' && (() => {
            const renderSubnetLayer = (title, keys) => {
              const activeKeys = keys.filter(k => Array.isArray(drillData[k]) && drillData[k].length > 0 && k !== 'Tags');
              if (activeKeys.length === 0) return null;
              return (
                <div className="mb-6 bg-[#13171e]/50 p-4 rounded-xl border border-zinc-800/50">
                  <h3 className="text-[12px] uppercase tracking-wider text-zinc-400 font-bold mb-4 flex items-center gap-2">{title}</h3>
                  <div className="flex flex-col gap-4">
                    {activeKeys.map(key => (
                      <div key={key}>
                        <h4 className="text-zinc-300 text-xs font-bold mb-2">{key}</h4>
                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
                          {drillData[key].map(res => (
                            <MicroCard key={getResourceId(res, key)} resource={res} resourceKey={key} onClick={onNodeClick} />
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            };

            const otherKeys = Object.keys(drillData).filter(k => !subnetEdgeKeys.includes(k) && !subnetComputeKeys.includes(k) && !subnetDataKeys.includes(k) && k !== 'Tags' && Array.isArray(drillData[k]));

            return (
              <div className="flex flex-col">
                {renderSubnetLayer('🌐 Edge & Network Flow', subnetEdgeKeys)}
                {renderSubnetLayer('⚙️ Compute & Application Layer', subnetComputeKeys)}
                {renderSubnetLayer('🗄️ Data & Storage Layer', subnetDataKeys)}
                {renderSubnetLayer('🛡️ Management & Other', otherKeys)}
              </div>
            );
          })()}

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
            {/* Clickable VPC Title / Dropdown */}
            <div className="flex items-center gap-2">
              <div
                className="flex items-center gap-3 bg-[#0a0a0f] py-2 px-5 rounded-xl border-[2px] border-purple-500/80 shadow-2xl shadow-purple-900/20 cursor-pointer hover:border-purple-400 transition-all duration-500 relative"
                onClick={() => setShowVpcDropdown(!showVpcDropdown)}
              >
                <Cloud className="w-5 h-5 text-purple-400" />
                <div className="flex flex-col items-start">
                  <div className="text-white text-sm font-bold truncate max-w-[250px] leading-tight flex items-center gap-1.5">
                    {vpc.Name || vpcId}
                    <ChevronDown size={14} className="text-zinc-500" />
                  </div>
                  <div className="text-purple-400/80 text-[9px] uppercase tracking-wider font-bold">Virtual Private Cloud</div>
                </div>

                {showVpcDropdown && (
                  <div className="absolute top-full mt-2 left-1/2 -translate-x-1/2 w-max min-w-[240px] bg-[#1a1d24] border border-[#2d333b] rounded-lg shadow-2xl py-1 z-50">
                    <div className="px-3 py-1.5 text-[10px] uppercase font-bold text-zinc-500 border-b border-[#2d333b] mb-1">Select VPC</div>
                    {allVpcs.map((v, idx) => (
                      <div
                        key={v.VpcId || idx}
                        className={`px-4 py-2 hover:bg-[#2d333b] text-sm text-zinc-300 transition-colors flex items-center gap-2 ${idx === currentVpcIndex ? 'bg-purple-500/10 text-purple-300 border-l-2 border-purple-500' : 'border-l-2 border-transparent'}`}
                        onClick={(e) => { e.stopPropagation(); setCurrentVpcIndex(idx); setShowVpcDropdown(false); }}
                      >
                        <Cloud className={`w-4 h-4 ${idx === currentVpcIndex ? 'text-purple-400' : 'text-zinc-500'}`} />
                        <div className="flex flex-col">
                          <span className="font-semibold text-white">{v.Name || v.VpcId}</span>
                          <span className="text-[10px] text-zinc-500">{v.CidrBlock}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              
              {/* Analytics & Details Button */}
              <button
                onClick={(e) => { e.stopPropagation(); onNodeClick({ id: vpcId, data: { label: vpc.Name || vpcId, type: 'VPC', ...vpc } }); }}
                className="p-2 bg-[#161b22] border-2 border-purple-500/30 rounded-xl hover:border-purple-500 hover:text-purple-400 transition-colors text-purple-400/80 shadow-lg ml-2"
                title="VPC Analytics & Details"
              >
                <BarChart2 className="w-5 h-5" />
              </button>
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
                  onNodeClick={onNodeClick}
                />
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

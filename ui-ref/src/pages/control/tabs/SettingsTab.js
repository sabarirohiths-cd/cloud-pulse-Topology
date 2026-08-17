import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Database, Eye, EyeOff, Search, CheckSquare, Settings2 } from 'lucide-react';
import { Virtuoso } from 'react-virtuoso';
import { FilterBar } from '../../../components/ui/FilterBar';
import { EmptyState } from '../../../components/ui/EmptyState';
import { toast } from 'sonner';
import { listResources, toggleVisibility } from '../../../api/control';
import { buildResourceTree, buildResourceMap } from '../../../utils/resource-tree';
import { SettingsRow } from './components/SettingsRow';

export function SettingsTab({ topFilters }) {
  const [resources, setResources] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  
  const [hasMore, setHasMore] = useState(true);
  const [offset, setOffset] = useState(0);
  const LIMIT = 50;

  const [filter, setFilter] = useState({
    group: 'All'
  });
  
  const [expandedRowIds, setExpandedRowIds] = useState(new Set());

  const toggleRow = (id) => {
    setExpandedRowIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) newSet.delete(id);
      else newSet.add(id);
      return newSet;
    });
  };

  const loadResources = async (reset = false) => {
    if (loading || (!hasMore && !reset)) return;

    setLoading(true);
    const currentOffset = reset ? 0 : offset;

    try {
      const data = await listResources(topFilters, LIMIT, currentOffset, true); // true = show hidden
      const mapped = (data || []).map(s => ({
        resource_id: s.resource_id,
        name: s.resource_name || s.resource_id,
        service_type: s.service_type,
        control_type: s.control_type,
        account_name: s.account_name,
        region: s.region,
        cloud_provider: s.cloud_provider || 'aws',
        instance_spec: s.instance_spec || 'unknown',
        tags_json: s.tags_json,
        status: s.status || 'UNKNOWN',
        parent_resource_id: s.parent_resource_id,
        is_visible: s.is_visible,
        schedule: {
          is_automation_enabled: s.is_automation_enabled,
          start_time: s.start_time,
          stop_time: s.stop_time,
          timezone: s.timezone,
          pattern: s.schedule_pattern,
          owner: s.owner_email
        }
      }));

      if (mapped.length < LIMIT) {
        setHasMore(false);
      } else {
        setHasMore(true);
      }

      setResources(prev => {
        if (reset) return mapped;
        // avoid duplicates
        const existingIds = new Set(prev.map(r => r.resource_id));
        return [...prev, ...mapped.filter(r => !existingIds.has(r.resource_id))];
      });
      setOffset(currentOffset + mapped.length);
    } catch (error) {
      console.error(error);
      toast.error('Failed to load resources for settings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setHasMore(true);
    setOffset(0);
    loadResources(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topFilters.account, topFilters.provider, topFilters.region]);

  const loadMore = useCallback(() => {
    if (!loading && hasMore) {
      loadResources(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, hasMore, offset, topFilters]);

  // Recursively find children IDs to cascade toggles locally
  // Recursively find children IDs to cascade toggles locally based on the EXACT visual hierarchy
  const getResourceAndChildrenIds = (resourceId, allResources) => {
    const { resourceMap } = buildResourceMap(allResources);
    
    const getIds = (node) => {
      let ids = [node.resource_id];
      for (const child of node.children) {
        ids = ids.concat(getIds(child));
      }
      return ids;
    };

    const targetNode = resourceMap.get(resourceId);
    return targetNode ? getIds(targetNode) : [resourceId];
  };

  const handleToggle = async (resource) => {
    const newState = !resource.is_visible;
    const targetIds = getResourceAndChildrenIds(resource.resource_id, resources);
    
    try {
      await toggleVisibility(targetIds, newState);
      toast.success(`${resource.name} ${targetIds.length > 1 ? `and ${targetIds.length - 1} nested items` : ''} now ${newState ? 'visible' : 'hidden'}`);
      
      setResources(prev => prev.map(r => 
        targetIds.includes(r.resource_id) ? { ...r, is_visible: newState } : r
      ));
    } catch (error) {
      console.error(error);
      toast.error('Failed to update visibility');
    }
  };

  const handleToggleAll = async (newVisibility) => {
    const allFilteredIds = resources
      .filter(r => filter.group === 'All' || getGroup(r.service_type) === filter.group)
      .filter(r =>
        (r.name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (r.resource_id || '').toLowerCase().includes(searchQuery.toLowerCase())
      )
      .map(r => r.resource_id);

    if (allFilteredIds.length === 0) return;
    
    try {
      await toggleVisibility(allFilteredIds, newVisibility);
      toast.success(`Updated visibility for ${allFilteredIds.length} resources`);
      setResources(prev => prev.map(r => 
        allFilteredIds.includes(r.resource_id) ? { ...r, is_visible: newVisibility } : r
      ));
    } catch (error) {
      console.error(error);
      toast.error('Failed to update visibility in bulk');
    }
  };

  const getGroup = (type) => {
    const t = (type || '').toUpperCase();
    if (['RDS', 'AURORA'].includes(t)) return 'RDS';
    if (['EC2'].includes(t)) return 'EC2';
    return t;
  };

  const uniqueGroups = Array.from(new Set(resources.map(r => getGroup(r.service_type)))).sort();
  const groupOptions = [
    { label: 'All Groups', value: 'All' },
    ...uniqueGroups.map(g => ({ label: g, value: g }))
  ];

  const filteredResources = resources
    .filter(r => filter.group === 'All' || getGroup(r.service_type) === filter.group)
    .filter(r =>
      (r.name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (r.resource_id || '').toLowerCase().includes(searchQuery.toLowerCase())
    );

  const treeData = useMemo(() => buildResourceTree(filteredResources, true, expandedRowIds), [filteredResources, expandedRowIds]); // Always true (Group View)

  return (
    <div className="space-y-4 animate-in fade-in duration-300 w-full">
      
      <div className="flex items-center justify-between mb-2">
        <FilterBar
          showLabel={true}
          className="flex flex-wrap items-center gap-4"
          filters={[
            { label: "Group:", value: filter.group, onChange: v => setFilter({ ...filter, group: v }), options: groupOptions, width: "max-w-[150px]" }
          ]}
        />

        <div className="flex items-center gap-2">
          <div className="relative w-64">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-zinc-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search resources..."
              className="w-full pl-9 pr-3 py-1.5 bg-[#1e1e24] border border-zinc-800 rounded-lg text-xs text-white placeholder-zinc-500 outline-none focus:border-blue-500 transition-colors"
            />
          </div>
        </div>
      </div>

      <div className="bg-[#111114] border border-[#1f1f24] rounded-2xl shadow-xl [overflow:clip]">
        <div className="flex items-center justify-between p-4 border-b border-zinc-800/80 bg-zinc-900/50">
          <div className="text-sm font-medium text-zinc-400">
            {treeData.length} Resource{treeData.length !== 1 && 's'} Found
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleToggleAll(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-bold rounded-lg transition-colors bg-zinc-800 text-zinc-300 hover:text-white border border-zinc-700 hover:bg-zinc-700 uppercase tracking-wider"
            >
              <CheckSquare className="h-3 w-3" /> Show All
            </button>
            <button
              onClick={() => handleToggleAll(false)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-bold rounded-lg transition-colors bg-zinc-800 text-zinc-300 hover:text-white border border-zinc-700 hover:bg-zinc-700 uppercase tracking-wider"
            >
              <EyeOff className="h-3 w-3" /> Hide All
            </button>
          </div>
        </div>

        {(treeData.length === 0 && (loading || (offset === 0 && hasMore))) ? (
          <div className="p-4 space-y-4">
            <div className="h-16 bg-zinc-800/50 animate-pulse rounded-xl" />
            <div className="h-16 bg-zinc-800/50 animate-pulse rounded-xl" />
            <div className="h-16 bg-zinc-800/50 animate-pulse rounded-xl" />
          </div>
        ) : treeData.length > 0 ? (
          <Virtuoso
            useWindowScroll={!document.getElementById('main-scroll-container')}
            customScrollParent={document.getElementById('main-scroll-container')}
            data={treeData}
            endReached={loadMore}
            itemContent={(index, r) => (
              <SettingsRow
                key={r.resource_id}
                r={r}
                isGroupView={true}
                toggleRow={toggleRow}
                handleToggle={handleToggle}
              />
            )}
          />
        ) : (
          <EmptyState icon={Database} message="No resources found matching filters." height="h-[400px]" />
        )}
      </div>
    </div>
  );
}

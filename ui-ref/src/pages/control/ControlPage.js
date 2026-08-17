import { useState, useEffect } from 'react';
import { RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { getControlSummary, getFilterOptions } from '../../api/control';
import { listConfigs } from '../../api/config';
import { useControlSync } from '../../utils/syncManager';
import { FilterBar } from '../../components/ui/FilterBar';
import { OverviewTab } from './tabs/OverviewTab';
import { ActivityLogTab } from './tabs/ActivityLogTab';
import { ResourcesTab } from './tabs/ResourcesTab';
import { SettingsTab } from './tabs/SettingsTab';
import { ScrollToTopButton } from '../../components/ui/ScrollToTopButton';
import { NotificationBell } from '../../components/ui/NotificationBell';

export default function ControlPage() {
  const [activeTab, setActiveTab] = useState(() => localStorage.getItem('pulse_control_active_tab') || 'overview');
  const [summary, setSummary] = useState({ total_count: 0, running_count: 0, stopped_count: 0, terminated_count: 0, active_schedules_count: 0 });
  const [syncRefreshTrigger, setSyncRefreshTrigger] = useState(0);
  const [loadingSummary, setLoadingSummary] = useState(false);
  // Global filters mimicking the reference UI
  const [topFilters, setTopFilters] = useState({
    provider: localStorage.getItem('pulse_control_provider') || 'AWS',
    account: localStorage.getItem('pulse_control_account') || '', // Start empty or from storage
    region: 'All Regions',
    tag: 'All Tags',
    range: 30
  });

  const { syncing, startControlSync } = useControlSync(topFilters?.account);

  useEffect(() => {
    if (topFilters.provider) localStorage.setItem('pulse_control_provider', topFilters.provider);
    if (topFilters.account) localStorage.setItem('pulse_control_account', topFilters.account);
  }, [topFilters.provider, topFilters.account]);

  const [verifiedConfigs, setVerifiedConfigs] = useState([]);

  const uniqueProviders = [...new Set(verifiedConfigs.map(c => (c.provider || '').toUpperCase()))].sort();
  const availableProviders = uniqueProviders.length > 0 ? uniqueProviders : ['AWS', 'AZURE', 'GCP'];

  const filteredConfigs = verifiedConfigs.filter(c => (c.provider || '').toUpperCase() === topFilters.provider);
  const availableAccounts = filteredConfigs.map(c => c.account_name);

  const [availableRegions, setAvailableRegions] = useState(['All Regions']);
  const [availableTags, setAvailableTags] = useState(['All Tags']);

  const handleTopFilterChange = (key, value) => {
    if (key === 'provider') {
      const filtered = verifiedConfigs.filter(c => (c.provider || '').toUpperCase() === value);
      let newAccount = '';

      const stillValid = filtered.find(c => c.account_name === topFilters.account);
      if (!stillValid && filtered.length > 0) {
        newAccount = filtered[0].account_name;
      } else if (stillValid) {
        newAccount = topFilters.account;
      }

      setTopFilters(prev => ({ ...prev, provider: value, account: newAccount }));
    } else {
      setTopFilters(prev => ({ ...prev, [key]: value }));
    }
  };

  useEffect(() => {
    loadConfigs();
    loadLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadSummary();
    loadOptions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topFilters.account, topFilters.provider, topFilters.region, topFilters.tag]);

  useEffect(() => {
    const handleGlobalRefresh = () => {
      loadSummary();
      setSyncRefreshTrigger(prev => prev + 1);
    };

    window.addEventListener('app:refresh-data', handleGlobalRefresh);
    return () => window.removeEventListener('app:refresh-data', handleGlobalRefresh);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topFilters.account, topFilters.provider, topFilters.region, topFilters.tag]);

  const loadOptions = async () => {
    try {
      const options = await getFilterOptions({ account: topFilters.account, provider: topFilters.provider });
      if (options) {
        setAvailableRegions(['All Regions', ...(options.regions || [])]);
        setAvailableTags(['All Tags', ...(options.tags || [])]);
      }
    } catch (err) {
      console.error("Failed to load filter options", err);
    }
  };

  const loadLogs = async () => {
    // Action logging is handled internally by tabs, but if needed for global refresh, we could trigger an event.
    // We pass this as onActionLogged to ResourcesTab, so it can just trigger a refresh if needed.
    // Actually, since ActivityLogTab loads its own data on mount, we don't need global state.
  };

  const loadConfigs = async () => {
    try {
      const res = await listConfigs();
      const configs = res.data.configs || [];
      const vConfigs = configs.filter(c => c.verified);
      setVerifiedConfigs(vConfigs);

      if (vConfigs.length > 0) {
        // First try to restore the account saved in localStorage if it's verified
        const savedAccount = localStorage.getItem('pulse_control_account');
        const savedMatch = vConfigs.find(c => c.account_name === savedAccount);

        let currentProvider = topFilters.provider;
        let currentAccount = topFilters.account;

        if (savedMatch) {
          currentProvider = savedMatch.provider ? savedMatch.provider.toUpperCase() : 'AWS';
          currentAccount = savedMatch.account_name;
          setTopFilters(prev => ({ ...prev, provider: currentProvider, account: currentAccount }));
        }

        const providerConfigs = vConfigs.filter(c => (c.provider || '').toUpperCase() === currentProvider);

        if (providerConfigs.length > 0) {
          const hasCurrentAccount = providerConfigs.find(c => c.account_name === currentAccount);
          if (!hasCurrentAccount) {
            setTopFilters(prev => ({ ...prev, account: providerConfigs[0].account_name }));
          }
        } else {
          setTopFilters(prev => ({
            ...prev,
            provider: (vConfigs[0].provider || '').toUpperCase(),
            account: vConfigs[0].account_name
          }));
        }
      }
    } catch (err) {
      console.error("Failed to load configs", err);
    }
  };

  const handleSync = () => {
    console.log(`[Sync Process] Starting sync for account: ${topFilters.account}`);
    startControlSync(topFilters.account, async () => {
      await loadSummary();
      setSyncRefreshTrigger(prev => prev + 1);
    });
  };

  const loadSummary = async () => {
    setLoadingSummary(true);
    try {
      const summaryData = await getControlSummary(topFilters);
      if (summaryData) {
        setSummary(summaryData);
      }
    } catch (err) {
      toast.error('Failed to load summary from backend');
    } finally {
      setLoadingSummary(false);
    }
  };

  return (
    <>
      <div className="sticky -top-6 h-6 -mx-6 -mt-6 bg-[#0a0a0f]/80 backdrop-blur-md z-30 pointer-events-none" />
      <div className="space-y-6 relative">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            {topFilters.provider && (
              <img src={`/${topFilters.provider.toLowerCase()}-logo.svg`} alt="" className="h-10 w-10 object-contain shrink-0" />
            )}
            <div>
              <h1 className="text-xl font-semibold flex items-center gap-3 text-[#e4e4e7] tracking-tight">
                {topFilters.provider || 'Cloud'} - Control Insights ({topFilters.account || 'None'})
              </h1>
              <p className="text-[11px] text-[#a1a1aa] mt-1">Manage real-time execution & power scheduling for cloud resources</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <NotificationBell />
            <button onClick={handleSync} disabled={syncing} className="flex items-center gap-2 px-3 py-1.5 text-[11px] uppercase tracking-wider font-semibold bg-transparent border border-zinc-700 text-zinc-300 rounded-md hover:bg-zinc-800 disabled:opacity-50 transition-colors">
              <RefreshCw className={`h-3 w-3 ${syncing ? 'animate-spin' : ''}`} />{syncing ? 'Syncing...' : 'Sync Now'}
            </button>
          </div>
        </div>

        <FilterBar
          filters={[
            { label: "Provider:", value: topFilters.provider, onChange: v => handleTopFilterChange('provider', v), options: availableProviders.map(p => ({ label: p, value: p })), width: "max-w-[110px]" },
            { label: "Account:", value: topFilters.account, onChange: v => handleTopFilterChange('account', v), options: availableAccounts.map(a => ({ label: a, value: a })), width: "max-w-[150px]" },
            { label: "Region:", value: topFilters.region, onChange: v => handleTopFilterChange('region', v), options: availableRegions.map(r => ({ label: r, value: r })), width: "max-w-[120px]" },
            { label: "Tag:", value: topFilters.tag, onChange: v => handleTopFilterChange('tag', v), options: availableTags.map(t => ({ label: t, value: t })), width: "max-w-[150px]" },
            {
              label: "Range:",
              value: topFilters.range,
              onChange: v => handleTopFilterChange('range', v),
              options: [
                { label: 'Today', value: 1 },
                { label: 'Last 7 days', value: 7 },
                { label: 'Last 14 days', value: 14 },
                { label: 'Last 30 days', value: 30 }
              ],
              width: "w-auto"
            }
          ]}
        />

        {/* Tabs and Content Group */}
        <div>
          {/* Main Global Tab Bar */}
          <div className="border-b border-zinc-800 flex gap-6">
            {['overview', 'activity', 'resources', 'settings'].map(t => (
              <button
                key={t}
                onClick={() => {
                  setActiveTab(t);
                  localStorage.setItem('pulse_control_active_tab', t);
                }}
                className={`pb-3 text-sm font-medium border-b-2 capitalize transition-colors ${activeTab === t ? 'border-white text-white' : 'border-transparent text-zinc-500 hover:text-zinc-300'}`}
              >
                {t}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="pt-4">
            {activeTab === 'overview' && (
              <OverviewTab 
                totalCount={summary.total_count} 
                runningCount={summary.running_count} 
                stoppedCount={summary.stopped_count} 
                terminatedCount={summary.terminated_count}
                activeSchedulesCount={summary.active_schedules_count}
                typeBreakdown={summary.type_breakdown}
                regionBreakdown={summary.region_breakdown}
                topFilters={topFilters}
              />
            )}
            {activeTab === 'activity' && <ActivityLogTab topFilters={topFilters} />}
            {activeTab === 'resources' && (
              <ResourcesTab
                topFilters={topFilters}
                onActionLogged={loadLogs}
                syncRefreshTrigger={syncRefreshTrigger}
              />
            )}
            {activeTab === 'settings' && (
              <SettingsTab
                topFilters={topFilters}
              />
            )}
          </div>
        </div>

        {activeTab !== 'overview' && <ScrollToTopButton />}
      </div>
    </>
  );
}

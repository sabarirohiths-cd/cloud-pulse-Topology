import { useState, useEffect } from 'react';
import { Plus, Trash2, Clock, Cloud, MoreVertical, X, ShieldCheck, FileEdit, Server, Activity, CheckCircle2, Key, Boxes } from 'lucide-react';
import { toast } from 'sonner';
import { listConfigs, createConfig, verifyConfig, deleteConfig, updateAutoSync, editConfig, updateCredentials } from '../../api/config';
import { EmptyState } from '../../components/ui/EmptyState';

import { SyncSettingsModal } from './sections/SyncSettingsModal';
import { ProviderLogo } from '../../components/ui/ProviderLogo';

const AVAILABLE_MODULES = [
  { id: 'topology', label: 'Topology', icon: Boxes, color: 'text-purple-400', border: 'border-purple-400/30', bg: 'bg-purple-400/10' }
];

const initialProviderForm = {
  activeProvider: 'aws',
  active_modules: ['topology'],
  aws: { account_name: '', region: 'us-east-1', use_iam_role: false, access_key: '', secret_key: '', session_token: '', assume_role_arn: '', external_id: '' },
  azure: { account_name: '', tenant_id: '', subscription_id: '', use_managed_identity: false, client_id: '', client_secret: '', user_assigned_id: '', cloud_environment: 'AzurePublicCloud' },
  gcp: { account_name: '', service_account_json: '' }
};

export default function ConfigPage() {
  const [configs, setConfigs] = useState([]);
  const [activeViewProviderIndex, setActiveViewProviderIndex] = useState(0);
  const providerList = ['aws', 'azure', 'gcp'];
  
  const [showForm, setShowForm] = useState(false);
  const [providerForm, setProviderForm] = useState(initialProviderForm);
  const [saving, setSaving] = useState(false);
  const [editingConfigId, setEditingConfigId] = useState(null);

  const [syncForm, setSyncForm] = useState({ enabled: false, time: '', timezone: 'Asia/Kolkata' });
  const [showSyncModal, setShowSyncModal] = useState(false);
  const [syncConfigId, setSyncConfigId] = useState(null);
  const [actionMenuOpen, setActionMenuOpen] = useState(null);

  const [showCredsModal, setShowCredsModal] = useState(false);
  const [credsConfigId, setCredsConfigId] = useState(null);
  const [credsForm, setCredsForm] = useState({ access_key: '', secret_key: '', session_token: '' });

  useEffect(() => { load(); }, []);
  const load = async () => { try { const r = await listConfigs(); setConfigs(r.data?.configs || []); } catch { } };

  // Handle click outside to close the action menu
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (actionMenuOpen && !event.target.closest('.action-menu-container')) {
        setActionMenuOpen(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [actionMenuOpen]);

  const handleSave = async () => {
    const activeData = providerForm[providerForm.activeProvider];
    if (!activeData.account_name) { toast.error('Account name required'); return; }

    setSaving(true);
    try {
      if (editingConfigId) {
        const payload = {
          account_name: activeData.account_name,
          active_modules: providerForm.active_modules.join(','),
        };
        if (providerForm.activeProvider === 'aws') payload.default_region = activeData.region;
        await editConfig(editingConfigId, payload);
        toast.success('Config updated');
      } else {
        const payload = {
          provider: providerForm.activeProvider,
          account_name: activeData.account_name,
          default_region: providerForm.activeProvider === 'aws' ? activeData.region : 'global',
          credentials: { ...activeData },
          active_modules: providerForm.active_modules.join(',')
        };

        delete payload.credentials.account_name;
        delete payload.credentials.region;

        if (providerForm.activeProvider === 'aws') {
          payload.credentials.aws_access_key_id = payload.credentials.access_key;
          payload.credentials.aws_secret_access_key = payload.credentials.secret_key;
          payload.credentials.aws_session_token = payload.credentials.session_token;
          delete payload.credentials.access_key;
          delete payload.credentials.secret_key;
          delete payload.credentials.session_token;
        }

        await createConfig(payload);
        toast.success(`${providerForm.activeProvider.toUpperCase()} config saved`);
      }
      setShowForm(false);
      setProviderForm(initialProviderForm);
      setEditingConfigId(null);
      await load();
    } catch (e) {
      let errMessage = 'Save failed';
      const detail = e.response?.data?.detail;
      if (detail) {
        if (Array.isArray(detail)) {
          errMessage = detail.map(d => `${d.loc.join('.')}: ${d.msg}`).join(', ');
        } else {
          errMessage = detail;
        }
      }
      toast.error(errMessage);
    }
    finally { setSaving(false); }
  };

  const handleEditConfig = (c) => {
    setEditingConfigId(c.id);
    const form = { ...initialProviderForm, activeProvider: c.provider.toLowerCase(), active_modules: (c.active_modules ?? 'topology').split(',').filter(Boolean) };
    if (c.provider.toLowerCase() === 'aws') form.aws = { ...form.aws, account_name: c.account_name, region: c.region };
    else if (c.provider.toLowerCase() === 'azure') form.azure = { ...form.azure, account_name: c.account_name };
    else if (c.provider.toLowerCase() === 'gcp') form.gcp = { ...form.gcp, account_name: c.account_name };
    setProviderForm(form);
    setShowForm(true);
  };

  const handleVerify = async (id) => {
    try {
      const r = await verifyConfig(id);
      if (r.data.verified) toast.success(r.data.message);
      else toast.error(r.data.message);
      await load();
    } catch (e) { toast.error('Verification failed'); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this config?')) return;
    try { await deleteConfig(id); toast.success('Deleted'); await load(); } catch { toast.error('Delete failed'); }
  };

  const handleSaveSync = async (id) => {
    if (syncForm.enabled && !syncForm.time) {
      toast.error('Please specify a time for auto sync');
      return;
    }
    try {
      await updateAutoSync(id, syncForm.enabled, syncForm.time, syncForm.timezone);
      toast.success('Auto sync settings saved');
      setShowSyncModal(false);
      await load();
    } catch (e) { toast.error('Failed to save auto sync settings'); }
  };

  const handleSaveCreds = async () => {
    if (!credsForm.access_key && !credsForm.secret_key && !credsForm.session_token) {
      toast.error('Please provide at least one credential to update');
      return;
    }
    setSaving(true);
    try {
      await updateCredentials(credsConfigId, {
        aws_access_key_id: credsForm.access_key,
        aws_secret_access_key: credsForm.secret_key,
        aws_session_token: credsForm.session_token
      });
      toast.success('Credentials updated');
      setShowCredsModal(false);
      setCredsForm({ access_key: '', secret_key: '', session_token: '' });
      await load();
    } catch (e) {
      toast.error('Failed to update credentials');
    } finally {
      setSaving(false);
    }
  };

  const sortedConfigs = [
    ...configs.filter(c => c.provider.toLowerCase() === 'aws'),
    ...configs.filter(c => c.provider.toLowerCase() === 'azure'),
    ...configs.filter(c => c.provider.toLowerCase() === 'gcp')
  ];

  return (
    <div className="space-y-6 w-full flex-1 overflow-y-auto p-6 pb-32 relative">
      {/* Page Header */}
      <div className="flex items-center justify-between mb-8">
        
        {/* Left: Title */}
        <div>
          <h1 className="text-xl font-bold tracking-tight">Cloud Configuration</h1>
          <p className="text-sm text-zinc-500 mt-1">Connect AWS, Azure, or GCP credentials to enable discovery and automation.</p>
        </div>
        
        {/* Right: Actions & Switcher */}
        <div className="flex items-center gap-4">
          <div className="inline-flex items-center bg-zinc-900/50 p-1 rounded-lg border border-zinc-800/80 shadow-sm">
            {providerList.map((p, idx) => (
              <button
                key={p}
                onClick={() => setActiveViewProviderIndex(idx)}
                className={`px-5 py-1.5 text-[11px] font-bold uppercase tracking-widest rounded-md transition-all duration-200 ${
                  activeViewProviderIndex === idx
                    ? 'bg-zinc-800 text-white shadow-sm ring-1 ring-white/10'
                    : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50'
                }`}
              >
                {p}
              </button>
            ))}
          </div>

          <button onClick={() => { setShowForm(true); setProviderForm({...initialProviderForm, activeProvider: providerList[activeViewProviderIndex]}); setEditingConfigId(null); }} className="flex items-center gap-2 px-4 py-2 text-[13px] font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-lg shadow-blue-900/20">
            <Plus className="h-4 w-4" /> Add Connection
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      {(() => {
        const currentProvider = providerList[activeViewProviderIndex];
        const providerConfigs = configs.filter(c => c.provider.toLowerCase() === currentProvider);
        
        if (providerConfigs.length === 0) {
          return (
            <EmptyState
              icon={Cloud}
              message={`No active connections for ${currentProvider.toUpperCase()}. Click 'Add Connection' to get started.`}
              height="h-[400px]"
            />
          );
        }

        return (
          <div className="space-y-8 animate-in fade-in duration-500">
              <div key={currentProvider} className="space-y-3">
                {/* Section Header */}
                <h2 className="text-[12px] font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-2.5">
                  {currentProvider === 'aws' ? 'Amazon Web Services' : currentProvider === 'azure' ? 'Microsoft Azure' : 'Google Cloud'}
                  <span className="ml-2 px-2 py-0.5 rounded-full bg-zinc-800/80 text-[10px] text-zinc-500 border border-zinc-700/50">
                    {providerConfigs.length} Hub{providerConfigs.length !== 1 && 's'}
                  </span>
                </h2>

                {/* Table Container */}
                <div className="border border-zinc-800/80 rounded-xl bg-[#12141a] shadow-sm">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-zinc-900/50 border-b border-zinc-800/80 text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">
                        <th className="px-4 py-3.5 rounded-tl-xl">Organization / Hub</th>
                        <th className="px-4 py-3.5">Connection Status</th>
                        <th className="px-4 py-3.5">Region Scope</th>
                        <th className="px-4 py-3.5">Active Modules</th>
                        <th className="px-4 py-3.5">Auto-Sync</th>
                        <th className="px-4 py-3.5 text-right w-16 rounded-tr-xl">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800/50">
                      {providerConfigs.map((c, idx) => {
                        const isNearBottom = providerConfigs.length > 4 && idx >= providerConfigs.length - 2;
                        return (
                        <tr key={c.id} className="hover:bg-zinc-800/30 transition-colors group">

                          {/* Column 1: Account / Hub */}
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-4">
                              <ProviderLogo provider={c.provider.toLowerCase()} verified={c.verified} className="h-6 w-auto max-w-[24px] shrink-0" />
                              <div className="min-w-0">
                                <div className="text-[13px] font-semibold text-zinc-200 truncate">{c.account_name}</div>
                                <div className="flex items-center gap-2 mt-1">
                                  <span className="px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 uppercase tracking-widest font-bold text-[8px]">
                                    Master Hub
                                  </span>
                                </div>
                              </div>
                            </div>
                          </td>

                          {/* Column 2: Status */}
                          <td className="px-4 py-3 align-middle">
                            {c.verified ? (
                              <span className="inline-flex items-center gap-1.5 text-[10px] uppercase tracking-wider font-bold text-emerald-400 bg-emerald-400/10 px-2 py-1 rounded border border-emerald-400/20">
                                <span className="relative flex h-1.5 w-1.5">
                                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                  <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
                                </span>
                                Verified
                              </span>
                            ) : (
                              <div className="flex flex-col gap-1.5 items-start">
                                <span className="inline-flex items-center gap-1.5 text-[10px] uppercase tracking-wider font-bold text-zinc-400 bg-zinc-800 px-2 py-1 rounded border border-zinc-700">
                                  <span className="h-1.5 w-1.5 rounded-full bg-zinc-500"></span>
                                  Unverified
                                </span>
                                {c.last_error && c.last_error.toLowerCase().includes('expired') && (
                                  <span className="inline-flex items-center gap-1 text-[9px] uppercase tracking-wider font-semibold text-rose-400 bg-rose-400/10 px-1.5 py-0.5 rounded border border-rose-400/20">
                                    Token Expired
                                  </span>
                                )}
                              </div>
                            )}
                          </td>

                          {/* Column 3: Region */}
                          <td className="px-4 py-3 align-middle">
                            <span className="text-[12px] text-zinc-300 font-medium bg-zinc-900/50 px-2.5 py-1 rounded-md border border-zinc-800/80">
                              {c.region || 'Global'}
                            </span>
                          </td>

                          {/* Column 4: Active Modules */}
                          <td className="px-4 py-3 align-middle">
                            <div className="flex flex-wrap gap-1.5">
                              {(c.active_modules ?? 'topology').split(',').filter(Boolean).map(m => {
                                const mod = AVAILABLE_MODULES.find(mod => mod.id === m);
                                const label = mod ? mod.label : m;
                                const colorClass = mod ? mod.color : 'text-zinc-400';
                                const bgClass = mod ? mod.bg : 'bg-zinc-800';
                                const borderClass = mod ? mod.border : 'border-zinc-700';
                                return (
                                  <div key={m} className={`flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold tracking-widest uppercase border ${bgClass} ${borderClass} ${colorClass}`}>
                                    {label}
                                  </div>
                                );
                              })}
                            </div>
                          </td>

                          {/* Column 5: Sync */}
                          <td className="px-4 py-3 align-middle">
                            {c.auto_sync_enabled ? (
                              <div className="flex flex-col items-start gap-0.5">
                                <span className="text-[12px] font-medium text-zinc-300 flex items-center gap-1.5">
                                  <Clock className="w-3.5 h-3.5 text-blue-400" /> {c.auto_sync_time}
                                </span>
                                <span className="text-[10px] text-zinc-500 pl-5">{c.auto_sync_timezone}</span>
                              </div>
                            ) : (
                              <span className="text-[11px] font-medium text-zinc-600 bg-zinc-900/50 px-2 py-0.5 rounded border border-zinc-800/50">Disabled</span>
                            )}
                          </td>

                          {/* Column 6: Actions */}
                          <td className="px-4 py-3 text-right align-middle">
                            <div className="relative inline-block text-left action-menu-container">
                              <button onClick={() => setActionMenuOpen(actionMenuOpen === c.id ? null : c.id)} className="p-1.5 text-zinc-400 hover:text-white rounded-md hover:bg-zinc-800 transition-colors">
                                <MoreVertical className="h-5 w-5" />
                              </button>

                              {actionMenuOpen === c.id && (
                                <div className={`absolute right-0 ${isNearBottom ? 'bottom-full mb-1' : 'top-full mt-1'} w-48 bg-[#1a1d24] border border-zinc-700 rounded-lg shadow-2xl py-1 z-50 animate-in fade-in zoom-in-95 duration-100`}>
                                  <button onClick={() => { setActionMenuOpen(null); handleVerify(c.id); }} className="w-full text-left px-3 py-2 text-[12px] text-zinc-300 hover:text-white hover:bg-zinc-800/80 flex items-center gap-2 transition-colors">
                                    <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" /> Verify Connection
                                  </button>
                                  <button onClick={() => { setActionMenuOpen(null); handleEditConfig(c); }} className="w-full text-left px-3 py-2 text-[12px] text-zinc-300 hover:text-white hover:bg-zinc-800/80 flex items-center gap-2 transition-colors">
                                    <FileEdit className="h-3.5 w-3.5 text-blue-400" /> Edit Details
                                  </button>
                                  {c.provider === 'aws' && (
                                    <button onClick={() => {
                                      setActionMenuOpen(null);
                                      setCredsConfigId(c.id);
                                      setCredsForm({ access_key: '', secret_key: '', session_token: '' });
                                      setShowCredsModal(true);
                                    }} className="w-full text-left px-3 py-2 text-[12px] text-zinc-300 hover:text-white hover:bg-zinc-800/80 flex items-center gap-2 transition-colors">
                                      <Key className="h-3.5 w-3.5 text-amber-400" /> Update Credentials
                                    </button>
                                  )}
                                  <button onClick={() => {
                                    setActionMenuOpen(null);
                                    setSyncConfigId(c.id);
                                    setSyncForm({ enabled: c.auto_sync_enabled || false, time: c.auto_sync_time || '', timezone: c.auto_sync_timezone || 'Asia/Kolkata' });
                                    setShowSyncModal(true);
                                  }} className="w-full text-left px-3 py-2 text-[12px] text-zinc-300 hover:text-white hover:bg-zinc-800/80 flex items-center gap-2 transition-colors">
                                    <Clock className="h-3.5 w-3.5 text-purple-400" /> Sync Settings
                                  </button>
                                  <div className="my-1 h-px bg-zinc-800" />
                                  <button onClick={() => { setActionMenuOpen(null); handleDelete(c.id); }} className="w-full text-left px-3 py-2 text-[12px] text-red-400 hover:text-red-300 hover:bg-red-950/50 flex items-center gap-2 transition-colors">
                                    <Trash2 className="h-3.5 w-3.5" /> Delete Connection
                                  </button>
                                </div>
                              )}
                            </div>
                          </td>

                        </tr>
                      )})}
                    </tbody>
                  </table>
                </div>
              </div>
          </div>
        );
      })()}

      {/* Modal Form */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => { setShowForm(false); setProviderForm(initialProviderForm); setEditingConfigId(null); }} />
          <div className="relative w-full max-w-[480px] bg-[#0e1015] border border-zinc-800 rounded-xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden animate-in zoom-in-95 duration-200">

            {/* Drawer Header */}
            <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between bg-zinc-900/20">
              <h2 className="text-sm font-semibold text-white">{editingConfigId ? 'Edit Cloud Connection' : 'Add Cloud Connection'}</h2>
              <button onClick={() => { setShowForm(false); setProviderForm(initialProviderForm); setEditingConfigId(null); }} className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-md transition-colors">
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Drawer Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">

              <div className="space-y-4">
                <h3 className="text-[11px] font-bold tracking-widest text-zinc-500 uppercase">Provider Details</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-[10px] text-zinc-500 block mb-1 font-medium">Cloud Provider</label>
                    <select value={providerForm.activeProvider} onChange={e => setProviderForm({ ...initialProviderForm, activeProvider: e.target.value })} disabled={!!editingConfigId} className="w-full text-[11px] bg-zinc-900 border border-zinc-700 rounded-lg px-2 py-1.5 text-white disabled:opacity-50 focus:border-blue-500 outline-none transition-colors">
                      <option value="aws">Amazon Web Services</option><option value="azure">Microsoft Azure</option><option value="gcp">Google Cloud Platform</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] text-zinc-500 block mb-1 font-medium">Account Name</label>
                    <input value={providerForm[providerForm.activeProvider].account_name} onChange={e => setProviderForm({ ...providerForm, [providerForm.activeProvider]: { ...providerForm[providerForm.activeProvider], account_name: e.target.value } })} className="w-full text-[11px] bg-zinc-900 border border-zinc-700 rounded-lg px-2 py-1.5 text-white focus:border-blue-500 outline-none transition-colors" placeholder="e.g. Production AWS" />
                  </div>
                </div>

                {providerForm.activeProvider === 'aws' && (
                  <div>
                    <label className="text-[10px] text-zinc-500 block mb-1 font-medium">Region (optional)</label>
                    <input value={providerForm.aws.region} onChange={e => setProviderForm({ ...providerForm, aws: { ...providerForm.aws, region: e.target.value } })} className="w-full text-[11px] bg-zinc-900 border border-zinc-700 rounded-lg px-2 py-1.5 text-white focus:border-blue-500 outline-none transition-colors" placeholder="e.g. us-east-1 (Leave blank to auto-discover)" />
                  </div>
                )}
                {providerForm.activeProvider === 'azure' && (
                  <div>
                    <label className="text-[10px] text-zinc-500 block mb-1 font-medium">Subscription ID (optional)</label>
                    <input value={providerForm.azure.subscription_id} onChange={e => setProviderForm({ ...providerForm, azure: { ...providerForm.azure, subscription_id: e.target.value } })} className="w-full text-[11px] bg-zinc-900 border border-zinc-700 rounded-lg px-2 py-1.5 text-white font-mono focus:border-blue-500 outline-none transition-colors" placeholder="Leave blank to scan all subscriptions" />
                  </div>
                )}
              </div>

              {!editingConfigId && (
                <div className="space-y-4 pt-2">
                  <h3 className="text-[11px] font-bold tracking-widest text-zinc-500 uppercase">Authentication Credentials</h3>

                  {/* AWS Credentials */}
                  {providerForm.activeProvider === 'aws' && (
                    <div className="space-y-3 bg-zinc-900/50 p-3 rounded-xl border border-zinc-800/80">
                      <label className="flex items-center gap-2.5 text-[13px] text-white cursor-pointer select-none">
                        <input type="checkbox" checked={providerForm.aws.use_iam_role} onChange={e => setProviderForm({ ...providerForm, aws: { ...providerForm.aws, use_iam_role: e.target.checked } })} className="w-4 h-4 rounded border-zinc-700 bg-zinc-800 text-blue-500 focus:ring-blue-500/20" />
                        Use AWS IAM Role
                      </label>
                      {!providerForm.aws.use_iam_role && (
                        <div className="space-y-4 pt-2">
                          <div className="grid grid-cols-2 gap-4">
                            <div><label className="text-[10px] text-zinc-500 block mb-1">Access Key ID</label>
                              <input value={providerForm.aws.access_key} onChange={e => setProviderForm({ ...providerForm, aws: { ...providerForm.aws, access_key: e.target.value } })} className="w-full text-[11px] bg-zinc-950 border border-zinc-700/80 rounded-lg px-2 py-1.5 text-white font-mono focus:border-blue-500 outline-none" placeholder="AKIAIOSFODNN7EXAMPLE" /></div>
                            <div><label className="text-[10px] text-zinc-500 block mb-1">Secret Access Key</label>
                              <input type="password" value={providerForm.aws.secret_key} onChange={e => setProviderForm({ ...providerForm, aws: { ...providerForm.aws, secret_key: e.target.value } })} className="w-full text-[11px] bg-zinc-950 border border-zinc-700/80 rounded-lg px-2 py-1.5 text-white font-mono focus:border-blue-500 outline-none" placeholder="••••••••" /></div>
                          </div>
                          <div><label className="text-[10px] text-zinc-500 block mb-1">AWS Session Token (optional)</label>
                            <input type="password" value={providerForm.aws.session_token} onChange={e => setProviderForm({ ...providerForm, aws: { ...providerForm.aws, session_token: e.target.value } })} className="w-full text-[11px] bg-zinc-950 border border-zinc-700/80 rounded-lg px-2 py-1.5 text-white font-mono focus:border-blue-500 outline-none" placeholder="IQoJb3JpZ2luX2Vj..." /></div>
                        </div>
                      )}
                      <div className="grid grid-cols-2 gap-4 pt-2">
                        <div><label className="text-[10px] text-zinc-500 block mb-1">Assume Role ARN (optional)</label>
                          <input value={providerForm.aws.assume_role_arn} onChange={e => setProviderForm({ ...providerForm, aws: { ...providerForm.aws, assume_role_arn: e.target.value } })} className="w-full text-[11px] bg-zinc-950 border border-zinc-700/80 rounded-lg px-2 py-1.5 text-white font-mono focus:border-blue-500 outline-none" placeholder="arn:aws:iam::..." /></div>
                        <div><label className="text-[10px] text-zinc-500 block mb-1">External ID (optional)</label>
                          <input value={providerForm.aws.external_id} onChange={e => setProviderForm({ ...providerForm, aws: { ...providerForm.aws, external_id: e.target.value } })} className="w-full text-[11px] bg-zinc-950 border border-zinc-700/80 rounded-lg px-2 py-1.5 text-white font-mono focus:border-blue-500 outline-none" /></div>
                      </div>
                    </div>
                  )}

                  {/* Azure Credentials */}
                  {providerForm.activeProvider === 'azure' && (
                    <div className="space-y-3 bg-zinc-900/50 p-3 rounded-xl border border-zinc-800/80">
                      <div className="grid grid-cols-2 gap-4">
                        <div><label className="text-[10px] text-zinc-500 block mb-1">Directory (Tenant) ID</label>
                          <input value={providerForm.azure.tenant_id} onChange={e => setProviderForm({ ...providerForm, azure: { ...providerForm.azure, tenant_id: e.target.value } })} className="w-full text-[11px] bg-zinc-950 border border-zinc-700/80 rounded-lg px-2 py-1.5 text-white font-mono focus:border-blue-500 outline-none" placeholder="xxxx-xxxx-xxxx-xxxx" /></div>
                        <div><label className="text-[10px] text-zinc-500 block mb-1">Azure Cloud Environment</label>
                          <select value={providerForm.azure.cloud_environment} onChange={e => setProviderForm({ ...providerForm, azure: { ...providerForm.azure, cloud_environment: e.target.value } })} className="w-full text-[11px] bg-zinc-950 border border-zinc-700/80 rounded-lg px-2 py-1.5 text-white focus:border-blue-500 outline-none">
                            <option value="AzurePublicCloud">AzurePublicCloud</option>
                            <option value="AzureUSGovernmentCloud">AzureUSGovernmentCloud</option>
                            <option value="AzureChinaCloud">AzureChinaCloud</option>
                          </select></div>
                      </div>

                      <label className="flex items-center gap-2.5 text-[13px] text-white cursor-pointer select-none pt-2">
                        <input type="checkbox" checked={providerForm.azure.use_managed_identity} onChange={e => setProviderForm({ ...providerForm, azure: { ...providerForm.azure, use_managed_identity: e.target.checked } })} className="w-4 h-4 rounded border-zinc-700 bg-zinc-800 text-blue-500 focus:ring-blue-500/20" />
                        Use Managed Identity (VM Profile)
                      </label>

                      {!providerForm.azure.use_managed_identity ? (
                        <div className="grid grid-cols-2 gap-4 pt-2">
                          <div><label className="text-[10px] text-zinc-500 block mb-1">Application (Client) ID</label>
                            <input value={providerForm.azure.client_id} onChange={e => setProviderForm({ ...providerForm, azure: { ...providerForm.azure, client_id: e.target.value } })} className="w-full text-[11px] bg-zinc-950 border border-zinc-700/80 rounded-lg px-2 py-1.5 text-white font-mono focus:border-blue-500 outline-none" placeholder="xxxx-xxxx-xxxx-xxxx" /></div>
                          <div><label className="text-[10px] text-zinc-500 block mb-1">Client Secret</label>
                            <input type="password" value={providerForm.azure.client_secret} onChange={e => setProviderForm({ ...providerForm, azure: { ...providerForm.azure, client_secret: e.target.value } })} className="w-full text-[11px] bg-zinc-950 border border-zinc-700/80 rounded-lg px-2 py-1.5 text-white font-mono focus:border-blue-500 outline-none" placeholder="••••••••" /></div>
                        </div>
                      ) : (
                        <div className="pt-2"><label className="text-[10px] text-zinc-500 block mb-1">User-Assigned Identity Client ID (optional)</label>
                          <input value={providerForm.azure.user_assigned_id} onChange={e => setProviderForm({ ...providerForm, azure: { ...providerForm.azure, user_assigned_id: e.target.value } })} className="w-full text-[11px] bg-zinc-950 border border-zinc-700/80 rounded-lg px-2 py-1.5 text-white font-mono focus:border-blue-500 outline-none" placeholder="xxxx-xxxx-xxxx-xxxx" /></div>
                      )}
                    </div>
                  )}

                  {/* GCP Credentials */}
                  {providerForm.activeProvider === 'gcp' && (
                    <div className="space-y-3 bg-zinc-900/50 p-3 rounded-xl border border-zinc-800/80">
                      <div><label className="text-[10px] text-zinc-500 block mb-1">Service Account Private Key JSON</label>
                        <textarea value={providerForm.gcp.service_account_json} onChange={e => setProviderForm({ ...providerForm, gcp: { ...providerForm.gcp, service_account_json: e.target.value } })} className="w-full h-40 text-[12px] bg-zinc-950 border border-zinc-700/80 rounded-lg px-2 py-1.5 text-white font-mono resize-none focus:border-blue-500 outline-none" placeholder={`{
                        "type": "service_account",
                        "project_id": "...",
  "private_key": "..."
}`} /></div>
                    </div>
                  )}
                </div>
              )}

              {/* Active Modules Selection */}
              <div className="space-y-3 pt-2">
                <h3 className="text-[10px] font-bold tracking-widest text-zinc-500 uppercase">Active Modules</h3>
                <div className="grid grid-cols-2 gap-2">
                  {AVAILABLE_MODULES.map(m => {
                    const isActive = providerForm.active_modules.includes(m.id);
                    const Icon = m.icon;
                    return (
                      <div
                        key={m.id}
                        onClick={() => {
                          let next = [...providerForm.active_modules];
                          if (!isActive) next.push(m.id);
                          else next = next.filter(i => i !== m.id);
                          setProviderForm({ ...providerForm, active_modules: next });
                        }}
                        className={`cursor-pointer rounded-lg p-2 border transition-all select-none ${isActive ? 'bg-zinc-800 border-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.1)]' : 'bg-zinc-900/50 border-zinc-800 hover:border-zinc-700'}`}
                      >
                        <div className="flex items-center gap-2">
                          <div className={`p-1.5 rounded-md ${isActive ? m.bg + ' ' + m.color : 'bg-zinc-800 text-zinc-500'}`}>
                            <Icon className="h-4 w-4" />
                          </div>
                          <div>
                            <p className={`text-[10px] font-semibold ${isActive ? 'text-white' : 'text-zinc-400'}`}>{m.label}</p>
                            <p className="text-[9px] text-zinc-500 mt-0.5">{isActive ? 'Enabled' : 'Disabled'}</p>
                          </div>
                          {isActive && <CheckCircle2 className="h-3 w-3 text-blue-500 ml-auto" />}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Drawer Footer */}
            <div className="px-4 py-3 border-t border-zinc-800 bg-zinc-900/20 flex justify-end gap-3">
              <button onClick={() => { setShowForm(false); setProviderForm(initialProviderForm); setEditingConfigId(null); }} className="px-4 py-2 text-[13px] font-medium text-zinc-400 bg-transparent rounded-lg hover:bg-zinc-800 transition-colors">Cancel</button>
              <button onClick={handleSave} disabled={saving} className="px-6 py-2 text-[13px] font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors shadow-lg shadow-blue-900/20">{saving ? 'Saving...' : 'Save Configuration'}</button>
            </div>
          </div>
        </div>
      )}

      {/* Sync Modal Overlay */}
      <SyncSettingsModal
        show={showSyncModal}
        onClose={() => setShowSyncModal(false)}
        syncForm={syncForm}
        setSyncForm={setSyncForm}
        onSave={handleSaveSync}
        configId={syncConfigId}
      />

      {/* Credentials Modal */}
      {showCredsModal && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowCredsModal(false)} />
          <div className="relative w-[480px] bg-[#12141a] border border-zinc-800 rounded-xl shadow-2xl p-6 animate-in zoom-in-95 duration-100">
            <h3 className="text-sm font-semibold text-white mb-1">Update AWS Credentials</h3>
            <p className="text-[12px] text-zinc-400 mb-6">Enter new values. Only the fields you fill in will be updated.</p>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-[10px] text-zinc-500 block mb-1">Access Key ID (optional)</label>
                  <input value={credsForm.access_key} onChange={e => setCredsForm({ ...credsForm, access_key: e.target.value })} className="w-full text-[11px] bg-zinc-950 border border-zinc-700/80 rounded-lg px-2 py-1.5 text-white font-mono focus:border-amber-500 outline-none" placeholder="AKIAIOSFODNN7EXAMPLE" />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-500 block mb-1">Secret Access Key (optional)</label>
                  <input type="password" value={credsForm.secret_key} onChange={e => setCredsForm({ ...credsForm, secret_key: e.target.value })} className="w-full text-[11px] bg-zinc-950 border border-zinc-700/80 rounded-lg px-2 py-1.5 text-white font-mono focus:border-amber-500 outline-none" placeholder="••••••••" />
                </div>
              </div>
              <div>
                <label className="text-[10px] text-zinc-500 block mb-1">AWS Session Token (optional)</label>
                <input type="password" value={credsForm.session_token} onChange={e => setCredsForm({ ...credsForm, session_token: e.target.value })} className="w-full text-[11px] bg-zinc-950 border border-zinc-700/80 rounded-lg px-2 py-1.5 text-white font-mono focus:border-amber-500 outline-none" placeholder="IQoJb3JpZ2luX2Vj..." />
              </div>
            </div>

            <div className="flex gap-3 justify-end mt-8">
              <button onClick={() => setShowCredsModal(false)} className="px-4 py-2 text-[13px] font-medium text-zinc-400 hover:bg-zinc-800 rounded-lg transition-colors">Cancel</button>
              <button onClick={handleSaveCreds} disabled={saving} className="px-5 py-2 text-[13px] font-medium bg-amber-500 text-black rounded-lg hover:bg-amber-400 shadow-lg shadow-amber-900/20 transition-colors disabled:opacity-50">
                {saving ? 'Updating...' : 'Update Credentials'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

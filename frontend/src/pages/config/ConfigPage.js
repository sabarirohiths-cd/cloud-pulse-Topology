import { useState, useEffect } from 'react';
import { Plus, Trash2, Clock, Cloud } from 'lucide-react';
import { toast } from 'sonner';
import { listConfigs, createConfig, verifyConfig, deleteConfig, updateAutoSync } from '../../api/config';
import { CustomSelect } from '../../components/ui/CustomSelect';
import { EmptyState } from '../../components/ui/EmptyState';

const ProviderLogo = ({ provider, verified }) => {
  const isGrayscale = !verified;

  if (provider === 'aws') {
    return <img src="/aws-logo.svg" alt="AWS" className={`h-6 w-auto max-w-[40px] object-contain ${isGrayscale ? 'grayscale opacity-50' : ''}`} />;
  }
  if (provider === 'azure') {
    return <img src="/azure-logo.svg" alt="Azure" className={`h-6 w-auto max-w-[40px] object-contain ${isGrayscale ? 'grayscale opacity-50' : ''}`} />;
  }
  if (provider === 'gcp') {
    return <img src="/gcp-logo.svg" alt="GCP" className={`h-6 w-auto max-w-[40px] object-contain ${isGrayscale ? 'grayscale opacity-50' : ''}`} />;
  }
  return <Cloud className={`h-6 w-6 ${isGrayscale ? 'text-zinc-500' : 'text-blue-400'}`} />;
};

const TIMEZONES = [
  { label: 'IST (Asia/Kolkata)', value: 'Asia/Kolkata' },
  { label: 'UTC', value: 'UTC' },
  { label: 'EST (America/New_York)', value: 'America/New_York' },
  { label: 'CST (America/Chicago)', value: 'America/Chicago' },
  { label: 'MST (America/Denver)', value: 'America/Denver' },
  { label: 'PST (America/Los_Angeles)', value: 'America/Los_Angeles' },
  { label: 'GMT (Europe/London)', value: 'Europe/London' },
  { label: 'CET (Europe/Paris)', value: 'Europe/Paris' },
  { label: 'JST (Asia/Tokyo)', value: 'Asia/Tokyo' },
  { label: 'AEST (Australia/Sydney)', value: 'Australia/Sydney' },
  { label: 'GST (Asia/Dubai)', value: 'Asia/Dubai' },
  { label: 'SGT (Asia/Singapore)', value: 'Asia/Singapore' }
];

const initialProviderForm = {
  activeProvider: 'aws',
  aws: { account_name: '', region: 'us-east-1', use_iam_role: false, access_key: '', secret_key: '', session_token: '', assume_role_arn: '', external_id: '' },
  azure: { account_name: '', tenant_id: '', subscription_id: '', use_managed_identity: false, client_id: '', client_secret: '', user_assigned_id: '', cloud_environment: 'AzurePublicCloud' },
  gcp: { account_name: '', service_account_json: '' }
};

export default function ConfigPage() {
  const [configs, setConfigs] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [providerForm, setProviderForm] = useState(initialProviderForm);
  const [saving, setSaving] = useState(false);
  const [editingSync, setEditingSync] = useState(null);
  const [syncForm, setSyncForm] = useState({ enabled: false, time: '', timezone: 'Asia/Kolkata' });

  useEffect(() => { load(); }, []);
  const load = async () => { try { const r = await listConfigs(); setConfigs(r.data?.configs || []); } catch { } };

  const handleSave = async () => {
    const activeData = providerForm[providerForm.activeProvider];
    if (!activeData.account_name) { toast.error('Account name required'); return; }

    setSaving(true);
    try {
      const payload = {
        provider: providerForm.activeProvider,
        account_name: activeData.account_name,
        default_region: providerForm.activeProvider === 'aws' ? activeData.region : 'global',
        credentials: { ...activeData }
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
      setShowForm(false);
      setProviderForm(initialProviderForm);
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
      setEditingSync(null);
      await load();
    } catch (e) { toast.error('Failed to save auto sync settings'); }
  };

  return (
    <div className="space-y-5 w-full">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold">Cloud Configuration</h1><p className="text-sm text-zinc-500">Add AWS, Azure, or GCP credentials for resource discovery</p></div>
        <button onClick={() => { setShowForm(!showForm); if (showForm) setProviderForm(initialProviderForm); }} className="flex items-center gap-2 px-4 py-2 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          <Plus className="h-3.5 w-3.5" /> Add Config
        </button>
      </div>

      {/* Add Form */}
      {showForm && (
        <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-xl p-5 space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div><label className="text-[10px] text-zinc-500 uppercase block mb-1">Provider</label>
              <select value={providerForm.activeProvider} onChange={e => setProviderForm({ ...initialProviderForm, activeProvider: e.target.value })} className="w-full text-xs bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white">
                <option value="aws">AWS</option><option value="azure">Azure</option><option value="gcp">GCP</option>
              </select></div>
            <div><label className="text-[10px] text-zinc-500 uppercase block mb-1">Account Name</label>
              <input value={providerForm[providerForm.activeProvider].account_name} onChange={e => setProviderForm({ ...providerForm, [providerForm.activeProvider]: { ...providerForm[providerForm.activeProvider], account_name: e.target.value } })} className="w-full text-xs bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white" placeholder="My Cloud Account" /></div>

            {providerForm.activeProvider === 'aws' && (
              <div><label className="text-[10px] text-zinc-500 uppercase block mb-1">Region (optional)</label>
                <input value={providerForm.aws.region} onChange={e => setProviderForm({ ...providerForm, aws: { ...providerForm.aws, region: e.target.value } })} className="w-full text-xs bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white" placeholder="Leave blank to auto-discover" /></div>
            )}
            {providerForm.activeProvider === 'azure' && (
              <div><label className="text-[10px] text-zinc-500 uppercase block mb-1">Subscription ID (optional)</label>
                <input value={providerForm.azure.subscription_id} onChange={e => setProviderForm({ ...providerForm, azure: { ...providerForm.azure, subscription_id: e.target.value } })} className="w-full text-xs bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white font-mono" placeholder="Leave blank to scan all subscriptions" /></div>
            )}

          </div>

          {/* AWS Block */}
          {providerForm.activeProvider === 'aws' && (
            <div className="space-y-3">
              <label className="flex items-center gap-2 text-xs text-zinc-300">
                <input type="checkbox" checked={providerForm.aws.use_iam_role} onChange={e => setProviderForm({ ...providerForm, aws: { ...providerForm.aws, use_iam_role: e.target.checked } })} className="rounded" />
                Use IAM Role (EC2 instance profile)
              </label>
              {!providerForm.aws.use_iam_role && (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div><label className="text-[10px] text-zinc-500 uppercase block mb-1">Access Key</label>
                      <input value={providerForm.aws.access_key} onChange={e => setProviderForm({ ...providerForm, aws: { ...providerForm.aws, access_key: e.target.value } })} className="w-full text-xs bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white font-mono" placeholder="AKIAIOSFODNN7EXAMPLE" /></div>
                    <div><label className="text-[10px] text-zinc-500 uppercase block mb-1">Secret Key</label>
                      <input type="password" value={providerForm.aws.secret_key} onChange={e => setProviderForm({ ...providerForm, aws: { ...providerForm.aws, secret_key: e.target.value } })} className="w-full text-xs bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white font-mono" placeholder="••••••••" /></div>
                  </div>
                  <div><label className="text-[10px] text-zinc-500 uppercase block mb-1">AWS Session Token (optional)</label>
                    <input type="password" value={providerForm.aws.session_token} onChange={e => setProviderForm({ ...providerForm, aws: { ...providerForm.aws, session_token: e.target.value } })} className="w-full text-xs bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white font-mono" placeholder="IQoJb3JpZ2luX2Vj..." /></div>
                </div>
              )}
              <div className="grid grid-cols-2 gap-3">
                <div><label className="text-[10px] text-zinc-500 uppercase block mb-1">Assume Role ARN (optional)</label>
                  <input value={providerForm.aws.assume_role_arn} onChange={e => setProviderForm({ ...providerForm, aws: { ...providerForm.aws, assume_role_arn: e.target.value } })} className="w-full text-xs bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white font-mono" placeholder="arn:aws:iam::123456789:role/..." /></div>
                <div><label className="text-[10px] text-zinc-500 uppercase block mb-1">External ID (optional)</label>
                  <input value={providerForm.aws.external_id} onChange={e => setProviderForm({ ...providerForm, aws: { ...providerForm.aws, external_id: e.target.value } })} className="w-full text-xs bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white font-mono" /></div>
              </div>
            </div>
          )}

          {/* Azure Block */}
          {providerForm.activeProvider === 'azure' && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div><label className="text-[10px] text-zinc-500 uppercase block mb-1">Directory (Tenant) ID</label>
                  <input value={providerForm.azure.tenant_id} onChange={e => setProviderForm({ ...providerForm, azure: { ...providerForm.azure, tenant_id: e.target.value } })} className="w-full text-xs bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white font-mono" placeholder="xxxx-xxxx-xxxx-xxxx" /></div>
                <div><label className="text-[10px] text-zinc-500 uppercase block mb-1">Azure Cloud Environment</label>
                  <select value={providerForm.azure.cloud_environment} onChange={e => setProviderForm({ ...providerForm, azure: { ...providerForm.azure, cloud_environment: e.target.value } })} className="w-full text-xs bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white">
                    <option value="AzurePublicCloud">AzurePublicCloud</option>
                    <option value="AzureUSGovernmentCloud">AzureUSGovernmentCloud</option>
                    <option value="AzureChinaCloud">AzureChinaCloud</option>
                  </select></div>
              </div>

              <label className="flex items-center gap-2 text-xs text-zinc-300">
                <input type="checkbox" checked={providerForm.azure.use_managed_identity} onChange={e => setProviderForm({ ...providerForm, azure: { ...providerForm.azure, use_managed_identity: e.target.checked } })} className="rounded" />
                Use Managed Identity (VM Profile)
              </label>

              {!providerForm.azure.use_managed_identity ? (
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="text-[10px] text-zinc-500 uppercase block mb-1">Application (Client) ID</label>
                    <input value={providerForm.azure.client_id} onChange={e => setProviderForm({ ...providerForm, azure: { ...providerForm.azure, client_id: e.target.value } })} className="w-full text-xs bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white font-mono" placeholder="xxxx-xxxx-xxxx-xxxx" /></div>
                  <div><label className="text-[10px] text-zinc-500 uppercase block mb-1">Client Secret</label>
                    <input type="password" value={providerForm.azure.client_secret} onChange={e => setProviderForm({ ...providerForm, azure: { ...providerForm.azure, client_secret: e.target.value } })} className="w-full text-xs bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white font-mono" placeholder="••••••••" /></div>
                </div>
              ) : (
                <div><label className="text-[10px] text-zinc-500 uppercase block mb-1">User-Assigned Identity Client ID (optional)</label>
                  <input value={providerForm.azure.user_assigned_id} onChange={e => setProviderForm({ ...providerForm, azure: { ...providerForm.azure, user_assigned_id: e.target.value } })} className="w-full text-xs bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white font-mono" placeholder="xxxx-xxxx-xxxx-xxxx" /></div>
              )}
            </div>
          )}

          {/* GCP Block */}
          {providerForm.activeProvider === 'gcp' && (
            <div className="space-y-3">


              <div><label className="text-[10px] text-zinc-500 uppercase block mb-1">Service Account Private Key Configuration</label>
                <textarea value={providerForm.gcp.service_account_json} onChange={e => setProviderForm({ ...providerForm, gcp: { ...providerForm.gcp, service_account_json: e.target.value } })} className="w-full h-32 text-xs bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white font-mono resize-none" placeholder={'{\n  "type": "service_account",\n  "project_id": "...",\n  "private_key": "..."\n}'} /></div>
            </div>
          )}

          <div className="flex gap-2">
            <button onClick={handleSave} disabled={saving} className="px-4 py-2 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">{saving ? 'Saving...' : 'Save'}</button>
            <button onClick={() => { setShowForm(false); setProviderForm(initialProviderForm); }} className="px-4 py-2 text-xs text-zinc-400 border border-zinc-700 rounded-lg hover:bg-zinc-800">Cancel</button>
          </div>
        </div>
      )}

      {/* Config List */}
      <div className="space-y-2">
        {configs.map(c => (
          <div key={c.id} className="bg-zinc-900/50 border border-zinc-800/50 rounded-xl">
            <div className="p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <ProviderLogo provider={c.provider.toLowerCase()} verified={c.verified} />
                <div>
                  <span className="text-sm text-white font-medium">{c.account_name}</span>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] text-zinc-500 uppercase">{c.provider}</span>
                    <span className="text-[10px] text-zinc-600">•</span>
                    <span className="text-[10px] text-zinc-500">{c.region}</span>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${c.verified ? 'bg-green-500/10 text-green-400' : 'bg-zinc-700/50 text-zinc-500'}`}>{c.verified ? 'Verified' : 'Unverified'}</span>
                    {c.auto_sync_enabled && <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 flex items-center gap-1"><Clock className="h-2.5 w-2.5" /> {c.auto_sync_time} {c.auto_sync_timezone}</span>}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => {
                  if (editingSync === c.id) setEditingSync(null);
                  else { setEditingSync(c.id); setSyncForm({ enabled: c.auto_sync_enabled || false, time: c.auto_sync_time || '', timezone: c.auto_sync_timezone || 'Asia/Kolkata' }); }
                }} className="text-[10px] text-zinc-400 hover:text-white px-2 py-1 rounded hover:bg-zinc-800">Auto Sync</button>
                <button onClick={() => handleVerify(c.id)} className="text-[10px] text-blue-400 hover:text-blue-300 px-2 py-1 rounded hover:bg-blue-500/10">Verify</button>
                <button onClick={() => handleDelete(c.id)} className="text-zinc-500 hover:text-red-400 p-1 rounded hover:bg-red-500/10"><Trash2 className="h-3.5 w-3.5" /></button>
              </div>
            </div>

            {editingSync === c.id && (
              <div className="px-5 py-4 bg-zinc-950/50 border-t border-zinc-800/50 flex items-center gap-5 flex-wrap rounded-b-xl">
                <div className="flex items-center gap-4 bg-zinc-900 border border-zinc-800 rounded-lg p-1.5 px-3">
                  <label className="flex items-center gap-2 text-xs font-medium text-zinc-300 cursor-pointer">
                    <input type="radio" name={`sync-${c.id}`} checked={syncForm.enabled} onChange={() => setSyncForm({ ...syncForm, enabled: true })} className="accent-blue-500 w-3.5 h-3.5" /> Enable
                  </label>
                  <span className="w-px h-4 bg-zinc-700"></span>
                  <label className="flex items-center gap-2 text-xs font-medium text-zinc-400 cursor-pointer">
                    <input type="radio" name={`sync-${c.id}`} checked={!syncForm.enabled} onChange={() => setSyncForm({ ...syncForm, enabled: false })} className="accent-zinc-500 w-3.5 h-3.5" /> Disable
                  </label>
                </div>

                {syncForm.enabled && (
                  <>
                    <div className="flex items-center bg-[#1e1e24] border border-zinc-800 rounded-md px-3 py-1.5 focus-within:border-blue-500 transition-colors">
                      <span className="text-xs text-zinc-400 mr-2">Time:</span>
                      <input type="time" value={syncForm.time} onChange={e => setSyncForm({ ...syncForm, time: e.target.value })} className="text-xs font-semibold text-zinc-200 bg-transparent outline-none w-[50px] hide-time-icon" />
                    </div>

                    <CustomSelect
                      label=""
                      value={syncForm.timezone}
                      onChange={v => setSyncForm({ ...syncForm, timezone: v })}
                      options={TIMEZONES}
                      width="w-[120px]"
                    />
                  </>
                )}
                <div className="flex-1"></div>
                <button onClick={() => handleSaveSync(c.id)} className="px-4 py-2 text-xs font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors shadow-lg shadow-blue-900/20">Save Sync Settings</button>
              </div>
            )}
          </div>
        ))}
        {configs.length === 0 && !showForm && <EmptyState icon={Cloud} message="No cloud configs. Click 'Add Config' to get started." height="h-[300px]" />}
      </div>
    </div>
  );
}

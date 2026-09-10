import React from 'react';

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

export const SyncSettingsModal = ({ show, onClose, syncForm, setSyncForm, onSave, configId }) => {
  if (!show) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-[400px] bg-[#12141a] border border-zinc-800 rounded-xl shadow-2xl p-6 animate-in zoom-in-95 duration-100">
        <h3 className="text-sm font-semibold text-white mb-1">Auto Sync Settings</h3>
        <p className="text-[12px] text-zinc-400 mb-6">Schedule automatic background syncing for this cloud connection.</p>

        <div className="space-y-5">
          <div className="flex bg-zinc-900 rounded-lg p-1 border border-zinc-800">
            <button onClick={() => setSyncForm({ ...syncForm, enabled: false })} className={`flex-1 py-1.5 text-[12px] font-medium rounded-md transition-colors ${!syncForm.enabled ? 'bg-zinc-700 text-white shadow-sm' : 'text-zinc-500 hover:text-zinc-300'}`}>Disabled</button>
            <button onClick={() => setSyncForm({ ...syncForm, enabled: true })} className={`flex-1 py-1.5 text-[12px] font-medium rounded-md transition-colors ${syncForm.enabled ? 'bg-blue-600 text-white shadow-sm' : 'text-zinc-500 hover:text-zinc-300'}`}>Enabled</button>
          </div>

          {syncForm.enabled && (
            <div className="space-y-4 pt-2">
              <div>
                <label className="text-[10px] text-zinc-500 block mb-1">Time</label>
                <input type="time" value={syncForm.time} onChange={e => setSyncForm({ ...syncForm, time: e.target.value })} className="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-[13px] text-white focus:border-blue-500 outline-none" />
              </div>
              <div>
                <label className="text-[10px] text-zinc-500 block mb-1">Timezone</label>
                <select value={syncForm.timezone} onChange={e => setSyncForm({ ...syncForm, timezone: e.target.value })} className="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-[13px] text-white focus:border-blue-500 outline-none">
                  {TIMEZONES.map(tz => <option key={tz.value} value={tz.value}>{tz.label}</option>)}
                </select>
              </div>
            </div>
          )}
        </div>

        <div className="flex gap-3 justify-end mt-8">
          <button onClick={onClose} className="px-4 py-2 text-[13px] font-medium text-zinc-400 hover:bg-zinc-800 rounded-lg transition-colors">Cancel</button>
          <button onClick={() => onSave(configId)} className="px-5 py-2 text-[13px] font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 shadow-lg shadow-blue-900/20 transition-colors">Save Settings</button>
        </div>
      </div>
    </div>
  );
};

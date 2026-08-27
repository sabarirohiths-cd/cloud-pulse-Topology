import React, { useState } from 'react';

const ALL_REGIONS = [
  { id: 'us-east-1', name: 'US East (N. Virginia)' },
  { id: 'us-east-2', name: 'US East (Ohio)' },
  { id: 'us-west-1', name: 'US West (N. California)' },
  { id: 'us-west-2', name: 'US West (Oregon)' },
  { id: 'af-south-1', name: 'Africa (Cape Town)' },
  { id: 'ap-east-1', name: 'Asia Pacific (Hong Kong)' },
  { id: 'ap-south-1', name: 'Asia Pacific (Mumbai)' },
  { id: 'ap-south-2', name: 'Asia Pacific (Hyderabad)' },
  { id: 'ap-southeast-1', name: 'Asia Pacific (Singapore)' },
  { id: 'ap-southeast-2', name: 'Asia Pacific (Sydney)' },
  { id: 'ap-southeast-3', name: 'Asia Pacific (Jakarta)' },
  { id: 'ap-southeast-4', name: 'Asia Pacific (Melbourne)' },
  { id: 'ap-northeast-1', name: 'Asia Pacific (Tokyo)' },
  { id: 'ap-northeast-2', name: 'Asia Pacific (Seoul)' },
  { id: 'ap-northeast-3', name: 'Asia Pacific (Osaka)' },
  { id: 'ca-central-1', name: 'Canada (Central)' },
  { id: 'ca-west-1', name: 'Canada (Calgary)' },
  { id: 'eu-central-1', name: 'Europe (Frankfurt)' },
  { id: 'eu-central-2', name: 'Europe (Zurich)' },
  { id: 'eu-west-1', name: 'Europe (Ireland)' },
  { id: 'eu-west-2', name: 'Europe (London)' },
  { id: 'eu-west-3', name: 'Europe (Paris)' },
  { id: 'eu-south-1', name: 'Europe (Milan)' },
  { id: 'eu-south-2', name: 'Europe (Spain)' },
  { id: 'eu-north-1', name: 'Europe (Stockholm)' },
  { id: 'il-central-1', name: 'Israel (Tel Aviv)' },
  { id: 'me-south-1', name: 'Middle East (Bahrain)' },
  { id: 'me-central-1', name: 'Middle East (UAE)' },
  { id: 'sa-east-1', name: 'South America (São Paulo)' }
];

export default function ScanConfigurationModal({ onClose, onStartScan, initialRegions }) {
  const [selectedRegions, setSelectedRegions] = useState(initialRegions && initialRegions.length > 0 ? initialRegions : ['ap-south-1']);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const toggleRegion = (regionId) => {
    setSelectedRegions(prev => 
      prev.includes(regionId) 
        ? prev.filter(r => r !== regionId)
        : [...prev, regionId]
    );
  };

  const handleStartScan = () => {
    if (selectedRegions.length === 0) {
      alert("Please select at least one region.");
      return;
    }
    if (isSubmitting) return;
    setIsSubmitting(true);
    onStartScan(selectedRegions);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-70">
      <div className="bg-[#0e1015] border border-[#1e232b] rounded-lg shadow-xl w-full max-w-2xl overflow-hidden">
        <div className="p-4 border-b border-[#1e232b] flex justify-between items-center">
          <h2 className="text-white font-semibold text-lg">Scan Configuration</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
        <div className="p-4 max-h-[60vh] overflow-y-auto custom-scrollbar">
          <p className="text-gray-300 text-sm mb-4">Select the AWS regions you want to include in this topology scan.</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {ALL_REGIONS.map(region => (
              <label key={region.id} className="flex items-start space-x-3 text-sm cursor-pointer bg-[#1a1d24] p-3 rounded-lg border border-[#2d333b] hover:border-gray-500 transition-colors">
                <input 
                  type="checkbox" 
                  checked={selectedRegions.includes(region.id)}
                  onChange={() => toggleRegion(region.id)}
                  className="mt-1 rounded border-gray-500 text-blue-600 focus:ring-blue-500 bg-[#0a0a0f]"
                />
                <div className="flex flex-col">
                  <span className="text-gray-200 font-medium">{region.name}</span>
                  <span className="text-gray-500 text-xs mt-0.5">{region.id}</span>
                </div>
              </label>
            ))}
          </div>
        </div>
        <div className="p-4 border-t border-[#1e232b] flex justify-end gap-3 bg-[#0a0a0f]">
          <button 
            onClick={onClose} 
            disabled={isSubmitting}
            className="px-4 py-2 bg-[#1a1d24] text-gray-300 rounded-md text-sm hover:bg-[#2d333b] hover:text-white transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button 
            onClick={handleStartScan} 
            disabled={isSubmitting}
            className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isSubmitting ? (
              <>
                <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Starting...
              </>
            ) : (
              'Start Scan'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

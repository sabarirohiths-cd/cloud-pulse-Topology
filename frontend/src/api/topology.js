import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const getComputeResources = async (accountId, regions = ['ap-south-1'], computeType = 'EC2') => {
  const promises = regions.map(region => 
    axios.get(`${API_BASE_URL}/topology/scan/compute-resources`, {
      params: {
        account_id: accountId,
        region,
        compute_type: computeType
      }
    }).then(res => res.data?.resources || []).catch(err => {
      console.warn(`Failed to load resources for region ${region}:`, err);
      return [];
    })
  );

  const results = await Promise.all(promises);
  return { resources: results.flat() };
};

export const scanComputeFlow = async (accountId, region = 'ap-south-1', computeType = 'EC2', resourceId, observabilityOptions = [], lookbackMinutes = 15) => {
  const payload = {
    account_id: accountId,
    region: region,
    compute_type: computeType,
    resource_id: resourceId
  };

  if (observabilityOptions && observabilityOptions.length > 0) {
    payload.observability_options = observabilityOptions;
  }
  if (lookbackMinutes) {
    payload.lookback_minutes = lookbackMinutes;
  }

  const response = await axios.post(`${API_BASE_URL}/topology/scan/compute-flow`, payload);
  return response.data;
};
export const getLocalComputeFlow = async (region = 'ap-south-1') => {
  const response = await axios.get(`${API_BASE_URL}/topology/scan/compute-flow/local`, {
    params: { region, _t: Date.now() }
  });
  return response.data;
};

export const getCachedRegions = async () => {
  const response = await axios.get(`${API_BASE_URL}/topology/scan/regions/cached`, {
    params: { _t: Date.now() }
  });
  return response.data?.regions || [];
};

export const getLocalTrace = async (computeId) => {
  const response = await axios.get(`${API_BASE_URL}/topology/scan/compute-flow/local/${computeId}`, {
    params: { _t: Date.now() }
  });
  return response.data;
};

export const getLocalComputeResources = async (region, computeType = 'EC2') => {
  const response = await axios.get(`${API_BASE_URL}/topology/scan/compute-resources/local`, {
    params: { region, compute_type: computeType, _t: Date.now() }
  });
  return response.data?.resources || [];
};

export const getSupportedComputeTypes = async () => {
  const response = await axios.get(`${API_BASE_URL}/topology/supported-compute-types`, {
    params: { _t: Date.now() }
  });
  return response.data?.compute_types || ['EC2'];
};

import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export const scanTopology = async (accountId, regions = ['ap-south-1']) => {
  const response = await axios.post(`${API_BASE_URL}/topology/scan`, { account_id: accountId, regions });
  return response.data;
};


export const getTopologyByAccount = async (accountId) => {
  const response = await axios.get(`${API_BASE_URL}/topology/${accountId}`);
  return response.data;
};

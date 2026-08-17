import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export const scanTopology = async (regions = ['ap-south-1']) => {
  const response = await axios.post(`${API_BASE_URL}/topology/scan`, { regions });
  return response.data;
};

export const getSampleTopology = async () => {
  const response = await axios.get(`${API_BASE_URL}/topology/sample`);
  return response.data;
};

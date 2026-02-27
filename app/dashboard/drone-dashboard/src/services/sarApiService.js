// src/services/sarApiService.js
/**
 * QuickScout SAR API Service
 * All API calls for SAR mission planning, execution, and monitoring.
 */

import axios from 'axios';
import { getBackendURL } from '../utilities/utilities';

const sarAPI = () => `${getBackendURL()}/api/sar`;

export const computePlan = async (missionRequest) => {
  const response = await axios.post(`${sarAPI()}/mission/plan`, missionRequest, {
    timeout: 30000,
  });
  return response.data;
};

export const launchMission = async (missionId) => {
  const response = await axios.post(`${sarAPI()}/mission/launch?mission_id=${encodeURIComponent(missionId)}`);
  return response.data;
};

export const getMissionStatus = async (missionId) => {
  const response = await axios.get(`${sarAPI()}/mission/${missionId}/status`);
  return response.data;
};

export const pauseMission = async (missionId, posIds = null) => {
  const params = posIds ? `?pos_ids=${posIds.join('&pos_ids=')}` : '';
  const response = await axios.post(`${sarAPI()}/mission/${missionId}/pause${params}`);
  return response.data;
};

export const resumeMission = async (missionId, posIds = null) => {
  const params = posIds ? `?pos_ids=${posIds.join('&pos_ids=')}` : '';
  const response = await axios.post(`${sarAPI()}/mission/${missionId}/resume${params}`);
  return response.data;
};

export const abortMission = async (missionId, posIds = null, returnBehavior = 'return_home') => {
  let params = `?return_behavior=${returnBehavior}`;
  if (posIds) params += `&pos_ids=${posIds.join('&pos_ids=')}`;
  const response = await axios.post(`${sarAPI()}/mission/${missionId}/abort${params}`);
  return response.data;
};

export const createPOI = async (missionId, poi) => {
  const response = await axios.post(`${sarAPI()}/poi?mission_id=${encodeURIComponent(missionId)}`, poi);
  return response.data;
};

export const getPOIs = async (missionId) => {
  const response = await axios.get(`${sarAPI()}/poi?mission_id=${encodeURIComponent(missionId)}`);
  return response.data;
};

export const updatePOI = async (poiId, updates) => {
  const response = await axios.patch(`${sarAPI()}/poi/${poiId}`, updates);
  return response.data;
};

export const deletePOI = async (poiId) => {
  const response = await axios.delete(`${sarAPI()}/poi/${poiId}`);
  return response.data;
};

export const batchElevation = async (points) => {
  const response = await axios.post(`${sarAPI()}/elevation/batch`, points);
  return response.data;
};

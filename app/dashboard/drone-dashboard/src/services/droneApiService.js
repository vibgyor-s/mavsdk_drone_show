// app/dashboard/drone-dashboard/src/services/droneApiService.js

import axios from 'axios';
import { getBackendURL } from '../utilities/utilities';

/**
 * Builds a standardized command object for an action mission.
 * @param {number} actionType - The numeric code (e.g. 101 for LAND).
 * @param {string[]|undefined} droneIds - Array of drone IDs (if applicable).
 * @param {number} triggerTime - Optional trigger time for scheduling (default immediate).
 */
export const buildActionCommand = (actionType, droneIds = [], triggerTime = 0) => {
  // Note: If droneIds is empty, backend might interpret as "All Drones"
  // or you can handle that in your caller.
  return {
    missionType: String(actionType), // Convert to string for drone API compatibility
    target_drones: droneIds,
    triggerTime: String(triggerTime), // ensure it's a string
  };
};

export const sendDroneCommand = async (commandData) => {
  const requestURI = `${getBackendURL()}/submit_command`;

  try {
    const response = await axios.post(requestURI, commandData);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getCommandStatus = async (commandId) => {
  const requestURI = `${getBackendURL()}/command/${commandId}`;

  try {
    const response = await axios.get(requestURI);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getSwarmClusterStatus = async () => {
  try {
    // Get swarm leaders and status information
    const [leadersResponse, statusResponse] = await Promise.all([
      axios.get(`${getBackendURL()}/api/swarm/leaders`),
      axios.get(`${getBackendURL()}/api/swarm/trajectory/status`)
    ]);

    const leadersData = leadersResponse.data;
    const statusData = statusResponse.data;

    if (!leadersData.success || !statusData.success) {
      throw new Error('Failed to fetch cluster information');
    }

    // Transform the data to match the UI expectations
    const clusters = leadersData.leaders.map(leaderId => ({
      leader_id: leaderId,
      follower_count: leadersData.hierarchies[leaderId] || 0,
      has_trajectory: leadersData.uploaded_leaders.includes(leaderId) && statusData.status.processed_trajectories > 0
    }));

    return {
      clusters,
      total_leaders: leadersData.leaders.length,
      total_followers: Object.values(leadersData.hierarchies).reduce((sum, count) => sum + count, 0),
      processed_trajectories: statusData.status.processed_trajectories || 0
    };
  } catch (error) {
    throw error;
  }
};

export const getProcessingRecommendation = async () => {
  try {
    const response = await axios.get(`${getBackendURL()}/api/swarm/trajectory/recommendation`);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const processTrajectories = async (options = {}) => {
  const requestURI = `${getBackendURL()}/api/swarm/trajectory/process`;

  try {
    const response = await axios.post(requestURI, {
      force_clear: options.force_clear || false,
      auto_reload: options.auto_reload !== false // default true
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const clearProcessedData = async () => {
  const requestURI = `${getBackendURL()}/api/swarm/trajectory/clear-processed`;

  try {
    const response = await axios.post(requestURI);
    return response.data;
  } catch (error) {
    throw error;
  }
};

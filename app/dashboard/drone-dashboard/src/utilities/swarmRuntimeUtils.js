import { DRONE_ACTION_TYPES, DRONE_MISSION_TYPES } from '../constants/droneConstants';

export const SWARM_RUNTIME_SCOPE = {
  DRONE: 'drone',
  CLUSTER: 'cluster',
};

export const SWARM_RUNTIME_ACTIONS = {
  START: {
    key: 'START',
    missionType: DRONE_MISSION_TYPES.SMART_SWARM,
    label: 'Start Smart Swarm',
    operatorLabel: 'Start Smart Swarm',
    tone: 'primary',
    description: 'Start live Smart Swarm following for the current scope.',
  },
  STOP_HOLD: {
    key: 'STOP_HOLD',
    missionType: DRONE_ACTION_TYPES.HOLD,
    label: 'Stop Swarm (Hold)',
    operatorLabel: 'Stop Smart Swarm (Hold)',
    tone: 'secondary',
    description: 'Exit active following and command the selected drones to hold position.',
  },
  LAND: {
    key: 'LAND',
    missionType: DRONE_ACTION_TYPES.LAND,
    label: 'Land Swarm',
    operatorLabel: 'Land Swarm',
    tone: 'danger',
    description: 'Override the current swarm behavior and land the selected drones.',
  },
  RTL: {
    key: 'RTL',
    missionType: DRONE_ACTION_TYPES.RETURN_RTL,
    label: 'RTL Swarm',
    operatorLabel: 'RTL Swarm',
    tone: 'warning',
    description: 'Override the current swarm behavior and return the selected drones to launch.',
  },
};

export function resolveSwarmRuntimeTargets(
  viewModel,
  scope = SWARM_RUNTIME_SCOPE.DRONE,
  selectedDroneId = null,
  selectedClusterId = null
) {
  const drones = Array.isArray(viewModel?.drones) ? viewModel.drones : [];
  const dronesById = viewModel?.dronesById || {};
  const clusters = Array.isArray(viewModel?.clusters) ? viewModel.clusters : [];

  if (drones.length === 0) {
    return {
      selectedDrone: null,
      cluster: null,
      targetIds: [],
      scopeLabel: 'No swarm drones available',
      targetSummary: 'Load or save a Smart Swarm assignment before issuing runtime commands.',
    };
  }

  const selectedDrone = (selectedDroneId && dronesById[selectedDroneId]) || drones[0];

  if (scope === SWARM_RUNTIME_SCOPE.DRONE) {
    return {
      selectedDrone,
      cluster: null,
      targetIds: [selectedDrone.hw_id],
      scopeLabel: `${selectedDrone.title} (1 drone)`,
      targetSummary: 'Targets only the selected drone. Other swarm drones continue until they receive their own command, failover event, or follow-chain update.',
    };
  }

  const selectedCluster = clusters.find(
    (candidate) => candidate.id === selectedDrone?.clusterId && candidate.type === 'cluster'
  )
    || clusters.find((candidate) => candidate.id === selectedClusterId && candidate.type === 'cluster')
    || clusters.find((candidate) => candidate.type === 'cluster')
    || null;

  const targetIds = selectedCluster?.drones?.map((drone) => drone.hw_id) || [];
  const count = targetIds.length;

  return {
    selectedDrone,
    cluster: selectedCluster,
    targetIds,
    scopeLabel: selectedCluster
      ? `${selectedCluster.title} (${count} drone${count === 1 ? '' : 's'})`
      : `${selectedDrone?.title || 'Selected drone'} has no valid executable cluster`,
    targetSummary: selectedCluster
      ? `${selectedCluster.subtitle} · ${count} target drone${count === 1 ? '' : 's'}`
      : 'Resolve follow-chain warnings before sending cluster-scoped Smart Swarm commands.',
  };
}

export function buildSwarmRuntimeCommand(actionKey, targetIds = []) {
  const action = SWARM_RUNTIME_ACTIONS[actionKey];
  if (!action) {
    throw new Error(`Unknown swarm runtime action: ${actionKey}`);
  }

  return {
    missionType: String(action.missionType),
    triggerTime: '0',
    target_drones: targetIds,
    operatorLabel: action.operatorLabel,
    command_scope: 'smart_swarm_runtime',
  };
}

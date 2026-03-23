import { buildSwarmViewModel } from './swarmDesignUtils';
import {
  buildSwarmRuntimeCommand,
  resolveSwarmRuntimeTargets,
  SWARM_RUNTIME_ACTIONS,
  SWARM_RUNTIME_SCOPE,
} from './swarmRuntimeUtils';

describe('swarmRuntimeUtils', () => {
  const config = [
    { hw_id: 1, pos_id: 1 },
    { hw_id: 2, pos_id: 2 },
    { hw_id: 3, pos_id: 3 },
  ];
  const assignments = [
    { hw_id: 1, follow: 0, offset_x: 0, offset_y: 0, offset_z: 0, frame: 'ned' },
    { hw_id: 2, follow: 1, offset_x: 3, offset_y: 0, offset_z: 0, frame: 'ned' },
    { hw_id: 3, follow: 2, offset_x: 0, offset_y: 1, offset_z: 0, frame: 'body' },
  ];

  test('resolveSwarmRuntimeTargets defaults to selected drone scope', () => {
    const viewModel = buildSwarmViewModel(assignments, config);

    expect(resolveSwarmRuntimeTargets(viewModel, SWARM_RUNTIME_SCOPE.DRONE, '3')).toMatchObject({
      targetIds: ['3'],
      scopeLabel: 'Drone 3 (1 drone)',
    });
  });

  test('resolveSwarmRuntimeTargets expands the selected executable cluster', () => {
    const viewModel = buildSwarmViewModel(assignments, config);

    expect(resolveSwarmRuntimeTargets(viewModel, SWARM_RUNTIME_SCOPE.CLUSTER, '3')).toMatchObject({
      targetIds: ['1', '2', '3'],
      scopeLabel: 'Leader Drone 1 (3 drones)',
    });
  });

  test('resolveSwarmRuntimeTargets blocks invalid cluster scope', () => {
    const invalidViewModel = buildSwarmViewModel(
      [
        { hw_id: 1, follow: 2, offset_x: 0, offset_y: 0, offset_z: 0, frame: 'ned' },
        { hw_id: 2, follow: 1, offset_x: 0, offset_y: 0, offset_z: 0, frame: 'ned' },
      ],
      [
        { hw_id: 1, pos_id: 1 },
        { hw_id: 2, pos_id: 2 },
      ]
    );

    expect(resolveSwarmRuntimeTargets(invalidViewModel, SWARM_RUNTIME_SCOPE.CLUSTER, '1')).toMatchObject({
      targetIds: [],
      targetSummary: 'Resolve follow-chain warnings before sending cluster-scoped Smart Swarm commands.',
    });
  });

  test('buildSwarmRuntimeCommand preserves action mission type and explicit scope metadata', () => {
    expect(buildSwarmRuntimeCommand(SWARM_RUNTIME_ACTIONS.STOP_HOLD.key, ['2', '3'])).toEqual({
      missionType: '102',
      triggerTime: '0',
      target_drones: ['2', '3'],
      operatorLabel: 'Stop Smart Swarm (Hold)',
      command_scope: 'smart_swarm_runtime',
    });
  });
});

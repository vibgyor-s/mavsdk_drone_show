import {
  buildSuggestedHwIds,
  getDuplicateAssignments,
  getOnlineDroneCount,
  normalizeDroneConfigData,
  toBackendConfigDrone,
} from './missionIdentityUtils';

describe('missionIdentityUtils', () => {
  test('normalizeDroneConfigData canonicalizes mixed numeric/string IDs', () => {
    const normalized = normalizeDroneConfigData([
      { hw_id: 1, pos_id: '01', ip: '10.0.0.1', mavlink_port: 14550, serial_port: '', baudrate: 0 },
      { hw_id: '2', pos_id: 2, ip: '10.0.0.2', mavlink_port: '14551', serial_port: '/dev/ttyS0', baudrate: '57600' },
    ]);

    expect(normalized).toEqual([
      expect.objectContaining({ hw_id: '1', pos_id: '1', mavlink_port: '14550', baudrate: '0' }),
      expect.objectContaining({ hw_id: '2', pos_id: '2', mavlink_port: '14551', baudrate: '57600' }),
    ]);
  });

  test('buildSuggestedHwIds returns numeric gaps and next sequential slot', () => {
    expect(buildSuggestedHwIds([
      { hw_id: '1' },
      { hw_id: 3 },
      { hw_id: '4' },
    ])).toEqual(['2', '5']);
  });

  test('getDuplicateAssignments detects mixed-type duplicate hardware and position IDs', () => {
    const duplicates = getDuplicateAssignments([
      { hw_id: 1, pos_id: 1 },
      { hw_id: '1', pos_id: '2' },
      { hw_id: 3, pos_id: '2' },
    ]);

    expect(duplicates.duplicateHwIds).toEqual([
      { hw_id: '1', pos_ids: ['1', '2'] },
    ]);
    expect(duplicates.duplicatePosIds).toEqual([
      { pos_id: '2', hw_ids: ['1', '3'] },
    ]);
  });

  test('getOnlineDroneCount prefers last_heartbeat and ignores stale drones', () => {
    const now = Date.now();
    const heartbeats = {
      '1': { last_heartbeat: now - 5_000 },
      '2': { timestamp: now - 50_000 },
      '3': { last_heartbeat: now - 15_000 },
    };

    expect(getOnlineDroneCount(heartbeats)).toBe(2);
  });

  test('toBackendConfigDrone coerces numeric identity fields back to integers', () => {
    expect(toBackendConfigDrone({
      hw_id: '7',
      pos_id: '9',
      ip: '10.0.0.7',
      mavlink_port: '14557',
      serial_port: '',
      baudrate: '0',
    })).toEqual({
      hw_id: 7,
      pos_id: 9,
      ip: '10.0.0.7',
      mavlink_port: 14557,
      serial_port: '',
      baudrate: 0,
    });
  });
});

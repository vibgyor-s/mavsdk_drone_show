import { FIELD_NAMES } from '../constants/fieldMappings';
import { getDroneReadinessModel } from './droneReadiness';

describe('getDroneReadinessModel', () => {
  it('returns ready when telemetry is live and no blockers exist', () => {
    const drone = {
      [FIELD_NAMES.IS_READY_TO_ARM]: true,
      [FIELD_NAMES.READINESS_STATUS]: 'ready',
      [FIELD_NAMES.READINESS_SUMMARY]: 'Ready to fly',
      [FIELD_NAMES.PREFLIGHT_BLOCKERS]: [],
      [FIELD_NAMES.PREFLIGHT_WARNINGS]: [],
      [FIELD_NAMES.STATUS_MESSAGES]: [],
      [FIELD_NAMES.READINESS_CHECKS]: [],
    };

    const result = getDroneReadinessModel(drone, { level: 'online' });

    expect(result.isReady).toBe(true);
    expect(result.status).toBe('ready');
    expect(result.summary).toBe('Ready to fly');
  });

  it('adds a link guard when telemetry is stale', () => {
    const drone = {
      [FIELD_NAMES.IS_READY_TO_ARM]: true,
      [FIELD_NAMES.READINESS_STATUS]: 'ready',
      [FIELD_NAMES.READINESS_SUMMARY]: 'Ready to fly',
      [FIELD_NAMES.PREFLIGHT_BLOCKERS]: [],
      [FIELD_NAMES.PREFLIGHT_WARNINGS]: [],
      [FIELD_NAMES.STATUS_MESSAGES]: [],
      [FIELD_NAMES.READINESS_CHECKS]: [],
    };

    const result = getDroneReadinessModel(drone, { level: 'degraded' });

    expect(result.isReady).toBe(false);
    expect(result.status).toBe('unknown');
    expect(result.blockers[0].source).toBe('link');
  });
});

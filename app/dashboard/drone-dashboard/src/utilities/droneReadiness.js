import { FIELD_NAMES } from '../constants/fieldMappings';

const STATUS_LABELS = {
  ready: 'Ready to Fly',
  blocked: 'Not Ready',
  warning: 'Review Warnings',
  unknown: 'Unverified',
};

function normalizeMessages(messages) {
  if (!Array.isArray(messages)) {
    return [];
  }

  return messages
    .filter((message) => message && typeof message === 'object')
    .map((message) => ({
      source: message.source || 'telemetry',
      severity: message.severity || 'warning',
      message: message.message || 'Unknown status message',
      timestamp: Number(message.timestamp) || 0,
    }));
}

function normalizeChecks(checks) {
  if (!Array.isArray(checks)) {
    return [];
  }

  return checks
    .filter((check) => check && typeof check === 'object')
    .map((check) => ({
      id: check.id || 'check',
      label: check.label || 'Check',
      ready: Boolean(check.ready),
      detail: check.detail || '',
    }));
}

function dedupeMessages(messages) {
  const seen = new Set();

  return messages.filter((message) => {
    const key = `${message.source}:${message.message.trim().toLowerCase()}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function getAvailabilityGuard(runtimeStatus) {
  if (!runtimeStatus || runtimeStatus.level === 'online') {
    return null;
  }

  if (runtimeStatus.level === 'degraded') {
    return {
      source: 'link',
      severity: 'warning',
      message: 'Telemetry is delayed. Readiness cannot be trusted until live telemetry returns.',
      timestamp: Date.now(),
    };
  }

  return {
    source: 'link',
    severity: 'error',
    message: 'Telemetry link is stale or lost. Readiness is currently unavailable.',
    timestamp: Date.now(),
  };
}

export function getDroneReadinessModel(drone, runtimeStatus = null) {
  const blockers = normalizeMessages(drone?.[FIELD_NAMES.PREFLIGHT_BLOCKERS]);
  const warnings = normalizeMessages(drone?.[FIELD_NAMES.PREFLIGHT_WARNINGS]);
  const statusMessages = normalizeMessages(drone?.[FIELD_NAMES.STATUS_MESSAGES]);
  const checks = normalizeChecks(drone?.[FIELD_NAMES.READINESS_CHECKS]);

  const statusMessageKeys = new Set([
    ...blockers.map((message) => message.message.trim().toLowerCase()),
    ...warnings.map((message) => message.message.trim().toLowerCase()),
  ]);

  const recentMessages = dedupeMessages(statusMessages)
    .filter((message) => !statusMessageKeys.has(message.message.trim().toLowerCase()))
    .sort((left, right) => right.timestamp - left.timestamp);

  let status = drone?.[FIELD_NAMES.READINESS_STATUS] || (
    drone?.[FIELD_NAMES.IS_READY_TO_ARM] ? 'ready' : 'blocked'
  );
  let summary = drone?.[FIELD_NAMES.READINESS_SUMMARY]
    || (status === 'ready' ? 'Ready to fly' : 'Preflight checks are not complete.');

  const availabilityGuard = getAvailabilityGuard(runtimeStatus);
  if (availabilityGuard) {
    status = 'unknown';
    summary = availabilityGuard.message;
  }

  const visibleBlockers = availabilityGuard ? [availabilityGuard, ...blockers] : blockers;
  const issueCount = visibleBlockers.length + warnings.length;

  return {
    status,
    summary,
    statusLabel: STATUS_LABELS[status] || STATUS_LABELS.unknown,
    blockers: visibleBlockers,
    warnings,
    recentMessages,
    checks,
    issueCount,
    isReady: status === 'ready' && issueCount === 0,
    updatedAt: Number(drone?.[FIELD_NAMES.PREFLIGHT_LAST_UPDATE]) || null,
  };
}

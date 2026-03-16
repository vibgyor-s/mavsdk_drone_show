const LIVE_TELEMETRY_THRESHOLD_MS = 7_000;
const HEARTBEAT_GRACE_THRESHOLD_MS = 25_000;
const MS_PER_SECOND = 1_000;
const UNIX_MS_THRESHOLD = 1_000_000_000_000;

function normalizeTimestampMs(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return null;
  }

  if (numeric >= UNIX_MS_THRESHOLD) {
    return numeric;
  }

  return numeric * MS_PER_SECOND;
}

function toAgeSeconds(nowMs, timestampMs) {
  if (timestampMs === null) {
    return null;
  }

  return Math.max(0, Math.round((nowMs - timestampMs) / MS_PER_SECOND));
}

function formatAge(ageSeconds, label) {
  if (ageSeconds === null) {
    return `${label}: unavailable`;
  }

  return `${label}: ${ageSeconds}s ago`;
}

export function getDroneRuntimeStatus(drone, nowMs = Date.now()) {
  const telemetryTimestamp = normalizeTimestampMs(drone?.timestamp ?? drone?.update_time);
  const heartbeatTimestamp = normalizeTimestampMs(drone?.heartbeat_last_seen);
  const telemetryAgeSec = toAgeSeconds(nowMs, telemetryTimestamp);
  const heartbeatAgeSec = toAgeSeconds(nowMs, heartbeatTimestamp);

  const hasLiveTelemetry =
    telemetryTimestamp !== null && nowMs - telemetryTimestamp <= LIVE_TELEMETRY_THRESHOLD_MS;
  const hasRecentHeartbeat =
    heartbeatTimestamp !== null && nowMs - heartbeatTimestamp <= HEARTBEAT_GRACE_THRESHOLD_MS;

  if (hasLiveTelemetry) {
    return {
      level: 'online',
      indicatorClass: 'active',
      label: 'Live telemetry',
      tooltip: `${formatAge(telemetryAgeSec, 'Telemetry')} | ${formatAge(heartbeatAgeSec, 'Heartbeat')}`,
      telemetryAgeSec,
      heartbeatAgeSec,
    };
  }

  if (hasRecentHeartbeat) {
    return {
      level: 'degraded',
      indicatorClass: 'degraded',
      label: 'Heartbeat only',
      tooltip: `Telemetry delayed. ${formatAge(telemetryAgeSec, 'Telemetry')} | ${formatAge(heartbeatAgeSec, 'Heartbeat')}`,
      telemetryAgeSec,
      heartbeatAgeSec,
    };
  }

  if (telemetryTimestamp !== null || heartbeatTimestamp !== null) {
    return {
      level: 'offline',
      indicatorClass: 'offline',
      label: 'Link lost',
      tooltip: `No recent telemetry or heartbeat. ${formatAge(telemetryAgeSec, 'Telemetry')} | ${formatAge(heartbeatAgeSec, 'Heartbeat')}`,
      telemetryAgeSec,
      heartbeatAgeSec,
    };
  }

  return {
    level: 'unknown',
    indicatorClass: 'unknown',
    label: 'Waiting for link',
    tooltip: 'No telemetry or heartbeat received yet.',
    telemetryAgeSec: null,
    heartbeatAgeSec: null,
  };
}

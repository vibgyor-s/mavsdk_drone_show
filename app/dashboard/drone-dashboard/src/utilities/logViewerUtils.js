const SESSION_ID_PATTERN = /^s_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})(?:_\d+)?$/;

export const formatBytes = (bytes) => {
  if (!Number.isFinite(bytes) || bytes < 0) {
    return '0 B';
  }

  const units = ['B', 'KB', 'MB', 'GB'];
  if (bytes === 0) {
    return units[0];
  }

  const exponent = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  );
  const value = bytes / (1024 ** exponent);
  const digits = value >= 100 || exponent === 0 ? 0 : 1;

  return `${value.toFixed(digits)} ${units[exponent]}`;
};

export const parseSessionTimestamp = (sessionId, modified = null) => {
  if (typeof sessionId === 'string') {
    const match = sessionId.match(SESSION_ID_PATTERN);
    if (match) {
      const [, year, month, day, hour, minute, second] = match;
      return new Date(Date.UTC(
        Number(year),
        Number(month) - 1,
        Number(day),
        Number(hour),
        Number(minute),
        Number(second),
      ));
    }
  }

  if (Number.isFinite(modified)) {
    return new Date(modified * 1000);
  }

  return null;
};

export const formatSessionLabel = (session) => {
  if (!session) {
    return 'Unknown Session';
  }

  const parsed = parseSessionTimestamp(session.session_id, session.modified);
  const parts = [];

  if (parsed && !Number.isNaN(parsed.getTime())) {
    const dateLabel = new Intl.DateTimeFormat(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
      timeZone: 'UTC',
    }).format(parsed);
    parts.push(`${dateLabel} UTC`);
  } else if (session.session_id) {
    parts.push(session.session_id);
  }

  if (Number.isFinite(session.size_bytes)) {
    parts.push(formatBytes(session.size_bytes));
  }

  return parts.join(' · ') || 'Unknown Session';
};

export const getEntryTimestampMs = (entry) => {
  if (!entry?.ts) {
    return null;
  }

  const value = new Date(entry.ts).getTime();
  return Number.isNaN(value) ? null : value;
};

export const filterEntriesByAbsoluteTimeRange = (entries, start = '', end = '') => {
  const startMs = start ? new Date(start).getTime() : null;
  const endMs = end ? new Date(end).getTime() : null;
  const hasStart = Number.isFinite(startMs);
  const hasEnd = Number.isFinite(endMs);

  if (!hasStart && !hasEnd) {
    return entries;
  }

  return entries.filter((entry) => {
    const tsMs = getEntryTimestampMs(entry);
    if (!Number.isFinite(tsMs)) {
      return false;
    }
    if (hasStart && tsMs < startMs) {
      return false;
    }
    if (hasEnd && tsMs > endMs) {
      return false;
    }
    return true;
  });
};

export const filterEntriesByRelativeWindow = (entries, durationMs) => {
  if (!Number.isFinite(durationMs) || durationMs <= 0) {
    return entries;
  }

  const timestamps = entries
    .map(getEntryTimestampMs)
    .filter((value) => Number.isFinite(value));

  if (timestamps.length === 0) {
    return entries;
  }

  const newestTs = Math.max(...timestamps);
  const cutoff = newestTs - durationMs;

  return entries.filter((entry) => {
    const tsMs = getEntryTimestampMs(entry);
    return !Number.isFinite(tsMs) || tsMs >= cutoff;
  });
};

export const buildComponentCatalog = (entries, registry = {}) => {
  const map = new Map();

  Object.entries(registry || {}).forEach(([name, info]) => {
    map.set(name, {
      name,
      category: info?.category || 'unknown',
      description: info?.description || '',
    });
  });

  for (const entry of entries || []) {
    const name = entry?.component;
    if (!name) {
      continue;
    }

    const existing = map.get(name);
    map.set(name, {
      name,
      category: existing?.category || entry?.source || 'unknown',
      description: existing?.description || '',
    });
  }

  return Array.from(map.values()).sort((left, right) => (
    left.name.localeCompare(right.name)
  ));
};

export const applySeverityFocus = (entries, focus) => {
  if (!focus) {
    return entries;
  }

  if (focus === 'warnings') {
    return entries.filter((entry) => entry?.level === 'WARNING');
  }

  if (focus === 'errors') {
    return entries.filter((entry) => entry?.level === 'ERROR' || entry?.level === 'CRITICAL');
  }

  return entries;
};

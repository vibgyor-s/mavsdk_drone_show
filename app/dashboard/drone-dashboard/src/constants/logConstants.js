// src/constants/logConstants.js
// Constants for the Log Viewer UI

export const LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];

export const LOG_LEVEL_COLORS = {
  DEBUG:    { bg: 'var(--color-bg-tertiary)',    text: 'var(--color-text-secondary)', icon: 'bug' },
  INFO:     { bg: 'var(--color-info-light)',      text: 'var(--color-info)',           icon: 'info-circle' },
  WARNING:  { bg: 'var(--color-warning-light)',   text: 'var(--color-warning)',        icon: 'exclamation-triangle' },
  ERROR:    { bg: 'var(--color-danger-light)',     text: 'var(--color-danger)',         icon: 'times-circle' },
  CRITICAL: { bg: 'var(--color-danger-light)',     text: 'var(--color-danger)',         icon: 'skull-crossbones' },
};

// Operations mode shows WARNING+ by default
export const OPS_DEFAULT_LEVEL = 'WARNING';
// Developer mode shows all levels
export const DEV_DEFAULT_LEVEL = 'DEBUG';

// SSE ring buffer size — max log lines held in memory
export const MAX_LOG_LINES = 5000;

// SSE batching interval (ms) — prevents re-render per line
export const SSE_BATCH_INTERVAL_MS = 200;

// Health bar poll interval (ms)
export const HEALTH_POLL_INTERVAL_MS = 5000;

// Modes
export const MODES = { OPS: 'operations', DEV: 'developer' };

// Live-view time windows
export const LIVE_TIME_WINDOWS = [
  { value: 'all', label: 'All Buffered', durationMs: null },
  { value: '5m', label: 'Last 5m', durationMs: 5 * 60 * 1000 },
  { value: '15m', label: 'Last 15m', durationMs: 15 * 60 * 1000 },
  { value: '1h', label: 'Last 1h', durationMs: 60 * 60 * 1000 },
];

// Exact-severity drill-down from the health bar
export const SEVERITY_FOCUS = {
  WARNINGS: 'warnings',
  ERRORS: 'errors',
};

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

// Historical session pagination
export const SESSION_PAGE_SIZE = 100;

// Health bar poll interval (ms)
export const HEALTH_POLL_INTERVAL_MS = 5000;

// Modes
export const MODES = { OPS: 'operations', DEV: 'developer' };

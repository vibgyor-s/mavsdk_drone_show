// src/components/logs/LogLiveIndicator.js
import React from 'react';

const LogLiveIndicator = ({ connected, paused }) => {
  const dotClass = paused ? 'paused' : connected ? '' : 'disconnected';
  const label = paused ? 'PAUSED' : connected ? 'LIVE' : 'OFFLINE';

  return (
    <span className="log-live-indicator" aria-live="polite">
      <span className={`log-live-dot ${dotClass}`} />
      {label}
    </span>
  );
};

export default LogLiveIndicator;

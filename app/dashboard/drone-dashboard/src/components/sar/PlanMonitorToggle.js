// src/components/sar/PlanMonitorToggle.js
import React from 'react';

const PlanMonitorToggle = ({ mode, onModeChange }) => (
  <div className="qs-mode-toggle">
    <button
      className={`qs-mode-btn ${mode === 'plan' ? 'active' : ''}`}
      onClick={() => onModeChange('plan')}
    >
      Plan
    </button>
    <button
      className={`qs-mode-btn ${mode === 'monitor' ? 'active' : ''}`}
      onClick={() => onModeChange('monitor')}
    >
      Monitor
    </button>
  </div>
);

export default PlanMonitorToggle;

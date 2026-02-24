// src/components/sar/MissionStatsBar.js
import React from 'react';

const formatTime = (seconds) => {
  if (!seconds || seconds <= 0) return '--:--';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, '0')}`;
};

const MissionStatsBar = ({ missionStatus }) => {
  if (!missionStatus) return null;

  const coverage = missionStatus.total_coverage_percent || 0;
  const elapsed = missionStatus.elapsed_time_s || 0;
  const state = missionStatus.state || 'unknown';
  const droneCount = Object.keys(missionStatus.drone_states || {}).length;

  return (
    <div className="qs-stats-bar">
      <div className="qs-stat">
        <span className="qs-stat-label">Status:</span>
        <span className={`qs-stat-value ${state === 'executing' ? 'success' : state === 'paused' ? 'warning' : ''}`}>
          {state.toUpperCase()}
        </span>
      </div>
      <div className="qs-stat">
        <span className="qs-stat-label">Drones:</span>
        <span className="qs-stat-value">{droneCount}</span>
      </div>
      <div className="qs-stat">
        <span className="qs-stat-label">Coverage:</span>
        <span className="qs-stat-value success">{coverage.toFixed(1)}%</span>
      </div>
      <div className="qs-progress-bar">
        <div className="qs-progress-fill" style={{ width: `${coverage}%` }} />
      </div>
      <div className="qs-stat">
        <span className="qs-stat-label">Elapsed:</span>
        <span className="qs-stat-value">{formatTime(elapsed)}</span>
      </div>
    </div>
  );
};

export default MissionStatsBar;

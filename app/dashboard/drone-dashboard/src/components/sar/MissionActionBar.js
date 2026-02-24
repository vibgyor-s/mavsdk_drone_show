// src/components/sar/MissionActionBar.js
import React from 'react';
import { FaPlay, FaPause, FaHome, FaTimesCircle } from 'react-icons/fa';

const MissionActionBar = ({ onResume, onPause, onRTL, onAbort, missionState }) => {
  if (!missionState || missionState === 'planning' || missionState === 'ready') return null;

  return (
    <div className="qs-action-bar">
      <button
        className="qs-action-btn resume"
        onClick={onResume}
        title="Resume Mission"
        disabled={missionState !== 'paused'}
      >
        <FaPlay />
      </button>
      <button
        className="qs-action-btn pause"
        onClick={onPause}
        title="Pause Mission"
        disabled={missionState !== 'executing'}
      >
        <FaPause />
      </button>
      <button
        className="qs-action-btn rtl"
        onClick={onRTL}
        title="Return to Launch"
      >
        <FaHome />
      </button>
      <button
        className="qs-action-btn abort"
        onClick={() => {
          if (window.confirm('Abort mission? All drones will execute return behavior.')) {
            onAbort();
          }
        }}
        title="Abort Mission"
      >
        <FaTimesCircle />
      </button>
    </div>
  );
};

export default MissionActionBar;

// src/components/logs/LogHealthBar.js
import React, { useState, useEffect, useMemo } from 'react';
import { FaServer, FaPlane, FaExclamationTriangle, FaTimesCircle, FaClock } from 'react-icons/fa';
import { getSources } from '../../services/logService';
import { HEALTH_POLL_INTERVAL_MS } from '../../constants/logConstants';

const LogHealthBar = ({ entries }) => {
  const [droneCount, setDroneCount] = useState(0);
  const [gcsOnline, setGcsOnline] = useState(false);

  const { errorCount, warningCount } = useMemo(() => {
    let errors = 0, warnings = 0;
    for (const e of entries) {
      if (e.level === 'ERROR' || e.level === 'CRITICAL') errors++;
      else if (e.level === 'WARNING') warnings++;
    }
    return { errorCount: errors, warningCount: warnings };
  }, [entries]);

  useEffect(() => {
    let mounted = true;
    const fetchSources = async () => {
      try {
        const data = await getSources();
        if (!mounted) return;
        setGcsOnline(true);
        const components = data.components || {};
        const droneSources = Object.values(components).filter(c => c.category === 'drone');
        setDroneCount(droneSources.length);
      } catch {
        if (mounted) setGcsOnline(false);
      }
    };
    fetchSources();
    const timer = setInterval(fetchSources, HEALTH_POLL_INTERVAL_MS);
    return () => { mounted = false; clearInterval(timer); };
  }, []);

  return (
    <div className="log-health-bar" role="status" aria-label="System health">
      <div className="log-health-stat">
        <FaServer size={12} />
        <span>GCS</span>
        <span className="stat-value" style={{ color: gcsOnline ? 'var(--color-success)' : 'var(--color-danger)' }}>
          {gcsOnline ? 'Online' : 'Offline'}
        </span>
      </div>
      <div className="log-health-stat">
        <FaPlane size={12} />
        <span>Drones</span>
        <span className="stat-value">{droneCount}</span>
      </div>
      <div className="log-health-stat error-count">
        <FaTimesCircle size={12} />
        <span>Errors</span>
        <span className="stat-value">{errorCount}</span>
      </div>
      <div className="log-health-stat warning-count">
        <FaExclamationTriangle size={12} />
        <span>Warnings</span>
        <span className="stat-value">{warningCount}</span>
      </div>
      <div className="log-health-stat">
        <FaClock size={12} />
        <span>Entries</span>
        <span className="stat-value">{entries.length}</span>
      </div>
    </div>
  );
};

export default LogHealthBar;

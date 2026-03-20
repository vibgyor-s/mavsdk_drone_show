// src/components/logs/LogSourceTree.js
import React, { useState, useEffect } from 'react';
import { FaCircle } from 'react-icons/fa';
import { getSources } from '../../services/logService';

const LogSourceTree = ({ selectedComponent, onSelect }) => {
  const [components, setComponents] = useState({});

  useEffect(() => {
    let mounted = true;
    const fetchData = async () => {
      try {
        const data = await getSources();
        if (mounted) setComponents(data.components || {});
      } catch {
        // Silently fail
      }
    };
    fetchData();
    return () => { mounted = false; };
  }, []);

  const entries = Object.entries(components);

  return (
    <div className="log-source-tree" role="listbox" aria-label="Log sources">
      <div className="log-source-tree-title">Components</div>
      <div
        className={`log-source-item ${!selectedComponent ? 'active' : ''}`}
        onClick={() => onSelect(null)}
        role="option"
        aria-selected={!selectedComponent}
      >
        <FaCircle size={6} />
        All Components
      </div>
      {entries.map(([name, info]) => (
        <div
          key={name}
          className={`log-source-item ${selectedComponent === name ? 'active' : ''}`}
          onClick={() => onSelect(name)}
          role="option"
          aria-selected={selectedComponent === name}
        >
          <FaCircle size={6} />
          {name}
          <span className="log-source-badge">{info.source}</span>
        </div>
      ))}
    </div>
  );
};

export default LogSourceTree;

// src/components/logs/LogSourceTree.js
import React from 'react';
import { FaCircle } from 'react-icons/fa';

const LogSourceTree = ({ components, selectedComponent, onSelect }) => {
  const entries = components || [];

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
      {entries.map((entry) => (
        <div
          key={entry.name}
          className={`log-source-item ${selectedComponent === entry.name ? 'active' : ''}`}
          onClick={() => onSelect(entry.name)}
          role="option"
          aria-selected={selectedComponent === entry.name}
        >
          <FaCircle size={6} />
          {entry.name}
          <span className="log-source-badge">{entry.category}</span>
        </div>
      ))}
    </div>
  );
};

export default LogSourceTree;

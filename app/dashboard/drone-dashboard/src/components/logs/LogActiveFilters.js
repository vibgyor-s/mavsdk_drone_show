// src/components/logs/LogActiveFilters.js
import React from 'react';
import { FaFilter, FaTimes } from 'react-icons/fa';

const LogActiveFilters = ({ filters, onClearAll }) => {
  if (!filters?.length) {
    return null;
  }

  return (
    <div className="log-active-filters" role="status" aria-label="Active log filters">
      <div className="log-active-filters-label">
        <FaFilter size={11} />
        Active Filters
      </div>
      <div className="log-active-filters-list">
        {filters.map((filter) => (
          <button
            key={filter.key}
            type="button"
            className="log-filter-chip"
            onClick={filter.onRemove}
            title={`Remove ${filter.label}`}
          >
            <span>{filter.label}</span>
            <FaTimes size={10} />
          </button>
        ))}
      </div>
      <button
        type="button"
        className="log-clear-filters-button"
        onClick={onClearAll}
      >
        Clear All Filters
      </button>
    </div>
  );
};

export default LogActiveFilters;

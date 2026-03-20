// src/components/logs/LogRowDetail.js
import React from 'react';

const LogRowDetail = ({ entry }) => {
  if (!entry) return null;
  return (
    <div className="log-row-detail" role="region" aria-label="Log entry details">
      <pre>{JSON.stringify(entry, null, 2)}</pre>
    </div>
  );
};

export default LogRowDetail;

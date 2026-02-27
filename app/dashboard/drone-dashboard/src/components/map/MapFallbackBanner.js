// src/components/map/MapFallbackBanner.js
// Dismissible notification shown when Mapbox -> Leaflet fallback occurs

import React, { useState } from 'react';
import { useMapContext } from '../../contexts/MapContext';
import '../../styles/MapCommon.css';

const SESSION_KEY = 'mds_fallback_banner_dismissed';

const MapFallbackBanner = () => {
  const { provider, isMapboxAvailable, fallbackReason } = useMapContext();
  const [dismissed, setDismissed] = useState(
    () => sessionStorage.getItem(SESSION_KEY) === '1'
  );

  // Only show when we fell back to leaflet and mapbox isn't available
  if (dismissed || provider !== 'leaflet' || isMapboxAvailable) {
    return null;
  }

  const handleDismiss = () => {
    setDismissed(true);
    sessionStorage.setItem(SESSION_KEY, '1');
  };

  return (
    <div className="mds-map-fallback-banner">
      <span className="mds-map-fallback-banner-text">
        Mapbox unavailable — using OpenStreetMap.
        {fallbackReason && <small style={{ opacity: 0.7 }}> ({fallbackReason})</small>}
      </span>
      <div className="mds-map-fallback-banner-actions">
        <button onClick={handleDismiss} title="Dismiss">
          Dismiss
        </button>
      </div>
    </div>
  );
};

export default MapFallbackBanner;

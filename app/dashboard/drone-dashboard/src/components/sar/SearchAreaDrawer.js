// src/components/sar/SearchAreaDrawer.js
/**
 * Polygon drawing component for search area definition.
 * Uses Mapbox GL Draw with react-map-gl useControl hook.
 * Falls back to setup instructions if Mapbox token not configured.
 */

import React, { useCallback, useRef, useEffect } from 'react';
import { area as turfArea } from '@turf/turf';

let MapboxDraw;
let useControl;
let mapboxDrawAvailable = false;

try {
  MapboxDraw = require('@mapbox/mapbox-gl-draw');
  if (MapboxDraw.default) MapboxDraw = MapboxDraw.default;
  const rgl = require('react-map-gl');
  useControl = rgl.useControl;
  mapboxDrawAvailable = true;
} catch (e) {
  console.warn('Mapbox GL Draw not available:', e.message);
}

// Draw control wrapper for react-map-gl
const DrawControl = ({ onAreaChange }) => {
  const drawRef = useRef(null);

  const handleCreate = useCallback((e) => {
    if (!drawRef.current) return;
    const data = drawRef.current.getAll();
    if (data.features.length > 1) {
      // Only keep the latest polygon
      const ids = data.features.slice(0, -1).map(f => f.id);
      ids.forEach(id => drawRef.current.delete(id));
    }
    const feature = data.features[data.features.length - 1];
    if (feature && feature.geometry.type === 'Polygon') {
      const coords = feature.geometry.coordinates[0].slice(0, -1); // Remove closing point
      const points = coords.map(([lng, lat]) => ({ lat, lng }));
      const areaSqM = turfArea(feature);
      onAreaChange(points, areaSqM);
    }
  }, [onAreaChange]);

  const handleUpdate = useCallback((e) => {
    handleCreate(e);
  }, [handleCreate]);

  const handleDelete = useCallback(() => {
    onAreaChange([], 0);
  }, [onAreaChange]);

  useControl(
    () => {
      if (!mapboxDrawAvailable) return null;
      const draw = new MapboxDraw({
        displayControlsDefault: false,
        controls: {
          polygon: true,
          trash: true,
        },
        defaultMode: 'simple_select',
      });
      drawRef.current = draw;
      return draw;
    },
    ({ map }) => {
      if (!mapboxDrawAvailable) return;
      map.on('draw.create', handleCreate);
      map.on('draw.update', handleUpdate);
      map.on('draw.delete', handleDelete);
    },
    ({ map }) => {
      if (!mapboxDrawAvailable) return;
      map.off('draw.create', handleCreate);
      map.off('draw.update', handleUpdate);
      map.off('draw.delete', handleDelete);
    },
    { position: 'top-left' }
  );

  return null;
};

export const MapboxSetupInstructions = () => (
  <div className="qs-mapbox-setup">
    <h3>Mapbox Token Required</h3>
    <p>
      QuickScout requires a Mapbox access token for the interactive map.
      Add your token to the environment configuration:
    </p>
    <p><code>REACT_APP_MAPBOX_ACCESS_TOKEN=pk.your_token_here</code></p>
    <p>
      Get a free token at{' '}
      <a href="https://www.mapbox.com/" target="_blank" rel="noopener noreferrer">
        mapbox.com
      </a>
    </p>
  </div>
);

// Safe wrapper: only renders DrawControl when Mapbox Draw is available
const SafeDrawControl = (props) => {
  if (!mapboxDrawAvailable || !useControl) return null;
  return <DrawControl {...props} />;
};

export default SafeDrawControl;

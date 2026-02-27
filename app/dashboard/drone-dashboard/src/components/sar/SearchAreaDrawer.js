// src/components/sar/SearchAreaDrawer.js
/**
 * Polygon drawing component for search area definition (Mapbox mode).
 * Uses Mapbox GL Draw with react-map-gl useControl hook.
 *
 * Exports:
 *   default        – SafeDrawControl (the draw interaction)
 *   SearchAreaOverlay   – Source/Layer that renders the completed polygon
 *   MapboxDrawActionBar – Instruction bar + Reset button (reuses .ldc-* CSS)
 *   MapboxSetupInstructions – Shown when no Mapbox token
 */

import React, { useCallback, useRef, useEffect } from 'react';
import { area as turfArea } from '@turf/turf';

let MapboxDraw;
let useControl;
let RglSource, RglLayer;
let mapboxDrawAvailable = false;

try {
  MapboxDraw = require('@mapbox/mapbox-gl-draw');
  if (MapboxDraw.default) MapboxDraw = MapboxDraw.default;
  require('@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css');
  const rgl = require('react-map-gl');
  useControl = rgl.useControl;
  RglSource = rgl.Source;
  RglLayer = rgl.Layer;
  mapboxDrawAvailable = true;
} catch (e) {
  console.warn('Mapbox GL Draw not available:', e.message);
}

// ---------------------------------------------------------------------------
// Custom Mapbox GL Draw styles — blue theme matching Leaflet draw overlay
// Replaces the default orange/gray that is nearly invisible on satellite.
// ---------------------------------------------------------------------------
const DRAW_STYLES = [
  // Active polygon fill (while being drawn / selected)
  {
    id: 'gl-draw-polygon-fill-active',
    type: 'fill',
    filter: ['all', ['==', 'active', 'true'], ['==', '$type', 'Polygon']],
    paint: { 'fill-color': '#3b82f6', 'fill-outline-color': '#3b82f6', 'fill-opacity': 0.15 },
  },
  // Inactive polygon fill
  {
    id: 'gl-draw-polygon-fill-static',
    type: 'fill',
    filter: ['all', ['==', 'active', 'false'], ['==', '$type', 'Polygon']],
    paint: { 'fill-color': '#3b82f6', 'fill-outline-color': '#3b82f6', 'fill-opacity': 0.15 },
  },
  // Active polygon stroke
  {
    id: 'gl-draw-polygon-stroke-active',
    type: 'line',
    filter: ['all', ['==', 'active', 'true'], ['==', '$type', 'Polygon']],
    layout: { 'line-cap': 'round', 'line-join': 'round' },
    paint: { 'line-color': '#3b82f6', 'line-dasharray': [0.2, 2], 'line-width': 2 },
  },
  // Inactive polygon stroke
  {
    id: 'gl-draw-polygon-stroke-static',
    type: 'line',
    filter: ['all', ['==', 'active', 'false'], ['==', '$type', 'Polygon']],
    layout: { 'line-cap': 'round', 'line-join': 'round' },
    paint: { 'line-color': '#3b82f6', 'line-width': 2 },
  },
  // Active line (edge being drawn)
  {
    id: 'gl-draw-line-active',
    type: 'line',
    filter: ['all', ['==', '$type', 'LineString'], ['==', 'active', 'true']],
    layout: { 'line-cap': 'round', 'line-join': 'round' },
    paint: { 'line-color': '#3b82f6', 'line-dasharray': [0.2, 2], 'line-width': 2 },
  },
  // Inactive line
  {
    id: 'gl-draw-line-static',
    type: 'line',
    filter: ['all', ['==', '$type', 'LineString'], ['==', 'active', 'false']],
    layout: { 'line-cap': 'round', 'line-join': 'round' },
    paint: { 'line-color': '#3b82f6', 'line-width': 2 },
  },
  // Vertex points
  {
    id: 'gl-draw-polygon-and-line-vertex-active',
    type: 'circle',
    filter: ['all', ['==', 'meta', 'vertex'], ['==', '$type', 'Point'], ['!=', 'mode', 'static']],
    paint: { 'circle-radius': 6, 'circle-color': '#3b82f6', 'circle-stroke-color': '#fff', 'circle-stroke-width': 2 },
  },
  // Midpoints
  {
    id: 'gl-draw-polygon-midpoint',
    type: 'circle',
    filter: ['all', ['==', '$type', 'Point'], ['==', 'meta', 'midpoint']],
    paint: { 'circle-radius': 4, 'circle-color': '#3b82f6' },
  },
];

// ---------------------------------------------------------------------------
// DrawControl — hooks into react-map-gl via useControl
// ---------------------------------------------------------------------------
const DrawControl = ({ onAreaChange, controlRef }) => {
  const drawRef = useRef(null);

  // Expose reset() to parent via controlRef
  useEffect(() => {
    if (controlRef) {
      controlRef.current = {
        reset: () => {
          if (drawRef.current) {
            drawRef.current.deleteAll();
            drawRef.current.changeMode('draw_polygon');
          }
        },
      };
    }
    return () => { if (controlRef) controlRef.current = null; };
  }, [controlRef]);

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
    // Clear draw features and re-enter draw mode;
    // the completed polygon is shown by <SearchAreaOverlay>.
    drawRef.current.deleteAll();
    drawRef.current.changeMode('draw_polygon');
  }, [onAreaChange]);

  const handleUpdate = useCallback((e) => {
    handleCreate(e);
  }, [handleCreate]);

  const handleDelete = useCallback(() => {
    onAreaChange([], 0);
    if (drawRef.current) {
      drawRef.current.changeMode('draw_polygon');
    }
  }, [onAreaChange]);

  useControl(
    () => {
      if (!mapboxDrawAvailable) return null;
      const draw = new MapboxDraw({
        displayControlsDefault: false,
        controls: { polygon: false, trash: false },
        defaultMode: 'draw_polygon',
        styles: DRAW_STYLES,
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

// ---------------------------------------------------------------------------
// SearchAreaOverlay — renders the completed polygon as a Source + Layer
// so it persists on the map after drawing (DrawControl clears its features).
// ---------------------------------------------------------------------------
export const SearchAreaOverlay = ({ searchArea }) => {
  if (!RglSource || !RglLayer || !searchArea || searchArea.length < 3) return null;

  const coordinates = searchArea.map(p => [p.lng, p.lat]);
  coordinates.push(coordinates[0]); // Close ring for GeoJSON

  const geojson = {
    type: 'Feature',
    geometry: { type: 'Polygon', coordinates: [coordinates] },
  };

  return (
    <RglSource id="search-area-overlay" type="geojson" data={geojson}>
      <RglLayer
        id="search-area-fill"
        type="fill"
        paint={{ 'fill-color': '#3b82f6', 'fill-opacity': 0.15 }}
      />
      <RglLayer
        id="search-area-stroke"
        type="line"
        paint={{ 'line-color': '#3b82f6', 'line-width': 2 }}
      />
    </RglSource>
  );
};

// ---------------------------------------------------------------------------
// MapboxDrawActionBar — instruction bar with Reset button.
// Reuses the same .ldc-* CSS classes as LeafletDrawControl for consistency.
// ---------------------------------------------------------------------------
export const MapboxDrawActionBar = ({ searchArea, onReset }) => {
  const hasArea = searchArea && searchArea.length >= 3;

  return (
    <div className="ldc-instruction-bar">
      <span className="ldc-instruction-text">
        {hasArea
          ? `Search area defined \u2014 ${searchArea.length} points`
          : 'Click to add points, double-click to finish'}
      </span>
      <div className="ldc-action-group">
        {hasArea && (
          <button className="ldc-action-btn ldc-action-btn--reset" onClick={onReset}>
            Reset
          </button>
        )}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// MapboxSetupInstructions — shown when no token is configured
// ---------------------------------------------------------------------------
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

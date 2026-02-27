// src/components/sar/SearchAreaDrawer.js
/**
 * Polygon drawing component for search area definition (Mapbox mode).
 * Uses Mapbox GL Draw with react-map-gl useControl hook.
 *
 * After drawing, the polygon stays in the draw control in direct_select mode
 * so the user can drag vertices to reshape, or select + Backspace to remove.
 * When the component re-mounts (e.g. plan→monitor→plan) the existing search
 * area is restored into the draw control for continued editing.
 *
 * Exports:
 *   default                – SafeDrawControl (the draw interaction)
 *   MapboxDrawActionBar    – Instruction bar + Reset button (reuses .ldc-* CSS)
 *   MapboxSetupInstructions – Shown when no Mapbox token
 */

import React, { useCallback, useRef, useEffect } from 'react';
import { area as turfArea } from '@turf/turf';

let MapboxDraw;
let useControl;
let mapboxDrawAvailable = false;

try {
  MapboxDraw = require('@mapbox/mapbox-gl-draw');
  if (MapboxDraw.default) MapboxDraw = MapboxDraw.default;
  require('@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css');
  const rgl = require('react-map-gl');
  useControl = rgl.useControl;
  mapboxDrawAvailable = true;
} catch (e) {
  console.warn('Mapbox GL Draw not available:', e.message);
}

// ---------------------------------------------------------------------------
// Custom Mapbox GL Draw styles — blue theme matching Leaflet draw overlay.
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
  // Midpoints (drag to add a vertex between two existing ones)
  {
    id: 'gl-draw-polygon-midpoint',
    type: 'circle',
    filter: ['all', ['==', '$type', 'Point'], ['==', 'meta', 'midpoint']],
    paint: { 'circle-radius': 4, 'circle-color': '#3b82f6' },
  },
];

// ---------------------------------------------------------------------------
// DrawControl — hooks into react-map-gl via useControl.
//
// Props:
//   onAreaChange(points, areaSqM) — called when polygon changes
//   controlRef   — ref exposed to parent for reset()
//   initialArea  — existing search area to restore on mount [{lat,lng},…]
// ---------------------------------------------------------------------------
const DrawControl = ({ onAreaChange, controlRef, initialArea }) => {
  const drawRef = useRef(null);
  const initialAreaRef = useRef(initialArea);

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

  // Restore existing search area polygon when component mounts
  useEffect(() => {
    const area = initialAreaRef.current;
    if (!drawRef.current || !area || area.length < 3) return;

    const coords = area.map(p => [p.lng, p.lat]);
    coords.push(coords[0]); // close ring
    const ids = drawRef.current.add({
      type: 'Feature',
      geometry: { type: 'Polygon', coordinates: [coords] },
    });
    if (ids && ids[0]) {
      // Brief delay ensures the control is fully mounted on the map
      setTimeout(() => {
        if (drawRef.current) {
          try {
            drawRef.current.changeMode('direct_select', { featureId: ids[0] });
          } catch (_) {
            drawRef.current.changeMode('simple_select');
          }
        }
      }, 50);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // draw.create — polygon completed; switch to direct_select for vertex editing.
  // changeMode must be deferred: calling it synchronously inside the create handler
  // causes DrawPolygon.onStop to fire draw.create again → infinite recursion.
  const handleCreate = useCallback((e) => {
    if (!drawRef.current) return;
    // Remove old polygons, keep only the newest
    const data = drawRef.current.getAll();
    if (data.features.length > 1) {
      const ids = data.features.slice(0, -1).map(f => f.id);
      ids.forEach(id => drawRef.current.delete(id));
    }
    const feature = e.features && e.features[0];
    if (feature && feature.geometry.type === 'Polygon') {
      const coords = feature.geometry.coordinates[0].slice(0, -1);
      const points = coords.map(([lng, lat]) => ({ lat, lng }));
      const areaSqM = turfArea(feature);
      onAreaChange(points, areaSqM);
      // Deferred: enter vertex-editing mode after the current event cycle completes
      const fid = feature.id;
      setTimeout(() => {
        if (drawRef.current) {
          try {
            drawRef.current.changeMode('direct_select', { featureId: fid });
          } catch (_) {
            // Feature may have been deleted between event and timeout
          }
        }
      }, 0);
    }
  }, [onAreaChange]);

  // draw.update — vertex dragged or added via midpoint; recalculate area
  const handleUpdate = useCallback((e) => {
    const feature = e.features && e.features[0];
    if (feature && feature.geometry.type === 'Polygon') {
      const coords = feature.geometry.coordinates[0].slice(0, -1);
      const points = coords.map(([lng, lat]) => ({ lat, lng }));
      const areaSqM = turfArea(feature);
      onAreaChange(points, areaSqM);
    }
  }, [onAreaChange]);

  // draw.delete — polygon removed (vertex delete made it invalid, or reset)
  const handleDelete = useCallback(() => {
    onAreaChange([], 0);
    if (drawRef.current) {
      drawRef.current.changeMode('draw_polygon');
    }
  }, [onAreaChange]);

  useControl(
    () => {
      if (!mapboxDrawAvailable) return null;
      const hasInitial = initialAreaRef.current && initialAreaRef.current.length >= 3;
      const draw = new MapboxDraw({
        displayControlsDefault: false,
        controls: { polygon: false, trash: false },
        // Start in simple_select when restoring (useEffect will switch to direct_select),
        // otherwise start in draw_polygon for immediate drawing.
        defaultMode: hasInitial ? 'simple_select' : 'draw_polygon',
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
// MapboxDrawActionBar — instruction bar with Reset button.
// Reuses the same .ldc-* CSS classes as LeafletDrawControl for consistency.
// ---------------------------------------------------------------------------
export const MapboxDrawActionBar = ({ searchArea, onReset }) => {
  const hasArea = searchArea && searchArea.length >= 3;

  return (
    <div className="ldc-instruction-bar">
      <span className="ldc-instruction-text">
        {hasArea
          ? 'Drag vertices to edit \u00b7 Select + Backspace to remove'
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

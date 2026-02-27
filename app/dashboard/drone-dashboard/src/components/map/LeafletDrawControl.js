// src/components/map/LeafletDrawControl.js
// Click-to-draw polygon for Leaflet — no extra npm packages needed.
// Same interface as SearchAreaDrawer.js: onAreaChange(points, areaSqM)

import React, { useState, useCallback, useRef } from 'react';
import { useMapEvents, Polyline, Polygon, Marker } from 'react-leaflet';
import { area as turfArea, polygon as turfPolygon } from '@turf/turf';
import L from 'leaflet';

const vertexIcon = (fillColor) =>
  L.divIcon({
    html: `<div style="width:12px;height:12px;border-radius:50%;background:${fillColor};border:2px solid #fff;box-shadow:0 0 3px rgba(0,0,0,0.4)"></div>`,
    className: '',
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });

const LeafletDrawControl = ({ onAreaChange }) => {
  const [vertices, setVertices] = useState([]);
  const [isComplete, setIsComplete] = useState(false);
  const [dragIndex, setDragIndex] = useState(null);
  const lastClickTime = useRef(0);

  // Calculate area and notify parent
  const notifyArea = useCallback(
    (pts, closed) => {
      if (!onAreaChange) return;
      if (!closed || pts.length < 3) {
        onAreaChange([], 0);
        return;
      }
      const points = pts.map(([lat, lng]) => ({ lat, lng }));
      // Build GeoJSON polygon for turf (lng,lat order, closed ring)
      const coords = pts.map(([lat, lng]) => [lng, lat]);
      coords.push(coords[0]); // close ring
      try {
        const poly = turfPolygon([coords]);
        const areaSqM = turfArea(poly);
        onAreaChange(points, areaSqM);
      } catch {
        onAreaChange(points, 0);
      }
    },
    [onAreaChange]
  );

  // Map click handler
  useMapEvents({
    click(e) {
      if (isComplete) return;

      const now = Date.now();
      const isDoubleClick = now - lastClickTime.current < 400;
      lastClickTime.current = now;

      if (isDoubleClick && vertices.length >= 3) {
        // Double-click to close polygon
        setIsComplete(true);
        notifyArea(vertices, true);
        return;
      }

      const newVerts = [...vertices, [e.latlng.lat, e.latlng.lng]];
      setVertices(newVerts);
    },
  });

  // Handle vertex drag
  const handleVertexDrag = useCallback(
    (index, e) => {
      const { lat, lng } = e.latlng;
      setVertices((prev) => {
        const updated = [...prev];
        updated[index] = [lat, lng];
        if (isComplete) {
          notifyArea(updated, true);
        }
        return updated;
      });
    },
    [isComplete, notifyArea]
  );

  // Clear/reset
  const handleClear = useCallback(() => {
    setVertices([]);
    setIsComplete(false);
    setDragIndex(null);
    if (onAreaChange) onAreaChange([], 0);
  }, [onAreaChange]);

  // Close polygon programmatically
  const handleClose = useCallback(() => {
    if (vertices.length >= 3) {
      setIsComplete(true);
      notifyArea(vertices, true);
    }
  }, [vertices, notifyArea]);

  return (
    <>
      {/* Drawing controls */}
      <div
        style={{
          position: 'absolute',
          top: 10,
          left: 10,
          zIndex: 1000,
          display: 'flex',
          gap: 4,
        }}
      >
        {!isComplete && vertices.length >= 3 && (
          <button
            onClick={handleClose}
            style={{
              padding: '4px 10px',
              fontSize: 12,
              background: '#28a745',
              color: '#fff',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
            }}
          >
            Close Polygon
          </button>
        )}
        {vertices.length > 0 && (
          <button
            onClick={handleClear}
            style={{
              padding: '4px 10px',
              fontSize: 12,
              background: '#dc3545',
              color: '#fff',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
            }}
          >
            Clear
          </button>
        )}
        {!isComplete && vertices.length === 0 && (
          <div
            style={{
              padding: '4px 10px',
              fontSize: 12,
              background: 'rgba(0,0,0,0.6)',
              color: '#fff',
              borderRadius: 4,
            }}
          >
            Click to draw search area
          </div>
        )}
      </div>

      {/* In-progress polyline */}
      {!isComplete && vertices.length >= 2 && (
        <Polyline
          positions={vertices}
          pathOptions={{ color: '#3b82f6', weight: 2, dashArray: '5 5' }}
        />
      )}

      {/* Completed polygon */}
      {isComplete && vertices.length >= 3 && (
        <Polygon
          positions={vertices}
          pathOptions={{
            color: '#3b82f6',
            fillColor: '#3b82f6',
            fillOpacity: 0.15,
            weight: 2,
          }}
        />
      )}

      {/* Vertex markers (draggable) */}
      {vertices.map((pos, i) => (
        <Marker
          key={i}
          position={pos}
          icon={vertexIcon(i === 0 ? '#28a745' : '#3b82f6')}
          draggable={true}
          eventHandlers={{
            dragstart: () => setDragIndex(i),
            drag: (e) => handleVertexDrag(i, e),
            dragend: () => setDragIndex(null),
          }}
        />
      ))}
    </>
  );
};

export default LeafletDrawControl;

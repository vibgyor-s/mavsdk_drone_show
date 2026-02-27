// src/components/map/LeafletDrawControl.js
// Click-to-draw polygon for Leaflet — no extra npm packages needed.
// Same interface as SearchAreaDrawer.js: onAreaChange(points, areaSqM)
// Uses deferred-click pattern to avoid stray vertex on double-click close.

import React, { useState, useCallback, useRef, useMemo, useEffect } from 'react';
import { useMapEvents, Polyline, Polygon, Marker, useMap } from 'react-leaflet';
import { area as turfArea, polygon as turfPolygon } from '@turf/turf';
import L from 'leaflet';

// Memoized icon factories (outside component to avoid recreation)
const createVertexIcon = (fillColor) =>
  L.divIcon({
    html: `<div style="width:12px;height:12px;border-radius:50%;background:${fillColor};border:2px solid #fff;box-shadow:0 0 3px rgba(0,0,0,0.4)"></div>`,
    className: '',
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });

const createStartIcon = () =>
  L.divIcon({
    html: `<div style="width:16px;height:16px;border-radius:50%;background:#28a745;border:2px solid #fff;box-shadow:0 0 6px rgba(40,167,69,0.6)"></div>`,
    className: '',
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });

const VERTEX_ICON = createVertexIcon('#3b82f6');
const START_ICON = createStartIcon();
const CLICK_DELAY = 300; // ms to differentiate single vs double click

const LeafletDrawControl = ({ onAreaChange }) => {
  const [vertices, setVertices] = useState([]);
  const [isComplete, setIsComplete] = useState(false);
  const [mousePos, setMousePos] = useState(null);
  const clickTimerRef = useRef(null);
  const pendingClickRef = useRef(null);
  const rafRef = useRef(null);
  const map = useMap();

  // Calculate area and notify parent
  const notifyArea = useCallback(
    (pts, closed) => {
      if (!onAreaChange) return;
      if (!closed || pts.length < 3) {
        onAreaChange([], 0);
        return;
      }
      const points = pts.map(([lat, lng]) => ({ lat, lng }));
      const coords = pts.map(([lat, lng]) => [lng, lat]);
      coords.push(coords[0]);
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

  // Close the polygon
  const closePolygon = useCallback(
    (verts) => {
      if (verts.length >= 3) {
        setIsComplete(true);
        setMousePos(null);
        notifyArea(verts, true);
      }
    },
    [notifyArea]
  );

  // Add a single vertex
  const addVertex = useCallback(
    (latlng) => {
      setVertices((prev) => {
        const newVerts = [...prev, [latlng.lat, latlng.lng]];
        return newVerts;
      });
    },
    []
  );

  // Deferred click: wait CLICK_DELAY ms; if another click arrives, treat as double-click
  useMapEvents({
    click(e) {
      if (isComplete) return;

      if (clickTimerRef.current) {
        // Second click within delay → double-click → close polygon
        clearTimeout(clickTimerRef.current);
        clickTimerRef.current = null;
        pendingClickRef.current = null;
        // Close with current vertices (don't add the second click as a vertex)
        setVertices((prev) => {
          if (prev.length >= 3) {
            closePolygon(prev);
          }
          return prev;
        });
        return;
      }

      // First click: defer
      pendingClickRef.current = e.latlng;
      clickTimerRef.current = setTimeout(() => {
        // Timer expired → commit vertex
        const latlng = pendingClickRef.current;
        if (latlng) {
          addVertex(latlng);
        }
        clickTimerRef.current = null;
        pendingClickRef.current = null;
      }, CLICK_DELAY);
    },
    dblclick(e) {
      // Prevent default zoom on double-click while drawing
      if (!isComplete) {
        e.originalEvent?.preventDefault?.();
        e.originalEvent?.stopPropagation?.();
      }
    },
    mousemove(e) {
      if (!isComplete && vertices.length > 0) {
        if (rafRef.current) cancelAnimationFrame(rafRef.current);
        rafRef.current = requestAnimationFrame(() => {
          setMousePos([e.latlng.lat, e.latlng.lng]);
        });
      }
    },
  });

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      if (clickTimerRef.current) clearTimeout(clickTimerRef.current);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  // Disable double-click zoom while drawing
  useEffect(() => {
    if (!isComplete) {
      map.doubleClickZoom.disable();
    } else {
      map.doubleClickZoom.enable();
    }
    return () => {
      map.doubleClickZoom.enable();
    };
  }, [isComplete, map]);

  // Handle vertex drag with requestAnimationFrame debounce
  const handleVertexDrag = useCallback(
    (index, e) => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(() => {
        const { lat, lng } = e.latlng;
        setVertices((prev) => {
          const updated = [...prev];
          updated[index] = [lat, lng];
          if (isComplete) {
            notifyArea(updated, true);
          }
          return updated;
        });
      });
    },
    [isComplete, notifyArea]
  );

  // Undo last vertex
  const handleUndo = useCallback(() => {
    setVertices((prev) => {
      const updated = prev.slice(0, -1);
      return updated;
    });
  }, []);

  // Clear/reset
  const handleClear = useCallback(() => {
    setVertices([]);
    setIsComplete(false);
    setMousePos(null);
    if (clickTimerRef.current) {
      clearTimeout(clickTimerRef.current);
      clickTimerRef.current = null;
    }
    if (onAreaChange) onAreaChange([], 0);
  }, [onAreaChange]);

  // Close polygon via button or clicking first vertex
  const handleClose = useCallback(() => {
    closePolygon(vertices);
  }, [vertices, closePolygon]);

  // Close on first vertex click (when >=3 vertices)
  const handleFirstVertexClick = useCallback((e) => {
    e.originalEvent?.stopPropagation?.();
    if (vertices.length >= 3 && !isComplete) {
      closePolygon(vertices);
    }
  }, [vertices, isComplete, closePolygon]);

  // Ctrl+Z undo and Escape key handler
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.ctrlKey && e.key === 'z' && !isComplete && vertices.length > 0) {
        e.preventDefault();
        handleUndo();
      }
      if (e.key === 'Escape' && !isComplete) {
        // Cancel any pending deferred click
        if (clickTimerRef.current) {
          clearTimeout(clickTimerRef.current);
          clickTimerRef.current = null;
        }
        pendingClickRef.current = null;
        // Reset drawing if vertices exist
        if (vertices.length > 0) {
          handleClear();
        }
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isComplete, vertices.length, handleUndo, handleClear]);

  // Instruction text based on state
  const instruction = useMemo(() => {
    if (isComplete) return 'Polygon complete. Click Reset to start over.';
    if (vertices.length === 0) return 'Click to place first point';
    if (vertices.length < 3) return `Click to add points (${vertices.length}/3 min) · Esc to cancel`;
    return 'Click to add points, double-click or click first point to close · Esc to reset';
  }, [isComplete, vertices.length]);

  // Preview line from last vertex to mouse cursor
  const previewLine = useMemo(() => {
    if (isComplete || vertices.length === 0 || !mousePos) return null;
    return [vertices[vertices.length - 1], mousePos];
  }, [isComplete, vertices, mousePos]);

  return (
    <>
      {/* Instruction bar — stopPropagation prevents clicks from bubbling to map */}
      <div className="ldc-instruction-bar" onClickCapture={e => e.stopPropagation()}>
        <span className="ldc-instruction-text">{instruction}</span>
        <div className="ldc-action-group">
          {!isComplete && vertices.length > 0 && (
            <button
              className="ldc-action-btn ldc-action-btn--undo"
              onClick={(e) => { e.stopPropagation(); handleUndo(); }}
              title="Undo last point (Ctrl+Z)"
            >
              Undo
            </button>
          )}
          {!isComplete && vertices.length >= 3 && (
            <button
              className="ldc-action-btn ldc-action-btn--close"
              onClick={(e) => { e.stopPropagation(); handleClose(); }}
            >
              Close Polygon
            </button>
          )}
          {vertices.length > 0 && (
            <button
              className="ldc-action-btn ldc-action-btn--reset"
              onClick={(e) => { e.stopPropagation(); handleClear(); }}
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Preview line from last vertex to cursor */}
      {previewLine && (
        <Polyline
          positions={previewLine}
          pathOptions={{ color: '#3b82f6', weight: 2, dashArray: '6 4', opacity: 0.6 }}
        />
      )}

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
          icon={i === 0 ? START_ICON : VERTEX_ICON}
          draggable={true}
          eventHandlers={{
            click: i === 0 ? handleFirstVertexClick : undefined,
            drag: (e) => handleVertexDrag(i, e),
          }}
        />
      ))}
    </>
  );
};

export default LeafletDrawControl;

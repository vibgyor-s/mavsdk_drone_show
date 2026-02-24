// src/components/sar/POIMarkerSystem.js
/**
 * POI marker system for map display and management.
 * Click-to-mark flow, colored by type/priority.
 */

import React, { useState, useCallback } from 'react';
import { createPOI } from '../../services/sarApiService';
import { toast } from 'react-toastify';

let Marker, Popup;
let mapboxAvailable = false;

try {
  const rgl = require('react-map-gl');
  Marker = rgl.Marker;
  Popup = rgl.Popup;
  mapboxAvailable = true;
} catch (e) {
  mapboxAvailable = false;
}

const PRIORITY_COLORS = {
  critical: '#dc3545',
  high: '#fd7e14',
  medium: '#ffc107',
  low: '#00d4ff',
};

const POIMarkerSystem = ({ pois, missionId, onPOIAdded, addingPOI, onMapClick }) => {
  const [selectedPOI, setSelectedPOI] = useState(null);

  const handleMapClick = useCallback(async (e) => {
    if (!addingPOI || !missionId) return;
    const { lng, lat } = e.lngLat;
    try {
      const poi = await createPOI(missionId, {
        lat, lng,
        type: 'other',
        priority: 'medium',
        notes: '',
      });
      if (onPOIAdded) onPOIAdded(poi);
      toast.success('POI added');
    } catch (err) {
      toast.error('Failed to add POI');
    }
  }, [addingPOI, missionId, onPOIAdded]);

  // Expose click handler
  if (onMapClick) {
    onMapClick.current = handleMapClick;
  }

  if (!mapboxAvailable || !pois || pois.length === 0) return null;

  return (
    <>
      {pois.map((poi) => (
        <Marker
          key={poi.id}
          latitude={poi.lat}
          longitude={poi.lng}
          anchor="center"
          onClick={(e) => {
            e.originalEvent.stopPropagation();
            setSelectedPOI(poi);
          }}
        >
          <div
            style={{
              width: 14,
              height: 14,
              borderRadius: '50%',
              background: PRIORITY_COLORS[poi.priority] || PRIORITY_COLORS.medium,
              border: '2px solid white',
              boxShadow: '0 0 4px rgba(0,0,0,0.5)',
              cursor: 'pointer',
            }}
          />
        </Marker>
      ))}

      {selectedPOI && (
        <Popup
          latitude={selectedPOI.lat}
          longitude={selectedPOI.lng}
          anchor="bottom"
          onClose={() => setSelectedPOI(null)}
          closeOnClick={false}
        >
          <div style={{ padding: 4, fontSize: 12, minWidth: 150 }}>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>
              {selectedPOI.type?.toUpperCase()} - {selectedPOI.priority?.toUpperCase()}
            </div>
            {selectedPOI.notes && <div style={{ marginBottom: 4 }}>{selectedPOI.notes}</div>}
            {selectedPOI.reported_by_drone && (
              <div style={{ color: '#888' }}>Drone: {selectedPOI.reported_by_drone}</div>
            )}
          </div>
        </Popup>
      )}
    </>
  );
};

export default POIMarkerSystem;

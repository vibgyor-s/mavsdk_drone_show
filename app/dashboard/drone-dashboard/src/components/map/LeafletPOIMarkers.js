// src/components/map/LeafletPOIMarkers.js
// POI markers for Leaflet — same interface as POIMarkerSystem.js

import React, { useState } from 'react';
import { CircleMarker, Popup, useMapEvents } from 'react-leaflet';
import { createPOI } from '../../services/sarApiService';
import { toast } from 'react-toastify';

const PRIORITY_COLORS = {
  critical: '#dc3545',
  high: '#fd7e14',
  medium: '#ffc107',
  low: '#00d4ff',
};

// Click handler component
const POIClickHandler = ({ addingPOI, missionId, onPOIAdded }) => {
  useMapEvents({
    click(e) {
      if (!addingPOI || !missionId) return;
      const { lat, lng } = e.latlng;

      createPOI(missionId, {
        lat,
        lng,
        type: 'other',
        priority: 'medium',
        notes: '',
      })
        .then((poi) => {
          if (onPOIAdded) onPOIAdded(poi);
          toast.success('POI added');
        })
        .catch(() => {
          toast.error('Failed to add POI');
        });
    },
  });
  return null;
};

const LeafletPOIMarkers = ({ pois, missionId, onPOIAdded, addingPOI }) => {
  const [selectedPOI, setSelectedPOI] = useState(null);

  if (!pois) return <POIClickHandler addingPOI={addingPOI} missionId={missionId} onPOIAdded={onPOIAdded} />;

  return (
    <>
      <POIClickHandler addingPOI={addingPOI} missionId={missionId} onPOIAdded={onPOIAdded} />

      {pois.map((poi) => (
        <CircleMarker
          key={poi.id}
          center={[poi.lat, poi.lng]}
          radius={7}
          pathOptions={{
            color: '#fff',
            fillColor: PRIORITY_COLORS[poi.priority] || PRIORITY_COLORS.medium,
            fillOpacity: 1,
            weight: 2,
          }}
          eventHandlers={{
            click: () => setSelectedPOI(poi),
          }}
        >
          {selectedPOI && selectedPOI.id === poi.id && (
            <Popup onClose={() => setSelectedPOI(null)}>
              <div style={{ padding: 4, fontSize: 12, minWidth: 150 }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>
                  {poi.type?.toUpperCase()} - {poi.priority?.toUpperCase()}
                </div>
                {poi.notes && <div style={{ marginBottom: 4 }}>{poi.notes}</div>}
                {poi.reported_by_drone && (
                  <div style={{ color: '#888' }}>Drone: {poi.reported_by_drone}</div>
                )}
              </div>
            </Popup>
          )}
        </CircleMarker>
      ))}
    </>
  );
};

export default LeafletPOIMarkers;

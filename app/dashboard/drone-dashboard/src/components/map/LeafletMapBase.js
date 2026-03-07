// src/components/map/LeafletMapBase.js
// Reusable Leaflet map wrapper — Google Satellite default, layer preference persisted

import React, { useCallback } from 'react';
import { MapContainer, TileLayer, LayersControl, useMapEvents } from 'react-leaflet';
import {
  TILE_LAYERS,
  LEAFLET_DEFAULTS,
  getUserTilePreference,
  setUserTilePreference,
} from '../../config/mapConfig';
import '../../styles/MapCommon.css';

const { BaseLayer } = LayersControl;

// Reverse-lookup: tile layer name → config key
const NAME_TO_KEY = Object.fromEntries(
  Object.entries(TILE_LAYERS).map(([key, cfg]) => [cfg.name, key])
);

/** Inner component that listens for layer changes and persists the choice */
const LayerPersist = () => {
  useMapEvents({
    baselayerchange(e) {
      const key = NAME_TO_KEY[e.name];
      if (key) setUserTilePreference(key);
    },
  });
  return null;
};

const LeafletMapBase = ({
  center = [35.6895, 139.6917],
  zoom = 13,
  style,
  children,
  showLayerControl = true,
  defaultLayer,
  onClick,
  className = '',
  ...rest
}) => {
  const activeLayer = defaultLayer || getUserTilePreference();

  return (
    <div className={`mds-map-container ${className}`} style={style}>
      <MapContainer
        center={center}
        zoom={zoom}
        minZoom={LEAFLET_DEFAULTS.minZoom}
        maxZoom={LEAFLET_DEFAULTS.maxZoom}
        maxBounds={LEAFLET_DEFAULTS.maxBounds}
        maxBoundsViscosity={LEAFLET_DEFAULTS.maxBoundsViscosity}
        worldCopyJump={LEAFLET_DEFAULTS.worldCopyJump}
        scrollWheelZoom
        style={{ width: '100%', height: '100%' }}
        {...rest}
      >
        {showLayerControl ? (
          <>
            <LayerPersist />
            <LayersControl position="topright">
              {Object.entries(TILE_LAYERS).map(([key, cfg]) => (
                <BaseLayer key={key} checked={activeLayer === key} name={cfg.name}>
                  <TileLayer
                    url={cfg.url}
                    attribution={cfg.attribution}
                    subdomains={cfg.subdomains}
                    maxNativeZoom={cfg.maxNativeZoom}
                    maxZoom={LEAFLET_DEFAULTS.maxZoom}
                    noWrap={true}
                  />
                </BaseLayer>
              ))}
            </LayersControl>
          </>
        ) : (
          <TileLayer
            url={TILE_LAYERS[activeLayer]?.url || TILE_LAYERS.googleSatellite.url}
            attribution={TILE_LAYERS[activeLayer]?.attribution || TILE_LAYERS.googleSatellite.attribution}
            subdomains={TILE_LAYERS[activeLayer]?.subdomains}
            maxNativeZoom={TILE_LAYERS[activeLayer]?.maxNativeZoom || TILE_LAYERS.googleSatellite.maxNativeZoom}
            maxZoom={LEAFLET_DEFAULTS.maxZoom}
            noWrap={true}
          />
        )}

        {children}
      </MapContainer>
    </div>
  );
};

export default LeafletMapBase;

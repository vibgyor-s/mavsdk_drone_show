// src/components/map/LeafletMapBase.js
// Reusable Leaflet map wrapper with normalized provider config and persisted layer preference

import React from 'react';
import { MapContainer, TileLayer, LayersControl, useMapEvents } from 'react-leaflet';
import {
  LEAFLET_DEFAULTS,
  getUserTilePreference,
  setUserTilePreference,
  getLeafletTileLayerConfig,
  TILE_LAYERS,
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
  const resolvedActiveLayer = getLeafletTileLayerConfig(activeLayer);

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
              {Object.keys(TILE_LAYERS).map((key) => {
                const cfg = getLeafletTileLayerConfig(key);
                return (
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
                );
              })}
            </LayersControl>
          </>
        ) : (
          <TileLayer
            url={resolvedActiveLayer.url}
            attribution={resolvedActiveLayer.attribution}
            subdomains={resolvedActiveLayer.subdomains}
            maxNativeZoom={resolvedActiveLayer.maxNativeZoom}
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

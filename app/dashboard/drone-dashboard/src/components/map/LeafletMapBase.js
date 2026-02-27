// src/components/map/LeafletMapBase.js
// Reusable Leaflet map wrapper with white-on-zoom-out fixes baked in

import React from 'react';
import { MapContainer, TileLayer, LayersControl } from 'react-leaflet';
import { TILE_LAYERS, LEAFLET_DEFAULTS } from '../../config/mapConfig';
import '../../styles/MapCommon.css';

const { BaseLayer } = LayersControl;

const LeafletMapBase = ({
  center = [35.6895, 139.6917],
  zoom = 13,
  style,
  children,
  showLayerControl = true,
  defaultLayer = 'osm',
  onClick,
  className = '',
  ...rest
}) => {
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
          <LayersControl position="topright">
            <BaseLayer checked={defaultLayer === 'osm'} name={TILE_LAYERS.osm.name}>
              <TileLayer
                url={TILE_LAYERS.osm.url}
                attribution={TILE_LAYERS.osm.attribution}
                maxNativeZoom={TILE_LAYERS.osm.maxNativeZoom}
                maxZoom={LEAFLET_DEFAULTS.maxZoom}
                noWrap={true}
              />
            </BaseLayer>
            <BaseLayer checked={defaultLayer === 'esriSatellite'} name={TILE_LAYERS.esriSatellite.name}>
              <TileLayer
                url={TILE_LAYERS.esriSatellite.url}
                attribution={TILE_LAYERS.esriSatellite.attribution}
                maxNativeZoom={TILE_LAYERS.esriSatellite.maxNativeZoom}
                maxZoom={LEAFLET_DEFAULTS.maxZoom}
                noWrap={true}
              />
            </BaseLayer>
            <BaseLayer checked={defaultLayer === 'openTopoMap'} name={TILE_LAYERS.openTopoMap.name}>
              <TileLayer
                url={TILE_LAYERS.openTopoMap.url}
                attribution={TILE_LAYERS.openTopoMap.attribution}
                maxNativeZoom={TILE_LAYERS.openTopoMap.maxNativeZoom}
                maxZoom={LEAFLET_DEFAULTS.maxZoom}
                noWrap={true}
              />
            </BaseLayer>
            <BaseLayer checked={defaultLayer === 'googleSatellite'} name={TILE_LAYERS.googleSatellite.name}>
              <TileLayer
                url={TILE_LAYERS.googleSatellite.url}
                attribution={TILE_LAYERS.googleSatellite.attribution}
                subdomains={TILE_LAYERS.googleSatellite.subdomains}
                maxNativeZoom={TILE_LAYERS.googleSatellite.maxNativeZoom}
                maxZoom={LEAFLET_DEFAULTS.maxZoom}
                noWrap={true}
              />
            </BaseLayer>
          </LayersControl>
        ) : (
          <TileLayer
            url={TILE_LAYERS[defaultLayer]?.url || TILE_LAYERS.osm.url}
            attribution={TILE_LAYERS[defaultLayer]?.attribution || TILE_LAYERS.osm.attribution}
            maxNativeZoom={TILE_LAYERS[defaultLayer]?.maxNativeZoom || TILE_LAYERS.osm.maxNativeZoom}
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

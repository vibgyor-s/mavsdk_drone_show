// src/config/mapConfig.js
// Shared map configuration constants for dual-provider (Mapbox + Leaflet) system

export const MAP_PROVIDERS = {
  MAPBOX: 'mapbox',
  LEAFLET: 'leaflet',
};

export const DEFAULT_PROVIDER = MAP_PROVIDERS.MAPBOX;

export const MAPBOX_TOKEN =
  process.env.REACT_APP_MAPBOX_ACCESS_TOKEN ||
  process.env.REACT_APP_MAPBOX_TOKEN ||
  process.env.REACT_APP_MAP_TOKEN ||
  '';

export const TILE_LAYERS = {
  osm: {
    name: 'OpenStreetMap',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://osm.org/copyright">OpenStreetMap</a> contributors',
  },
  esriSatellite: {
    name: 'Satellite (Esri)',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
  },
  openTopoMap: {
    name: 'OpenTopoMap',
    url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenTopoMap contributors',
  },
  googleSatellite: {
    name: 'Google Satellite',
    url: 'https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
    attribution: 'Map data &copy; Google',
    subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
  },
};

export const DEFAULT_CENTER = { lat: 35.6895, lng: 139.6917 }; // Tokyo

export const LEAFLET_DEFAULTS = {
  minZoom: 2,
  maxZoom: 22,
  maxBounds: [[-90, -180], [90, 180]],
  maxBoundsViscosity: 1.0,
  worldCopyJump: true,
};

export const PROVIDER_STORAGE_KEY = 'mds_map_provider';

// Mapbox connectivity check URL (lightweight style metadata)
export const MAPBOX_PING_URL = (token) =>
  `https://api.mapbox.com/styles/v1/mapbox/streets-v12?access_token=${token}`;

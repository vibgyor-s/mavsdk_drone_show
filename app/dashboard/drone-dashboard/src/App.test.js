import React from 'react';
import { render } from '@testing-library/react';

// Mock visualization libraries that require browser APIs unavailable in JSDOM.
// react-cytoscapejs and mapbox-gl are mapped to empty mocks via moduleNameMapper
// in package.json because their ESM exports prevent jest.mock from resolving them.
jest.mock('react-map-gl', () => ({
  __esModule: true,
  default: function MockMap({ children }) { return <div data-testid="map">{children}</div>; },
  Marker: function MockMarker() { return null; },
  NavigationControl: function MockNav() { return null; },
  Source: function MockSource() { return null; },
  Layer: function MockLayer() { return null; },
}));
jest.mock('react-plotly.js', () => {
  return function MockPlot() { return <div data-testid="plotly" />; };
});
jest.mock('react-leaflet', () => ({
  MapContainer: function MockMapContainer({ children }) { return <div>{children}</div>; },
  TileLayer: function MockTileLayer() { return null; },
  Marker: function MockMarker() { return null; },
  Popup: function MockPopup() { return null; },
  Polyline: function MockPolyline() { return null; },
  useMap: jest.fn(() => ({ setView: jest.fn(), fitBounds: jest.fn() })),
}));
jest.mock('@react-three/drei', () => ({
  OrbitControls: function MockOrbit() { return null; },
  Line: function MockLine() { return null; },
  Text: function MockText() { return null; },
}));
jest.mock('react-three-fiber', () => ({
  Canvas: function MockCanvas({ children }) { return <div>{children}</div>; },
  useFrame: jest.fn(),
  useThree: jest.fn(() => ({ camera: {}, gl: {} })),
}));
jest.mock('@mapbox/mapbox-gl-draw', () => jest.fn());

// Mock services that make HTTP calls
jest.mock('./services/logService', () => ({
  reportFrontendError: jest.fn().mockResolvedValue({ status: 'received' }),
  getSources: jest.fn().mockResolvedValue({ components: {} }),
  getHealth: jest.fn().mockResolvedValue({ status: 'healthy' }),
  fetchLogs: jest.fn().mockResolvedValue({ entries: [], total: 0 }),
}));
jest.mock('axios', () => ({
  get: jest.fn().mockResolvedValue({ data: [] }),
  post: jest.fn().mockResolvedValue({ data: {} }),
  create: jest.fn(() => ({
    get: jest.fn().mockResolvedValue({ data: [] }),
    post: jest.fn().mockResolvedValue({ data: {} }),
    interceptors: { request: { use: jest.fn() }, response: { use: jest.fn() } },
  })),
}));

import App from './App';

describe('App', () => {
  test('renders without crashing', () => {
    render(<App />);
    expect(document.querySelector('.app-container')).toBeInTheDocument();
  });
});

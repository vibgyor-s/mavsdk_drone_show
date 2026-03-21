import React from 'react';
import { render } from '@testing-library/react';

// Mock all page-level components to avoid pulling in heavy visualization
// dependencies (leaflet, mapbox, cytoscape, plotly, three.js, geodesy)
// that use ESM and browser APIs incompatible with JSDOM.
jest.mock('./pages/Overview', () => () => <div data-testid="overview" />);
jest.mock('./pages/SwarmDesign', () => () => <div data-testid="swarm-design" />);
jest.mock('./pages/MissionConfig', () => () => <div data-testid="mission-config" />);
jest.mock('./pages/DroneShowDesign', () => () => <div data-testid="drone-show-design" />);
jest.mock('./pages/CustomShowPage', () => () => <div data-testid="custom-show" />);
jest.mock('./pages/GlobeView', () => () => <div data-testid="globe-view" />);
jest.mock('./pages/ManageDroneShow', () => () => <div data-testid="manage-drone-show" />);
jest.mock('./pages/SwarmTrajectory', () => () => <div data-testid="swarm-trajectory" />);
jest.mock('./pages/TrajectoryPlanning', () => () => <div data-testid="trajectory-planning" />);
jest.mock('./pages/QuickScoutPage', () => () => <div data-testid="quickscout" />);
jest.mock('./pages/LogViewer', () => () => <div data-testid="log-viewer" />);
jest.mock('./components/DroneDetail', () => () => <div data-testid="drone-detail" />);
jest.mock('./components/SidebarMenu', () => ({ collapsed, onToggle }) => (
  <nav data-testid="sidebar" data-collapsed={collapsed} />
));
jest.mock('./components/SyncWarningBanner', () => () => null);
jest.mock('./components/ErrorBoundary', () => ({ children }) => <>{children}</>);

// Mock services
jest.mock('./services/logService', () => ({
  reportFrontendError: jest.fn().mockResolvedValue({ status: 'received' }),
}));

import App from './App';

describe('App', () => {
  test('renders without crashing', () => {
    const { container } = render(<App />);
    expect(container.querySelector('.app-container')).toBeInTheDocument();
  });

  test('renders sidebar navigation', () => {
    render(<App />);
    expect(document.querySelector('[data-testid="sidebar"]')).toBeInTheDocument();
  });

  test('renders default route (Overview)', () => {
    render(<App />);
    expect(document.querySelector('[data-testid="overview"]')).toBeInTheDocument();
  });
});

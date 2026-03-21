import React from 'react';
import { render } from '@testing-library/react';

// Mock eagerly loaded components
jest.mock('./pages/Overview', () => () => <div data-testid="overview" />);
jest.mock('./pages/MissionConfig', () => () => <div data-testid="mission-config" />);
jest.mock('./components/SidebarMenu', () => ({ collapsed, onToggle }) => (
  <nav data-testid="sidebar" data-collapsed={collapsed} />
));
jest.mock('./components/SyncWarningBanner', () => () => null);
jest.mock('./components/ErrorBoundary', () => ({ children }) => <>{children}</>);

// Mock lazy-loaded pages — must return { default: Component } for React.lazy
jest.mock('./pages/SwarmDesign', () => ({ __esModule: true, default: () => <div data-testid="swarm-design" /> }));
jest.mock('./pages/DroneShowDesign', () => ({ __esModule: true, default: () => <div data-testid="drone-show-design" /> }));
jest.mock('./pages/CustomShowPage', () => ({ __esModule: true, default: () => <div data-testid="custom-show" /> }));
jest.mock('./pages/GlobeView', () => ({ __esModule: true, default: () => <div data-testid="globe-view" /> }));
jest.mock('./pages/ManageDroneShow', () => ({ __esModule: true, default: () => <div data-testid="manage-drone-show" /> }));
jest.mock('./pages/SwarmTrajectory', () => ({ __esModule: true, default: () => <div data-testid="swarm-trajectory" /> }));
jest.mock('./pages/TrajectoryPlanning', () => ({ __esModule: true, default: () => <div data-testid="trajectory-planning" /> }));
jest.mock('./pages/QuickScoutPage', () => ({ __esModule: true, default: () => <div data-testid="quickscout" /> }));
jest.mock('./pages/LogViewer', () => ({ __esModule: true, default: () => <div data-testid="log-viewer" /> }));
jest.mock('./components/DroneDetail', () => ({ __esModule: true, default: () => <div data-testid="drone-detail" /> }));

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

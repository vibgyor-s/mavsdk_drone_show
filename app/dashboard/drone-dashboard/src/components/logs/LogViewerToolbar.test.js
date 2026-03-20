// src/components/logs/LogViewerToolbar.test.js
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import LogViewerToolbar from './LogViewerToolbar';
import { MODES } from '../../constants/logConstants';

describe('LogViewerToolbar', () => {
  const defaultProps = {
    mode: MODES.OPS,
    onModeChange: jest.fn(),
    level: 'WARNING',
    onLevelChange: jest.fn(),
    paused: false,
    onTogglePause: jest.fn(),
    connected: true,
    searchQuery: '',
    onSearchChange: jest.fn(),
    sessions: [],
    selectedSession: null,
    onSessionSelect: jest.fn(),
    sessionsLoading: false,
    onExportOpen: jest.fn(),
    onClear: jest.fn(),
  };

  test('renders Ops and Dev mode buttons', () => {
    render(<LogViewerToolbar {...defaultProps} />);
    expect(screen.getByText('Ops')).toBeInTheDocument();
    expect(screen.getByText('Dev')).toBeInTheDocument();
  });

  test('clicking Dev button calls onModeChange', () => {
    render(<LogViewerToolbar {...defaultProps} />);
    fireEvent.click(screen.getByText('Dev'));
    expect(defaultProps.onModeChange).toHaveBeenCalledWith(MODES.DEV);
  });

  test('shows search input only in Dev mode', () => {
    const { rerender } = render(<LogViewerToolbar {...defaultProps} />);
    expect(screen.queryByPlaceholderText('Search logs...')).not.toBeInTheDocument();
    rerender(<LogViewerToolbar {...defaultProps} mode={MODES.DEV} />);
    expect(screen.getByPlaceholderText('Search logs...')).toBeInTheDocument();
  });

  test('shows Export button only in Dev mode', () => {
    const { rerender } = render(<LogViewerToolbar {...defaultProps} />);
    expect(screen.queryByText('Export')).not.toBeInTheDocument();
    rerender(<LogViewerToolbar {...defaultProps} mode={MODES.DEV} />);
    expect(screen.getByText('Export')).toBeInTheDocument();
  });
});

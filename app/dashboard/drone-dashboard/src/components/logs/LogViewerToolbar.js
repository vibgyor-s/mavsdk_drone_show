// src/components/logs/LogViewerToolbar.js
import React from 'react';
import { FaEye, FaCode, FaPause, FaPlay, FaSearch, FaDownload, FaTrash } from 'react-icons/fa';
import { LOG_LEVELS, MODES } from '../../constants/logConstants';
import LogLiveIndicator from './LogLiveIndicator';
import LogSessionSelector from './LogSessionSelector';

const LogViewerToolbar = ({
  mode,
  onModeChange,
  level,
  onLevelChange,
  paused,
  onTogglePause,
  connected,
  searchQuery,
  onSearchChange,
  sessions,
  selectedSession,
  onSessionSelect,
  sessionsLoading,
  onExportOpen,
  onClear,
}) => {
  return (
    <div className="log-toolbar" role="toolbar" aria-label="Log viewer controls">
      {/* Mode toggle */}
      <div className="log-mode-toggle">
        <button
          className={mode === MODES.OPS ? 'active' : ''}
          onClick={() => onModeChange(MODES.OPS)}
          title="Operations mode — WARNING+ only"
        >
          <FaEye size={12} /> Ops
        </button>
        <button
          className={mode === MODES.DEV ? 'active' : ''}
          onClick={() => onModeChange(MODES.DEV)}
          title="Developer mode — all levels, search, export"
        >
          <FaCode size={12} /> Dev
        </button>
      </div>

      {/* Level filter */}
      <div className="log-toolbar-group">
        <select
          value={level || ''}
          onChange={e => onLevelChange(e.target.value || null)}
          aria-label="Minimum log level"
        >
          <option value="">All Levels</option>
          {LOG_LEVELS.map(l => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>
      </div>

      {/* Session selector */}
      <LogSessionSelector
        sessions={sessions}
        selectedSession={selectedSession}
        onSelect={onSessionSelect}
        loading={sessionsLoading}
      />

      {/* Live indicator */}
      {!selectedSession && (
        <LogLiveIndicator connected={connected} paused={paused} />
      )}

      <div className="log-toolbar-spacer" />

      {/* Search (Developer mode only) */}
      {mode === MODES.DEV && (
        <div className="log-toolbar-group">
          <FaSearch size={12} />
          <input
            type="text"
            className="log-search-input"
            placeholder="Search logs..."
            value={searchQuery}
            onChange={e => onSearchChange(e.target.value)}
            aria-label="Search log messages"
          />
        </div>
      )}

      {/* Pause/Resume */}
      {!selectedSession && (
        <button onClick={onTogglePause} title={paused ? 'Resume' : 'Pause'}>
          {paused ? <FaPlay size={12} /> : <FaPause size={12} />}
        </button>
      )}

      {/* Clear */}
      <button onClick={onClear} title="Clear log entries">
        <FaTrash size={12} />
      </button>

      {/* Export (Developer mode only) */}
      {mode === MODES.DEV && (
        <button onClick={onExportOpen} title="Export sessions">
          <FaDownload size={12} /> Export
        </button>
      )}
    </div>
  );
};

export default LogViewerToolbar;

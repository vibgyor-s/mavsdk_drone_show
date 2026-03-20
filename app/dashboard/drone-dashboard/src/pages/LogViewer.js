// src/pages/LogViewer.js
/**
 * Log Viewer — real-time and historical log viewing for drone operations.
 * Operations mode (default): WARNING+, health bar, live feed.
 * Developer mode: all levels, component tree, search, export.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';
import { useTheme } from '../hooks/useTheme';
import useLogStream from '../hooks/useLogStream';
import { getSessions, getSessionContent } from '../services/logService';
import { MODES, OPS_DEFAULT_LEVEL, DEV_DEFAULT_LEVEL } from '../constants/logConstants';

import LogViewerToolbar from '../components/logs/LogViewerToolbar';
import LogHealthBar from '../components/logs/LogHealthBar';
import LogTable from '../components/logs/LogTable';
import LogSourceTree from '../components/logs/LogSourceTree';
import LogExportDialog from '../components/logs/LogExportDialog';

import '../styles/LogViewer.css';

const LogViewer = () => {
  const { isDark } = useTheme();

  // UI state
  const [mode, setMode] = useState(MODES.OPS);
  const [level, setLevel] = useState(OPS_DEFAULT_LEVEL);
  const [component, setComponent] = useState(null);
  const [paused, setPaused] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showExport, setShowExport] = useState(false);

  // Session state
  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [selectedSession, setSelectedSession] = useState(null);
  const [historicalEntries, setHistoricalEntries] = useState([]);

  // SSE stream (disabled when viewing historical session; paused freezes display but keeps connection)
  const streamEnabled = !selectedSession;
  const { entries: liveEntries, connected, error: streamError, clear } = useLogStream({
    level,
    component,
    enabled: streamEnabled,
    paused,
  });

  // Show SSE errors as toast
  useEffect(() => {
    if (streamError) toast.warning(streamError);
  }, [streamError]);

  // Fetch session list
  const fetchSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const data = await getSessions();
      setSessions(data.sessions || []);
    } catch {
      // Silently fail — not critical
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  useEffect(() => { fetchSessions(); }, [fetchSessions]);

  // Load historical session content
  useEffect(() => {
    if (!selectedSession) {
      setHistoricalEntries([]);
      return;
    }
    let mounted = true;
    const loadSession = async () => {
      try {
        // Fetch all lines — DataGrid handles client-side pagination via pageSizeOptions
        const data = await getSessionContent(selectedSession, {
          level,
          component,
        });
        // Add stable _id for DataGrid row keys
        const lines = (data.lines || []).map((line, idx) => ({ ...line, _id: `hist_${idx}` }));
        if (mounted) setHistoricalEntries(lines);
      } catch (err) {
        if (mounted) toast.error(`Failed to load session: ${err.message}`);
      }
    };
    loadSession();
    return () => { mounted = false; };
  }, [selectedSession, level, component]);

  // Mode change: switch level defaults
  const handleModeChange = useCallback((newMode) => {
    setMode(newMode);
    if (newMode === MODES.OPS) {
      setLevel(OPS_DEFAULT_LEVEL);
      setSearchQuery('');
      setComponent(null);
    } else {
      setLevel(DEV_DEFAULT_LEVEL);
    }
  }, []);

  // Displayed entries: live or historical
  const displayedEntries = selectedSession ? historicalEntries : liveEntries;

  return (
    <div className={`log-viewer-page ${isDark ? 'dark' : 'light'}`}>
      <LogViewerToolbar
        mode={mode}
        onModeChange={handleModeChange}
        level={level}
        onLevelChange={setLevel}
        paused={paused}
        onTogglePause={() => setPaused(p => !p)}
        connected={connected}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        sessions={sessions}
        selectedSession={selectedSession}
        onSessionSelect={(sid) => { setSelectedSession(sid); setPaused(false); }}
        sessionsLoading={sessionsLoading}
        onExportOpen={() => { fetchSessions(); setShowExport(true); }}
        onClear={clear}
      />

      <LogHealthBar entries={displayedEntries} />

      <div style={{ display: 'flex', flex: 1, gap: 'var(--spacing-sm)', overflow: 'hidden' }}>
        {/* Source tree — Developer mode only */}
        {mode === MODES.DEV && (
          <div style={{ width: 200, flexShrink: 0 }}>
            <LogSourceTree
              selectedComponent={component}
              onSelect={setComponent}
            />
          </div>
        )}

        <LogTable
          entries={displayedEntries}
          autoScroll={!selectedSession}
          searchQuery={searchQuery}
        />
      </div>

      {showExport && (
        <LogExportDialog
          sessions={sessions}
          onClose={() => setShowExport(false)}
        />
      )}
    </div>
  );
};

export default LogViewer;

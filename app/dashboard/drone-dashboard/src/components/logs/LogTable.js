// src/components/logs/LogTable.js
import React, { useState, useEffect, useMemo } from 'react';
import { DataGrid, useGridApiRef } from '@mui/x-data-grid';
import { FaBug, FaInfoCircle, FaExclamationTriangle, FaTimesCircle, FaSkull } from 'react-icons/fa';
import { useTheme } from '../../hooks/useTheme';
import LogRowDetail from './LogRowDetail';

const LEVEL_ICONS = {
  DEBUG: FaBug,
  INFO: FaInfoCircle,
  WARNING: FaExclamationTriangle,
  ERROR: FaTimesCircle,
  CRITICAL: FaSkull,
};

/** Format ISO timestamp to HH:MM:SS.mmm */
const formatTs = (ts) => {
  if (!ts) return '--:--:--';
  try {
    const d = new Date(ts);
    return d.toISOString().slice(11, 23);
  } catch {
    return ts.slice(11, 23) || ts;
  }
};

const columns = [
  {
    field: 'ts',
    headerName: 'Time',
    width: 100,
    renderCell: (params) => (
      <span className="log-ts-cell">{formatTs(params.value)}</span>
    ),
  },
  {
    field: 'level',
    headerName: 'Level',
    width: 90,
    renderCell: (params) => {
      const Icon = LEVEL_ICONS[params.value] || FaInfoCircle;
      return (
        <span className={`log-level-cell level-${params.value || 'INFO'}`}>
          <Icon size={10} />
          {params.value || 'INFO'}
        </span>
      );
    },
  },
  {
    field: 'component',
    headerName: 'Component',
    width: 130,
    renderCell: (params) => (
      <span className="log-component-cell" title={params.value}>{params.value || '-'}</span>
    ),
  },
  {
    field: 'drone_id',
    headerName: 'Drone',
    width: 70,
    renderCell: (params) => (
      <span className="log-drone-cell">{params.value != null ? `#${params.value}` : '-'}</span>
    ),
  },
  {
    field: 'msg',
    headerName: 'Message',
    flex: 1,
    minWidth: 200,
  },
];

const LogTable = ({ entries, autoScroll = true, searchQuery = '' }) => {
  const { isDark } = useTheme();
  const [selectedRow, setSelectedRow] = useState(null);
  const gridRef = useGridApiRef();

  // Entries already have stable _id from useLogStream; use it as row id
  const filtered = useMemo(() => {
    if (!searchQuery) return entries;
    const q = searchQuery.toLowerCase();
    return entries.filter(e => {
      const extraText = e.extra ? JSON.stringify(e.extra) : '';
      const text = [
        e.msg || '',
        e.component || '',
        e.level || '',
        e.source || '',
        e.drone_id != null ? `drone ${e.drone_id}` : '',
        extraText,
      ].join(' ').toLowerCase();
      return text.includes(q);
    });
  }, [entries, searchQuery]);

  // Auto-scroll to latest entry
  useEffect(() => {
    if (autoScroll && filtered.length > 0 && gridRef.current) {
      try {
        gridRef.current.scrollToIndexes({ rowIndex: filtered.length - 1 });
      } catch {
        // Graceful fallback
      }
    }
  }, [filtered.length, autoScroll, gridRef]);

  const getRowClassName = (params) => {
    return `level-${params.row.level || 'INFO'}`;
  };

  const getRowId = (row) => row._id;

  const selectedEntry = selectedRow != null ? filtered.find(e => e._id === selectedRow) : null;

  return (
    <div className="log-table-container">
      <DataGrid
        apiRef={gridRef}
        rows={filtered}
        columns={columns}
        getRowId={getRowId}
        density="compact"
        rowHeight={28}
        columnHeaderHeight={36}
        disableColumnMenu
        disableRowSelectionOnClick
        getRowClassName={getRowClassName}
        onRowClick={(params) => setSelectedRow(
          selectedRow === params.row._id ? null : params.row._id
        )}
        hideFooter={filtered.length <= 100}
        pageSizeOptions={[100, 500, 1000]}
        initialState={{
          pagination: { paginationModel: { pageSize: 100 } },
        }}
        sx={{
          border: 'none',
          '& .MuiDataGrid-cell': {
            color: isDark ? '#ffffff' : '#1a1d21',
          },
          '& .MuiDataGrid-columnHeader': {
            color: isDark ? '#a2a5b9' : '#4a5568',
          },
          '& .MuiDataGrid-footerContainer': {
            color: isDark ? '#a2a5b9' : '#4a5568',
          },
          '& .MuiDataGrid-virtualScroller': {
            backgroundColor: 'transparent',
          },
        }}
        localeText={{
          noRowsLabel: searchQuery ? 'No log entries matching search' : 'No log entries',
        }}
      />
      {selectedEntry && <LogRowDetail entry={selectedEntry} />}
    </div>
  );
};

export default LogTable;

import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import Papa from 'papaparse';
import {
  FaCloudUploadAlt,
  FaDownload,
  FaExclamationTriangle,
  FaLayerGroup,
  FaProjectDiagram,
  FaSave,
  FaSearch,
  FaSyncAlt,
  FaUndo,
  FaUpload,
} from 'react-icons/fa';
import { toast } from 'react-toastify';
import DroneCard from '../components/DroneCard';
import DroneGraph from '../components/DroneGraph';
import SwarmPlots from '../components/SwarmPlots';
import '../styles/SwarmDesign.css';
import { getBackendURL } from '../utilities/utilities';
import {
  buildSwarmViewModel,
  buildWorkingSwarmAssignments,
  getDirtyAssignmentIds,
  normalizeConfigDrone,
  normalizeSwarmAssignment,
  toSwarmApiPayload,
} from '../utilities/swarmDesignUtils';

const CSV_HEADERS = ['hw_id', 'follow', 'offset_x', 'offset_y', 'offset_z', 'frame'];

function hasIncompleteNumericValue(value) {
  if (typeof value !== 'string') {
    return false;
  }

  return ['', '-', '.', '-.'].includes(value.trim());
}

function getSelectedSearchFields(drone) {
  return [
    drone.hw_id,
    drone.pos_id,
    drone.roleLabel,
    drone.ip,
    drone.follow,
    drone.title,
    drone.subtitle,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
}

function SwarmDesign() {
  const backendURL = getBackendURL();
  const cardRefs = useRef({});

  const [configData, setConfigData] = useState([]);
  const [serverSwarmData, setServerSwarmData] = useState([]);
  const [baselineAssignments, setBaselineAssignments] = useState([]);
  const [workingAssignments, setWorkingAssignments] = useState([]);
  const [selectedDroneId, setSelectedDroneId] = useState(null);
  const [expandedDroneId, setExpandedDroneId] = useState(null);
  const [pendingCardFocusId, setPendingCardFocusId] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [saving, setSaving] = useState(false);

  const viewModel = buildSwarmViewModel(workingAssignments, configData);
  const dirtyIds = getDirtyAssignmentIds(workingAssignments, baselineAssignments);
  const dirtyIdSet = new Set(dirtyIds);
  const syncChanges = buildWorkingSwarmAssignments(configData, serverSwarmData).syncChanges;
  const selectedDrone = selectedDroneId ? viewModel.dronesById[selectedDroneId] : null;
  const selectedClusterId = selectedDrone?.clusterRootId
    || viewModel.clusters.find((cluster) => cluster.type === 'cluster')?.id
    || null;

  const hasBlockingIssues = viewModel.summary.blockingIssueCount > 0;
  const hasPendingSync = syncChanges.addedIds.length > 0 || syncChanges.removedIds.length > 0;
  const hasStagedChanges = dirtyIds.length > 0;
  const hasIncompleteInputs = workingAssignments.some((assignment) =>
    ['offset_x', 'offset_y', 'offset_z'].some((field) => hasIncompleteNumericValue(assignment[field]))
  );

  const searchValue = searchTerm.trim().toLowerCase();
  const filteredClusters = viewModel.clusters
    .map((cluster) => ({
      ...cluster,
      drones: cluster.drones.filter((drone) => (
        searchValue.length === 0 || getSelectedSearchFields(drone).includes(searchValue)
      )),
    }))
    .filter((cluster) => cluster.drones.length > 0);

  const filteredDroneIds = new Set(
    filteredClusters.flatMap((cluster) => cluster.drones.map((drone) => drone.hw_id))
  );
  const visibleDroneCount = filteredClusters.reduce((count, cluster) => count + cluster.drones.length, 0);
  const droneRosterKey = viewModel.drones.map((drone) => drone.hw_id).join('|');

  useEffect(() => {
    let isActive = true;

    async function loadSwarmDesignData() {
      try {
        const [swarmResponse, configResponse] = await Promise.all([
          axios.get(`${backendURL}/get-swarm-data`),
          axios.get(`${backendURL}/get-config-data`),
        ]);

        if (!isActive) {
          return;
        }

        const normalizedConfig = configResponse.data
          .map((entry) => normalizeConfigDrone(entry))
          .filter(Boolean);
        const normalizedSwarm = swarmResponse.data
          .map((entry) => normalizeSwarmAssignment(entry))
          .filter(Boolean);
        const { assignments } = buildWorkingSwarmAssignments(normalizedConfig, normalizedSwarm);
        const firstDroneId = assignments[0]?.hw_id || null;

        setConfigData(normalizedConfig);
        setServerSwarmData(normalizedSwarm);
        setBaselineAssignments(assignments);
        setWorkingAssignments(assignments);
        setSelectedDroneId((currentId) => assignments.some((assignment) => assignment.hw_id === currentId) ? currentId : firstDroneId);
        setExpandedDroneId((currentId) => assignments.some((assignment) => assignment.hw_id === currentId) ? currentId : firstDroneId);
      } catch (error) {
        console.error('Error fetching Smart Swarm data:', error);
        toast.error('Failed to load Smart Swarm configuration.');
      }
    }

    loadSwarmDesignData();

    return () => {
      isActive = false;
    };
  }, [backendURL]);

  useEffect(() => {
    if (viewModel.drones.length === 0) {
      if (selectedDroneId !== null) {
        setSelectedDroneId(null);
      }
      if (expandedDroneId !== null) {
        setExpandedDroneId(null);
      }
      return;
    }

    if (!selectedDroneId || !viewModel.dronesById[selectedDroneId]) {
      const nextDroneId = viewModel.drones[0].hw_id;
      setSelectedDroneId(nextDroneId);
      setExpandedDroneId(nextDroneId);
    }
    if (expandedDroneId && !viewModel.dronesById[expandedDroneId]) {
      setExpandedDroneId(selectedDroneId || viewModel.drones[0].hw_id);
    }
  }, [droneRosterKey, expandedDroneId, selectedDroneId]);

  useEffect(() => {
    if (!pendingCardFocusId) {
      return;
    }

    const targetNode = cardRefs.current[pendingCardFocusId];
    if (!targetNode) {
      return;
    }

    targetNode.scrollIntoView({
      behavior: 'smooth',
      block: 'center',
    });
    targetNode.focus({ preventScroll: true });
    setPendingCardFocusId(null);
  }, [filteredClusters, pendingCardFocusId]);

  const refreshFromServer = async () => {
    const [swarmResponse, configResponse] = await Promise.all([
      axios.get(`${backendURL}/get-swarm-data`),
      axios.get(`${backendURL}/get-config-data`),
    ]);

    const normalizedConfig = configResponse.data
      .map((entry) => normalizeConfigDrone(entry))
      .filter(Boolean);
    const normalizedSwarm = swarmResponse.data
      .map((entry) => normalizeSwarmAssignment(entry))
      .filter(Boolean);
    const { assignments } = buildWorkingSwarmAssignments(normalizedConfig, normalizedSwarm);

    setConfigData(normalizedConfig);
    setServerSwarmData(normalizedSwarm);
    setBaselineAssignments(assignments);
    setWorkingAssignments(assignments);
  };

  const handleAssignmentChange = (hwId, patch) => {
    setWorkingAssignments((currentAssignments) => (
      currentAssignments.map((assignment) => (
        assignment.hw_id === hwId
          ? {
              ...assignment,
              ...patch,
            }
          : assignment
      ))
    ));
  };

  const handleSelectDrone = (droneId, { fromGraph = false } = {}) => {
    if (fromGraph && searchValue && !filteredDroneIds.has(droneId)) {
      setSearchTerm('');
    }

    setSelectedDroneId(droneId);
    setExpandedDroneId(droneId);
    setPendingCardFocusId(droneId);
  };

  const handleToggleExpand = (droneId) => {
    setExpandedDroneId((currentId) => currentId === droneId ? null : droneId);
  };

  const handleImport = (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';

    if (!file) {
      return;
    }

    const reader = new FileReader();
    reader.onload = (loadEvent) => {
      const fileText = loadEvent.target?.result;
      if (typeof fileText !== 'string') {
        toast.error('Unable to read the selected file.');
        return;
      }

      const applyImportedAssignments = (rawAssignments) => {
        const importedAssignments = rawAssignments
          .map((assignment) => normalizeSwarmAssignment(assignment))
          .filter(Boolean);
        const importedResult = buildWorkingSwarmAssignments(configData, importedAssignments);

        setWorkingAssignments(importedResult.assignments);

        const importedCount = importedAssignments.length;
        const defaultedCount = importedResult.syncChanges.addedIds.length;
        const ignoredCount = importedResult.syncChanges.removedIds.length;

        toast.success(
          `Imported ${importedCount} assignment${importedCount === 1 ? '' : 's'}`
          + `${defaultedCount > 0 ? `, added ${defaultedCount} default fleet entr${defaultedCount === 1 ? 'y' : 'ies'}` : ''}`
          + `${ignoredCount > 0 ? `, ignored ${ignoredCount} non-fleet entr${ignoredCount === 1 ? 'y' : 'ies'}` : ''}.`
        );
      };

      try {
        const parsedJson = JSON.parse(fileText);
        const rawAssignments = Array.isArray(parsedJson)
          ? parsedJson
          : parsedJson.assignments || [];

        if (rawAssignments.length === 0) {
          toast.error('No swarm assignments found in the JSON file.');
          return;
        }

        applyImportedAssignments(rawAssignments);
        return;
      } catch {
        Papa.parse(fileText, {
          header: false,
          skipEmptyLines: true,
          complete: ({ data }) => {
            if (!Array.isArray(data) || data.length < 2) {
              toast.error('The CSV file is empty or incomplete.');
              return;
            }

            const header = data[0].map((cell) => String(cell).trim());
            if (header.join(',') !== CSV_HEADERS.join(',')) {
              toast.error(`CSV header mismatch. Expected: ${CSV_HEADERS.join(', ')}`);
              return;
            }

            const rows = data.slice(1).map((row) => ({
              hw_id: row[0],
              follow: row[1],
              offset_x: row[2],
              offset_y: row[3],
              offset_z: row[4],
              frame: row[5],
            }));

            applyImportedAssignments(rows);
          },
          error: () => {
            toast.error('Failed to parse the imported CSV file.');
          },
        });
      }
    };

    reader.readAsText(file);
  };

  const handleJsonExport = () => {
    const payload = {
      version: 1,
      assignments: toSwarmApiPayload(workingAssignments),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'swarm.json';
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleCsvExport = () => {
    const payload = toSwarmApiPayload(workingAssignments);
    const csv = Papa.unparse(payload, { columns: CSV_HEADERS });
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'swarm_assignments.csv';
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleRevert = () => {
    if (!hasStagedChanges) {
      return;
    }

    if (!window.confirm('Revert all staged Smart Swarm changes back to the last loaded configuration?')) {
      return;
    }

    setWorkingAssignments(baselineAssignments);
    toast.info('Reverted local Smart Swarm changes.');
  };

  const saveSwarmData = async (withCommit) => {
    setSaving(true);

    try {
      const response = await axios.post(
        `${backendURL}/save-swarm-data?commit=${withCommit ? 'true' : 'false'}`,
        toSwarmApiPayload(workingAssignments)
      );

      toast.success(response.data.message || 'Smart Swarm configuration saved successfully.');
      await refreshFromServer();
    } catch (error) {
      console.error('Failed to save Smart Swarm configuration:', error);
      toast.error('Failed to save Smart Swarm configuration.');
    } finally {
      setSaving(false);
    }
  };

  const confirmAndSave = (withCommit) => {
    if (hasBlockingIssues) {
      toast.error('Resolve blocking follow-chain issues before saving Smart Swarm assignments.');
      return;
    }

    if (hasIncompleteInputs) {
      toast.error('Complete or clear all offset fields before saving.');
      return;
    }

    if (!hasStagedChanges && !hasPendingSync) {
      toast.info('No Smart Swarm changes are staged for update.');
      return;
    }

    const summaryLines = [
      `${viewModel.summary.totalDrones} airframes across ${viewModel.summary.clusterCount} cluster${viewModel.summary.clusterCount === 1 ? '' : 's'}`,
      `${viewModel.summary.topLeaderCount} top leaders, ${viewModel.summary.relayLeaderCount} relay leaders, ${viewModel.summary.followerCount} followers`,
      `${dirtyIds.length} staged assignment change${dirtyIds.length === 1 ? '' : 's'}`,
      `${syncChanges.addedIds.length + syncChanges.removedIds.length} fleet sync update${syncChanges.addedIds.length + syncChanges.removedIds.length === 1 ? '' : 's'}`,
      `${viewModel.summary.attentionCount} airframe${viewModel.summary.attentionCount === 1 ? '' : 's'} flagged for operator attention`,
    ];

    if (!window.confirm(
      `${withCommit ? 'Commit' : 'Update'} Smart Swarm assignments?\n\n${summaryLines.map((line) => `- ${line}`).join('\n')}`
    )) {
      return;
    }

    saveSwarmData(withCommit);
  };

  const summaryCards = [
    {
      icon: <FaLayerGroup />,
      label: 'Airframes',
      value: viewModel.summary.totalDrones,
      tone: 'neutral',
    },
    {
      icon: <FaProjectDiagram />,
      label: 'Clusters',
      value: viewModel.summary.clusterCount,
      tone: 'neutral',
    },
    {
      icon: <FaSyncAlt />,
      label: 'Relay Leaders',
      value: viewModel.summary.relayLeaderCount,
      tone: 'warning',
    },
    {
      icon: <FaSave />,
      label: 'Staged Changes',
      value: dirtyIds.length,
      tone: dirtyIds.length > 0 ? 'info' : 'neutral',
    },
    {
      icon: <FaExclamationTriangle />,
      label: 'Attention',
      value: viewModel.summary.attentionCount,
      tone: viewModel.summary.attentionCount > 0 ? 'danger' : 'success',
    },
  ];

  return (
    <div className="swarm-design-page">
      <header className="swarm-design-hero">
        <div className="swarm-design-hero__copy">
          <span className="swarm-design-hero__eyebrow">Smart Swarm Control Surface</span>
          <h1>Operational Swarm Design</h1>
          <p>
            Airframe IDs represent physical aircraft. Position IDs represent show slots.
            Follow chains always target airframe IDs, while position IDs stay mapped to trajectory roles.
          </p>
        </div>

        <div className="swarm-design-hero__actions">
          <button
            type="button"
            className="swarm-action-button update"
            onClick={() => confirmAndSave(false)}
            disabled={saving || hasBlockingIssues || hasIncompleteInputs || (!hasStagedChanges && !hasPendingSync)}
          >
            <FaSyncAlt />
            Update Swarm
          </button>
          <button
            type="button"
            className="swarm-action-button commit"
            onClick={() => confirmAndSave(true)}
            disabled={saving || hasBlockingIssues || hasIncompleteInputs || (!hasStagedChanges && !hasPendingSync)}
          >
            <FaCloudUploadAlt />
            Commit Changes
          </button>
          <label className="swarm-action-button import">
            <FaUpload />
            Import JSON / CSV
            <input type="file" accept=".json,.csv" onChange={handleImport} />
          </label>
          <button type="button" className="swarm-action-button secondary" onClick={handleJsonExport} disabled={workingAssignments.length === 0}>
            <FaDownload />
            Export JSON
          </button>
          <button type="button" className="swarm-action-button secondary" onClick={handleCsvExport} disabled={workingAssignments.length === 0}>
            <FaDownload />
            Export CSV
          </button>
          <button type="button" className="swarm-action-button ghost" onClick={handleRevert} disabled={!hasStagedChanges}>
            <FaUndo />
            Revert Local
          </button>
        </div>
      </header>

      <section className="swarm-summary-grid">
        {summaryCards.map((card) => (
          <div key={card.label} className={`swarm-summary-card ${card.tone}`}>
            <span className="swarm-summary-card__icon">{card.icon}</span>
            <span className="swarm-summary-card__value">{card.value}</span>
            <span className="swarm-summary-card__label">{card.label}</span>
          </div>
        ))}
      </section>

      <section className="swarm-status-strip">
        <div className="swarm-status-card identity">
          <strong>Identity model</strong>
          <span>Hot-swaps change position slots, not follow-chain targeting. Validate role swaps before flight.</span>
        </div>

        {hasPendingSync && (
          <div className="swarm-status-card sync">
            <strong>Fleet sync pending</strong>
            <span>
              {syncChanges.addedIds.length > 0 && `Add default assignments for airframes ${syncChanges.addedIds.join(', ')}. `}
              {syncChanges.removedIds.length > 0 && `Prune legacy assignments for airframes ${syncChanges.removedIds.join(', ')}.`}
            </span>
          </div>
        )}

        {viewModel.summary.roleSwapCount > 0 && (
          <div className="swarm-status-card note">
            <strong>Role swaps active</strong>
            <span>{viewModel.summary.roleSwapCount} airframe{viewModel.summary.roleSwapCount === 1 ? '' : 's'} are flying a different position slot than their hardware ID.</span>
          </div>
        )}

        {(hasBlockingIssues || hasIncompleteInputs) && (
          <div className="swarm-status-card attention">
            <strong>Save blocked</strong>
            <span>
              {hasBlockingIssues ? 'Resolve self-follow, missing leader, or cycle issues.' : ''}
              {hasBlockingIssues && hasIncompleteInputs ? ' ' : ''}
              {hasIncompleteInputs ? 'Complete partial offset values before update or commit.' : ''}
            </span>
          </div>
        )}
      </section>

      <div className="swarm-operations-layout">
        <section className="swarm-panel swarm-panel--assignments">
          <div className="swarm-panel__header">
            <div>
              <h2>Assignment Cards</h2>
              <p>Grouped by top leader so operators can audit follow chains cluster by cluster.</p>
            </div>

            <label className="swarm-search-field">
              <FaSearch />
              <input
                type="search"
                placeholder="Search airframe, position, leader, or IP"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
              />
            </label>
          </div>

          <div className="swarm-panel__subheader">
            <span>{visibleDroneCount} of {viewModel.summary.totalDrones} airframes visible</span>
            <span>{dirtyIds.length} staged</span>
          </div>

          <div className="swarm-cluster-stack">
            {filteredClusters.length === 0 && (
              <div className="swarm-empty-state">
                <strong>No matching airframes</strong>
                <span>Try a different search term or clear the filter.</span>
              </div>
            )}

            {filteredClusters.map((cluster) => (
              <section
                key={cluster.id}
                className={`swarm-cluster-section ${cluster.type === 'attention' ? 'attention' : ''}`}
              >
                <header className="swarm-cluster-section__header">
                  <div>
                    <h3>{cluster.title}</h3>
                    <p>{cluster.subtitle}</p>
                  </div>

                  <div className="swarm-cluster-section__stats">
                    <span>{cluster.counts.total} airframes</span>
                    <span>{cluster.counts.relayLeaders} relay</span>
                    <span>{cluster.counts.followers} followers</span>
                    {cluster.warningCount > 0 && <span>{cluster.warningCount} attention</span>}
                  </div>
                </header>

                <div className="swarm-card-list">
                  {cluster.drones.map((drone) => {
                    const rawAssignment = workingAssignments.find((assignment) => String(assignment.hw_id) === drone.hw_id) || drone;

                    return (
                      <DroneCard
                        key={drone.hw_id}
                        ref={(node) => {
                          if (node) {
                            cardRefs.current[drone.hw_id] = node;
                          } else {
                            delete cardRefs.current[drone.hw_id];
                          }
                        }}
                        drone={drone}
                        draftAssignment={rawAssignment}
                        followOptions={viewModel.followOptions}
                        onSelect={(droneId) => handleSelectDrone(droneId)}
                        onToggleExpand={handleToggleExpand}
                        onAssignmentChange={handleAssignmentChange}
                        isSelected={selectedDroneId === drone.hw_id}
                        isExpanded={expandedDroneId === drone.hw_id}
                        isDirty={dirtyIdSet.has(drone.hw_id)}
                      />
                    );
                  })}
                </div>
              </section>
            ))}
          </div>
        </section>

        <section className="swarm-panel swarm-panel--graph">
          <div className="swarm-panel__header">
            <div>
              <h2>Follow Chain Graph</h2>
              <p>Click any node to select the matching assignment card and inspect its upstream and downstream chain.</p>
            </div>
          </div>

          <div className="swarm-graph-panel">
            <div className="swarm-graph-stage">
              <DroneGraph
                swarmData={viewModel.drones}
                selectedDroneId={selectedDroneId}
                onSelectDrone={(droneId) => handleSelectDrone(droneId, { fromGraph: true })}
              />
            </div>

            <div className="swarm-graph-legend">
              <span className="legend-item leader">Top leader</span>
              <span className="legend-item relay">Relay leader</span>
              <span className="legend-item follower">Follower</span>
              <span className="legend-item line-solid">Geographic offset</span>
              <span className="legend-item line-dashed">Body-relative offset</span>
            </div>

            <div className="swarm-selection-panel">
              {selectedDrone ? (
                <>
                  <div className="swarm-selection-panel__header">
                    <div>
                      <span className="swarm-selection-panel__eyebrow">Selected Airframe</span>
                      <h3>{selectedDrone.title}</h3>
                    </div>
                    <span className={`swarm-role-badge ${selectedDrone.role}`}>{selectedDrone.roleLabel}</span>
                  </div>

                  <dl className="swarm-selection-panel__details">
                    <div>
                      <dt>Position Slot</dt>
                      <dd>{selectedDrone.pos_id}</dd>
                    </div>
                    <div>
                      <dt>Follow Target</dt>
                      <dd>{selectedDrone.follow === '0' ? 'Independent leader' : `Airframe ${selectedDrone.follow}`}</dd>
                    </div>
                    <div>
                      <dt>Offset Frame</dt>
                      <dd>{selectedDrone.frameLabel}</dd>
                    </div>
                    <div>
                      <dt>Relative Offset</dt>
                      <dd>{selectedDrone.offsetSummary}</dd>
                    </div>
                    <div>
                      <dt>Direct Followers</dt>
                      <dd>{selectedDrone.directFollowerCount}</dd>
                    </div>
                    <div>
                      <dt>Network Path</dt>
                      <dd>{selectedDrone.ip || 'Not assigned'}</dd>
                    </div>
                  </dl>

                  {selectedDrone.warnings.length > 0 && (
                    <div className="swarm-selection-panel__warnings">
                      {selectedDrone.warnings.map((warning) => (
                        <div key={`${selectedDrone.hw_id}-${warning.code}`} className={`selection-warning ${warning.severity}`}>
                          <FaExclamationTriangle />
                          <span>{warning.message}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <div className="swarm-empty-state compact">
                  <strong>No airframe selected</strong>
                  <span>Select a graph node or assignment card to inspect its details.</span>
                </div>
              )}
            </div>
          </div>
        </section>
      </div>

      <section className="swarm-panel swarm-panel--plots">
        <div className="swarm-panel__header">
          <div>
            <h2>Formation Analysis</h2>
            <p>Cluster plots are relative previews for design review. They are not live telemetry views.</p>
          </div>
        </div>

        <SwarmPlots
          swarmData={workingAssignments}
          configData={configData}
          selectedClusterId={selectedClusterId}
        />
      </section>
    </div>
  );
}

export default SwarmDesign;

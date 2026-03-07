import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Papa from 'papaparse';
import '../styles/SwarmDesign.css';
import DroneGraph from '../components/DroneGraph';
import SwarmPlots from '../components/SwarmPlots';
import DroneCard from '../components/DroneCard';
import { getBackendURL } from '../utilities/utilities';
import { FaSyncAlt, FaCloudUploadAlt } from 'react-icons/fa';  // For icons
import { toast } from 'react-toastify';  // For toast notifications

// Handle both string and number comparisons for follow field (JSON gives numbers, CSV gives strings)
const isLeader = (drone) => drone.follow === 0 || drone.follow === '0';

const categorizeDrones = (swarmData) => {
    const topLeaders = swarmData.filter(drone => isLeader(drone));
    const topLeaderIdsSet = new Set(topLeaders.map(leader => leader.hw_id));

    const followerCounts = {};
    swarmData.forEach(drone => {
        const followKey = String(drone.follow);
        if (!followerCounts[followKey]) {
            followerCounts[followKey] = 0;
        }
        followerCounts[followKey]++;
    });

    const intermediateLeaders = swarmData.filter(drone =>
        !topLeaderIdsSet.has(drone.hw_id) && followerCounts[String(drone.hw_id)]
    );

    return {
        topLeaders,
        intermediateLeaders
    };
};

const isEqual = (arr1, arr2) => JSON.stringify(arr1) === JSON.stringify(arr2);

const SwarmDesign = () => {
    const [swarmData, setSwarmData] = useState([]);
    const [configData, setConfigData] = useState([]);
    const [selectedDroneId, setSelectedDroneId] = useState(null);
    const [changes, setChanges] = useState({ added: [], removed: [] });
    const [saving, setSaving] = useState(false);

    const backendURL = getBackendURL(); // Uses REACT_APP_GCS_PORT

    // Initial fetch of both datasets
    useEffect(() => {
        const fetchSwarmData = axios.get(`${backendURL}/get-swarm-data`);
        const fetchConfigData = axios.get(`${backendURL}/get-config-data`);
        Promise.all([fetchSwarmData, fetchConfigData])
            .then(([swarmRes, configRes]) => {
                setSwarmData(swarmRes.data);
                setConfigData(configRes.data);
            })
            .catch(err => {
                console.error('Error fetching data:', err);
                toast.error('Failed to fetch swarm or config data.');
            });
    }, []);

    // Merge config + swarm, detect adds/removes
    useEffect(() => {
        if (swarmData.length === 0 || configData.length === 0) return;

        let merged = [...swarmData];

        const added = configData
            .filter(c => !swarmData.some(s => s.hw_id === c.hw_id))
            .map(c => c.hw_id);
        const removed = swarmData
            .filter(s => !configData.some(c => c.hw_id === s.hw_id))
            .map(s => s.hw_id);
        setChanges({ added, removed });

        configData.forEach(c => {
            if (!swarmData.some(s => s.hw_id === c.hw_id)) {
                merged.push({
                    hw_id: c.hw_id,
                    follow: 0,
                    offset_x: 0.0,
                    offset_y: 0.0,
                    offset_z: 0.0,
                    frame: "ned"
                });
            }
        });

        merged = merged.filter(s => configData.some(c => c.hw_id === s.hw_id));

        if (!isEqual(merged, swarmData)) {
            setSwarmData(merged);
        }
    }, [configData, swarmData]);

    const handleSaveChanges = (hw_id, updated) => {
        setSwarmData(prev => prev.map(d => d.hw_id === hw_id ? updated : d));
    };

    const dronesFollowing = leaderId =>
        swarmData.filter(d => String(d.follow) === String(leaderId)).map(d => d.hw_id);

    const confirmAndSave = withCommit => {
        const summary = swarmData.map(d => {
            const role = isLeader(d)
                ? 'Top Leader'
                : dronesFollowing(d.hw_id).length
                ? 'Intermediate Leader'
                : 'Follower';
            return `Drone ${d.hw_id}: ${role}${role !== 'Top Leader' ? ` (→${d.follow})` : ''}`;
        }).join('\n');

        if (window.confirm(`Proceed to ${withCommit ? 'commit' : 'update'} swarm?\n\n${summary}`)) {
            saveSwarmData(withCommit);
        }
    };

    const saveSwarmData = async withCommit => {
        setSaving(true);
        try {
            const url = `${backendURL}/save-swarm-data${withCommit ? '?commit=true' : '?commit=false'}`;
            const res = await axios.post(url, swarmData);
            toast.success(res.data.message || 'Saved successfully.');
            // re-fetch
            const [swRes, cfgRes] = await Promise.all([
                axios.get(`${backendURL}/get-swarm-data`),
                axios.get(`${backendURL}/get-config-data`)
            ]);
            setSwarmData(swRes.data);
            setConfigData(cfgRes.data);
        } catch (err) {
            console.error('Save failed:', err);
            toast.error('Save failed.');
        } finally {
            setSaving(false);
        }
    };

    const handleImport = e => {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = ev => {
            const text = ev.target.result;
            try {
                // Try JSON first
                const data = JSON.parse(text);
                const assignments = data.assignments || (Array.isArray(data) ? data : []);
                if (assignments.length > 0) {
                    setSwarmData(assignments);
                    toast.success(`Imported ${assignments.length} swarm assignments from JSON`);
                } else {
                    toast.error('No assignments found in JSON file');
                }
            } catch {
                // Fall back to CSV (Papa Parse)
                Papa.parse(text, {
                    complete: ({ data }) => {
                        const header = data[0].map(h => h.trim());
                        const expected = ["hw_id", "follow", "offset_x", "offset_y", "offset_z", "frame"];
                        if (header.toString() !== expected.toString()) {
                            return toast.error('CSV header mismatch.');
                        }
                        const parsed = data.slice(1)
                            .map(r => ({
                                hw_id: r[0], follow: r[1],
                                offset_x: r[2], offset_y: r[3],
                                offset_z: r[4], frame: r[5]
                            }))
                            .filter(d => d.hw_id);
                        setSwarmData(parsed);
                        toast.success(`Imported ${parsed.length} swarm assignments from CSV`);
                    },
                    header: false
                });
            }
        };
        reader.readAsText(file);
    };

    const handleJSONExport = () => {
        const data = { version: 1, assignments: swarmData };
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = 'swarm.json';
        link.click();
    };

    const handleCSVExport = () => {
        const csv = Papa.unparse(swarmData);
        const blob = new Blob([csv], { type: 'text/csv' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = 'swarm_export.csv';
        link.click();
    };

    const handleRevert = () => {
        if (window.confirm('Revert all changes?')) {
            window.location.reload();
        }
    };

    return (
        <div className="swarm-design-container">
            {/* Clean Full-Width Button Bar */}
            <div className="top-button-bar">
                <button
                    className="top-btn update"
                    onClick={() => confirmAndSave(false)}
                    disabled={saving}
                >
                    <FaSyncAlt /> Update Swarm
                </button>
                <button
                    className="top-btn commit"
                    onClick={() => confirmAndSave(true)}
                    disabled={saving}
                >
                    <FaCloudUploadAlt /> Commit Changes
                </button>
                <label className="top-btn import">
                    Import
                    <input
                        type="file"
                        accept=".json,.csv"
                        onChange={handleImport}
                    />
                </label>
                <button
                    className="top-btn export"
                    onClick={handleJSONExport}
                    disabled={saving}
                >
                    Export JSON
                </button>
                <button
                    className="top-btn export"
                    onClick={handleCSVExport}
                    disabled={saving}
                >
                    Export CSV
                </button>
                <button
                    className="top-btn revert"
                    onClick={handleRevert}
                    disabled={saving}
                >
                    Revert
                </button>
            </div>

            

            {/* Two-Column Layout */}
            <div className="two-column-layout">
                {/* Left Column: Drone List and Fields */}
                <div className="left-column">
                    <h3>Drone Configuration ({swarmData.length} drones)</h3>
                    <div className="drone-list">
                        {swarmData.length ? swarmData.map(drone => (
                            <DroneCard
                                key={drone.hw_id}
                                drone={drone}
                                allDrones={swarmData}
                                onSaveChanges={handleSaveChanges}
                                isSelected={selectedDroneId === drone.hw_id}
                            />
                        )) : (
                            <div className="empty-state">
                                <p>No data available for swarm configuration.</p>
                            </div>
                        )}
                    </div>
                </div>

                {/* Right Column: Graph View */}
                <div className="right-column">
                    <h3>Formation Preview</h3>
                    <div className="graph-view">
                        <DroneGraph
                            swarmData={swarmData}
                            onSelectDrone={setSelectedDroneId}
                        />
                    </div>
                </div>
            </div>

            {/* Separate Bottom Section: Clustered Plots */}
            <div className="plots-section">
                <h3>Formation Analysis & Plots</h3>
                <SwarmPlots swarmData={swarmData} />
            </div>
            {(changes.added.length || changes.removed.length) && (
                <div className="notification-container">
                    {changes.added.length > 0 && <span>Added: {changes.added.join(', ')}</span>}
                    {changes.removed.length > 0 && <span>Removed: {changes.removed.join(', ')}</span>}
                </div>
            )}
        </div>
    );
};

export default SwarmDesign;

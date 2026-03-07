// DroneCard.js

import React, { useState, useEffect } from 'react';
import '../styles/DroneCard.css';

const categorizeDroneRole = (drone, followerCounts, topLeaderIdsSet) => {
    if (String(drone.follow) === '0') return 'Top Leader';
    if (!topLeaderIdsSet.has(drone.hw_id) && followerCounts[String(drone.hw_id)]) return 'Intermediate Leader';
    return 'Follower';
};

const dronesFollowing = (droneId, allDrones) => {
    return allDrones.filter(d => String(d.follow) === String(droneId)).map(d => d.hw_id);
};

const DroneCard = ({ drone, allDrones, onSaveChanges, isSelected }) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const [selectedFollow, setSelectedFollow] = useState(drone.follow);
    const [offsets, setOffsets] = useState({
        x: drone.offset_x,
        y: drone.offset_y,
        z: drone.offset_z
    });
    const [frame, setFrame] = useState(drone.frame === 'body' ? 'body' : 'ned');

    // Count followers for each drone
    const followerCounts = {};
    allDrones.forEach(d => {
        const followKey = String(d.follow);
        if (!followerCounts[followKey]) {
            followerCounts[followKey] = 0;
        }
        followerCounts[followKey]++;
    });

    const topLeaderIdsSet = new Set(allDrones.filter(d => String(d.follow) === '0').map(leader => leader.hw_id));
    const role = categorizeDroneRole(drone, followerCounts, topLeaderIdsSet);

    useEffect(() => {
        if (String(selectedFollow) === '0') {
            setOffsets({ x: 0, y: 0, z: 0 });
        }
    }, [selectedFollow]);

    // Dynamic labels based on coordinate frame
    const offsetXLabel = frame === 'body' ? 'Offset Forward (m)' : 'Offset North (m)';
    const offsetYLabel = frame === 'body' ? 'Offset Right (m)' : 'Offset East (m)';

    const handleSave = () => {
        onSaveChanges(drone.hw_id, {
            ...drone,
            follow: selectedFollow,
            offset_x: offsets.x,
            offset_y: offsets.y,
            offset_z: offsets.z,
            frame: frame
        });
        setIsExpanded(false);
    };

    const dronesThatFollowThis = dronesFollowing(drone.hw_id, allDrones);

    return (
        <div className={`drone-card ${isExpanded ? 'selected-drone' : ''} ${isSelected ? 'selected' : ''}`}  >
            <h3 onClick={() => setIsExpanded(!isExpanded)}>Drone {drone.hw_id} → Pos {drone.pos_id}</h3>

            <p>
                {role === 'Top Leader' ?
                    <span className="role leader">Top Leader</span> :
                    role === 'Intermediate Leader' ?
                        <span className="role intermediate">Intermediate Leader (Follows Drone {selectedFollow})</span> :
                        <span className="role follower">Follows Drone {selectedFollow}</span>
                }
            </p>

            {dronesThatFollowThis.length > 0 && (
                <p className="followed-by-text">
                    Followed By: {dronesThatFollowThis.join(', ')}
                </p>
            )}

            <p className="collapsible-details">
                Position Offset (m): {offsetXLabel.split(' ')[1]}: {drone.offset_x}, {offsetYLabel.split(' ')[1]}: {drone.offset_y}, Up: {drone.offset_z}
            </p>

            {isExpanded && (
                <div>
                    <div className="form-group">
                        <label>Role: </label>
                        <select value={selectedFollow} onChange={e => setSelectedFollow(e.target.value)}>
                            <option value="0">Top Leader</option>
                            {allDrones.map(d => {
                                if (d.hw_id !== drone.hw_id) {
                                    return <option key={d.hw_id} value={d.hw_id}> Follow Drone {d.hw_id}</option>;
                                } else {
                                    return null;
                                }
                            })}
                        </select>
                    </div>

                    <div className="form-group">
                        <label>{offsetXLabel}: </label>
                        <input
                            type="number"
                            value={offsets.x}
                            onChange={e => setOffsets(prev => ({ ...prev, x: e.target.value }))}
                            disabled={String(selectedFollow) === '0'}
                        />
                    </div>

                    <div className="form-group">
                        <label>{offsetYLabel}: </label>
                        <input
                            type="number"
                            value={offsets.y}
                            onChange={e => setOffsets(prev => ({ ...prev, y: e.target.value }))}
                            disabled={String(selectedFollow) === '0'}
                        />
                    </div>

                    <div className="form-group">
                        <label>Offset Up (m): </label>
                        <input
                            type="number"
                            value={offsets.z}
                            onChange={e => setOffsets(prev => ({ ...prev, z: e.target.value }))}
                            disabled={String(selectedFollow) === '0'}
                        />
                    </div>

                    {/* Coordinate System Selection */}
                    <div className="form-group">
                        <label>Coordinate Type:</label>
                        <select value={frame} onChange={e => setFrame(e.target.value)}>
                            <option value="ned">North-East-Up (NEU)</option>
                            <option value="body">Body (Forward-Right-Up)</option>
                        </select>
                    </div>

                    <button onClick={handleSave}>Save Changes</button>
                </div>
            )}
        </div>
    );
};

export default DroneCard;

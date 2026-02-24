// src/pages/QuickScoutPage.js
/**
 * QuickScout SAR - Main page composition.
 * Plan mode: draw polygon, select drones, configure, compute plan, launch.
 * Monitor mode: watch mission progress, manage POIs, control drones.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import { toast } from 'react-toastify';
import { getTelemetryURL } from '../utilities/utilities';
import * as sarApi from '../services/sarApiService';

// SAR components
import PlanMonitorToggle from '../components/sar/PlanMonitorToggle';
import MissionStatsBar from '../components/sar/MissionStatsBar';
import MissionPlanSidebar from '../components/sar/MissionPlanSidebar';
import MissionMonitorSidebar from '../components/sar/MissionMonitorSidebar';
import MissionActionBar from '../components/sar/MissionActionBar';
import CoveragePreview from '../components/sar/CoveragePreview';
import POIMarkerSystem from '../components/sar/POIMarkerSystem';
import DrawControl, { MapboxSetupInstructions } from '../components/sar/SearchAreaDrawer';

// Styles
import '../styles/QuickScout.css';

// Conditional Mapbox imports
let Map, Marker;
let mapboxAvailable = false;
let mapboxToken = '';

try {
  const rgl = require('react-map-gl');
  Map = rgl.Map || rgl.default;
  Marker = rgl.Marker;
  require('mapbox-gl/dist/mapbox-gl.css');
  mapboxToken = process.env.REACT_APP_MAPBOX_TOKEN || '';
  mapboxAvailable = !!mapboxToken;
} catch (e) {
  console.warn('Mapbox not available:', e.message);
}

const DEFAULT_SURVEY_CONFIG = {
  algorithm: 'boustrophedon',
  sweep_width_m: 30,
  overlap_percent: 10,
  cruise_altitude_msl: 50,
  survey_altitude_agl: 40,
  cruise_speed_ms: 10,
  survey_speed_ms: 5,
  use_terrain_following: true,
  camera_interval_s: 2,
};

const QuickScoutPage = () => {
  // Mode
  const [mode, setMode] = useState('plan');

  // Plan state
  const [searchArea, setSearchArea] = useState([]);
  const [searchAreaSqM, setSearchAreaSqM] = useState(0);
  const [surveyConfig, setSurveyConfig] = useState(DEFAULT_SURVEY_CONFIG);
  const [selectedDrones, setSelectedDrones] = useState([]);
  const [coveragePlan, setCoveragePlan] = useState(null);
  const [computing, setComputing] = useState(false);
  const [launching, setLaunching] = useState(false);

  // Monitor state
  const [missionId, setMissionId] = useState(null);
  const [missionStatus, setMissionStatus] = useState(null);
  const [pois, setPois] = useState([]);
  const [addingPOI, setAddingPOI] = useState(false);

  // Telemetry
  const [drones, setDrones] = useState([]);

  // Map
  const [viewport, setViewport] = useState({
    longitude: 0, latitude: 0, zoom: 3,
  });
  const poiClickRef = useRef(null);

  // Telemetry polling
  useEffect(() => {
    const fetchTelemetry = async () => {
      try {
        const response = await axios.get(getTelemetryURL());
        const dronesArray = Object.keys(response.data).map((hw_ID) => ({
          hw_ID, ...response.data[hw_ID],
        }));
        setDrones(dronesArray);
      } catch (e) {
        // Silent failure
      }
    };
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 2000);
    return () => clearInterval(interval);
  }, []);

  // Mission status polling (monitor mode)
  useEffect(() => {
    if (mode !== 'monitor' || !missionId) return;

    const pollStatus = async () => {
      try {
        const status = await sarApi.getMissionStatus(missionId);
        setMissionStatus(status);

        const poisData = await sarApi.getPOIs(missionId);
        setPois(poisData);
      } catch (e) {
        // Mission may not exist yet
      }
    };
    pollStatus();
    const interval = setInterval(pollStatus, 2000);
    return () => clearInterval(interval);
  }, [mode, missionId]);

  // Center map on first drone with GPS
  useEffect(() => {
    if (viewport.zoom > 5) return; // Already positioned
    const droneWithGPS = drones.find(d => d.position_lat && d.position_long);
    if (droneWithGPS) {
      setViewport({
        longitude: droneWithGPS.position_long,
        latitude: droneWithGPS.position_lat,
        zoom: 15,
      });
    }
  }, [drones, viewport.zoom]);

  // Handlers
  const handleAreaChange = useCallback((points, areaSqM) => {
    setSearchArea(points);
    setSearchAreaSqM(areaSqM);
    setCoveragePlan(null); // Reset plan when area changes
  }, []);

  const handleDroneToggle = useCallback((posId) => {
    setSelectedDrones(prev =>
      prev.includes(posId) ? prev.filter(id => id !== posId) : [...prev, posId]
    );
  }, []);

  const handleComputePlan = useCallback(async () => {
    setComputing(true);
    try {
      const request = {
        search_area: {
          type: 'polygon',
          points: searchArea,
          area_sq_m: searchAreaSqM,
        },
        survey_config: surveyConfig,
        pos_ids: selectedDrones.length > 0 ? selectedDrones : null,
      };
      const response = await sarApi.computePlan(request);
      setCoveragePlan(response);
      setMissionId(response.mission_id);
      toast.success(`Plan computed: ${response.plans.length} drones, ${(response.total_area_sq_m / 10000).toFixed(1)} ha`);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      toast.error(`Planning failed: ${detail}`);
    } finally {
      setComputing(false);
    }
  }, [searchArea, searchAreaSqM, surveyConfig, selectedDrones]);

  const handleLaunchMission = useCallback(async () => {
    if (!missionId) return;
    setLaunching(true);
    try {
      await sarApi.launchMission(missionId);
      toast.success('Mission launched!');
      setMode('monitor');
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      toast.error(`Launch failed: ${detail}`);
    } finally {
      setLaunching(false);
    }
  }, [missionId]);

  const handlePause = useCallback(async () => {
    if (!missionId) return;
    try {
      await sarApi.pauseMission(missionId);
      toast.info('Mission paused');
    } catch (err) {
      toast.error('Pause failed');
    }
  }, [missionId]);

  const handleResume = useCallback(async () => {
    if (!missionId) return;
    try {
      await sarApi.resumeMission(missionId);
      toast.success('Mission resumed');
    } catch (err) {
      toast.error('Resume failed');
    }
  }, [missionId]);

  const handleAbort = useCallback(async () => {
    if (!missionId) return;
    try {
      await sarApi.abortMission(missionId);
      toast.warning('Mission aborted');
    } catch (err) {
      toast.error('Abort failed');
    }
  }, [missionId]);

  const handlePOIAdded = useCallback((poi) => {
    setPois(prev => [...prev, poi]);
    setAddingPOI(false);
  }, []);

  return (
    <div className="quickscout-page">
      {/* Top Bar */}
      <div className="qs-top-bar">
        <div className="qs-top-bar-left">
          <span className="qs-page-title">QuickScout SAR</span>
          <PlanMonitorToggle mode={mode} onModeChange={setMode} />
        </div>
        {mode === 'monitor' && missionId && (
          <button
            className={`qs-btn ${addingPOI ? 'qs-btn-warning' : 'qs-btn-primary'}`}
            onClick={() => setAddingPOI(!addingPOI)}
            style={{ fontSize: 12, padding: '4px 12px' }}
          >
            {addingPOI ? 'Cancel POI' : '+ Add POI'}
          </button>
        )}
      </div>

      {/* Stats Bar (monitor mode) */}
      {mode === 'monitor' && <MissionStatsBar missionStatus={missionStatus} />}

      {/* Main Layout */}
      <div className="qs-main-layout">
        {/* Map */}
        <div className="qs-map-container">
          {mapboxAvailable ? (
            <Map
              initialViewState={viewport}
              mapboxAccessToken={mapboxToken}
              mapStyle="mapbox://styles/mapbox/satellite-streets-v12"
              style={{ width: '100%', height: '100%' }}
              onClick={(e) => {
                if (addingPOI && poiClickRef.current) {
                  poiClickRef.current(e);
                }
              }}
            >
              {mode === 'plan' && <DrawControl onAreaChange={handleAreaChange} />}

              <CoveragePreview
                plans={coveragePlan?.plans}
                missionStatus={missionStatus}
              />

              <POIMarkerSystem
                pois={pois}
                missionId={missionId}
                onPOIAdded={handlePOIAdded}
                addingPOI={addingPOI}
                onMapClick={poiClickRef}
              />

              {/* Drone position markers */}
              {drones.filter(d => d.position_lat && d.position_long).map((drone) => (
                <Marker
                  key={drone.hw_ID}
                  latitude={drone.position_lat}
                  longitude={drone.position_long}
                  anchor="center"
                >
                  <div style={{
                    width: 20, height: 20,
                    background: 'var(--color-primary)',
                    borderRadius: '50%',
                    border: '2px solid white',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 9, fontWeight: 700, color: '#000',
                  }}>
                    {drone.hw_ID}
                  </div>
                </Marker>
              ))}
            </Map>
          ) : (
            <MapboxSetupInstructions />
          )}

          {/* Action Bar (monitor mode) */}
          {mode === 'monitor' && (
            <MissionActionBar
              missionState={missionStatus?.state}
              onResume={handleResume}
              onPause={handlePause}
              onRTL={() => handleAbort()}
              onAbort={handleAbort}
            />
          )}
        </div>

        {/* Sidebar */}
        {mode === 'plan' ? (
          <MissionPlanSidebar
            drones={drones}
            selectedDrones={selectedDrones}
            onDroneToggle={handleDroneToggle}
            surveyConfig={surveyConfig}
            onConfigChange={setSurveyConfig}
            onComputePlan={handleComputePlan}
            onLaunchMission={handleLaunchMission}
            coveragePlan={coveragePlan}
            searchArea={searchArea}
            computing={computing}
            launching={launching}
          />
        ) : (
          <MissionMonitorSidebar
            missionStatus={missionStatus}
            pois={pois}
            onDroneClick={(hwId) => {
              // Center map on drone
              const drone = drones.find(d => d.hw_ID === hwId);
              if (drone?.position_lat && drone?.position_long) {
                setViewport({
                  longitude: drone.position_long,
                  latitude: drone.position_lat,
                  zoom: 16,
                });
              }
            }}
            onPOIClick={(poi) => {
              setViewport({ longitude: poi.lng, latitude: poi.lat, zoom: 17 });
            }}
          />
        )}
      </div>
    </div>
  );
};

export default QuickScoutPage;

// src/components/map/ViewModeToggle.js
// Segmented control for switching between 3D Scene and Map View modes

import React from 'react';
import PropTypes from 'prop-types';
import '../../styles/GlobeView.css';

export const VIEW_MODES = {
  SCENE_3D: '3d',
  MAP: 'map',
};

const ViewModeToggle = ({ viewMode, onChange }) => (
  <div className="globe-view-mode-toggle">
    <button
      className={`globe-view-mode-btn ${viewMode === VIEW_MODES.SCENE_3D ? 'active' : ''}`}
      onClick={() => onChange(VIEW_MODES.SCENE_3D)}
    >
      3D Scene
    </button>
    <button
      className={`globe-view-mode-btn ${viewMode === VIEW_MODES.MAP ? 'active' : ''}`}
      onClick={() => onChange(VIEW_MODES.MAP)}
    >
      Map View
    </button>
  </div>
);

ViewModeToggle.propTypes = {
  viewMode: PropTypes.oneOf(Object.values(VIEW_MODES)).isRequired,
  onChange: PropTypes.func.isRequired,
};

export default ViewModeToggle;

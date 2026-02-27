// src/services/ElevationService.js
// Smart elevation fallback: Backend OpenTopoData -> Mapbox Tilequery -> Static estimation

import { getElevation } from '../utilities/utilities';
import { MAPBOX_TOKEN } from '../config/mapConfig';

// LRU cache for elevation results
const CACHE_MAX = 500;
const GRID_SNAP = 0.0002; // ~20m grid snapping for dedup
const cache = new Map();

function snapCoord(val) {
  return Math.round(val / GRID_SNAP) * GRID_SNAP;
}

function getCacheKey(lat, lng) {
  return `${snapCoord(lat).toFixed(4)},${snapCoord(lng).toFixed(4)}`;
}

function cacheSet(key, value) {
  if (cache.size >= CACHE_MAX) {
    // Evict oldest entry
    const firstKey = cache.keys().next().value;
    cache.delete(firstKey);
  }
  cache.set(key, value);
}

/**
 * Static geographic-region-based elevation estimation (last resort)
 */
function estimateStaticElevation(lat, lng) {
  const regions = [
    { bounds: [25, 50, -125, -100], elevation: 1800, name: 'Rocky Mountains' },
    { bounds: [28, 47, 65, 105], elevation: 2200, name: 'Himalayas' },
    { bounds: [40, 50, -10, 20], elevation: 900, name: 'Alps' },
    { bounds: [-56, -22, -75, -53], elevation: 1200, name: 'Andes' },
    { bounds: [27, 40, 73, 105], elevation: 4000, name: 'Tibetan Plateau' },
    { bounds: [34, 42, -114, -102], elevation: 1600, name: 'Colorado Plateau' },
    { bounds: [30, 49, -104, -88], elevation: 400, name: 'Great Plains' },
  ];

  for (const region of regions) {
    const [minLat, maxLat, minLng, maxLng] = region.bounds;
    if (lat >= minLat && lat <= maxLat && lng >= minLng && lng <= maxLng) {
      return region.elevation;
    }
  }

  if (Math.abs(lat) > 60) return 300;
  if (Math.abs(lat) < 30) return 50;
  return 150;
}

/**
 * Query Mapbox Tilequery API for elevation (secondary source)
 */
async function queryMapboxTilequery(lat, lng, timeout = 5000) {
  if (!MAPBOX_TOKEN) return null;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const url = `https://api.mapbox.com/v4/mapbox.mapbox-terrain-v2/tilequery/${lng},${lat}.json?layers=contour&limit=50&access_token=${MAPBOX_TOKEN}`;
    const response = await fetch(url, { signal: controller.signal });
    clearTimeout(timeoutId);

    if (!response.ok) return null;

    const data = await response.json();
    if (!data.features || data.features.length === 0) return null;

    const elevations = data.features
      .map((f) => f.properties.ele)
      .filter((ele) => typeof ele === 'number');

    if (elevations.length === 0) return null;
    return Math.max(...elevations);
  } catch {
    clearTimeout(timeoutId);
    return null;
  }
}

/**
 * Get terrain elevation with smart fallback chain.
 *
 * Fallback order:
 *  1. Backend OpenTopoData (getElevation from utilities.js)
 *  2. Mapbox Tilequery (if Mapbox available)
 *  3. Static geographic estimation
 *
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 * @param {object} options - { preferMapbox: false, timeout: 5000 }
 * @returns {{ elevation: number|null, source: string, error?: string }}
 */
export async function getTerrainElevation(lat, lng, options = {}) {
  const { preferMapbox = false, timeout = 5000 } = options;

  // Check cache first
  const key = getCacheKey(lat, lng);
  if (cache.has(key)) {
    return cache.get(key);
  }

  // Determine query order
  const sources = preferMapbox
    ? ['mapbox', 'backend', 'static']
    : ['backend', 'mapbox', 'static'];

  for (const source of sources) {
    try {
      if (source === 'backend') {
        const elevation = await Promise.race([
          getElevation(lat, lng),
          new Promise((_, reject) =>
            setTimeout(() => reject(new Error('timeout')), timeout)
          ),
        ]);
        if (elevation !== null && elevation !== undefined) {
          const result = { elevation, source: 'backend' };
          cacheSet(key, result);
          return result;
        }
      }

      if (source === 'mapbox') {
        const elevation = await queryMapboxTilequery(lat, lng, timeout);
        if (elevation !== null) {
          const result = { elevation, source: 'mapbox' };
          cacheSet(key, result);
          return result;
        }
      }

      if (source === 'static') {
        const elevation = estimateStaticElevation(lat, lng);
        const result = {
          elevation,
          source: 'static',
          error: 'Using estimated elevation data',
        };
        cacheSet(key, result);
        return result;
      }
    } catch {
      // Continue to next source
    }
  }

  // Should never reach here due to static fallback, but just in case
  const fallback = estimateStaticElevation(lat, lng);
  const result = { elevation: fallback, source: 'static', error: 'All sources failed' };
  cacheSet(key, result);
  return result;
}

/**
 * Clear the elevation cache
 */
export function clearElevationCache() {
  cache.clear();
}

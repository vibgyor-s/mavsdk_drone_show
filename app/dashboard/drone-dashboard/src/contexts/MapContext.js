// src/contexts/MapContext.js
// Provider detection + context for dual Mapbox/Leaflet map system

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  MAP_PROVIDERS,
  DEFAULT_PROVIDER,
  MAPBOX_TOKEN,
  PROVIDER_STORAGE_KEY,
  MAPBOX_PING_URL,
} from '../config/mapConfig';

const MapContext = createContext(null);

export const useMapContext = () => {
  const ctx = useContext(MapContext);
  if (!ctx) {
    // Return safe defaults when used outside provider (e.g. tests)
    return {
      provider: MAPBOX_TOKEN ? MAP_PROVIDERS.MAPBOX : MAP_PROVIDERS.LEAFLET,
      setProvider: () => {},
      isMapboxAvailable: !!MAPBOX_TOKEN,
      isLoading: false,
      mapboxToken: MAPBOX_TOKEN,
      fallbackReason: null,
    };
  }
  return ctx;
};

export const MapProvider = ({ children }) => {
  const [provider, setProviderState] = useState(() => {
    // Check localStorage for explicit user choice
    const stored = localStorage.getItem(PROVIDER_STORAGE_KEY);
    if (stored && Object.values(MAP_PROVIDERS).includes(stored)) {
      return stored;
    }
    // If no token, default to leaflet immediately
    if (!MAPBOX_TOKEN) return MAP_PROVIDERS.LEAFLET;
    return DEFAULT_PROVIDER;
  });

  const [isMapboxAvailable, setIsMapboxAvailable] = useState(!!MAPBOX_TOKEN);
  const [isLoading, setIsLoading] = useState(!!MAPBOX_TOKEN);
  const [fallbackReason, setFallbackReason] = useState(
    !MAPBOX_TOKEN ? 'No Mapbox token configured' : null
  );

  // Ping Mapbox to verify connectivity
  useEffect(() => {
    if (!MAPBOX_TOKEN) {
      setIsLoading(false);
      setIsMapboxAvailable(false);
      return;
    }

    // Check if user explicitly chose leaflet
    const stored = localStorage.getItem(PROVIDER_STORAGE_KEY);
    if (stored === MAP_PROVIDERS.LEAFLET) {
      setIsLoading(false);
      // Keep isMapboxAvailable check running so toggle is available
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    fetch(MAPBOX_PING_URL(MAPBOX_TOKEN), {
      method: 'HEAD',
      signal: controller.signal,
    })
      .then((res) => {
        clearTimeout(timeoutId);
        if (res.ok) {
          setIsMapboxAvailable(true);
          setFallbackReason(null);
        } else {
          setIsMapboxAvailable(false);
          setFallbackReason(`Mapbox returned HTTP ${res.status}`);
          // Re-read at decision time to avoid race with user toggling
          const currentStored = localStorage.getItem(PROVIDER_STORAGE_KEY);
          if (!currentStored) {
            setProviderState(MAP_PROVIDERS.LEAFLET);
          }
        }
      })
      .catch((err) => {
        clearTimeout(timeoutId);
        setIsMapboxAvailable(false);
        const reason =
          err.name === 'AbortError'
            ? 'Mapbox connection timed out'
            : `Mapbox unreachable: ${err.message}`;
        setFallbackReason(reason);
        // Re-read at decision time to avoid race with user toggling
        const currentStored = localStorage.getItem(PROVIDER_STORAGE_KEY);
        if (!currentStored) {
          setProviderState(MAP_PROVIDERS.LEAFLET);
        }
      })
      .finally(() => {
        setIsLoading(false);
      });

    return () => {
      clearTimeout(timeoutId);
      controller.abort();
    };
  }, []);

  const setProvider = useCallback((newProvider) => {
    if (Object.values(MAP_PROVIDERS).includes(newProvider)) {
      setProviderState(newProvider);
      localStorage.setItem(PROVIDER_STORAGE_KEY, newProvider);
    }
  }, []);

  const value = {
    provider,
    setProvider,
    isMapboxAvailable,
    isLoading,
    mapboxToken: MAPBOX_TOKEN,
    fallbackReason,
  };

  return <MapContext.Provider value={value}>{children}</MapContext.Provider>;
};

export default MapContext;

import { useState, useEffect, useRef } from 'react';
import { getElevation } from './utilities/utilities';

const useElevation = (lat, lon) => {
  const [elevation, setElevation] = useState(null);
  const fetchedKeyRef = useRef(null);

  useEffect(() => {
    if (lat === null || lat === undefined || lon === null || lon === undefined) {
      setElevation(null);
      fetchedKeyRef.current = null;
      return;
    }

    // Grid-snap to ~20 m to avoid refetching for tiny GPS jitter
    const snap = (v) => (Math.round(v / 0.0002) * 0.0002).toFixed(4);
    const key = `${snap(lat)},${snap(lon)}`;

    // Skip if we already fetched this snapped location
    if (fetchedKeyRef.current === key) return;
    fetchedKeyRef.current = key;

    const fetchData = async () => {
      const fetchedElevation = await getElevation(lat, lon);
      setElevation(fetchedElevation);
    };

    fetchData();
  }, [lat, lon]);

  return elevation;
};

export default useElevation;

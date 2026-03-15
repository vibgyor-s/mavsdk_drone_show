import {
  DEFAULT_LEAFLET_SUBDOMAINS,
  getLeafletTileLayerConfig,
} from './mapConfig';

describe('getLeafletTileLayerConfig', () => {
  test('provides safe subdomains for OpenStreetMap layers', () => {
    const layer = getLeafletTileLayerConfig('osm');

    expect(layer.url).toContain('{s}');
    expect(layer.subdomains).toBe(DEFAULT_LEAFLET_SUBDOMAINS);
  });

  test('provides safe subdomains for OpenTopoMap layers', () => {
    const layer = getLeafletTileLayerConfig('openTopoMap');

    expect(layer.url).toContain('{s}');
    expect(layer.subdomains).toBe(DEFAULT_LEAFLET_SUBDOMAINS);
  });

  test('preserves explicit provider subdomains', () => {
    const layer = getLeafletTileLayerConfig('googleSatellite');

    expect(layer.subdomains).toEqual(['mt0', 'mt1', 'mt2', 'mt3']);
  });

  test('falls back to default layer for unknown keys', () => {
    const layer = getLeafletTileLayerConfig('missing-layer');

    expect(layer.name).toBe('Google Satellite');
    expect(layer.subdomains).toEqual(['mt0', 'mt1', 'mt2', 'mt3']);
  });
});

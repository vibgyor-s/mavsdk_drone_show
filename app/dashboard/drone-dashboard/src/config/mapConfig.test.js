import {
  DEFAULT_LEAFLET_SUBDOMAINS,
  getLeafletTileLayerConfig,
  resolveTileLayerKey,
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

  test('provides safe subdomains for providers without {s} placeholders', () => {
    const layer = getLeafletTileLayerConfig('esriSatellite');

    expect(layer.url).toContain('arcgisonline');
    expect(layer.subdomains).toBe(DEFAULT_LEAFLET_SUBDOMAINS);
  });

  test('preserves explicit provider subdomains', () => {
    const layer = getLeafletTileLayerConfig('googleSatellite');

    expect(layer.subdomains).toEqual(['mt0', 'mt1', 'mt2', 'mt3']);
  });

  test('falls back to default layer for unknown keys', () => {
    const layer = getLeafletTileLayerConfig('missing-layer');

    expect(layer.key).toBe('esriSatellite');
    expect(layer.name).toBe('Satellite (Esri)');
    expect(layer.url).toContain('arcgisonline');
  });

  test('normalizes invalid tile keys to the default layer key', () => {
    expect(resolveTileLayerKey('missing-layer')).toBe('esriSatellite');
    expect(resolveTileLayerKey('osm')).toBe('osm');
  });
});

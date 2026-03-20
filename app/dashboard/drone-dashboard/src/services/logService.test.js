// src/services/logService.test.js
import { buildStreamURL } from './logService';

describe('logService', () => {
  describe('buildStreamURL', () => {
    test('returns base URL with no filters', () => {
      const url = buildStreamURL();
      expect(url).toContain('/api/logs/stream');
      expect(url).not.toContain('?');
    });

    test('appends level filter', () => {
      const url = buildStreamURL({ level: 'WARNING' });
      expect(url).toContain('level=WARNING');
    });

    test('uses drone proxy URL when droneId provided', () => {
      const url = buildStreamURL({}, 5);
      expect(url).toContain('/api/logs/drone/5/stream');
    });

    test('combines filters', () => {
      const url = buildStreamURL({ level: 'ERROR', component: 'gcs' });
      expect(url).toContain('level=ERROR');
      expect(url).toContain('component=gcs');
    });
  });
});

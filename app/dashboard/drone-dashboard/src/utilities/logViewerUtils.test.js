import {
  applySeverityFocus,
  buildComponentCatalog,
  filterEntriesByAbsoluteTimeRange,
  filterEntriesByRelativeWindow,
  formatSessionLabel,
  parseSessionTimestamp,
} from './logViewerUtils';

describe('logViewerUtils', () => {
  const toLocalInputValue = (isoString) => {
    const date = new Date(isoString);
    const pad = (value) => String(value).padStart(2, '0');

    return [
      date.getFullYear(),
      pad(date.getMonth() + 1),
      pad(date.getDate()),
    ].join('-') + `T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
  };

  test('parseSessionTimestamp parses canonical session ids in UTC', () => {
    const value = parseSessionTimestamp('s_20260320_072832');
    expect(value.toISOString()).toBe('2026-03-20T07:28:32.000Z');
  });

  test('formatSessionLabel uses timestamp and size_bytes', () => {
    const label = formatSessionLabel({
      session_id: 's_20260320_072832',
      size_bytes: 1536,
    });

    expect(label).toContain('2026');
    expect(label).toContain('UTC');
    expect(label).toContain('1.5 KB');
  });

  test('filterEntriesByAbsoluteTimeRange keeps entries inside bounds', () => {
    const entries = [
      { ts: '2026-03-20T07:28:30.000Z', msg: 'before' },
      { ts: '2026-03-20T07:28:32.000Z', msg: 'inside' },
      { ts: '2026-03-20T07:28:35.000Z', msg: 'after' },
    ];

    const result = filterEntriesByAbsoluteTimeRange(
      entries,
      toLocalInputValue('2026-03-20T07:28:31.000Z'),
      toLocalInputValue('2026-03-20T07:28:33.000Z'),
    );

    expect(result).toHaveLength(1);
    expect(result[0].msg).toBe('inside');
  });

  test('filterEntriesByRelativeWindow trims around the newest entry', () => {
    const entries = [
      { ts: '2026-03-20T07:20:00.000Z', msg: 'old' },
      { ts: '2026-03-20T07:27:00.000Z', msg: 'recent' },
      { ts: '2026-03-20T07:28:00.000Z', msg: 'newest' },
    ];

    const result = filterEntriesByRelativeWindow(entries, 2 * 60 * 1000);

    expect(result.map((entry) => entry.msg)).toEqual(['recent', 'newest']);
  });

  test('buildComponentCatalog merges registry and observed entries', () => {
    const catalog = buildComponentCatalog(
      [{ component: 'telemetry', source: 'drone' }],
      { gcs: { category: 'gcs', description: 'server' } },
    );

    expect(catalog).toEqual([
      { name: 'gcs', category: 'gcs', description: 'server' },
      { name: 'telemetry', category: 'drone', description: '' },
    ]);
  });

  test('applySeverityFocus supports warnings and errors drill-down', () => {
    const entries = [
      { level: 'INFO' },
      { level: 'WARNING' },
      { level: 'ERROR' },
      { level: 'CRITICAL' },
    ];

    expect(applySeverityFocus(entries, 'warnings')).toHaveLength(1);
    expect(applySeverityFocus(entries, 'errors')).toHaveLength(2);
  });
});

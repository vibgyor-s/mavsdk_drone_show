import {
  buildMissionConfigFormState,
  CUSTOM_FIELD_TYPES,
  getMissionConfigCustomFields,
  getPromotedMissionConfigField,
  normalizeMissionCustomFieldKey,
  serializeMissionConfigFormState,
  validateMissionCustomFields,
} from './missionConfigFields';

describe('missionConfigFields', () => {
  test('extracts and sorts additional fields separately from core mission fields', () => {
    const fields = getMissionConfigCustomFields({
      hw_id: '1',
      pos_id: '2',
      ip: '10.0.0.1',
      mavlink_port: '14550',
      serial_port: '',
      baudrate: '0',
      notes: 'Battery swapped',
      callsign: 'TEST-01',
      maintenance_tag: 'A2',
    });

    expect(fields.map((field) => field.key)).toEqual([
      'callsign',
      'maintenance_tag',
      'notes',
    ]);
  });

  test('promotes callsign as the preferred operator alias', () => {
    const promoted = getPromotedMissionConfigField({
      hw_id: 1,
      pos_id: 1,
      ip: '10.0.0.1',
      mavlink_port: 14550,
      callsign: 'VIPER-1',
      nickname: 'Backup Name',
    });

    expect(promoted).toEqual(expect.objectContaining({
      key: 'callsign',
      value: 'VIPER-1',
    }));
  });

  test('builds editable form state without dropping additional fields', () => {
    const formState = buildMissionConfigFormState({
      hw_id: 1,
      pos_id: 4,
      ip: '10.0.0.1',
      mavlink_port: 14550,
      serial_port: '',
      baudrate: 0,
      callsign: 'TEST-01',
      battery_cycles: 17,
      metadata: { hangar: 'B', ready: true },
    });

    expect(formState.custom_fields).toEqual([
      expect.objectContaining({ key: 'callsign', type: CUSTOM_FIELD_TYPES.TEXT, value: 'TEST-01' }),
      expect.objectContaining({ key: 'battery_cycles', type: CUSTOM_FIELD_TYPES.NUMBER, value: '17' }),
      expect.objectContaining({ key: 'metadata', type: CUSTOM_FIELD_TYPES.JSON }),
    ]);
  });

  test('serializes editable form state back to flat config fields', () => {
    const serialized = serializeMissionConfigFormState({
      hw_id: '7',
      pos_id: '9',
      ip: '10.0.0.7',
      mavlink_port: '14557',
      serial_port: '',
      baudrate: '0',
      isNew: false,
      custom_fields: [
        { id: 'c1', key: 'callsign', type: CUSTOM_FIELD_TYPES.TEXT, value: 'VIPER-7' },
        { id: 'c2', key: 'battery_cycles', type: CUSTOM_FIELD_TYPES.NUMBER, value: '24' },
        { id: 'c3', key: 'ready', type: CUSTOM_FIELD_TYPES.BOOLEAN, value: true },
      ],
    });

    expect(serialized).toEqual(expect.objectContaining({
      hw_id: '7',
      pos_id: '9',
      callsign: 'VIPER-7',
      battery_cycles: 24,
      ready: true,
    }));
  });

  test('normalizes custom field keys to lowercase snake_case', () => {
    expect(normalizeMissionCustomFieldKey('Call Sign')).toBe('call_sign');
    expect(normalizeMissionCustomFieldKey('batteryCycles')).toBe('battery_cycles');
  });

  test('rejects duplicate and reserved additional field keys', () => {
    const validation = validateMissionCustomFields([
      { id: 'a', key: 'my_field', type: CUSTOM_FIELD_TYPES.TEXT, value: 'A' },
      { id: 'b', key: 'My Field', type: CUSTOM_FIELD_TYPES.TEXT, value: 'B' },
      { id: 'c', key: 'hw_id', type: CUSTOM_FIELD_TYPES.TEXT, value: 'bad' },
    ]);

    expect(validation.isValid).toBe(false);
    // 'my_field' and 'My Field' both normalize to 'my_field' — duplicate
    expect(validation.errorsById.a.key).toMatch(/unique/i);
    expect(validation.errorsById.b.key).toMatch(/unique/i);
    // 'hw_id' is a reserved core field
    expect(validation.errorsById.c.key).toMatch(/reserved/i);
  });
});

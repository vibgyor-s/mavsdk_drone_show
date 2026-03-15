from unittest.mock import patch

from config import validate_and_process_config


def test_validate_and_process_config_reports_duplicate_hw_and_pos_ids():
    current_config = [
        {'hw_id': 1, 'pos_id': 1, 'ip': '10.0.0.1', 'mavlink_port': 14551},
    ]
    candidate_config = [
        {'hw_id': '1', 'pos_id': '2', 'ip': '10.0.0.1', 'mavlink_port': 14551},
        {'hw_id': 1, 'pos_id': 3, 'ip': '10.0.0.2', 'mavlink_port': 14552},
        {'hw_id': 4, 'pos_id': '3', 'ip': '10.0.0.4', 'mavlink_port': 14554},
    ]

    with patch('config.load_config', return_value=current_config):
        with patch('coordinate_utils.get_expected_position_from_trajectory', return_value=(0.0, 0.0)):
            report = validate_and_process_config(candidate_config, sim_mode=True)

    assert report['summary']['duplicate_hw_ids_count'] == 1
    assert report['warnings']['duplicate_hw_ids'] == [
        {
            'hw_id': 1,
            'pos_ids': [2, 3],
            'message': 'INVALID CONFIG: hw_id 1 is defined multiple times',
        }
    ]
    assert report['summary']['duplicates_count'] == 1
    assert report['warnings']['duplicates'] == [
        {
            'pos_id': 3,
            'hw_ids': [1, 4],
            'message': 'COLLISION RISK: pos_id 3 assigned to drones [1, 4]',
        }
    ]
    assert report['summary']['role_swaps_count'] == 3

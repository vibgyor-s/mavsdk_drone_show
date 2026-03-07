# tests/test_file_utils.py
"""
File Utilities Tests
====================
Tests for the shared CSV, JSON, and file I/O operations in functions/file_utils.py.
"""

import json
import pytest
import sys
import os
import tempfile
import csv

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'functions'))

from functions.file_utils import load_json, save_json


class TestLoadCSV:
    """Test CSV loading functionality"""

    def test_load_csv_success(self, tmp_path):
        """Test loading a valid CSV file"""
        from functions.file_utils import load_csv

        # Create test CSV
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("hw_id,pos_id,ip\n1,1,192.168.1.100\n2,2,192.168.1.101\n")

        data = load_csv(str(csv_file))

        assert len(data) == 2
        assert data[0]['hw_id'] == '1'
        assert data[0]['pos_id'] == '1'
        assert data[0]['ip'] == '192.168.1.100'
        assert data[1]['hw_id'] == '2'

    def test_load_csv_file_not_found(self):
        """Test loading non-existent file returns empty list"""
        from functions.file_utils import load_csv

        data = load_csv("/nonexistent/path/file.csv")

        assert data == []

    def test_load_csv_empty_file(self, tmp_path):
        """Test loading empty CSV returns empty list"""
        from functions.file_utils import load_csv

        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("hw_id,pos_id,ip\n")  # Header only

        data = load_csv(str(csv_file))

        assert data == []

    def test_load_csv_with_unicode(self, tmp_path):
        """Test loading CSV with unicode content"""
        from functions.file_utils import load_csv

        csv_file = tmp_path / "unicode.csv"
        csv_file.write_text("name,description\nDrone,Test drone\n", encoding='utf-8')

        data = load_csv(str(csv_file))

        assert len(data) == 1
        assert data[0]['name'] == 'Drone'


class TestSaveCSV:
    """Test CSV saving functionality"""

    def test_save_csv_success(self, tmp_path):
        """Test saving data to CSV"""
        from functions.file_utils import save_csv, load_csv

        data = [
            {'hw_id': '1', 'pos_id': '1', 'ip': '192.168.1.100'},
            {'hw_id': '2', 'pos_id': '2', 'ip': '192.168.1.101'}
        ]
        csv_file = tmp_path / "output.csv"

        result = save_csv(data, str(csv_file))

        assert result == True
        assert csv_file.exists()

        # Verify contents
        loaded = load_csv(str(csv_file))
        assert len(loaded) == 2
        assert loaded[0]['hw_id'] == '1'

    def test_save_csv_with_fieldnames(self, tmp_path):
        """Test saving CSV with specific column order"""
        from functions.file_utils import save_csv

        data = [{'ip': '192.168.1.100', 'hw_id': '1', 'pos_id': '1'}]
        csv_file = tmp_path / "ordered.csv"
        fieldnames = ['hw_id', 'pos_id', 'ip']

        save_csv(data, str(csv_file), fieldnames=fieldnames)

        # Read raw to check column order
        with open(csv_file) as f:
            header = f.readline().strip()
            assert header == 'hw_id,pos_id,ip'

    def test_save_csv_empty_data(self, tmp_path):
        """Test saving empty data returns False"""
        from functions.file_utils import save_csv

        csv_file = tmp_path / "empty.csv"

        result = save_csv([], str(csv_file))

        assert result == False
        assert not csv_file.exists()

    def test_save_csv_creates_directory(self, tmp_path):
        """Test that save_csv creates parent directories"""
        from functions.file_utils import save_csv

        data = [{'key': 'value'}]
        nested_dir = tmp_path / "nested" / "dir"
        csv_file = nested_dir / "file.csv"

        result = save_csv(data, str(csv_file))

        assert result == True
        assert csv_file.exists()


class TestValidateCSVSchema:
    """Test CSV schema validation"""

    def test_validate_schema_success(self):
        """Test validation with all required columns present"""
        from functions.file_utils import validate_csv_schema

        data = [{'hw_id': '1', 'pos_id': '1', 'ip': '192.168.1.100'}]
        required = ['hw_id', 'pos_id']

        is_valid, missing = validate_csv_schema(data, required)

        assert is_valid == True
        assert missing == []

    def test_validate_schema_missing_columns(self):
        """Test validation with missing columns"""
        from functions.file_utils import validate_csv_schema

        data = [{'hw_id': '1'}]
        required = ['hw_id', 'pos_id', 'ip']

        is_valid, missing = validate_csv_schema(data, required)

        assert is_valid == False
        assert 'pos_id' in missing
        assert 'ip' in missing
        assert 'hw_id' not in missing

    def test_validate_schema_empty_data(self):
        """Test validation with empty data"""
        from functions.file_utils import validate_csv_schema

        is_valid, missing = validate_csv_schema([], ['hw_id', 'pos_id'])

        assert is_valid == False
        assert missing == ['hw_id', 'pos_id']


class TestTrajectoryOperations:
    """Test trajectory file operations"""

    def test_load_trajectory_csv(self, tmp_path):
        """Test loading trajectory waypoints"""
        from functions.file_utils import load_trajectory_csv

        # Create trajectory CSV with standard naming
        csv_file = tmp_path / "trajectory.csv"
        csv_file.write_text(
            "t [ms],x [m],y [m],z [m],yaw [deg]\n"
            "0,0.0,0.0,0.0,0.0\n"
            "1000,1.0,2.0,5.0,90.0\n"
            "2000,2.0,4.0,10.0,180.0\n"
        )

        waypoints = load_trajectory_csv(str(csv_file))

        assert len(waypoints) == 3
        assert waypoints[0]['t'] == 0.0
        assert waypoints[0]['x'] == 0.0
        assert waypoints[1]['x'] == 1.0
        assert waypoints[1]['y'] == 2.0
        assert waypoints[1]['z'] == 5.0
        assert waypoints[1]['yaw'] == 90.0

    def test_load_trajectory_csv_alternate_format(self, tmp_path):
        """Test loading trajectory with px/py/pz format"""
        from functions.file_utils import load_trajectory_csv

        csv_file = tmp_path / "trajectory_alt.csv"
        csv_file.write_text(
            "t,px,py,pz,yaw\n"
            "0,0.0,0.0,0.0,0\n"
            "1000,5.5,6.6,7.7,45\n"
        )

        waypoints = load_trajectory_csv(str(csv_file))

        assert len(waypoints) == 2
        assert waypoints[1]['x'] == 5.5
        assert waypoints[1]['y'] == 6.6
        assert waypoints[1]['z'] == 7.7

    def test_get_trajectory_duration(self):
        """Test calculating trajectory duration"""
        from functions.file_utils import get_trajectory_duration

        waypoints = [
            {'t': 0},
            {'t': 30000},
            {'t': 60000}
        ]

        duration = get_trajectory_duration(waypoints)

        assert duration == 60.0  # 60000ms = 60 seconds

    def test_get_trajectory_duration_empty(self):
        """Test duration of empty trajectory"""
        from functions.file_utils import get_trajectory_duration

        duration = get_trajectory_duration([])

        assert duration == 0.0

    def test_get_trajectory_first_position(self, tmp_path):
        """Test getting first position from trajectory"""
        from functions.file_utils import get_trajectory_first_position

        csv_file = tmp_path / "trajectory.csv"
        csv_file.write_text(
            "t [ms],x [m],y [m],z [m],yaw [deg]\n"
            "0,1.5,2.5,3.5,0\n"
            "1000,10.0,20.0,30.0,90\n"
        )

        pos = get_trajectory_first_position(str(csv_file))

        assert pos is not None
        assert pos['x'] == 1.5
        assert pos['y'] == 2.5
        assert pos['z'] == 3.5

    def test_get_trajectory_first_position_empty_file(self, tmp_path):
        """Test first position of empty trajectory returns None"""
        from functions.file_utils import get_trajectory_first_position

        csv_file = tmp_path / "empty_traj.csv"
        csv_file.write_text("t [ms],x [m],y [m],z [m],yaw [deg]\n")

        pos = get_trajectory_first_position(str(csv_file))

        assert pos is None


class TestLoadJson:
    """Test JSON loading functionality"""

    def test_load_valid_json(self, tmp_path):
        p = tmp_path / "test.json"
        p.write_text('{"version": 1, "drones": [{"hw_id": 1}]}')
        data = load_json(str(p))
        assert data['version'] == 1
        assert len(data['drones']) == 1

    def test_load_missing_file(self, tmp_path):
        data = load_json(str(tmp_path / "nonexistent.json"))
        assert data == {}

    def test_load_invalid_json(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text('{invalid json}')
        data = load_json(str(p))
        assert data == {}

    def test_load_empty_file(self, tmp_path):
        p = tmp_path / "empty.json"
        p.write_text('')
        data = load_json(str(p))
        assert data == {}


class TestSaveJson:
    """Test JSON saving functionality"""

    def test_save_and_load(self, tmp_path):
        p = tmp_path / "out.json"
        data = {"version": 1, "drones": [{"hw_id": 1, "ip": "10.0.0.1"}]}
        result = save_json(data, str(p))
        assert result is True
        loaded = json.loads(p.read_text())
        assert loaded['version'] == 1
        assert loaded['drones'][0]['ip'] == '10.0.0.1'

    def test_trailing_newline(self, tmp_path):
        p = tmp_path / "out.json"
        save_json({"a": 1}, str(p))
        assert p.read_text().endswith('\n')

    def test_creates_parent_dirs(self, tmp_path):
        p = tmp_path / "sub" / "dir" / "out.json"
        result = save_json({"a": 1}, str(p))
        assert result is True
        assert p.exists()

    def test_unicode_preserved(self, tmp_path):
        p = tmp_path / "unicode.json"
        save_json({"notes": "Drone für Test"}, str(p))
        loaded = json.loads(p.read_text())
        assert loaded['notes'] == "Drone für Test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

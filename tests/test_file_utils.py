# tests/test_file_utils.py
"""
File Utilities Tests
====================
Tests for the shared CSV and file I/O operations in functions/file_utils.py.
"""

import pytest
import os
import tempfile
import csv


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

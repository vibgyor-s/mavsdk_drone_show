# tests/test_file_management.py
"""
File Management Tests
=====================
Tests for directory and file operations in functions/file_management.py.
"""

import pytest
import os
import tempfile


class TestEnsureDirectoryExists:
    """Test ensure_directory_exists function"""

    def test_creates_new_directory(self, tmp_path):
        """Test creating a new directory"""
        from functions.file_management import ensure_directory_exists

        new_dir = tmp_path / "new_folder"
        assert not new_dir.exists()

        ensure_directory_exists(str(new_dir))

        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_existing_directory_unchanged(self, tmp_path):
        """Test existing directory is not modified"""
        from functions.file_management import ensure_directory_exists

        # Create a file in the directory
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        ensure_directory_exists(str(tmp_path))

        assert tmp_path.exists()
        assert test_file.exists()
        assert test_file.read_text() == "test content"

    def test_creates_nested_directories(self, tmp_path):
        """Test creating nested directories"""
        from functions.file_management import ensure_directory_exists

        nested_dir = tmp_path / "level1" / "level2" / "level3"

        ensure_directory_exists(str(nested_dir))

        assert nested_dir.exists()
        assert nested_dir.is_dir()


class TestClearDirectory:
    """Test clear_directory function"""

    def test_clears_files(self, tmp_path):
        """Test clearing files from directory"""
        from functions.file_management import clear_directory

        # Create test files
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")

        assert len(list(tmp_path.iterdir())) == 2

        clear_directory(str(tmp_path))

        assert len(list(tmp_path.iterdir())) == 0

    def test_clears_subdirectories(self, tmp_path):
        """Test clearing subdirectories"""
        from functions.file_management import clear_directory

        # Create subdirectory with file
        sub_dir = tmp_path / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file.txt").write_text("content")

        clear_directory(str(tmp_path))

        assert not sub_dir.exists()

    def test_empty_directory_no_error(self, tmp_path):
        """Test clearing empty directory doesn't raise error"""
        from functions.file_management import clear_directory

        # Directory is already empty
        clear_directory(str(tmp_path))

        assert tmp_path.exists()


class TestCopyFiles:
    """Test copy_files function"""

    def test_copies_files(self, tmp_path):
        """Test copying files to destination"""
        from functions.file_management import copy_files

        # Setup source and destination
        source = tmp_path / "source"
        dest = tmp_path / "dest"
        source.mkdir()
        dest.mkdir()

        # Create source files
        (source / "file1.txt").write_text("content1")
        (source / "file2.txt").write_text("content2")

        copy_files(str(source), str(dest))

        assert (dest / "file1.txt").exists()
        assert (dest / "file2.txt").exists()
        assert (dest / "file1.txt").read_text() == "content1"

    def test_skips_directories(self, tmp_path):
        """Test that subdirectories are not copied"""
        from functions.file_management import copy_files

        source = tmp_path / "source"
        dest = tmp_path / "dest"
        source.mkdir()
        dest.mkdir()

        # Create a file and a subdirectory
        (source / "file.txt").write_text("content")
        (source / "subdir").mkdir()

        copy_files(str(source), str(dest))

        assert (dest / "file.txt").exists()
        assert not (dest / "subdir").exists()

    def test_empty_source_no_error(self, tmp_path):
        """Test copying from empty source doesn't raise error"""
        from functions.file_management import copy_files

        source = tmp_path / "source"
        dest = tmp_path / "dest"
        source.mkdir()
        dest.mkdir()

        copy_files(str(source), str(dest))

        assert len(list(dest.iterdir())) == 0


class TestSetupLogging:
    """Test setup_logging function"""

    def test_setup_logging_runs(self):
        """Test setup_logging runs without error"""
        from functions.file_management import setup_logging

        # Should not raise
        setup_logging()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

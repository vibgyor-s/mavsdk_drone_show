"""
Tests for PX4 SITL rcS override management.
"""

import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "multiple_sitl" / "configure_px4_sitl_rcs.py"
SPEC = importlib.util.spec_from_file_location("configure_px4_sitl_rcs", MODULE_PATH)
configurer = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(configurer)


def write_rcs(tmp_path: Path, contents: str) -> Path:
    rcs_path = tmp_path / "rcS"
    rcs_path.write_text(contents, encoding="utf-8")
    return rcs_path


class TestConfigurePx4SitlRcs:
    def test_discover_hwid_from_directory(self, tmp_path: Path):
        (tmp_path / "7.hwID").write_text("", encoding="utf-8")
        assert configurer.discover_hwid(tmp_path) == 7

    def test_parse_param_assignment_rejects_invalid_name(self):
        with pytest.raises(ValueError):
            configurer.parse_param_assignment("bad-name=1")

    def test_configure_rcs_inserts_managed_block_after_anchor(self, tmp_path: Path):
        rcs_path = write_rcs(
            tmp_path,
            "#!/bin/sh\n"
            "param set MAV_SYS_ID $((px4_instance+1))\n"
            "echo ready\n",
        )

        changed = configurer.configure_rcs(
            rcs_path,
            hwid=3,
            params=[("COM_RC_IN_MODE", "4"), ("SDLOG_MODE", "-1")],
        )

        text = rcs_path.read_text(encoding="utf-8")
        assert changed is True
        assert "param set MAV_SYS_ID 3\n" in text
        assert "param set COM_RC_IN_MODE 4\n" in text
        assert "param set SDLOG_MODE -1\n" in text
        assert text.index(configurer.BEGIN_MARKER) > text.index(configurer.MAV_SYS_ID_PATTERN)

    def test_configure_rcs_replaces_existing_managed_block_idempotently(self, tmp_path: Path):
        rcs_path = write_rcs(
            tmp_path,
            "#!/bin/sh\n"
            "param set MAV_SYS_ID $((px4_instance+1))\n"
            f"{configurer.BEGIN_MARKER}"
            "param set MAV_SYS_ID 1\n"
            "param set COM_RC_IN_MODE 1\n"
            f"{configurer.END_MARKER}"
            "echo ready\n",
        )

        changed = configurer.configure_rcs(
            rcs_path,
            hwid=1,
            params=[("COM_RC_IN_MODE", "4")],
        )
        second_changed = configurer.configure_rcs(
            rcs_path,
            hwid=1,
            params=[("COM_RC_IN_MODE", "4")],
        )

        text = rcs_path.read_text(encoding="utf-8")
        assert changed is True
        assert second_changed is False
        assert text.count(configurer.BEGIN_MARKER) == 1
        assert "param set COM_RC_IN_MODE 4\n" in text
        assert "param set COM_RC_IN_MODE 1\n" not in text

    def test_find_insert_index_falls_back_to_last_mav_sys_id_line(self):
        lines = [
            "#!/bin/sh\n",
            "param set SOME_OTHER_PARAM 1\n",
            "param set MAV_SYS_ID 10\n",
        ]

        assert configurer.find_insert_index(lines, Path("/tmp/rcS")) == 3

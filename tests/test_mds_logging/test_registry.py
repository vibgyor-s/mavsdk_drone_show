"""Tests for mds_logging.registry — component self-registration."""
from mds_logging.registry import register_component, get_registry, clear_registry


class TestRegistry:
    def setup_method(self):
        clear_registry()

    def test_register_and_retrieve(self):
        register_component("coordinator", "drone", "System init")
        reg = get_registry()
        assert "coordinator" in reg
        assert reg["coordinator"]["category"] == "drone"

    def test_register_multiple(self):
        register_component("api", "gcs", "FastAPI server")
        register_component("coordinator", "drone", "Init")
        assert len(get_registry()) == 2

    def test_overwrite_existing(self):
        register_component("api", "gcs", "Old desc")
        register_component("api", "gcs", "New desc")
        assert get_registry()["api"]["description"] == "New desc"

"""Tests for mds_logging.cli — shared CLI argument parser."""
import argparse
from mds_logging.cli import add_log_arguments


class TestCLIArgs:
    def test_adds_verbose_flag(self):
        parser = argparse.ArgumentParser()
        add_log_arguments(parser)
        args = parser.parse_args(["--verbose"])
        assert args.verbose is True

    def test_adds_quiet_flag(self):
        parser = argparse.ArgumentParser()
        add_log_arguments(parser)
        args = parser.parse_args(["--quiet"])
        assert args.quiet is True

    def test_default_no_flags(self):
        parser = argparse.ArgumentParser()
        add_log_arguments(parser)
        args = parser.parse_args([])
        assert args.verbose is False
        assert args.quiet is False

    def test_debug_is_alias_for_verbose(self):
        parser = argparse.ArgumentParser()
        add_log_arguments(parser)
        args = parser.parse_args(["--debug"])
        assert args.verbose is True

    def test_log_json_flag(self):
        parser = argparse.ArgumentParser()
        add_log_arguments(parser)
        args = parser.parse_args(["--log-json"])
        assert args.log_json is True

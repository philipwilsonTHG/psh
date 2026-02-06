"""Fixtures for behavioral golden tests."""

import pytest


def pytest_addoption(parser):
    """Add --compare-bash option for conformance verification."""
    parser.addoption(
        "--compare-bash",
        action="store_true",
        default=False,
        help="Also run each golden test against bash and compare output",
    )

"""Pytest configuration and fixtures for PSH tests."""
import os
import pytest


def pytest_runtest_setup(item):
    """Apply custom marker logic before running tests."""
    # Check for visitor_xfail marker
    visitor_xfail_marker = item.get_closest_marker("visitor_xfail")
    
    if visitor_xfail_marker:
        # Visitor executor is now the only executor
        # All tests with visitor_xfail should be marked as expected failure
        reason = visitor_xfail_marker.kwargs.get('reason', 'Expected to fail due to pytest output capture limitations')
        item.add_marker(pytest.mark.xfail(reason=reason))
"""Pytest configuration and fixtures for PSH tests."""
import os
import pytest


def pytest_runtest_setup(item):
    """Apply custom marker logic before running tests."""
    # Check for visitor_xfail marker
    visitor_xfail_marker = item.get_closest_marker("visitor_xfail")
    
    if visitor_xfail_marker:
        # Check if we're using the visitor executor
        # Visitor executor is now the default (as of v0.50.0)
        # Only use legacy executor if PSH_USE_VISITOR_EXECUTOR is explicitly set to 0/false/no
        use_legacy = os.environ.get('PSH_USE_VISITOR_EXECUTOR', '1').lower() in ('0', 'false', 'no')
        use_visitor = not use_legacy
        
        if use_visitor:
            # Mark as expected failure when using visitor executor
            reason = visitor_xfail_marker.kwargs.get('reason', 'Expected to fail with visitor executor')
            item.add_marker(pytest.mark.xfail(reason=reason))
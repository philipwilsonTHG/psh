"""Configuration for testing with unified types."""

import pytest
from psh.shell import Shell


def pytest_addoption(parser):
    """Add command line option for unified types testing."""
    parser.addoption(
        "--unified-types",
        action="store_true",
        default=False,
        help="Run tests with unified types enabled"
    )


@pytest.fixture
def use_unified_types(request):
    """Fixture that returns whether to use unified types."""
    return request.config.getoption("--unified-types")


@pytest.fixture
def shell_unified(use_unified_types):
    """Create a shell instance configured for unified types testing."""
    shell = Shell()
    # Store the unified types preference in shell state
    shell.state.use_unified_types = use_unified_types
    return shell


@pytest.fixture
def parse_func(use_unified_types):
    """Return appropriate parse function based on unified types setting."""
    if use_unified_types:
        from psh.parser_refactored import parse
        return lambda tokens: parse(tokens, use_unified_types=True)
    else:
        from psh.parser import parse
        return parse


# Mark for tests that should run with both type systems
unified_parametrize = pytest.mark.parametrize(
    "parser_mode", 
    ["legacy", "unified"],
    indirect=True
)


@pytest.fixture
def parser_mode(request):
    """Fixture for parametrized parser mode."""
    mode = request.param
    if mode == "unified":
        from psh.parser_refactored import parse
        return lambda tokens: parse(tokens, use_unified_types=True)
    else:
        from psh.parser import parse
        return parse
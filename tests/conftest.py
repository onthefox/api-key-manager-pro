"""Shared pytest configuration for the test suite."""

import pytest

# Load required plugins explicitly. This works whether or not plugin
# autoloading is enabled (the root conftest.py disables autoload when a
# known-broken third-party plugin is installed in the environment).
pytest_plugins = ["pytest_asyncio"]


def pytest_configure(config: "pytest.Config") -> None:
    """Register custom markers used by the suite."""
    config.addinivalue_line(
        "markers",
        "integration: tests that exercise multiple components together",
    )

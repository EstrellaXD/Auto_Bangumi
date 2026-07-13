"""Keep Docker/process E2E lanes opt-in during ordinary pytest runs."""

import pytest


def pytest_collection_modifyitems(config, items):
    """Skip E2E items unless the caller supplied an E2E marker expression."""

    marker_expr = config.getoption("-m", default="")
    if "e2e" in marker_expr:
        return
    skip = pytest.mark.skip(reason="E2E tests require an explicit: pytest -m e2e")
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip)

"""Auto-loaded pytest fixture; no model or network integration."""
import pytest

from .core import REDELIVERY_ERROR_MODES, Replay


def pytest_addoption(parser):
    group = parser.getgroup("replay-twice")
    group.addoption("--replay-threads", type=int, default=8, help="concurrent delivery threads")
    group.addoption("--replay-repeats", type=int, default=1, help="trials per selected scenario")
    group.addoption("--replay-redelivery-errors", choices=REDELIVERY_ERROR_MODES, default="report",
                    help="'report' warns when the handler raised on a delivery but the effect "
                         "happened once; 'fail' fails the drill")


@pytest.fixture
def replay(request):
    return Replay(
        threads=request.config.getoption("--replay-threads"),
        repeats=request.config.getoption("--replay-repeats"),
        redelivery_errors=request.config.getoption("--replay-redelivery-errors"),
    )

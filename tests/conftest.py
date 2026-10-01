"""Test setup: a throwaway database, a fixed secret, no rate limits, and (unless a test is marked real_auth)
a signed-in test user so the engine tests can call /simulate directly."""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="reality-test-")
os.environ["REALITY_DATABASE_PATH"] = os.path.join(_tmp, "test.db")
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["SIMULATE_RATE_PER_S"] = "100000"
os.environ["ASK_RATE_PER_MIN"] = "100000"

import pytest  # noqa: E402

from app.main import app  # noqa: E402
from app.platform.auth import current_user  # noqa: E402

TEST_USER = {"id": "usr_test", "email": "test@example.com", "name": "Test", "created_at": 0.0, "google": False,
             "has_password": True}


@pytest.fixture(autouse=True)
def _signed_in(request):
    if request.node.get_closest_marker("real_auth"):
        app.dependency_overrides.pop(current_user, None)
        yield
        return
    app.dependency_overrides[current_user] = lambda: TEST_USER
    yield
    app.dependency_overrides.pop(current_user, None)

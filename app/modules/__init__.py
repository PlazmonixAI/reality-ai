"""Importing this package registers every tool.
Add one import line here for each new tool file."""
from app.modules.mathematics import algebra  # noqa: F401
from app.modules.mathematics import calculus  # noqa: F401
from app.modules.mathematics import linear_algebra  # noqa: F401
from app.modules.mathematics import numerical  # noqa: F401
from app.modules.mathematics import ode  # noqa: F401
from app.modules.physics import elements  # noqa: F401
from app.modules.physics import orbital  # noqa: F401
from app.modules.physics import propagation  # noqa: F401
from app.modules.physics import classical  # noqa: F401
from app.modules.physics import propulsion  # noqa: F401

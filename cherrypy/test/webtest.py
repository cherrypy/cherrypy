"""A deprecated web app testing helper interface."""

# for compatibility, expose cheroot webtest here
import warnings

from cheroot.test.webtest import (  # ruff: ignore[unused-import]
    interface,
    WebCase,
    cleanHeaders,
    shb,
    openURL,
    ServerError,
    server_error,
)


warnings.warn('Use cheroot.test.webtest', DeprecationWarning)

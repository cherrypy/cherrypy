"""Test module for the @-decorator syntax, which is version-specific."""

import cherrypy
from cherrypy import expose, tools


class ExposeExamples(object):
    """Exposed routes test app."""

    @expose
    def no_call(self):
        """Return a string on ``/no_call``."""
        return "Mr E. R. Bradshaw"

    @expose()
    def call_empty(self):
        """Return a string on ``/call_empty``."""
        return "Mrs. B.J. Smegma"

    @expose("call_alias")
    def nesbitt(self):
        """Return "Mr Nesbitt" on ``/call_alias``."""
        return "Mr Nesbitt"

    @expose(["alias1", "alias2"])
    def andrews(self):
        """Return a string on ``/andrews``, ``/alias1``, ``/alias2``."""
        return "Mr Ken Andrews"

    @expose(alias="alias3")
    def watson(self):
        """Return "Mr. and Mrs. Watson" on ``/watson``, ``/alias3``."""
        return "Mr. and Mrs. Watson"


class ToolExamples(object):
    """A web app with tools."""

    @expose
    # This is here to demonstrate that using the config decorator
    # does not overwrite other config attributes added by the Tool
    # decorator (in this case response_headers).
    @cherrypy.config(**{"response.stream": True})
    @tools.response_headers(headers=[("Content-Type", "application/data")])
    def blah(self):
        """Emit "Blah" on ``/blah``."""
        yield b"blah"

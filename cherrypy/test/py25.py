"""Test module for Python 2.5-specific syntax, like the @-decorator syntax."""

from cherrypy import expose


class ExposeExamples(object):
    
    @expose
    def no_call(self):
        return "Mr E. R. Bradshaw"
    
    @expose()
    def call_empty(self):
        return "Mrs. B.J. Smegma"
    
    @expose("call_alias")
    def nesbitt(self):
        return "Mr Nesbitt"
    
    @expose(["alias1", "alias2"])
    def andrews(self):
        return "Mr Ken Andrews"
    
    @expose(alias="alias3")
    def watson(self):
        return "Mr. and Mrs. Watson"



"""Base class for CherryPy filters."""

class BaseFilter(object):
    """
    Base class for filters. Derive new filter classes from this, then
    override some of the methods to add some side-effects.
    """
    
    def onStartResource(self):
        """Called before any request processing has been done"""
        pass
    
    def beforeRequestBody(self):
        """Called after the request header has been read/parsed"""
        pass
    
    def beforeMain(self):
        """ Called after the request body has been read/parsed"""
        pass
    
    def beforeFinalize(self):
        """Called before final output processing"""
        pass
    
    def beforeErrorResponse(self):
        """Called before _cpOnError and/or finalizing output"""
        pass
    
    def afterErrorResponse(self):
        """Called after _cpOnError and finalize"""
        pass
    
    def onEndResource(self):
        """Called after finalizing the output (status, header, and body)"""
        pass
    
    def onEndRequest(self):
        """Called when the server closes the request."""
        pass


"""Base class for CherryPy filters."""

class BaseFilter(object):
    """
    Base class for filters. Derive new filter classes from this, then
    override some of the methods to add some side-effects.
    """
    
    def on_start_resource(self):
        """Called before any request processing has been done"""
        pass
    
    def before_request_body(self):
        """Called after the request header has been read/parsed"""
        pass
    
    def before_main(self):
        """ Called after the request body has been read/parsed"""
        pass
    
    def before_finalize(self):
        """Called before final output processing"""
        pass
    
    def before_error_response(self):
        """Called before _cp_on_error and/or finalizing output"""
        pass
    
    def after_error_response(self):
        """Called after _cp_on_error and finalize"""
        pass
    
    def on_end_resource(self):
        """Called after finalizing the output (status, header, and body)"""
        pass
    
    def on_end_request(self):
        """Called when the server closes the request."""
        pass


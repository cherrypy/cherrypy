import cherrypy


def log_request_headers(debug=False):
    """Write request headers to the cherrypy error log."""
    h = ["  %s: %s" % (k, v) for k, v in cherrypy.serving.request.header_list]
    cherrypy.log('\nRequest Headers:\n' + '\n'.join(h), "HTTP")

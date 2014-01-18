import cherrypy


def log_hooks(debug=False):
    """Write request.hooks to the cherrypy error log."""
    request = cherrypy.serving.request

    msg = []
    # Sort by the standard points if possible.
    from cherrypy.lib import _cprequest
    points = _cprequest.hookpoints
    for k in request.hooks.keys():
        if k not in points:
            points.append(k)

    for k in points:
        msg.append("    %s:" % k)
        v = request.hooks.get(k, [])
        v.sort()
        for h in v:
            msg.append("        %r" % h)
    cherrypy.log('\nRequest Hooks for ' + cherrypy.url() +
                 ':\n' + '\n'.join(msg), "HTTP")

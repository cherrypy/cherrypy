import cherrypy
from cherrypy.lib.dispatch import Dispatcher


def VirtualHost(next_dispatcher=Dispatcher(), use_x_forwarded_host=True,
                **domains):
    """
    Select a different handler based on the Host header.

    This can be useful when running multiple sites within one CP server.
    It allows several domains to point to different parts of a single
    website structure. For example::

        http://www.domain.example  ->  root
        http://www.domain2.example  ->  root/domain2/
        http://www.domain2.example:443  ->  root/secure

    can be accomplished via the following config::

        [/]
        request.dispatch = cherrypy.dispatch.VirtualHost(
            **{'www.domain2.example': '/domain2',
               'www.domain2.example:443': '/secure',
              })

    next_dispatcher
        The next dispatcher object in the dispatch chain.
        The VirtualHost dispatcher adds a prefix to the URL and calls
        another dispatcher. Defaults to cherrypy.dispatch.Dispatcher().

    use_x_forwarded_host
        If True (the default), any "X-Forwarded-Host"
        request header will be used instead of the "Host" header. This
        is commonly added by HTTP servers (such as Apache) when proxying.

    ``**domains``
        A dict of {host header value: virtual prefix} pairs.
        The incoming "Host" request header is looked up in this dict,
        and, if a match is found, the corresponding "virtual prefix"
        value will be prepended to the URL path before calling the
        next dispatcher. Note that you often need separate entries
        for "example.com" and "www.example.com". In addition, "Host"
        headers may contain the port number.
    """
    from cherrypy.lib import httputil

    def vhost_dispatch(path_info):
        request = cherrypy.serving.request
        header = request.headers.get

        domain = header('Host', '')
        if use_x_forwarded_host:
            domain = header("X-Forwarded-Host", domain)

        prefix = domains.get(domain, "")
        if prefix:
            path_info = httputil.urljoin(prefix, path_info)

        result = next_dispatcher(path_info)

        # Touch up staticdir config. See
        # https://bitbucket.org/cherrypy/cherrypy/issue/614.
        section = request.config.get('tools.staticdir.section')
        if section:
            section = section[len(prefix):]
            request.config['tools.staticdir.section'] = section

        return result
    return vhost_dispatch
**************
Request Bodies
**************

Beginning in CherryPy 3.2, application authors have complete control over the
parsing of HTTP request entities. In short, ``cherrypy.request.body`` is now always
set to an instance of ``_cpreqbody.RequestBody``, and *that* class is a subclass
of ``_cprequest.Entity``.

Entity
======

The ``Entity`` class collects information about the HTTP request entity. When a
given entity is of MIME type "multipart", each part is parsed into its own
Entity instance, and the set of parts stored in ``entity.parts``.

Between the ``before_request_body`` and ``before_handler`` tools, CherryPy tries to
process the request body (if any) by calling ``request.body.process()`` . This uses
the ``content_type`` of the Entity to look up a suitable processor in ``Entity.processors``,
a dict. If a matching processor cannot be found for the complete Content-Type,
it tries again using the major type. For example, if a request with an entity of
type "image/jpeg" arrives, but no processor can be found for that complete type,
then one is sought for the major type "image". If a processor is still not
found, then the ``default_proc`` method of the Entity is called (which does nothing
by default; you can override this too).

CherryPy 3.2 includes processors for the "application/x-www-form-urlencoded"
type, the "multipart/form-data" type, and the "multipart" major type.
CherryPy 3.2 processes these types almost exactly as older versions. Parts are
passed as arguments to the page handler using their ``Content-Disposition.name`` if
given, otherwise in a generic "parts" argument. Each such part is either a
string, or the Part itself if it's a file. (In this case it will have ``file`` and ``filename``
attributes, or possibly a ``value`` attribute). Each Part is itself a subclass of
Entity, and has its own ``process`` method and ``processors`` dict.

There is a separate processor for the "multipart" major type which is more
flexible, and simply stores all multipart parts in ``request.body.parts`` . You can
enable it with::

    cherrypy.request.body.processors[u'multipart'] = _cpreqbody.process_multipart

in an ``on_start_resource`` tool.


Entity Attributes
-----------------

 * attempt_charsets: a list of strings, each of which should be a known
   encoding. When the Content-Type of the request body warrants it, each of the
   given encodings will be tried in order. The first one to successfully decode
   the entity without raising an error is stored as ``entity.charset``. This
   defaults to ``['utf-8']`` (plus 'ISO-8859-1' for "text/\*" types, as required by 
   `HTTP/1.1 <http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.7.1>`_), 
   but ``['us-ascii', 'utf-8']`` for multipart parts.
 * charset: the successful decoding; see "attempt_charsets" above.
 * content_type: the value of the Content-Type request header, or, if the
   Entity is part of a multipart payload, the Content-Type given in the MIME
   headers for this part.
 * default_content_type: This defines a default ``Content-Type`` to use
   if no Content-Type header is given. The empty string is used for
   the ``request.body``, which results in the request body not being read or
   parsed at all. This is by design, a missing
   ``Content-Type`` header in the HTTP request entity is an error at best,
   and a security hole at worst. For
   multipart parts, however, the MIME spec declares that a part with no
   Content-Type defaults to "text/plain" (the built-in ``Part`` class does that).
 * default_proc: a method which is run if a more-specific processor cannot be
   found for the given ``Content-Type``.
 * filename: if the entity (or part) bears a ``Content-Disposition`` header, its
   filename parameter (if any) is stored here.
 * fp: the readable socket file object.
 * fullvalue: a method which returns the ``Entity`` as a string, regardless of
   whether it is stored in a file or not.
 * headers: this is a copy of the ``request.headers`` for the ``request.body``.
   For multipart parts, it is the set of headers for that part.
 * length: the value of the ``Content-Length`` header, if provided.
 * make_file: a method which returns a file-like object in which to dump the
   entity. By default, this is ``tempfile.TemporaryFile()`` . But see ``Part.maxrambytes``, below.
 * name: the "name" parameter of the ``Content-Disposition`` header, if any.
 * params: processors for some ``Content-Type`` (e.g.
   'application/x-www-form-urlencoded' or 'multipart') attempt to parse these
   formats into a dict of params. It will be the portion of ``request.params``
   that come from the message body (sometimes called "POST params", although
   they can be sent with various HTTP method verbs).
 * parts: a list of sub-Entity instances if the ``Content-Type`` is of major type
   "multipart".
 * part_class: the class used for multipart parts. You can replace this with
   custom subclasses to alter the processing of multipart parts.
 * processors: see discussion above.
 * type: a deprecated alias for ``content_type``.

The ``request.body`` adds a couple more (which, like any ``request.body`` attribute, you can set in config):

 * bufsize: The buffer size used when reading the socket.
 * maxbytes: If more than ``maxbytes`` bytes are read from the socket, then ``MaxSizeExceeded`` is raised.

The Part subclass is used for multipart parts, and adds the following attributes:

 * boundary: the MIME multipart boundary.
 * maxrambytes: the threshold of bytes after which point the ``Part`` will store
   its data in a file (generated by the ``make_file`` method) instead of a string.
   Defaults to 1000, just like the ``cgi`` module in Python's standard library.

Custom Processors
=================

You can add your own processors for any specific or major MIME type. Simply add
it to the ``processors`` dict in a hook/tool that runs at ``on_start_resource`` or ``before_request_body``. 
Here's the built-in JSON tool for an example::

    #!python
    def json_in(force=True, debug=False):
        request = cherrypy.serving.request
        def json_processor(entity):
            """Read application/json data into request.json."""
            if not entity.headers.get(u"Content-Length", u""):
                raise cherrypy.HTTPError(411)
            
            body = entity.fp.read()
            try:
                request.json = json_decode(body)
            except ValueError:
                raise cherrypy.HTTPError(400, 'Invalid JSON document')
        if force:
            request.body.processors.clear()
            request.body.default_proc = cherrypy.HTTPError(
                415, 'Expected an application/json content type')
        request.body.processors[u'application/json'] = json_processor

We begin by defining a new ``json_processor`` function to stick in the ``processors``
dictionary. All processor functions take a single argument, the ``Entity`` instance
they are to process. It will be called whenever a request is received (for those
URI's where the tool is turned on) which has a ``Content-Type`` of
"application/json".

First, it checks for a valid ``Content-Length`` (raising 411 if not valid), then
reads the remaining bytes on the socket. The ``fp`` object knows its own length, so
it won't hang waiting for data that never arrives. It will return when all data
has been read. Then, we decode those bytes using Python's built-in ``json`` module,
and stick the decoded result onto ``request.json`` . If it cannot be decoded, we
raise 400.

If the "force" argument is True (the default), the ``Tool`` clears the ``processors``
dict so that request entities of other ``Content-Types`` aren't parsed at all. Since
there's no entry for those invalid MIME types, the ``default_proc`` method of ``cherrypy.request.body``
is called. But this does nothing by default (usually to provide the page handler an opportunity to handle it.)
But in our case, we want to raise 415, so we replace ``request.body.default_proc``
with the error (``HTTPError`` instances, when called, raise themselves).

If we were defining a custom processor, we can do so without making a ``Tool``. Just add the config entry::

    request.body.processors = {u'application/json': json_processor}

Note that you can only replace the ``processors`` dict wholesale this way, not update the existing one.

# this file contains built in error pages

# this is code borrowed from python2.4's string module
####################################################################
import re as _re

class _multimap:
    """Helper class for combining multiple mappings.

    Used by .{safe_,}substitute() to combine the mapping and keyword
    arguments.
    """
    def __init__(self, primary, secondary):
        self._primary = primary
        self._secondary = secondary

    def __getitem__(self, key):
        try:
            return self._primary[key]
        except KeyError:
            return self._secondary[key]


class _TemplateMetaclass(type):
    pattern = r"""
    %(delim)s(?:
      (?P<escaped>%(delim)s) |   # Escape sequence of two delimiters
      (?P<named>%(id)s)      |   # delimiter and a Python identifier
      {(?P<braced>%(id)s)}   |   # delimiter and a braced identifier
      (?P<invalid>)              # Other ill-formed delimiter exprs
    )
    """

    def __init__(cls, name, bases, dct):
        super(_TemplateMetaclass, cls).__init__(name, bases, dct)
        if 'pattern' in dct:
            pattern = cls.pattern
        else:
            pattern = _TemplateMetaclass.pattern % {
                'delim' : _re.escape(cls.delimiter),
                'id'    : cls.idpattern,
                }
        cls.pattern = _re.compile(pattern, _re.IGNORECASE | _re.VERBOSE)


class Template:
    """A string class for supporting $-substitutions."""
    __metaclass__ = _TemplateMetaclass

    delimiter = '$'
    idpattern = r'[_a-z][_a-z0-9]*'

    def __init__(self, template):
        self.template = template

    # Search for $$, $identifier, ${identifier}, and any bare $'s

    def _invalid(self, mo):
        i = mo.start('invalid')
        lines = self.template[:i].splitlines(True)
        if not lines:
            colno = 1
            lineno = 1
        else:
            colno = i - len(''.join(lines[:-1]))
            lineno = len(lines)
        raise ValueError('Invalid placeholder in string: line %d, col %d' %
                         (lineno, colno))

    def substitute(self, *args, **kws):
        if len(args) > 1:
            raise TypeError('Too many positional arguments')
        if not args:
            mapping = kws
        elif kws:
            mapping = _multimap(kws, args[0])
        else:
            mapping = args[0]
        # Helper function for .sub()
        def convert(mo):
            # Check the most common path first.
            named = mo.group('named') or mo.group('braced')
            if named is not None:
                val = mapping[named]
                # We use this idiom instead of str() because the latter will
                # fail if val is a Unicode containing non-ASCII characters.
                return '%s' % val
            if mo.group('escaped') is not None:
                return self.delimiter
            if mo.group('invalid') is not None:
                self._invalid(mo)
            raise ValueError('Unrecognized named group in pattern',
                             self.pattern)
        return self.pattern.sub(convert, self.template)

    def safe_substitute(self, *args, **kws):
        if len(args) > 1:
            raise TypeError('Too many positional arguments')
        if not args:
            mapping = kws
        elif kws:
            mapping = _multimap(kws, args[0])
        else:
            mapping = args[0]
        # Helper function for .sub()
        def convert(mo):
            named = mo.group('named')
            if named is not None:
                try:
                    # We use this idiom instead of str() because the latter
                    # will fail if val is a Unicode containing non-ASCII
                    return '%s' % mapping[named]
                except KeyError:
                    return self.delimiter + named
            braced = mo.group('braced')
            if braced is not None:
                try:
                    return '%s' % mapping[braced]
                except KeyError:
                    return self.delimiter + '{' + braced + '}'
            if mo.group('escaped') is not None:
                return self.delimiter
            if mo.group('invalid') is not None:
                return self.delimiter
            raise ValueError('Unrecognized named group in pattern',
                             self.pattern)
        return self.pattern.sub(convert, self.template)

_defaultStyle ='''
    <style type="text/css">
    .poweredBy {
        margin-top: 20px;
        border-top: 2px solid black;
    }

    #traceback {
        color: red;
    }
    </style>
'''

_defaultTemplate = Template('''<?xml version="1.0" encoding="$encoding"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html>
<head>
    <title>$errorString</title>
    $style
</head>
    <body>
        <h2>$errorString</h2>
        <p>$message</p>
        <pre id="traceback">$traceback</pre>
    <div class="poweredBy">
    <span>Powered by <a href="http://www.cherrypy.org">CherryPy $version</a></span>
    </div>
    </body>
</html>
''')

import cherrypy

import BaseHTTPServer
_httpResponses = BaseHTTPServer.BaseHTTPRequestHandler.responses

_templateDefaults = {
        'encoding' : 'UTF-8',
        'message'  : 'There was an error',
        'traceback' : '',
        'referer' : '',
        'requestPath' : ''
    }

def getErrorPage(status, customTrace = None, customMessage = None):
    statusString, message = _httpResponses[status]
    if customMessage is not None:
        message = customMessage

    statusString = '%d %s' % (status, statusString)
    
    templateData = _templateDefaults.copy()
    
    templateData['errorString'] = statusString
    templateData['message'] = message
    
    templateData['requestPath'] = cherrypy.request.path
    templateData['version'] = cherrypy.__version__

    style = cherrypy.config.get('httperror.style', _defaultStyle)
    templateData['style'] = style
    
    if customTrace:
        templateData['traceback'] = customTrace
    else:
        defaultOn = (cherrypy.config.get('server.environment') == 'development')
        if cherrypy.config.get('server.showTracebacks', defaultOn):
            templateData['traceback'] = cherrypy._cputil.formatExc()
    page = _defaultTemplate.safe_substitute(templateData)
    return statusString, page

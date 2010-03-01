******************************
Choosing a templating language
******************************

CherryPy is an open-ended HTTP framework that integrates with a wide variety of
templating systems. So the first point we want to make is that you should do
your own study *with your own data* to find out which one is best for you.

That said, we recommend you start with one of these three:

`Mako <http://www.makotemplates.org/>`_
=======================================

Mako is a template library written in Python. It provides a familiar, non-XML
syntax which compiles into Python modules for maximum performance. Mako's syntax
and API borrows from the best ideas of many others, including Django templates,
Cheetah, Myghty, and Genshi. Conceptually, Mako is an embedded Python (i.e.
Python Server Page) language, which refines the familiar ideas of componentized
layout and inheritance to produce one of the most straightforward and flexible
models available, while also maintaining close ties to Python calling and
scoping semantics.

Mako snippet::

    <table>
        % for row in rows:
            ${makerow(row)}
        % endfor
    </table>


CherryPy integration example::

    import cherrypy
    from mako.template import Template
    from mako.lookup import TemplateLookup
    lookup = TemplateLookup(directories=['html'])
    
    class Root:
        @cherrypy.expose
        def index(self):
            tmpl = lookup.get_template("index.html")
            return tmpl.render(salutation="Hello", target="World")


`Jinja2 <http://jinja.pocoo.org/2/>`_
=====================================

Jinja2 is a library for Python 2.4 and onwards that is designed to be flexible,
fast and secure. If you have any exposure to other text-based template languages,
such as Smarty or Django, you should feel right at home with Jinja2. It’s both
designer and developer friendly by sticking to Python’s principles and adding
functionality useful for templating environments.

The key-features are...

 * ... configurable syntax. If you are generating LaTeX or other formats with
   Jinja2 you can change the delimiters to something that integrates better
   into the LaTeX markup.
 * ... fast. While performance is not the primarily target of Jinja2 it’s
   surprisingly fast. The overhead compared to regular Python code was reduced
   to the very minimum.
 * ... easy to debug. Jinja2 integrates directly into the python traceback
   system which allows you to debug Jinja2 templates with regular python
   debugging helpers.
 * ... secure. It’s possible to evaluate untrusted template code if the optional
   sandbox is enabled. This allows Jinja2 to be used as templating language for
   applications where users may modify the template design.

Jinja2 snippet::

    <ul id="navigation">
    {% for item in navigation %}
        <li><a href="{{ item.href }}">{{ item.caption }}</a></li>
    {% endfor %}
    </ul>


CherryPy integration example::

    import cherrypy
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader('templates'))
    
    class Root:
        @cherrypy.expose
        def index(self):
            tmpl = env.get_template('index.html')
            return tmpl.render(salutation='Hello', target='World')


`Genshi <http://genshi.edgewall.org>`_
=======================================

Genshi is a Python library that provides an integrated set of components for
parsing, generating, and processing HTML, XML or other textual content for
output generation on the web.

The main feature is a template language that is smart about markup: unlike
conventional template languages that only deal with bytes and (if you're lucky)
characters, Genshi knows the difference between tags, attributes, and actual
text nodes, and uses that knowledge to your advantage.

Plain XHTML templates make Genshi easy to use even for web designers who don't
know Python. Do you know XHTML? Then you're 75% of the way there! It's
considered by many to be the successor to Kid.

See the `Genshi tutorial <http://tools.cherrypy.org/wiki/Genshi>`_.

Because it parses HTML/XML, it can be slower than other solutions.
See `Genshi performance <http://genshi.edgewall.org/wiki/GenshiPerformance>`_
for more information.

Genshi snippet::

    <ol py:if="links">
      <li py:for="link in links">
        <a href="${link.url}">${link.title}</a>
        posted by ${link.username} at ${link.time.strftime('%x %X')}
      </li>
    </ol>

CherryPy integration example::

    import cherrypy
    from genshi.template import TemplateLoader
    loader = TemplateLoader('/path/to/templates', auto_reload=True)
    
    class Root:
        @cherrypy.expose
        def index(self):
            tmpl = loader.load('index.html')
            page = tmpl.generate(salutation='Hello', target='World')
            return page.render('html', doctype='html')


Others
======

 * Cheetah
 * ClearSilver
 * Kid
 * HTMLTemplate
 * Nevow
 * PSP
 * PyMeld
 * py.xml
 * XSLT
 * Xyaptu
 * ZPT


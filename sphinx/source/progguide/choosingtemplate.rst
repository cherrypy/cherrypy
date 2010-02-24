.. _ChoosingATemplatingLanguage:

******************************
Choosing a templating language
******************************

CherryPy is an open-ended Web framework that integrates with a wide variety of templating systems. This document is to help you choose which one is right for you.

Cheetah
=======

.. tabularcolumns:: |l|c|l|

================= ================ ================
Feature           Supported        Comment
================= ================ ================
Caching           [X]              You can compile templates into python classes.
Speed             moderate         Not a speed demon. But critical part of the library (the namemapper) is also available as binary for linux, windows and makes for great performance improvement
Wysiwyg           [ ]              No. Use any text editor  
Flexibility       Great
Pythonic design   [X]              Very much so, it can use python constructs in the template
Pure python       Yes
XML Syntax        [ ]              Thank heavens no!
Language elements                  See the `Cheetah <http://www.cheetahtemplate.org/>`_ docs
Learning curve    very short
Community         Large
Summary:                           Cheetah is one of the simplest and most comprehensive templating engines you'll find. Excellent documentation.
================= ================ ================



ClearSilver
===========

====================  ============  ==================
Feature               Supported     Comment
====================  ============  ==================
Caching               [ ]           
Speed                               ''Untested, we don't have a benchmark yet''     
Wysiwyg               [ ]           No. Use any text editor     
Targets               All       
Flexibility           Great           
Pythonic design       []            Written in c, includes drivers for python, ruby, perl, and java     
CherryPy Integration  []           
Pure python           No           
XML Syntax            [X]           
Language elements                   See the `ClearSilver <http://www.clearsilver.net/docs/>`_ docs     
Learning curve        short           
Community             Small           
i18n                  [ ]           
Summary:                            ClearSilver uses a dataset driven approach which completely separates layout and application logic.     
====================  ============  ==================

`Genshi <http://genshi.edgewall.org>`_
=======================================

See the `Genshi tutorial <http://tools.cherrypy.org/wiki/Genshi>`_.

==================== =============== ==================
Feature              Supported       Comment    
==================== =============== ==================
Caching              [X]             
Speed                                `Genshi performance <http://genshi.edgewall.org/wiki/GenshiPerformance>`_
WYSIWYG              [X]             If you're using a XHTML Compliant WYSIWYG editor.
Targets              XML or Text     Only used for outputting structured text files or XML based files such as XHTML 
Flexibility          Great           
Pythonic design      [X]          
CherryPy Integration [X]             `Genshi Tutorial with CherryPy <http://genshi.edgewall.org/wiki/GenshiTutorial>`_
Pure python          [X]           
XML Syntax           [X]             XHTML + additional namespaces     
Language elements                    XHTML + additional tags and inline Python.  See `Genshi's Documentation <http://genshi.edgewall.org/wiki/Documentation/index.html>`_.
Learning curve       short           Do you know XHTML?  Then you're 75% of the way there!
Community            Growing         Trac and `TurboGears <http://www.turbogears.org/>`_ (via `ToscaWidgets <http://toscawidgets.org/>`_) are both moving to Genshi.
i18n                 [X]             
Summary:                             Plain XHTML templates make Genshi easy to use even for web designers who don't know Python.  Its considered by many to be the successor to Kid.
==================== =============== ==================

Kid
===

HTMLTemplate
============

Nevow
=====

PSP
===

PyMeld
======

===================== ========== ===============
Feature               Supported  Comment       
===================== ========== ===============
Caching               [ ]        Left to the user.      
Speed                            ''Untested, we don't have a benchmark yet''     
Wysiwyg               [X]        Templates are pure HTML/XHTML and can contain dummy content     
Targets               All       
Flexibility                      HTML-ish markup only. No other formats.           
Pythonic design       [X]        Very.     
CherryPy Integration  [ ]           
Pure python           Yes           
XML Syntax            [ ]        Not really. Relies on "id" attributes in HTML/XHTML.     
Language elements                See the `PyMeld docs <http://www.entrian.com/PyMeld/>`_     
Learning curve                   Gentle and short            
Community                        `None <http://www.google.com/search?q=%22pymeld+users%22>`_           
i18n                  [ ]        Left to user      
Summary:                         Elegant and unique tool for manipulating HTML in a Pythonic way. Any (X)HTML element with an "id" attribute can be manipulated -- including cloning, deletion, or attribute changing.     
===================== ========== ===============


XSLT
====

===================== ============== =====================
Feature               Supported      Comment       
===================== ============== =====================
Caching               [ ]            None but the Picket filter has a basic cache.      
Speed                                ''Untested, we don't have a benchmark yet''     
Wysiwyg               [ ]            No. Use any text editor or specific XSL editor     
Targets               All       
Flexibility           Great           
Pythonic design       [ ]            It's totally language/platform independent     
CherryPy Integration  [X]            [wiki:Picket Picket] is a filter implementation using the `4Suite <http://4suite.org>`_ framework     
Pure python           No           
XML Syntax            [X]           
Language elements                    See the `XSLT <http://www.w3.org/TR/xslt>`_ doc     
Learning curve        Depends on you XSLT is quite a big beast but you will find plenty of documentation      
Community             Big           
i18n                  [X]           
Summary:                             It's a standard. XSLT is fantastic if you are mainly using XML documents. It's also totally language and platform independent and therefore you will not have to learn a new templating language if you change your programming language.    
===================== ============== =====================

Xyaptu
======

===================== ============== =====================
Feature               Supported      Comment       
===================== ============== =====================
Caching               [ ]            Only if there is a !DoneByMyselfImplementation. - xyaptu is a templating unit, nothing more..      
Speed                                ''Untested, we don't have a benchmark yet''     
Wysiwyg               [ ]            Nope: Nano, vim, emacs, notepad.... but by using xmlstyle tags, the language is designed not to interfere with graphical design software (as long as this software will also leave in unknown tags that is)    
Targets               anything       Whether it be javascript, xml, html, python, csv or whatever you want. 
Flexibility           no complaints  Loops, conditions, not target language dependent     
Pythonic design       [X]            Using dictionaries, tuples, strings and generators     
CherryPy Integration  [X]            There is a filter built on top of CherryPy, including samples etc     
Pure python           [X]            all the way. 3 modules: the Filter, Xyaptu and Yaptu - works everywhere     
Language elements     7              See the XyaptuFilter, subsection Markup-syntax     
Learning curve        curve?         Hardly any. The filter might be the toughest part (say, 5 minutes?)      
Community             Tiny           Too bad, but it's the truth     
i18n                  [X]            not using the i18n module though. Xyaptu is based on Document Name Spaces, this is a regular dictionary. The keys are in your template, and will be replaced with the values in this dictionary. So having multiple dictionaries (one for each language) is enough.. It's not perfect, but at least it's something usefull :)      
Summary:                             see: XyaptuFilter [[br]] Xyaptu stands for: eXtended  Yet Another Python Templating Unit    
===================== ============== =====================

ZPT
===

===================== ============== =====================
Feature               Supported      Comment       
===================== ============== =====================
Caching               [ ]            ''Unknown''          
Speed                 [ ]          
WYSIWYG               [ ]            XHTML can be edited in a WYSIWYG editor, with scripting is placed in an XML namespace for tags and attributes     
Targets               XML            Includes XHTML and other XML formats (SVG, MathML, etc.)    
Pythonic design       [ ]          
Flexibility               
CherryPy Integration               
Pure Python           [X]          
 XML Syntax           [X]           
Language Elements                    See `ZPT Documentation <http://www.zope.org/Documentation/Books/ZopeBook/2_6Edition/AppendixC.stx>`_     
Learning Curve        Medium         Learning curve depends on knowledge of Python and XML    
Community             Medium         `Zope <http://www.zope.org/>`_ depends on ZPT, so community support is readily available.     
i18n                  Unknown        i18n features are available in the Zope framework, but may not work outside of Zope.     
Summary                              Zope Page Templates are relatively easy for web designers to edit without disturbing scripting already embedded in the page. The basic syntax tends to be clean and simple, while more complex tasks are possible. However, ZPT can only be used with XML documents, not other text-based documents such as CSS or JavaScript.     
===================== ============== =====================

py.xml
======

===================== ============== =====================
Feature               Supported      Comment       
===================== ============== =====================
Caching               [ ]            ''None''          
Speed                 [ ]          
WYSIWYG               [ ]            No. Use any text editor     
Targets               XML            Includes XHTML and other XML formats (SVG, MathML, etc.)    
Pythonic design       [X]            py.xml is designed to be a Python to generating XML     
Flexibility               
CherryPy Integration               
Pure Python           [X]          
 XML Syntax           [ ]            No. All code is generated with Python calls     
Language Elements               
Learning Curve        None           If you can do Python you can do py.xml     
Community             Unknown           
i18n                  None           You will have to provide i18n yourself     
Summary                              The py lib offers a pythonic way to generate xml/html, based on ideas from xist which uses python class objects to build xml trees. However, xist's implementation is somewhat heavy because it has additional goals like transformations and supporting many namespaces. But its basic idea is very easy.     
===================== ============== =====================

Old/Unmaintained
================

CherryTemplate
--------------

See http://cherrytemplate.python-hosting.com/

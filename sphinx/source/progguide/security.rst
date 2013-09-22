********************************
Securing CherryPy
********************************

There are several settings that can be enabled to make CherryPy pages more secure. These include:

    Transmitting data:

        #. Use Secure Cookies

    Rendering pages:

        #. Set HttpOnly cookies
        #. Set XFrame options
        #. Enable XSS Protection
        #. Set the Content Security Policy

An easy way to accomplish this is to set headers with a :doc:`Tool </tutorial/tools>` and wrap your entire CherryPy application with it::

    import cherrypy

    def secureheaders():
        headers = cherrypy.response.headers
        headers['X-Frame-Options'] = 'DENY'
        headers['X-XSS-Protection'] = '1; mode=block'
        headers['Content-Security-Policy'] = "default-src='self'"

    # set the priority according to your needs if you are hooking something
    # else on the 'before_finalize' hook point.
    cherrypy.tools.secureheaders = \
        cherrypy.Tool('before_finalize', secureheaders, priority=60)


Then, in the :doc:`configuration file </tutorial/config>` (or any other place that you want to enable the tool)::

    [/]
    tools.secureheaders.on = True


If you use :doc:`sessions </refman/lib/sessions>` you can also enable these settings::

    [/]
    tools.sessions.on = True
    # increase security on sessions
    tools.session.secure = True
    tools.sessions.httponly = True


If you use SSL you can also enable Strict Transport Security::

    # add this to secureheaders():
    # only add Strict-Transport headers if we're actually using SSL; see the ietf spec
    # "An HSTS Host MUST NOT include the STS header field in HTTP responses
    # conveyed over non-secure transport"
    # http://tools.ietf.org/html/draft-ietf-websec-strict-transport-sec-14#section-7.2
    if (cherrypy.server.ssl_certificate != None and cherrypy.server.ssl_private_key != None):
        headers['Strict-Transport-Security'] = 'max-age=31536000' # one year


Using Secure Socket Layers (SSL)
================================

CherryPy can encrypt connections using SSL to create an https connection. This keeps your web traffic secure. Here's how.

1. Generate a private key. We'll use openssl and follow the `OpenSSL Keys HOWTO <https://www.openssl.org/docs/HOWTO/keys.txt>`_.::

    $ openssl genrsa -out privkey.pem 2048

You can create either a key that requires a password to use, or one without a password. Protecting your private key with a password is much more secure, but requires that you enter the password every time you use the key. For example, you may have to enter the password when you start or restart your CherryPy server. This may or may not be feasible, depending on your setup.

If you want to require a password, add one of the ``-aes128``, ``-aes192`` or ``-aes256`` switches to the command above. You should not use any of the DES, 3DES, or SEED algoritms to protect your password, as they are insecure.

SSL Labs recommends using 2048-bit RSA keys for security (see references section at the end).


2. Generate a certificate. We'll use openssl and follow the `OpenSSL Certificates HOWTO <https://www.openssl.org/docs/HOWTO/certificates.txt>`_. Let's start off with a self-signed certificate for testing::

    $ openssl req -new -x509 -days 365 -key privkey.pem -out cert.pem

openssl will then ask you a series of questions. You can enter whatever values are applicable, or leave most fields blank. The one field you *must* fill in is the 'Common Name': enter the hostname you will use to access your site. If you are just creating a certificate to test on your own machine and you access the server by typing 'localhost' into your browser, enter the Common Name 'localhost'.


3. Decide whether you want to use python's built-in SSL library, or the pyOpenSSL library. CherryPy supports either.

    a) *Built-in.* To use python's built-in SSL, add the following line to your CherryPy config::

        cherrypy.server.ssl_module = 'builtin'

    b) *pyOpenSSL*. Because python did not have a built-in SSL library when CherryPy was first created, the default setting is to use pyOpenSSL. To use it you'll need to install it::

        $ pip install pyOpenSSL


4. Add the following lines in your CherryPy config to point to your certificate files::
    
    cherrypy.server.ssl_certificate = "cert.pem"
    cherrypy.server.ssl_private_key = "privkey.pem"


5. Start your CherryPy server normally. Note that if you are debugging locally and/or using a self-signed certificate, your browser may show you security warnings.



Further Security Resources
==========================

* For an introduction to webserver security see `Dan Callahan's presentation from PyCon CA 2013 <http://pyvideo.org/video/2315/quick-wins-for-better-website-security>`_.
* SSL Labs: `SSL/TLS Deployment Best Practises <https://www.ssllabs.com/projects/best-practices/>`_


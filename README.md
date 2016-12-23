# CherryPy

[![CherryPy Build Status](https://travis-ci.org/cherrypy/cherrypy.svg?branch=master)](https://travis-ci.org/cherrypy/cherrypy) [![Codacy Badge](https://api.codacy.com/project/badge/Grade/48b11060b5d249dc86e52dac2be2c715)](https://www.codacy.com/app/webknjaz/cherrypy-upstream?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=cherrypy/cherrypy&amp;utm_campaign=Badge_Grade)

Welcome to the GitHub-repository of [CherryPy](http://cherrypy.org/)!

CherryPy is a pythonic, object-oriented HTTP framework.

1. It allows building web applications in much the same way one would build any other object-oriented program.
2. This results in less and more readable code being developed faster. It's all just properties and methods.
3. It is now more than ten years old and has proven fast and very stable.
4. It is being used in production by many sites, from the simplest to the most demanding.
5. And perhaps most importantly, it is fun to work with :-)

Here's how easy it is to write "Hello World" in CherryPy:
```python
import cherrypy

class HelloWorld(object):
    @cherrypy.expose
    def index(self):
        return "Hello World!"

cherrypy.quickstart(HelloWorld())
```

And it continues to work that intuitively when systems grow, allowing for the Python object model to be dynamically presented as a web site and/or API.

### Table of contents
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->


- [Help](#help)
    - [I don't understand the documentation](#i-dont-understand-the-documentation)
    - [I have a question](#i-have-a-question)
    - [I have found a bug](#i-have-found-a-bug)
    - [I have a feature request](#i-have-a-feature-request)
    - [I want to discuss CherryPy, reach out to developers or CherryPy users users](#i-want-to-discuss-cherrypy-reach-out-to-developers-or-cherrypy-users)
- [Documentation](#documentation)
- [Installation](#installation)
  - [Pip](#pip)
  - [Source](#source)
- [Development](#development)
  - [Contributing](#contributing)
  - [Testing](#testing)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Help

What are my options if I feel I need help?

### I don't understand the documentation
While CherryPy is one of the easiest and most intuitive frameworks out there, the prerequisite for understanding the [CherryPy documentation](http://docs.cherrypy.org/en/latest/) is that you have a general understanding of Python and web development.

So if you have that, and still cannot understand the documentation, it is probably not your fault.
[Please create an issue](https://github.com/cherrypy/cherrypy/issues/new) in those cases.

### I have a question
If you have a question and cannot find an answer for it in issues or the the [documentation](http://docs.cherrypy.org/en/latest/), [please create an issue](https://github.com/cherrypy/cherrypy/issues/new).

Questions and their answers have great value for the community, and a tip is to really put the effort in and write a good explanation, you will get better and quicker answers.
Examples are strongly encouraged.

### I have found a bug
If no one have already, [create an issue](https://github.com/cherrypy/cherrypy/issues/new).
Be sure to provide ample information, remember that any help won't be better than your explanation.

Unless something is very obviously wrong, you are likely to be asked to provide a working example, displaying the erroneous behaviour.

<i>Note: While this might feel troublesome, a tip is to always make a separate example that have the same dependencies as your project. It is <b>great for troubleshooting</b> those annoying problems where you don't know if the problem is at your end or the components. Also, you can then easily fork and provide as an example.<br />
You will get answers and resolutions way quicker. Also, many other open source projects require it.</i>

### I have a feature request
[Good stuff! Please create an issue!](https://github.com/cherrypy/cherrypy/issues/new)<br />
<i>Note: Features are more likely to be added the more users they seem to benefit.</i>

### I want to discuss CherryPy, reach out to developers or CherryPy users
[The gitter page](https://gitter.im/cherrypy/cherrypy) is good for when you want to talk, but doesn't feel that the discussion has to be indexed for posterity.

# Documentation

* The official user documentation of CherryPy is at: http://docs.cherrypy.org/en/latest/
* Tutorials are included in the repository: https://github.com/cherrypy/cherrypy/tree/master/cherrypy/tutorial
* A general wiki at(will be moved to github): https://bitbucket.org/cherrypy/cherrypy/wiki/Home
* Plugins are described at: http://tools.cherrypy.org/

# Installation

To install CherryPy for use in your project, follow these instructions:

## From the PyPI package

```sh
pip install cherrypy
```
or (for python 3)
```sh
pip3 install cherrypy
```

## From source

Change to the directory where setup.py is located and type (Python 2.6 or later needed):
```sh
python setup.py install
```

# Development

## Contributing

Please follow the [contribution guidelines](https://github.com/cherrypy/cherrypy/blob/master/CONTRIBUTING.txt).
And by all means, [absorb the Zen of CherryPy](https://bitbucket.org/cherrypy/cherrypy/wiki/ZenOfCherryPy).

## Testing
* To run the regression tests, first install tox:
```sh
pip install tox
```
then run it
```sh
tox
```
* To run individual tests type:
```sh
tox -- -k test_foo
```

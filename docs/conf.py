#!/usr/bin/env python3
# -*- coding: utf-8 -*-

extensions = ['sphinx.ext.autodoc', 'jaraco.packaging.sphinx', 'rst.linker']

master_doc = "index"

link_files = {
    '../CHANGES.rst': dict(
        using=dict(GH='https://github.com'),
        replace=[
            dict(
                pattern=r'(Issue #|\B#)(?P<issue>\d+)',
                url='{package_url}/issues/{issue}',
            ),
            dict(
                pattern=r'(?m:^((?P<scm_version>v?\d+(\.\d+){1,2}))\n[-=]+\n)',
                with_scm='{text}\n{rev[timestamp]:%d %b %Y}\n',
            ),
            dict(
                pattern=r'PEP[- ](?P<pep_number>\d+)',
                url='https://peps.python.org/pep-{pep_number:0>4}/',
            ),
        ],
    )
}

# Be strict about any broken references:
nitpicky = True

# Include Python intersphinx mapping to prevent failures
# jaraco/skeleton#51
extensions += ['sphinx.ext.intersphinx']
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}

extensions += [
    # Stdlib extensions:
    'sphinx.ext.extlinks',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    # Third-party extensions:
    'sphinxcontrib.apidoc',
]


# TODO: generate these from project settings
class urls:
    github = 'https://github.com'
    github_repo = f'{github}/cherrypy/cherrypy'
    cheroot_github_repo = f'{github}/cherrypy/cheroot'


extlinks = {
    'issue': (f'{urls.github_repo}/issues/%s', '#'),
    'pr': (f'{urls.github_repo}/pull/%s', 'PR #'),
    'commit': (f'{urls.github_repo}/commit/%s', ''),
    'cr-issue': (f'{urls.cheroot_github_repo}/issues/%s', 'Cheroot #'),
    'cr-pr': (f'{urls.cheroot_github_repo}/pull/%s', 'Cheroot PR #'),
    'gh': (f'{urls.github}/%s', 'GitHub: '),
    'user': (f'{urls.github}/sponsors/%s', '@'),
}

intersphinx_mapping.update(
    {
        'cheroot': ('https://cheroot.cherrypy.dev/en/latest/', None),
        'pytest-docs': ('https://docs.pytest.org/en/latest/', None),
    }
)


# -- Options for LaTeX output --------------------------------------------

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author,
# documentclass [howto/manual]).
latex_documents = [
    (
        'index',
        'CherryPy.tex',
        'CherryPy Documentation',
        'CherryPy Team',
        'manual',
    ),
]


# TODO: move this to a plugin
def mock_pywin32():
    """Mock pywin32 module.

    Resulting in Linux hosts, including ReadTheDocs,
    and other environments that don't have pywin32 can generate the docs
    properly including the PDF version.
    See:
    http://read-the-docs.readthedocs.org/en/latest/faq.html#i-get-import-errors-on-libraries-that-depend-on-c-modules
    """
    import contextlib
    import importlib
    import sys

    with contextlib.suppress(ImportError):
        importlib.import_module('win32api')
        return

    from unittest import mock

    MOCK_MODULES = [
        'win32api',
        'win32con',
        'win32event',
        'win32service',
        'win32serviceutil',
    ]
    for mod_name in MOCK_MODULES:
        sys.modules[mod_name] = mock.MagicMock()


mock_pywin32()


# Ref: https://github.com/python-attrs/attrs/pull/571/files\
#      #diff-85987f48f1258d9ee486e3191495582dR82
default_role = 'any'


# -- Options for apidoc extension ----------------------------------------

apidoc_excluded_paths = []
apidoc_extra_args = [
    '--implicit-namespaces',
    '--private',  # include “_private” modules
]
apidoc_module_dir = '../cherrypy'
apidoc_module_first = False
apidoc_output_dir = 'pkg'
apidoc_separate_modules = True
apidoc_toc_file = None

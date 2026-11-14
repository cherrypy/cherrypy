# Naming the Ducks

Canonical names for this project, and how to refer to it in
prose. Other files in `.agents-ctx/` (and any generated content)
should say "the project" rather than hardcoding one of these --
reach for a specific name only when the distinction actually
matters (e.g. citing a package, an import, or a repository URL).

## Distribution / PyPI name: `CherryPy`

The installable, published name -- recorded in
`pyproject.toml`'s `[project].name` per PEP 621. This is also
the preferred way to refer to the project by name in prose.
Packaging tools normalize it to `cherrypy` -- that's the same
distribution.

## Python import name: `cherrypy`

`import cherrypy` is what code actually imports. The test suite
ships inside it, as `cherrypy.test`.

## GitHub repository slug: `cherrypy/cherrypy`

Use it verbatim when it's actually the repository being
referenced (URLs, `gh` invocations, PR/issue citations) -- not as
a stand-in for the project's name in prose.

## Don't confuse it with Cheroot

Cheroot, published from `cherrypy/cheroot`, is the HTTP server
CherryPy runs on, and its test helpers back CherryPy's web tests.
The two live in separate repositories and are released
separately. Say which one is meant.

# Naming the Ducks

Canonical names for this project, and how to refer to it in
prose. Other files in `.agents-ctx/` (and any generated content)
should say "the project" rather than hardcoding one of these --
reach for a specific name only when the distinction actually
matters (e.g. citing a package, an import, or a repository URL).

## Distribution / PyPI name: `ansible-pylibssh`

The installable, published name -- recorded in
`pyproject.toml`'s `[project].name` per PEP 621. This is also
the preferred way to refer to the project by name in prose.

## Python import name: `pylibsshext`

`import pylibsshext` is what code actually imports.
Long-standing and unlikely to change without a dedicated,
long-term migration effort -- don't "fix" it opportunistically.

## GitHub repository slug: `ansible/pylibssh`

Close to, but not the same as, the distribution name above. Use
it verbatim when it's actually the repository being referenced
(URLs, `gh` invocations, PR/issue citations) -- not as a
stand-in for the project's name in prose.

## Don't say bare `pylibssh`

`pylibssh` on its own is just the default local directory name
from a `git clone`d checkout -- nothing more. It's a common but
incorrect shorthand; prefer `ansible-pylibssh` instead.

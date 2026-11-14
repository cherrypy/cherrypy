# House Style

Grounded in the maintainer's review history and merged commits
(PR numbers below are from `ansible/pylibssh`), plus explicit
maintainer conventions carried across projects — not guesses.

## No new `@`-syntax in memory files

Do not introduce additional Claude `@`-mention/import syntax inside
any file under `.agents-ctx/`. The existing chain (`CLAUDE.md` ->
`AGENTS.md` -> `.agents-ctx/HOUSE_RULES.md`) is the only sanctioned
use of `@`-imports.

`@`-mentions load eagerly, at the start of every session, whether
or not the content ends up being relevant. Everything reachable
from `HOUSE_RULES.md` onward links to further material with plain
Markdown links instead, so an agent can pull it into context on
demand -- when a task actually needs it -- rather than having the
whole tree pollute the context window up front.

## Structural constraints

- No `setup.py`. Packaging metadata is declarative; don't
  reintroduce an imperative build script.
- No `tests/__init__.py`. Pytest must not promote the project
  root into `sys.path` via package discovery.

Here: `setup.py` was dropped in `b08a7fd4`. The metadata lives in
the PEP 621 `[project]` table of `pyproject.toml` (see
[NAMING_THE_DUCKS.md](NAMING_THE_DUCKS.md)).

## Python

- `typing` is aliased as `_t` (see [PR_HYGIENE.md](PR_HYGIENE.md)),
  `collections.abc` as `_c`.
- Tuples for fixed-size sequences such as command arguments or
  `parametrize` values; lists only where something needs to
  mutate them, or where a tool documents a list as its
  convention (e.g. `pytest_plugins`).
- Single quotes for inline strings, triple-double quotes for
  multi-line strings.
- `from __future__ import annotations` in every *new* `.py`
  module. Don't add it to existing modules as a side effect of an
  unrelated change, and not in Cython sources.
- Compose shell commands as argument sequences, or with
  `shlex.join` when a string is unavoidable. Never `shell=True`,
  never raw string concatenation into a subprocess.
- Sphinx-native docstrings -- `:param X:`, `:returns:`,
  `:raises X:`. Not Google, not Napoleon, not NumPy.

Here: quotes and `parametrize` tuples are enforced by
`.ruff.toml`, and the docstring style by `.darglint`. The Cython
sources and the libssh C API they wrap have conventions of their
own -- see [CYTHON_AND_LIBSSH.md](CYTHON_AND_LIBSSH.md).

## Configuration files

- YAML uses no-indent sequences (`- foo` at the same indent as
  its key).
- Long YAML values use a `>-` or `|-` block rather than
  trailing-backslash continuation.
- GitHub Actions `if:` expressions starting with `!` go in a `>-`
  block to keep them out of YAML's quoting rules.

Here: no-indent sequences are enforced by `.yamllint`; see
`.github/workflows/ci-cd.yml` for the block style.

## Markdown

- Admonitions use the GitHub-flavoured `> [!note]` /
  `> [!tip]` / `> [!important]` / `> [!warning]` /
  `> [!caution]` syntax.
- Inline code uses *single* backticks. Double backticks are RST,
  not Markdown -- easy to mix up in a project whose docs or change
  notes are RST.
- Prefer detached link definitions, grouped close to the
  paragraphs that use them rather than dumped at the bottom of
  the file. Inline `[text](url)` is fine when the URL appears once
  and the line stays readable.

## Links

Link Read the Docs projects through the shorter
`<project>.rtfd.io` domain, which redirects to `readthedocs.io` --
especially in code comments, where line length matters.

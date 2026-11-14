# Licensing

> [!important]
>
> License terms are the maintainer's decision, never the agent's.

- Never change the license terms, relicense, or alter license
  metadata -- license files, the `license` / `license-files`
  fields in packaging metadata, per-file license headers or SPDX
  tags -- without the maintainer's explicit approval. Present the
  change to the operator and wait.
- New source files carry the same license header as the existing
  ones, if any.
- Code copied in from elsewhere keeps its original license and
  notices. Before copying any, tell the operator where it comes
  from and under which license, and let them decide whether it
  can come in.

Here: ansible-pylibssh is `LGPL-2.1-or-later` (`LICENSE.rst`,
`pyproject.toml`). Source files carry the LGPL boilerplate header,
not SPDX tags. `build-scripts/manylinux-container-image/` is
derived from PyCA/infra and stays under Apache-2.0 / BSD-3-Clause,
with its license files next to it. The wheels bundle libssh, which
is LGPL-2.1 itself.

## Claude Code guard hook

`.claude/hooks/guard_license_changes.py` makes Claude Code ask the
operator before edits that touch license files, drop license
notices, or change license metadata, and before shell commands
that delete or rewrite license files. That prompt is a backstop,
not a rubber stamp: present the change to the operator *before*
attempting it. Agents other than Claude Code follow the same rule
without the backstop.

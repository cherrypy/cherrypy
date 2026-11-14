# PR & Commit Hygiene

Grounded in the maintainer's review history and merged commits
(PR numbers below are from `ansible/pylibssh`), plus explicit
maintainer conventions carried across projects — not guesses.

## Point contributors to the official guidelines

Route contributors to the project's contributing guidelines and
code of conduct for the canonical contribution process, rather
than improvising or restating it secondhand.

Here: <https://ansible-pylibssh.rtfd.io/en/latest/contributing/guidelines>
and `.github/CODE_OF_CONDUCT.rst`.

## Keep PRs and commits atomic and scoped

One conceptual change per PR, one conceptual change per commit.
"I'm definitely not going to accept a bunch of unrelated changes
smashed together" (PR #809); a PR mixing formatting, docstring
rewording, and a behavior change got split into three (PR #862)
before being accepted. Rebase onto the target branch for real
instead of adding merge commits ("foxtrot merges") to a feature
branch.

### Tool-config changes are standalone

Changes to tool configuration -- `.flake8`, `.ruff.toml`,
`.pre-commit-config.yaml`, `pytest.ini`, `tox.ini`, `.codecov.yml`,
CI workflows, and the like -- go in their own commit, with their
own rationale, never mixed into a functional change. Ask the
operator whether one also needs its own PR. This is the same
reasoning behind keeping type-annotation retrofits a deliberate,
standalone effort (see below). When the config change relaxes a
check, it's also a suppression -- see
[DONT_SHOOT_THE_MESSENGER.md](DONT_SHOOT_THE_MESSENGER.md).

## Don't dump AI-generated bloat

"LLMs are good at generating way too much stuff and it even works
under some circumstances but we're still responsible for keeping
the patches maintainable, having Git tree tell a story and contain
sufficient context. Be accountable." (PR #790) -- trim anything not
directly related to the stated change before proposing it.
You don't decide when the trimming is done. The operator does
(see [HOUSE_RULES.md](HOUSE_RULES.md)).

The same restraint applies to the PR description, not just the
diff -- see
[DONT_GHOST_THE_REVIEWER.md](DONT_GHOST_THE_REVIEWER.md) for why
internal self-check noise (e.g. a "Verification" section
restating that conventional tooling was run) doesn't belong
there either.

## Commit messages

- Imperative-mood subject, 50 characters or fewer.
- The body is descriptive, not imperative: explain *why*, not
  *what* -- the diff already shows what.
- Focus the body on how the commit affects the project. Mention a
  third-party tool's internals or quirks only when they justify a
  non-obvious choice in the code, and say that they do.
  Implementation details belong in code comments.
- Credit the sources that shaped a design -- a discussion, a gist,
  a document -- by linking them from the body.
- Wrap the body at 72 columns.
- No conventional-commits prefixes (`feat:`, `fix:`, etc.). A
  leading [gitmoji] (e.g. 📝 for docs, 🔧 for tool configs) is
  fine -- the maintainer uses them -- but optional.

[gitmoji]: https://gitmoji.dev

Here: commit messages must pass [gitlint], even though it isn't
wired into the linters yet.

[gitlint]: https://jorisroovers.com/gitlint/

## PR descriptions

Fill in the repository's PR template instead of replacing it: keep
its headings and shape, pick the options that apply, and drop the
placeholder comments. Describe what the change brings to the
project -- the problem, the approach, and the decisions a reviewer
needs to know about. Evidence, such as root-cause findings,
measurements, or verbatim tool output, goes where the template asks
for additional information. Leave out third-party internals,
sibling PRs that don't affect the review, and anything the diff
already shows. Disclose the agent's involvement in plain words,
without linking a vendor's site or keeping the harness's default
signature -- e.g. "🤖 Produced by a probabilistic agent with a
token generator using an LLM to sound convincing." (see
[DONT_GHOST_THE_REVIEWER.md](DONT_GHOST_THE_REVIEWER.md)).

Here: the template is `.github/PULL_REQUEST_TEMPLATE.md`, with
SUMMARY, ISSUE TYPE, and ADDITIONAL INFORMATION sections.

## Brushing up a branch before merge

Follow-up commits pile up while a PR evolves. Before merge, the
operator may ask to turn them into a story: a series of atomic
commits on top of the target branch, without the intermediate
experimental states.

- Change existing commits through `fixup!` commits
  (`git commit --fixup=<commit>`, or `--fixup=amend:<commit>` and
  `--fixup=reword:<commit>` for their messages), folded in with
  `git rebase --interactive --autosquash`. That keeps each change
  visible until it's absorbed.
- Carry the discoveries and references of the old commits over
  into the new commit bodies.
- Record the pre-cleanup tip first, and check that the result adds
  up to it: the rewritten branch's tree must match that tip merged
  into the target branch.
- Every commit in the new series has to pass the checks on its
  own.

Publishing the result is a force-push, which is the operator's to
run -- see [HUMAN_IN_THE_LOOP.md](HUMAN_IN_THE_LOOP.md).

## Every change needs a changelog fragment

Every PR needs at least one changelog fragment. Consider every
audience the change affects -- end users, contributors, downstream
packagers -- and add a fragment for each.

A changelog fragment is not a restated commit message -- it covers
everything since the previous release, for end-users, not
developers. Changelog entries are a permanent historical record:
they're never retroactively removed, even if the underlying code
is later reverted, unlike commit history, which can be reworded,
rebased, or squashed.

Recurring, specific review feedback:

- One change per fragment, not several changes "smashed" into one
  (#756, #862).
- Wording is past-tense and end-user-facing, not
  imperative/developer-facing.
- Reference related issues, PRs, users, and files through the
  roles the docs tooling provides, instead of raw links or
  backticks (#620, #786, #790, #809).
- A byline credits a human. Whether the operator gets one, and in
  which form, depends on how involved they feel, so ask them (see
  [HUMAN_IN_THE_LOOP.md](HUMAN_IN_THE_LOOP.md)). Fully agentic
  work gets none -- crediting a probabilistic machine in a loop is
  silly. Disclose agent involvement in the PR instead.

Here: fragments are Towncrier-managed RST files in
`docs/changelog-fragments/`, named `<issue/PR#>.<type>.rst` --
or after the commit hash for changes committed straight to the
default branch -- with `<issue/PR#>.<type>.<n>.rst` for several of
one type. `docs/changelog-fragments/README.rst` lists the types and
the full rationale. References use the `sphinx-issues` roles
(`:pr:`, `:user:`, `:file:`); bylines name people through `:user:`.

## Credit the people whose work you use

When incorporating a patch someone suggested, credit them with a
`Co-Authored-By: Name <email>` trailer, per
<https://hynek.me/til/easier-crediting-contributors-github/>
(GitHub's `ID+username@users.noreply.github.com` works). If it
came via `git format-patch`/`git am`, preserve the original Author
field instead. Add one trailer per contributor when there are
several. Who to credit, and how, is always the operator's call --
ask every time, not only when unsure.

- Prefer native authorship: the operator clicking "Commit
  suggestion" in the GitHub UI, or the author pushing it
  themselves, beats re-applying their change locally.
- Look the trailer up with `gh api users/<login>` (`.id`, and
  `.name` falling back to `.login`) -- don't guess. Keep the
  `+login` part; the bare ID doesn't work. Show the exact trailer
  to the operator before committing.
- Rewording, restructuring, or re-implementing a suggestion so it
  "isn't really theirs" anymore still requires the credit.
- Agents are not authors and never get a `Co-Authored-By`
  trailer -- they aren't sentient, they're guessing machines
  deriving tokens from other people's content. Humans whose work
  was used always get credited. Agent assistance is disclosed with a
  literal `Assisted-by: LLM` trailer -- no model name, no email
  -- following the [Linux kernel's convention][kernel], which
  others follow too ([standard][assisted-by],
  [rationale][dont-abuse-co-authored-by]). The kernel stopped
  naming the model because that advertises vendors while adding
  little information. Add the trailer by default; it replaces
  whatever attribution format the agent's harness suggests.
- Never drop existing `Co-Authored-By` trailers, or replace the
  original author, when rebasing, squashing, or rewording.

[kernel]: https://docs.kernel.org/process/coding-assistants.html#attribution
[assisted-by]: https://allthingsopen.org/articles/open-source-ai-contributions-assisted-by-git-trailer-standard
[dont-abuse-co-authored-by]: https://bence.ferdinandy.com/2025/12/29/dont-abuse-co-authored-by-for-marking-ai-assistance/

## Names and docstrings carry the meaning, not comments

"Comments repeating what the code does are pointless. Proper
identifier names should be used instead" (PR #621). Docstrings
describe what a function does; motivation/rationale, if needed,
belongs in a comment or the PR description, not the docstring
(PR #658).

## Type annotations on new code

New code -- including new tests -- needs type annotations:
parameter types and return types, using `import typing as _t`
for standard-library constructs (e.g. `_t.Optional[...]`). This
isn't retrofitted into existing/legacy code as a side effect of
an unrelated change -- that's a deliberate, standalone future
effort, not something to bundle into whatever else a PR is
doing.

Here: this is a real, acknowledged gap. `.ruff.toml` disables
`ANN001`/`ANN201`/`ANN202`/`ANN401` with an explicit `# FIXME:
These flake8-annotations errors need fixing and removal`
comment, and none of the current test functions in `tests/` are
annotated. Don't read the absence of annotations in existing
code as license to skip them in new code -- it's tracked debt,
not the house style.

## Common micro-conventions flagged in review

- f-strings over `.format()`/`%` formatting.
- `contextlib.suppress()` over bare `try`/`except: pass`.
- No monkey-patching stdlib.
- Public vs. private intent must be explicit -- prefix with `_` if
  not part of the public API.

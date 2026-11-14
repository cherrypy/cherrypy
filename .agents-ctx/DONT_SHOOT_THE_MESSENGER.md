# Don't Shoot the Messenger

> [!important]
>
> Linters, type checkers, coverage, and tests are messengers. When
> one of them reports a problem, fix the problem -- don't silence
> the messenger. Whether a check gets silenced is always the
> operator's decision, made case by case, never the agent's.

## What counts as silencing

All of these need an explicit, per-case decision from the
operator.

Linters, type checkers, coverage:

- Inline suppressions: `# noqa[: ...]`, `# ruff: noqa`,
  `# flake8: noqa`, `# type: ignore[...]`, `# mypy: ignore-errors`,
  `# pylint: disable=...`, `# pragma: no cover`.
- Config-level ignores: `per-file-ignores`, `extend-ignore`,
  `exclude` entries, and similar in `.flake8`, `.ruff.toml`, mypy
  or any other tool config. Editing a tool's config to make a
  finding go away is a suppression too.
- Disabling or narrowing a pre-commit hook, or bypassing hooks
  with `SKIP=` / `git commit --no-verify`.
- Loosening types to make a finding go away: replacing a precise
  annotation with `typing.Any`, or adding a `typing.cast()`. When
  a value really can be anything, `object` is the honest
  annotation.

Tests:

- Deleting a test, a fixture, or a whole test module.
- Commenting out a test or a test module.
- Adding `skip`/`skipif`/`xfail` markers to an existing test, or
  calling `pytest.skip()`/`pytest.xfail()`/`pytest.importorskip()`
  to dodge a failure.
- Weakening assertions: removing them, dropping `match=` from
  `pytest.raises()`, catching a broader exception type, or
  changing an expected value to match buggy output.
- Taking a test's expected values from the code's current output
  instead of from the issue, a spec, or a reference
  implementation. Such a test agrees with whatever bugs the code
  has, so it can never report them. See
  [TESTING.md](TESTING.md#tests-state-what-the-code-should-do-not-what-it-does).
- Adding `ignore` entries to `filterwarnings`.

Thresholds and CI:

- Lowering coverage targets, adding `continue-on-error`, dropping
  a job or a matrix entry.

Reporting:

- Running a subset (`-k`, `--deselect`, `--ignore`) is fine while
  iterating, but never report a run as green while failures are
  excluded from it.

## Don't game the messenger either

Silencing has a mirror image: making a check report success while
the thing it measures isn't actually true. A coverage number going
up is not proof that anything is better tested. Gaming a check is
no more the agent's call than silencing it.

These count as gaming:

- Tests that execute lines without checking behavior: no
  assertions, or assertions that can't fail.
- Reaching code through private or internal API (`_name()`), or
  calling it in an order or a number of times no real caller
  would, just to mark lines as covered.
- Forcing an object into a state that its public API, or a real
  external scenario, can never produce.

Instead, drive the code the way it runs for real: through the
public API, or an end-to-end scenario -- a full object lifecycle,
a failure provoked at a real boundary. Before writing a test for
an uncovered line, check whether existing tests already reach it
that way, and whether the coverage tool can see it at all. When a
line can't be reached realistically, stop and bring it to the
operator as a finding, not a test: it's either dead or purely
defensive code -- the operator decides whether to drop it or to
exclude it as described in [Presenting a case](#presenting-a-case)
-- or a blind spot of the tooling. Say what each new test proves,
not which lines it turns green.

Here: PR #879 added a test calling `_RemoteFile._cleanup()` by hand,
without assertions, to cover its early return on an already-closed
handle. Real use already takes that branch: `__exit__()` closes the
handle and `__dealloc__()` runs `_cleanup()` again, and a failed
`sftp_open()` deallocates an object whose handle was never set.
With Cython line tracing on, dozens of other tests in
`tests/unit/sftp_test.py`, including plain `SFTP.get()` and
`SFTP.put()` calls, were already recorded taking it.

## Presenting a case

When you believe silencing is warranted, stop and show the
operator, one case at a time:

1. The tool or test, the error code or failure message, and the
   `file:line`.
2. Why the cause can't reasonably be fixed right now.
3. The proposed scope -- line, file, or (rarely) directory.
4. The exact comment text that will accompany it.
5. When it can be removed -- the condition, the issue, or the
   upstream fix it waits for.

Then restate the trade-off in your own words and confirm the
operator understands and agrees with it. Approval of one case says
nothing about the next one.

## Preferred shape: line-scoped, explained, temporary

Scope a suppression to the single line that needs it, name the
specific codes, and explain why it exists and when it can go:

```python
value = call(42)  # noqa: WPS432  # mirrors an upstream constant; drop once it's exposed by name
```

Blanket `# noqa` without codes is rejected by the
`python-check-blanket-noqa` pre-commit hook anyway. A `skip` or
`xfail` carries a `reason=` that links the tracking issue.

Most suppressions should be temporary. Treat each as tracked debt,
not a resolution.

## File-level suppressions are exceptional

Acceptable only with the operator's decision, for well-reasoned
cases -- e.g. a test module that intentionally passes wrong
argument types to check that runtime validation rejects them.
Where the tool supports code-specific file-level directives
(`# ruff: noqa: <CODE>` at the top of the file), use those.
Otherwise, use a `per-file-ignores` entry preceded by a comment
explaining each code, following the convention at the top of the
`per-file-ignores` block in `.flake8`.

## Directory-scoped suppressions

Avoid globs like `tests/**.py` in ignore lists. They hide every
future violation in that tree, not just the one in front of you.
Only add one with a well-reasoned decision from the operator,
recorded in a comment next to the entry.

## Legitimate test changes still get presented

When behavior changes on purpose and a test's expectations have
to change with it, say so explicitly -- don't slip it into a
larger diff. The accepted `xfail`-only PR in
[TESTING.md](TESTING.md) openly adds a *new* failing test ahead of
its fix. It is not a way to hide an existing test that broke.

## Existing suppressions

Some suppressions in the tree predate this rule. Don't rewrite
them unasked. Point them out to the operator if they're in the
area you're touching. Removing a suppression that's no longer
needed is welcome, but show it too.

Here: e.g. the bare `# noqa: DAR101` lines in `tests/conftest.py`,
without an explanation.

## Tool-config changes are standalone

Changing a linter, test runner, coverage, or CI config is its own
atomic change, never mixed into a functional one. See
[PR_HYGIENE.md](PR_HYGIENE.md).

## Claude Code guard hook

`.claude/hooks/guard_silenced_checks.py` makes Claude Code ask the
operator before edits that add suppression markers, reduce the
number of tests or assertions under `tests/`, add private-method
calls there, touch tool configs, or bypass/delete things from the
shell. That prompt is a backstop, not a rubber stamp: present the
case as described above *before* attempting the edit. Agents other than Claude Code follow the same
rule without the backstop.

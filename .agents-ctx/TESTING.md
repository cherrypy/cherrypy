# Testing

Grounded in the maintainer's review history and merged commits
(PR numbers below are from `ansible/pylibssh`), plus explicit
maintainer conventions carried across projects — not guesses.

## Tests are proof, not decoration

New or changed behavior needs a test demonstrating it, covering the
cases actually touched (including edge cases like `None`). "I don't
think there's a proof that this works as intended without tests" is
a near-verbatim recurring review comment (e.g. PR #756, #786, #790,
#479, #669, #809). Missing test coverage is the single most common
reason PRs stall or get closed unmerged.

Justify new tests by what they actually verify, not by the
coverage number alone. Coverage still matters a lot -- 100%
coverage is a genuinely useful self-check (e.g. it can catch tests
that silently start getting skipped in CI). The point is: don't
game the number -- a test that exercises a line without
meaningfully checking behavior doesn't count, passing or not (see
"Don't game the messenger either" in
[DONT_SHOOT_THE_MESSENGER.md](DONT_SHOOT_THE_MESSENGER.md)). The
same reasoning-over-metrics standard applies to every change, not
just tests: infra, packaging, and runtime code all need
well-reasoned, architecturally sound justification, not just a
passing check.

Deleting, commenting out, skipping, xfailing, or weakening a test
is never the agent's call -- see
[DONT_SHOOT_THE_MESSENGER.md](DONT_SHOOT_THE_MESSENGER.md).

Here: `.codecov.yml` targets 100% for `src/`/`tests/`. It isn't
wired up as a required CI check yet, only because of unresolved
infra problems measuring Cython coverage -- not because it's
considered optional.

## Tests state what the code should do, not what it does

Expected values come from somewhere other than the code under
test: the issue, a spec or RFC, upstream library docs, or the
observed behavior of a reference implementation. A test whose
expectations were read off the implementation only restates it,
and it keeps passing when the code is wrong in the same way.
Doing so counts as silencing -- see
[DONT_SHOOT_THE_MESSENGER.md](DONT_SHOOT_THE_MESSENGER.md).

- Show that a regression test catches its bug. Run it against
  the unfixed code (revert or stash the fix) and confirm it fails
  for the reason the test names, then confirm it passes with the
  fix. Say in the PR how this was checked. This is a verification
  step, not a commit-ordering rule -- the test still lands in the
  same commit as the fix.
- For new behavior, write down the expected outcomes from the
  issue or spec before reading or writing the implementation, and
  bring them to the operator when the source is ambiguous rather
  than settling the question by running the code.
- Assert on outcomes a caller can observe, not on how the code
  gets there.
- When an expected value can't be traced to a source outside the
  code, say so to the operator instead of copying it from the
  current output.

Here: the live `sshd` in every test is the main independent
oracle -- prefer comparing against what the server, or the OpenSSH
client against the same server, actually does.

## No test classes

Every test in `tests/` is a plain `def test_*` function. Don't
introduce `unittest.TestCase` subclasses or bare grouping classes.

Here: there are zero `class` definitions anywhere in the test
suite, across the full project history.

## Prefer parametrize/fixtures over duplicated test logic

When two tests differ only in their input data, that's a
parametrized fixture or test, not two near-identical functions.
Precedent: PR #638 collapses two payload fixtures into one
parametrized fixture.

Loop-based checks inside a single test are generally a sign the
test should be parametrized instead. The one accepted exception is
`pytest-subtests` (the `subtests` fixture), for structured,
individually reported sub-assertions within one test.

Here: PR #638's result is
`@pytest.fixture(params=(32, SFTP_MAX_CHUNK + 1), ids=(...))`,
replacing `other_payload`/`large_payload`. A later commit merges
near-duplicate `NOTSET`/`TRACE` tests into a single
`@pytest.mark.parametrize` case.

## Real e2e over mocking

Don't introduce mocking as a substitute for exercising the real
behavior of the components involved.

Here: `tests/` contains zero uses of `mock`, `Mock`, or
`monkeypatch`. Every test -- unit and integration alike --
exercises a real `sshd` process spun up per-test via the
`sshd_addr` fixture in `tests/conftest.py`.

## Design for testability

Prefer decoupling techniques -- dependency injection in particular
-- that let code be tested in isolation, over reaching for
monkeypatching. Monkeypatching (via `unittest.mock` or the
`monkeypatch` fixture) is only acceptable at real system
boundaries: the system clock/timezone, environment variables, or
swapping in a stub server. It's not a substitute for designing
components to be testable on their own.

## Test doubles for intercepted components

When end-to-end tests need to patch or intercept a real component
-- say, to withhold a server's replies -- the test double gets its
own directory in the tests' stub area, named after its purpose
rather than the library it's built on. Its `fixtures.py` module is
the entry point, loaded as a local pytest plugin.

- Entry points are imported eagerly at startup, so they must not
  import their component's optional dependencies at the module
  level. Import those inside a fixture through
  `pytest.importorskip()`, so that a missing one skips only the
  tests that need it. That's a declared optional dependency, not
  a way to dodge a failure.
- The stub area is excluded from the doctest collection, which
  would otherwise import those dependencies.
- Code running in child processes only gets its coverage recorded
  when those processes exit cleanly instead of being killed.

Here: stubs live in `tests/_stubs/<component>/`, discovered via
`pytest_plugins` in `tests/conftest.py`, and excluded through
`norecursedirs` in `pytest.ini`. `tests/_stubs/sshd_mitm_tcp_relay/`
is the first one. Child-process coverage relies on
`concurrency = multiprocessing` in `.coveragerc`.

## Test layout

Test files are named `<topic>_test.py`, not `test_<topic>.py`.
Match the existing file when extending it.

Once the suite splits into categories, unit tests loosely mirror
the source modules -- `<module>_test.py`, with a new file only for
a genuinely new module -- while integration tests are organized by
scenario or feature instead.

Here: `tests/unit/` mirrors `src/pylibsshext/` -- `channel_test.py`,
`session_test.py`, `sftp_test.py`, `scp_test.py`, `version_test.py`.
The correspondence isn't strict 1:1: `errors` is covered via
`pytest.raises` inside other files, not its own file.
`tests/integration/` holds the scenario-based tests.

## Tests usually land in the same commit as the behavior they cover

When a change adds or alters behavior, the test change normally
lands in the *same* atomic commit, not a follow-up -- there's no
evidence of strict test-first/TDD commit ordering as a project
ritual. That style of TDD is mainly useful for interactive
development and exploration, used in tandem with continuous
adjustment, not as a blanket rule here.

The one accepted exception: a PR that adds only a failing test,
marked `@pytest.mark.xfail`, can be merged on its own ahead of the
fix, to be resolved in a follow-up. Don't treat a merged `xfail` as
done, though -- it's a tracked gap, not a resolution. This
exception covers adding a *new* failing test; marking an existing
test `xfail` because it broke is silencing it.

## Assertions

Use `pytest.raises(..., match=...)` -- never a bare
`pytest.raises(SomeError)` -- so the assertion pins down which
failure is expected, not just its type. Use a raw string (e.g.
`r'^foo\.bar$'`) or `re.escape(...)` for the `match=` pattern when it
contains regex metacharacters, to keep the regex intention explicit.

Keep each test focused on a few assertions. When testing a
multi-stage workflow (e.g. write followed by read), split the
stages into separate test functions. Assign a non-trivial
expression (such as `len(...)`) that a test keeps repeating to a
local variable instead.

Here: wemake-python-styleguide enforces both through flake8, at
its default limits -- at most 5 `assert` statements per function
(WPS218), and no expression repeated more than 4 times in one
function (WPS204).

## Filesystem fixtures

Use pytest's built-in `tmp_path` fixture; don't hand-roll
temp-directory setup/teardown.

## Test payload data: readable while debugging, random once stable

Printable, hand-crafted payload data helps root-cause bugs that
corrupt data -- readability matters more than realism while chasing
them. Once an implementation is no longer prone to that class of
bug, prefer `random.randbytes()`-style payloads instead: building
large printable payloads is inefficient, and random bytes exercise
the code more realistically at scale. This is a tradeoff that
shifts with implementation maturity, not a blanket "always use
random data" rule.

Here: the file-transfer tests moved to random payloads in PR #872.

## Type annotations on new tests

New test functions and fixtures need type annotations too --
parameters and return types -- same as any other new code. See
[PR_HYGIENE.md](PR_HYGIENE.md) for the full rule, including why it
isn't retrofitted onto existing code as a side effect.

## Every test and fixture has a one-line docstring

Describing what it checks or provides, not restating the code,
e.g. `"""Check that the config is parsed."""`. Enforced by the
linters in CI.

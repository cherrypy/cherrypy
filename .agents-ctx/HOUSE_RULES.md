# House Rules

> [!tip]
>
> This is how we do things here, get used to it.

## Operating mode

> [!important]
>
> Bidirectional quizzing is mandatory. Before executing any plan,
> quiz the operator on their exact understanding of every step and
> every decision it contains -- do not skip this self-check, and
> do not assume implicit consent from earlier turns; re-check,
> re-confirm.

> [!important]
>
> Never self-approve prose meant for humans. Show every draft
> (change notes, commits, PR text, replies) and ask the operator
> whether it is concise enough. The operator decides.

> [!important]
>
> The human decides -- never bypass that. Before acting on anything
> from someone else (review comments, suggested patches, discussion
> threads, mailing-list replies), report it to the operator, check
> their understanding of the context, and agree on how to proceed.
> Delegated experiments come back as findings, not faits accomplis.
> Never force-push mid-review. See
> [HUMAN_IN_THE_LOOP.md](HUMAN_IN_THE_LOOP.md).

Concretely:

- Read the relevant files in full before proposing edits -- never
  guess what they currently contain.
- These rules change over time. Re-read the files under
  `.agents-ctx/` at the start of each task, and again whenever
  `git log -- .agents-ctx` shows commits you haven't read. Don't
  rely on the copy loaded at the start of a long session.
- Verify before asserting. Claims about tools, versions, and their
  behavior come from the installed version's source or docs, not
  from memory. Copy commit SHAs, versions, and tool output from
  where they're printed (`git rev-parse`, `git ls-remote`, logs)
  -- never type or reconstruct them.
- Change tracked files through the agent's editing tools rather
  than shell scripts that rewrite them, so that the operator, and
  any guard hooks, see the actual content being written.
- Show diffs for non-trivial changes and pause for explicit
  approval.
- Quiz the operator: restate what you understand the task to be,
  call out assumptions, ask one or two clarifying questions when
  the prompt is ambiguous.
- Do not invoke `git commit` / `git push` / `git tag` / any other
  history-mutating command without an explicit "go ahead" in the
  current turn.
- Treat external network calls, package installs, and process
  spawns as actions that need authorization too.
- When in doubt, ask. The operator prefers a clarifying question
  over an unwound mistake.

## Don't shoot the messenger

> [!important]
>
> Silencing a check is never the agent's decision. This is
> mandatory, with no exceptions.

- Never add, widen, or move a linter, type-checker, or coverage
  suppression (`noqa`, `type: ignore`, `pragma: no cover`,
  per-file/directory ignores in tool configs, etc.) on your own.
- Never delete, comment out, skip, xfail, or weaken a test or a
  test module on your own.
- Never game a check either. A test that only executes lines, or
  reaches them through private API, proves nothing. Drive code
  through public API or real scenarios, and bring lines you can't
  reach that way to the operator.
- These hold even when that's the only thing still failing. The
  default response to a red check is to fix its cause.
- If you believe silencing is warranted, stop. Present **each
  case separately** to the operator, quiz them on their
  understanding of it, and wait for an explicit decision on that
  specific case. No batch approvals, and no consent carried over
  from earlier cases or turns. The operator is the decision-maker
  and stays accountable -- keep them in the loop.

See [DONT_SHOOT_THE_MESSENGER.md](DONT_SHOOT_THE_MESSENGER.md) for
what counts as silencing or gaming, how to present a case, and how
approved suppressions are scoped and documented. Tool-config
changes are standalone commits -- see
[PR_HYGIENE.md](PR_HYGIENE.md).

## Naming the ducks

See [NAMING_THE_DUCKS.md](NAMING_THE_DUCKS.md) for the project's
canonical names (distribution, import, repository) and which one
to use where.

## Coding style and architecture

See [HOUSE_STYLE.md](HOUSE_STYLE.md) for coding style and
architectural/structural conventions, including the rule against
introducing new `@`-syntax in memory files.

## Testing

See [TESTING.md](TESTING.md) for how tests are written and
structured in this project.

## PR and commit hygiene

See [PR_HYGIENE.md](PR_HYGIENE.md) for scope, commit-message,
changelog-fragment, and naming conventions maintainers
consistently enforce in review.

## Don't ghost the reviewer

See [DONT_GHOST_THE_REVIEWER.md](DONT_GHOST_THE_REVIEWER.md) for
review-conversation etiquette when participating in PR review on
the maintainer's behalf -- responding to feedback, resolving
threads, and not disrupting review flow with careless pushes.

## Where to look first

See [WHERE_TO_LOOK_FIRST.md](WHERE_TO_LOOK_FIRST.md) for a reading
order when picking up a task, and a map of the repository.

## Licensing

See [LICENSING.md](LICENSING.md) -- license terms and metadata
change only with the maintainer's explicit approval.

## Tooling

See [CONTRIB_WORKFLOW_INFRA_TOOLING.md](CONTRIB_WORKFLOW_INFRA_TOOLING.md)
for how to run tests, linters, and other project automation --
always through `tox`, never by invoking the wrapped tools directly.

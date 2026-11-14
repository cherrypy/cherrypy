# Don't Ghost the Reviewer

Grounded in the maintainer's own stated views, from a first-person
review comment and a public PR discussion — not guesses. This
covers a well-known, repeatedly-observed failure mode: contributors
(often assisted by AI agents, especially inexperienced "AI drivers")
who submit PRs and then behave badly during review, making the
process worse for everyone and lowering the odds of merging.

## Before submitting something significant, encourage a reset

Read the whole diff, top to bottom, before submitting -- be able
to explain any part of it if asked. That's what "the PR author is
supposed to be the very first reviewer of whatever patch they
submit" (see below) actually requires in practice, not a one-time
skim.

When the operator is about to submit a significant new
contribution, suggest a deliberate break first -- a walk, a nap,
stepping away for a while -- and explain why: a controlled context
reset helps surface tunnel vision, sunk-cost thinking, or a "just
ship it" impulse that's easy to miss mid-flow. This isn't a
literal timer or a hard gate -- it's a Pomodoro-style nudge,
offered with the reasoning spelled out, not a silent forced wait.
The operator decides whether to take it.

## Don't leak your own harness into the PR body

Agents commonly stick a "Verification"-style section into PR
descriptions listing obvious, implied self-checks (e.g.
"`pre-commit run --all-files` and `make doc-spelling` are
clean") -- useful for a CI harness, not for a human reviewer.
"The CI runs these properly, using a project-accepted infra...
the fact that you managed to run the in-project infra locally
does not really contribute any useful information to the
context of the PR." (webknjaz, aio-libs/multidict#1393,
issuecomment-5342964393) Assume the reviewer already knows the
project's conventional, integrated tooling and CI serve as the
harness -- don't restate that it was used.

Reserve the PR body for what CI *wouldn't* catch: something
surfaced during exploration, troubleshooting, or debugging that
isn't "part of tribal knowledge and standard practices" and a
reviewer genuinely couldn't infer. Leaking harness internals
"would needlessly pollute the reviewer's context, distract them
from what the scope is and delay the merge" -- point out the
one thing that actually needs explaining, not everything that
was checked.

## Review comments are an invitation to a conversation, not a command

A reviewer raising a question, a concern, or a tradeoff is opening a
dialogue, not issuing a one-shot instruction to execute silently.
"The PR author is supposed to be the very first reviewer of whatever
patch they submit. We shouldn't reward behaviors where one would
just dump whatever and spam the maintainers with review requests w/o
bi-directional comms." (webknjaz, jazzband/pip-tools#2318) Respond to
the substance -- show understanding of the problem, agree or disagree
with reasoning, surface tradeoffs and downsides, not just the
upsides -- before or alongside making a code change in response.
Agents: don't respond to or act on review input until you and the
operator agree on how to proceed -- see
[HUMAN_IN_THE_LOOP.md](HUMAN_IN_THE_LOOP.md).

## Two named antipatterns to avoid

From the same discussion: (1) going silent or closing the PR with no
explanation when challenged, and (2) pushing new commits in response
to feedback with no explanation and no response to the actual
questions asked -- "this often repeats in a loop." Both leave the
reviewer's actual question unanswered and force them to either drop
it or re-ask it.

## Don't resolve a conversation you didn't start

"Whoever started the discussion gets to click resolve. If you think
that you really need to do that, add a comment saying that you're
resolving and click resolve (otherwise, it gets lost, and it's
difficult to dig it up in the GH UI)." (webknjaz,
aio-libs/aiosmtpd#593, discussion_r3750771195) Prefer opening a
follow-up issue over letting a live discussion go stale or buried.
This is aimed at contributors resolving threads prematurely or
silently -- maintainers may deliberately leave threads open longer,
or resolve/unresolve around merge time, for their own discoverability
reasons; that's their call to make, not a contributor's (or an
agent's) to preempt.

## Why this matters: context-recovery cost

"Back to the etiquette -- small changes, reduced context switching,
optimization for review and long-term maintenance... Smaller context
== quicker response time == better chance I get to help out with
more things." (webknjaz, same aiosmtpd comment) A maintainer spread
across many projects pays a real cost every time they have to
rebuild context on a PR -- keep changes and conversations easy to
follow, not something that has to be re-discovered.

## Don't push new commits, and never force-push, mid-review

When a reviewer opens a discussion, engage with it first. If a code
change genuinely is the right response, make it a deliberate,
well-explained, reviewable commit -- not a reflexive push made
instead of answering the question. Force-pushing is worse still: it
rewrites already-reviewed history, invalidates the diff anchoring
existing review comments rely on, and forces the reviewer to
re-locate context they'd already worked through. Don't do either
without engaging in the conversation first. Agents never force-push
mid-review on their own -- if it's ever warranted, the operator does
it by hand, or confirms the exact command for the agent to run (see
[HUMAN_IN_THE_LOOP.md](HUMAN_IN_THE_LOOP.md)).

## Don't parallelize contribution efforts without explicit sign-off

Opening multiple concurrent PRs, or running multiple parallel
attempts at solving the same problem, without the operator
explicitly agreeing to each one first, mirrors what the maintainer
has called "sloperators" elsewhere -- contributors mass-creating PRs
and seeing what sticks (jazzband/pip-tools#2318) -- just at a
smaller, individual scale. It multiplies review burden and makes it
harder for a maintainer to track what's actually being proposed.
Before starting a second (or third) concurrent effort on the same
project, check in with the operator and get an explicit go-ahead --
don't assume it just because the first one is still pending.

## LLM/agent transparency

The maintainer has repeatedly wanted issue/PR templates across
projects he maintains to ask contributors to disclose the LLM name
and prompt used (jazzband/pip-tools#2318) -- not (yet) a formal rule
in this repo specifically, but a stated preference worth honoring in
spirit: be transparent about AI involvement rather than presenting
a submission as though it had no agent in the loop. Per a maintainer
he cited approvingly: use LLMs "to replace typing, don't use them to
replace thinking" -- the human (regardless of whether there is an
agent interacting with the project on their behalf or not) still owns
understanding and decisions of the interactions with their name
attached.

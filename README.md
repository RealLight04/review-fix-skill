# review-fix

**Stop burning Opus on one-line fixes.**

A [Claude Code](https://claude.com/claude-code) skill that grades each code
review finding by risk, then hands the fix to the cheapest model that can
safely do it — Haiku for mechanical edits, Sonnet for ordinary bugs, Opus for
anything expensive to get wrong.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-8A63D2.svg)](https://code.claude.com/docs/en/skills)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/RealLight04/review-fix-skill/pulls)

[한국어 README](README.ko.md) · [한국어 SKILL](SKILL.ko.md)

---

> New to Claude Code? A **skill** is a reusable prompt Claude Code loads on request (here, via
> `/review-fix`). A **finding** is one issue a code review reported — a file, a line, and what's
> wrong with it. This skill takes findings someone already produced and fixes them; it does not
> review code itself.

## Read this first: what you already have

Claude Code ships `/code-review --fix`, and it is good. Before installing
anything, know that it already:

- applies review findings straight to your working tree (`--fix`)
- follows your `CLAUDE.md` like any session (the managed GitHub Code Review also
  reads `REVIEW.md`; the local command does not)
- reports each finding back as **fixed, skipped, or no change needed**
- trades coverage against confidence via effort levels (`low` … `max`)
- escalates to a deeper cloud review with `/code-review ultra --fix`

If that covers your needs, you do not need this skill. Use the built-in one.

## What this adds

Two things `/code-review --fix` does not do.

**1. Per-finding model tiers.** The built-in fix path runs at one model. This
skill grades each finding and dispatches it to a different model accordingly:

| Tier | Test | Model |
|---|---|---|
| Mechanical | Rote change, easy to undo — dead file, unused import, typo | `haiku` |
| Ordinary | Everyday bug fix needing surrounding logic understood | `sonnet` |
| High-risk | Auth, payments, migrations, concurrency, cross-file behavior | `opus` |

Ties break upward. Grading down to save money is not allowed — a wrong fix
costs more than the model does.

**2. Escalation on failed verification.** Every tier verifies the subagent's
work rather than trusting its self-report (mechanical: check the file really
changed; ordinary: run the test script; high-risk: read the diff for scope
creep). When verification fails, the finding retries at the same tier with
tighter bounds, then one tier up, then stops and reports. No silent failures,
no infinite loops.

It also reads `CLAUDE.md` for paired-file rules — "change this file, change
that one too" — so a finding naming one half of a pair doesn't get fixed
halfway and reported as done.

## Prior art

Model tiering is not new, and this skill is a variation on work that came
before it:

- **[Aider's architect/editor split](https://aider.chat/2024/09/26/architect.html)**
  (Sept 2024) — a strong model plans the change, a cheap one writes the diff.
  The original of "split one task across model tiers." Tiers by *phase*, where
  this skill tiers by *risk*.
- **[AqueGen/model-routing](https://github.com/AqueGen/model-routing)** — routes
  Claude Code subagents by task type (scout, implementer, reviewer). Notably,
  it cites [RouteLLM (ICLR 2025)](https://arxiv.org/pdf/2406.18665) for the
  claim that *task-type routing beats complexity-score routing* — which is an
  argument against the approach this skill takes. Worth reading before you pick
  one.
- **[crissmoldovan/agent-skills](https://github.com/crissmoldovan/agent-skills)** —
  a multi-skill pack including a model-routing skill, profile-driven rather than
  automatic.

## What has not been measured

Honest disclosure, because nobody in this space seems to publish numbers:

- **Whether tiering nets out positive here.** Grading each finding costs tokens
  in the orchestrating session. That cost has not been weighed against the
  savings from cheaper fix models. It may not pay for itself on small batches.
- **Whether Haiku matches Opus on "mechanical" findings.** Measured once, on
  three small cases (see below). The tier boundaries are still mostly reasoned.

[review-fix-bench](https://github.com/RealLight04/review-fix-bench) has nine
cases aimed at the second question: whether a fix at each tier lands and stays
in scope, and whether the rubric picks the expected tier. It lives in its own
repository so the answers are not sitting in this skill's install folder.

A first run (81 fixes and 81 gradings across Haiku, Sonnet and Opus) is in the
[results](https://github.com/RealLight04/review-fix-bench/blob/main/results/RESULTS.md).
Haiku fixed all nine mechanical runs, like Opus. Haiku failed the one case with
a swallowed exception, which every grading run sent to Opus. The rubric matched
the expected tier in 58 of 81 gradings, and 13 times it rated a high-risk case
Ordinary. All three models fixed those two cases correctly, so the labels may be
set too high as much as the rubric too low. Either way the tier boundaries are
still a hypothesis. The token numbers are
dominated by subagent startup overhead, so the first question is still open.

## How this differs from delegate

[delegate](https://github.com/RealLight04/claude-delegate), by the same author,
also grades work, picks a model tier, and verifies the result. What separates
them is the input.

delegate takes any list of independent tasks, so before handing anything off it
checks whether each task makes sense without the conversation's context and how
many groups remain after grouping. review-fix takes only findings a code review
already produced. File, line and problem are fixed in advance, so there is less
to decide about whether to delegate, and more machinery for review fixes
specifically: filtering unverified findings, checking that a cited `CLAUDE.md`
rule actually exists, skipping findings whose cited lines no longer match the review,
and hashing already-dirty files so the report stays honest.

In practice:

- You ran `/code-review` on a PR and got six findings: two unused imports, a
  missing null check, a payment retry bug, and two `PLAUSIBLE` ones. Use
  review-fix. It fixes the four confirmed ones at their tiers and hands the two
  `PLAUSIBLE` ones back as a list.
- Before a release you have a README typo, a dark-mode bug on the settings page,
  a new log cleanup script and a payment module refactor. None of it came from a
  review and it is all different in kind, so use delegate. Four different files
  make four groups, run in parallel.
- With only one or two tasks, delegate is not worth it, and a single trivial
  finding does not need review-fix either. Just ask directly.

## Install

```bash
npx skills add RealLight04/review-fix-skill
```

<details>
<summary>Manual install</summary>

macOS / Linux:
```bash
git clone https://github.com/RealLight04/review-fix-skill.git ~/.claude/skills/review-fix
```

Windows PowerShell:
```powershell
git clone https://github.com/RealLight04/review-fix-skill.git `
  "$env:USERPROFILE\.claude\skills\review-fix"
```
</details>

## Use

Run a review first, then:

```
/review-fix
```

With no argument it uses the most recent review output in the conversation.
You can also paste findings directly:

```
/review-fix app/alerts.py:42 — dispatch() swallows the exception before commit, so alerts can double-send
```

Findings from review output that are marked `PLAUSIBLE` or carry no verdict are
listed but not touched — unverified claims don't get to edit your files.
Findings you paste yourself count as confirmed by you, unless they are
explicitly marked `PLAUSIBLE`. The skill still reads the cited code first and
reports "no change needed" if the problem is not there. Nothing is committed
until you ask.

Full behavior is in [SKILL.md](SKILL.md). It's the prompt Claude receives, so
reading it tells you exactly what happens.

## License

[MIT](LICENSE)

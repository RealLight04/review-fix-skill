---
name: review-fix
description: After a code review produces findings, grade each one by risk and complexity, then delegate the fix to the cheapest model that can safely do it (Haiku for mechanical, Sonnet for ordinary, Opus for high-risk). Use when a review is done and you are about to fix a batch of findings of differing severity.
argument-hint: "[optional: findings to fix — defaults to the most recent review in this conversation]"
allowed-tools: Read, Grep, Glob, Bash, Agent
---

## When NOT to use this

- One small finding. Grading it and handing it to a subagent costs more than
  just fixing it. This skill earns its keep when findings are several and their
  risk differs.
- No review has run yet. Run one first. This skill consumes findings, it does
  not produce them.
- You want every finding fixed by one model regardless of cost. Use
  `/code-review --fix` instead. It is simpler, and it runs at the session's
  model, so switch the session first if you want the strongest.

# Fix review findings, one model tier at a time

## Why

Findings from a single review differ wildly in risk. Deleting a dead file and
patching an auth edge case are not the same job. Handing both to one model
means either paying frontier prices for mechanical edits, or letting a cheap
model near code where a subtle mistake is expensive. This skill fixes the
grading rubric in place so the call is not re-improvised every time.

**This skill does not merely recommend a tier.** It passes `model` to the Agent
tool so the chosen model performs the edit. Orchestration (grading, ordering,
re-verification) stays in this session; the file edits happen in the chosen
model's subagent.

## Input

- If the user passed arguments (they arrive on the `ARGUMENTS:` line at the end
  of this prompt), treat them as the findings list. Findings passed this way
  count as confirmed by the user even without a `verdict` field, unless they are
  explicitly marked `PLAUSIBLE`. Still read the cited code before editing: if
  the described problem is not there, report "no change needed" instead of
  inventing a fix.
- Arguments that only point at findings already in the conversation (for
  example "fix #2 and #4") keep those findings' original verdicts.
- Otherwise use the most recent review output in this conversation. The
  `/code-review` and `ReportFindings` shape (`file`, `line`, `summary`,
  `failure_scenario`, optional `verdict`) is the common case, but output from
  any review-producing skill works the same way.
- If there are no findings at all, stop and say so. Do not start from "let's
  just look for something to fix."

## Step 1 — Filter

- Take a baseline before touching anything, in every repository the findings
  touch (`git -C <repo>` for any other than the current one):
  `git -c core.quotePath=false status --porcelain --untracked-files=all` (so each untracked file is
  listed on its own, not just its directory), plus `git hash-object <path>` for
  every file it lists. For a rename, hash the new path; strip the quotes git
  adds around paths that contain spaces. A deleted path has no hash; record it as deleted. The working
  tree may already carry unrelated modified or untracked files, and this skill
  may edit one of them. Paths alone cannot show that; the hashes can. Without a
  baseline, step 4 cannot separate "what this skill changed" from "what was
  already there."
- Only findings marked `CONFIRMED` (or otherwise stated to have passed
  verification), and findings the user passed directly as arguments (unless
  explicitly `PLAUSIBLE`), are eligible for automatic fixing.
- Findings taken from this conversation's review output (not passed as
  arguments) that are marked `PLAUSIBLE`, or carry no verdict at all, are
  **listed for the user and left alone.** An explicit `PLAUSIBLE` stays alone even when the user pastes it. Do
  not edit files on the strength of an unverified claim. This is a general
  principle, not a rule peculiar to this skill.
- Merge findings that duplicate or overlap each other (same file, same cause).
- If time has passed since the review, re-read the lines a finding cites and
  confirm they still match what the review describes (`git log` shows commits
  made since the review). Uncommitted changes that the review itself covered do
  not make a finding stale. Do not apply a stale review to current code: skip
  that finding and report it as "skipped (stale)".

## Step 2 — Grade each finding

Work down the table, and **when torn between two tiers, take the higher one.**
Never grade down to save money: a wrong fix costs more than the model does.

| Tier | Test | Examples | Model |
|---|---|---|---|
| Mechanical | Rote change. Almost no judgment, easy to undo | Delete dead file, drop unused import, typo, formatting, a fix the surrounding comment already spells out | `haiku` |
| Ordinary | An everyday bug fix that needs the surrounding logic understood | Wrong condition, missing null check, routine refactor, schema-safe column addition | `sonnet` |
| High-risk | Expensive to get wrong or hard to undo | Auth, payments, personal data, concurrency and transactions, architectural change, DB migrations, behavior changes spanning files, unclear trade-offs | `opus` |

If the project has a `CLAUDE.md`, read the relevant parts before grading. A
finding of the form "this violates the project rules" needs that rule to
actually exist. Check before grading it, so a hallucinated rule does not drive
a tier. In the same pass, look for paired-file rules ("changing this file means
changing that one too", for example a schema change touching both the model
definition and the migration list). When a finding names only one half of such
a pair, the real scope is the whole pair. Miss this and you will fix half the
problem and report it as done.

## Step 3 — Group, delegate, verify

**Findings in the same file, or in files bound together by a paired-file rule,
go in one Agent call.** Split across calls, they overwrite each other or land
half-applied. Findings whose files (and pairs) do not overlap can run in
parallel even at different tiers.

Even when files don't overlap and no paired-file rule applies, prefer grouping
findings that touch the same user-facing flow (error handling, form
validation, a shared UI state) into one call. Splitting by file boundary alone
can leave sibling files with mismatched tone or behavior after separate
subagents fix them independently.

**When a group mixes tiers, send the whole group at the highest tier present.**
A mechanical finding sharing a file with a high-risk one does not get handled
mechanically. Step 2's "take the higher one" applies here too.

Each Agent call states:

- the group's findings verbatim: file, line, summary, failure scenario
- that it fixes **these findings only**; no fixing other things it happens to notice
- the relevant `CLAUDE.md` rules, quoted, including the paired-file obligation
- that it deletes any scratch or cache files its own testing creates (temp
  scripts, `__pycache__`)
- that it must not commit; nothing is committed until the user explicitly asks

**At every tier, a subagent reporting "done" is not evidence that it is done.**
Tiers differ in how heavy the check is, not in whether there is one:

- Mechanical: confirm the result directly (the file it says it deleted is
  actually gone: `test -f`, `git status`).
- Ordinary: that, plus run the project's smoke or test script if one exists.
  For UI/frontend findings, a passing build is not the check. If a browser
  automation tool (e.g. Playwright) is available, exercise the actual behavior
  the finding names.
- High-risk: that, plus read the diff yourself and confirm it stayed inside the
  finding's scope before accepting it.

**When a check comes back wrong (the file is still there, the diff wandered
outside scope, tests broke), do not quietly move on:**

1. Retry at the same tier, stating what failed and bounding the scope harder.
2. If it fails again, retry once, one tier up (mechanical → ordinary,
   ordinary → high-risk). Never escalate to a model outside the Step 2 table.
3. If that retry also fails, or there is no tier above in the Step 2 table, stop
   retrying. Report what was attempted and the current state. Do not leave a
   silent failure, and do not loop.

## Step 4 — Report

One row per finding: summary, tier chosen, model actually used, the one-line
reason, and the outcome (fixed, skipped, skipped (stale), no change needed,
failed after retry).

Collect the unverified skips (`PLAUSIBLE`, or no verdict in review output)
separately and say plainly that they were left alone pending verification. When
there are several (roughly five or more), also write that list to a file (e.g.
`review-fix-pending.md`) alongside reporting it in the conversation, because the
list otherwise disappears once the conversation ends. Report that file as a
change this skill made, and leave it out of any commit.

Compare the final `git -c core.quotePath=false status --porcelain --untracked-files=all` and hashes
against the step 1 baseline and show **only what this skill changed.** New paths
are this skill's. A baseline path whose hash or status changed (for example,
modified to deleted), or that has vanished from the final status, was edited
here too; label it "already modified before, also edited by this skill." Only
baseline paths with an unchanged hash are named as pre-existing and unrelated,
never folded into one undifferentiated "files changed" list.

Nothing is committed or pushed until the user asks.

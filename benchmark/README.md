# review-fix benchmark

Nine small cases, each a code review finding with a known correct fix. They
exist to test two things the main README claims but has not measured:

1. **Grading.** Does review-fix put each finding in the tier a careful reviewer
   would? Compare the tier the skill reports with `cases/<name>/expected.json`.
2. **Fixing.** At a given model tier, does the fix land and stay inside the
   finding's scope? `verify.py` answers both halves: did the intended change
   happen, and did anything else change.

What it does **not** measure is token cost: neither the grading overhead nor
the savings from cheaper fix models. If you want those numbers, read them off
`/cost` (or your usage page) for each run and write them into your results.
The runner does not collect them.

No results are published yet.

## Requirements

Python 3.8 or later, standard library only. Some fixture files import FastAPI
or SQLAlchemy, but the verifiers only read those as text.

## Safety

- `prepare` writes only into a new directory, an empty one, or one an earlier
  `prepare` created (it leaves a `.review-fix-bench` marker). It refuses
  anything else and never deletes a folder it did not make. With no workdir it
  creates a fresh temporary directory.
- `verify` runs the code a model edited inside the verifier's Python process.
  Treat that like running untrusted code: use a throwaway directory, ideally
  inside a container or VM. `risk-02` is about killing processes, so while it
  verifies, imports of `os`, `signal`, `subprocess`, `psutil` and `ctypes` get
  an inert stand-in.

## Commands

```
python benchmark/run.py selftest                   # every case: FAIL unfixed, PASS on its reference fix
python benchmark/run.py prepare <case> [workdir]   # copy a case's starting files
python benchmark/run.py show <case>                # print the finding to hand over
python benchmark/run.py verify <case> <workdir>    # PASS, or FAIL with reasons
```

## Protocol

1. `python benchmark/run.py prepare <case>` and note the workdir it prints.
2. Open Claude Code in that workdir. Do not mention the case name in the
   session: names start with the expected tier (`mech-`, `ord-`, `risk-`).
3. Measure one of:
   - **Grading.** Run `/review-fix` with the output of `show <case>` as the
     argument. Record the tier the skill reports.
   - **Fixing at one tier.** Start the session on that model (for example
     `claude --model haiku`), paste the output of `show <case>`, and ask for
     that fix only.
4. `python benchmark/run.py verify <case> <workdir>`.
5. Record the result. Run each case several times per model; one run says
   little.

A results table can be as simple as:

| date | case | mode | model | tier reported | verify | tokens (optional) | notes |
|---|---|---|---|---|---|---|---|

## Cases

| Case | What the finding is about |
|---|---|
| `mech-01-dead-file` | A template nothing routes to anymore |
| `mech-02-unused-import` | Two imports the module never uses |
| `mech-03-typo-constant` | A typo in one user-facing message |
| `ord-01-wrong-operator` | One comparison in a filter reversed |
| `ord-02-missing-none-check` | An unparseable date crashes the whole run |
| `ord-03-unstable-key` | Rows without a date collide on the same key |
| `risk-01-swallowed-exception` | An alert goes out before the commit that records it |
| `risk-02-kill-by-path` | Test cleanup kills the production server on another port |
| `risk-03-paired-schema` | A column change that `CLAUDE.md` says must touch two files |

## Adding a case

```
cases/<name>/
  files/          the starting state, copied into the workdir
  finding.md      what the reviewer reported; never the expected tier
  expected.json   {"tier": "mechanical" | "ordinary" | "high-risk"}
  verify.py       uses harness.main; checks the fix landed and nothing else changed
  reference/      a correct fix, overlaid on files/; reference/DELETE lists paths to remove
```

Then run `selftest`. It rejects a case whose verifier passes the untouched
starting state, crashes instead of reporting, or rejects the reference fix.

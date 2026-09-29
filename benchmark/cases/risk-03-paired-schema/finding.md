# Finding

**File:** `app/models.py:8`
**Verdict:** CONFIRMED

`Show` has no `poster_url` column, so the collector's poster field is silently
dropped on insert. The column needs to be added.

**Failure scenario:** posters never appear on the site, and nobody can tell
why, because the write succeeds.

**Note:** the project's CLAUDE.md is in the working directory. Read it before
editing.

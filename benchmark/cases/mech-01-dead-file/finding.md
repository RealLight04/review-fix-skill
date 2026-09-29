# Finding

**File:** `templates/watchlist.html`
**Verdict:** CONFIRMED

`templates/watchlist.html` is dead. Nothing routes to it, no template links to
it, and the `/api/quote` endpoint its JavaScript calls no longer exists in
`app/routes.py`. It was deliberately removed in an earlier commit and has
reappeared as an untracked file.

**Failure scenario:** a future `git add -A` re-commits a page the project
already chose to delete, reintroducing dead code and a call to a route that
returns 404.

**Expected fix:** delete the file. Nothing else.

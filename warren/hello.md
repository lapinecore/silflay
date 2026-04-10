# GitHub-as-Social-Media: lapinecore Profile Feed

## Context

The `lapinecore/lapinecore` repo is the GitHub profile README — visible at github.com/lapinecore. The goal is to turn it into a lightweight social media feed: releases from tagged project repos become posts, surfaced in the profile README. Archive files are the canonical feed; README is a rendered view of the top N.

No automated triggers for now. You run the script locally whenever you want to sync.

---

## Repo Topic Tags

| Topic | Repo type | What counts as a post |
|-------|-----------|----------------------|
| `lapinecore-project` | software, 3D printables, etc. | new **releases** only |
| `lapinecore-feed` | writing, silflay, scratchpad | new `.md` files added to `warren/` subdirectory |

---

## Architecture

Convention: all tooling/config lives in `.lapine/` — applies to every lapinecore repo, not just this one.

```
lapinecore/lapinecore/
├── README.md              ← generated, top N posts (must be at root)
├── archive/               ← browsable feed content (at root by design)
│   └── YYYY-MM/
│       └── DD-slug.md     ← one file per post
└── .lapine/               ← all machinery, never clutters root
    ├── update_feed.py
    ├── requirements.txt
    └── state.json         ← cursor: last-processed point per repo
```

**Post file format** (`archive/YYYY-MM/DD-slug.md`):
```markdown
---
title: Widget v2.0
date: 2026-04-08
repo: lapinecore/widget
type: release
url: https://github.com/lapinecore/widget/releases/tag/v2.0
summary: New export formats and better performance.
---
```

Body is optional — short posts can include full content; longer ones use summary + link.

---

## Script: `update_feed.py`

**Config (top of file):**
```python
GITHUB_USER   = "lapinecore"
FEED_SIZE     = 10          # posts shown in README
ARCHIVE_DIR   = "archive"
STATE_FILE    = ".lapine/state.json"
```
GitHub token read from env var `GITHUB_TOKEN`.

---

### Incremental state: `.lapine/state.json`

Tracks the last-processed point per repo so each run only fetches *new* content:

```json
{
  "lapinecore/widget": {
    "type": "project",
    "last_release_id": 12345678
  },
  "lapinecore/siflay": {
    "type": "feed",
    "last_commit_sha": "abc123def456"
  }
}
```

- **project repos**: store `last_release_id` (GitHub release ID, integer). On next run, fetch releases and stop when `release.id <= last_release_id`.
- **feed repos**: store `last_commit_sha`. On next run, use `GET /repos/{owner}/{repo}/commits?since={sha_date}` and filter for `.md` file changes only.

State file is committed to the repo so it persists across machines.

---

### What it does when run:

1. **Load state** from `.lapine/state.json` (empty dict if first run)
2. **Fetch project repos** — `GET /search/repositories?q=topic:lapinecore-project+user:{GITHUB_USER}`
3. **For each project repo:** fetch releases newer than `last_release_id` → write archive files → update cursor
4. **Fetch feed repos** — `GET /search/repositories?q=topic:lapinecore-feed+user:{GITHUB_USER}`
5. **For each feed repo:** fetch commits since `last_commit_sha` → filter for `.md` file additions under `warren/` → write archive files → update cursor
6. **Save updated state** to `.lapine/state.json`
7. **Read all archive files**, sort by date descending, take top `FEED_SIZE`
8. **Regenerate README.md**

---

## README Output Format

```markdown
# lapinecore

<!-- optional: a static header line you control -->

---

### [Widget v2.0](https://github.com/lapinecore/widget/releases/tag/v2.0)
*April 8, 2026 · [lapinecore/widget](https://github.com/lapinecore/widget)*

New export formats and better performance.

---

### [title](url)
*date · [repo](repo_url)*

summary or full body

---

*[all posts →](archive/)*
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `.lapine/update_feed.py` | Main script |
| `.lapine/requirements.txt` | `requests` |
| `.lapine/state.json` | Cursor state (created by script on first run, committed) |
| `archive/` | Browsable feed content (created by script if absent) |

README.md is overwritten by the script (not hand-edited after initial setup).

---

## Verification

**First run (project repo):**
1. Add `lapinecore-project` topic to a repo that has at least one release
2. `export GITHUB_TOKEN=...`
3. `python .lapine/update_feed.py`
4. Confirm `archive/YYYY-MM/` has a file for the release
5. Confirm `.lapine/state.json` has `last_release_id` set for that repo
6. Confirm `README.md` shows the post
7. Run again — confirm no new archive file, no README change

**First run (feed repo):**
1. Add `lapinecore-feed` topic to silflay
2. Add a `.md` file to `silflay/warren/`
3. Run script — confirm archive file created
4. Confirm `.lapine/state.json` has `last_commit_at` set for silflay
5. Run again — confirm no re-processing
6. Confirm a `.md` added outside `warren/` (e.g. root) is NOT picked up

**End-to-end:**
5. Push everything to GitHub, visit github.com/lapinecore — README renders as feed

---

## Out of Scope (for now)

- Automated GitHub Action trigger
- siflay "quick post" handling (non-release posts)
- Pagination for repos/releases with many entries

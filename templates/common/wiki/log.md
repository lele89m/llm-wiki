# Wiki Log

Append-only chronological record of all operations.

**Format**: `## [YYYY-MM-DD] operation | description`
**Operations**: `ingest` | `query` | `lint` | `update`

**Quick grep**:
```bash
grep "^## \[" wiki/log.md | tail -10    # last 10 entries
grep "ingest" wiki/log.md               # all ingests
```

---

<!-- entries below, oldest at top — append new entries at the bottom -->

# Global picker and creation order

Vini approved this behavior on 2026-11-16. Running `left-undone` without arguments always lists verifiable Herdr conversations regardless of directory. Choosing a conversation opens its panel or reveals its existing panel. `--repo` remains an explicit filter.

The panel opens newest first. A top button and key 6 toggle newest or oldest first. Each item shows its local creation time, which stays fixed across edits. Unknown dates sort last in either direction, with ties broken by ID. Sort across all sources. The order applies for the current opening. Selections follow IDs.

## Approaches

Sorting in the panel preserves the existing internal order for other consumers. A separate table with immutable timestamps makes migration compatible with older processes and independent of the curator's conflict-detection clock. Neither IDs nor mutable curation timestamps establish creation dates. Legacy records without a verified source display “unknown date”. New imports use their local arrival time. Collected items use a valid transcript timestamp when available.

## Boundaries

Use the Python standard library and keep the existing models. Preserve identity checks, concurrency, history, tombstones and existing Markdown formats. The four curation improvements are separate work. Leave the fix/codex-active-thread worktree intact. Avoid commits, pushes and Herdr restarts. Validate with temporary state and test sessions only. Install files after testing.

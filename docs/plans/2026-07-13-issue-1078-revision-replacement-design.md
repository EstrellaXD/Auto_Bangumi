# Issue #1078: revision collision and automatic replacement

Date: 2026-07-13

## Context

When a completed V1 episode already owns the canonical media name, a later V2
release resolves to the same `SxxExx` target. The current renamer has no durable
terminal state for that collision. It also treats qBittorrent `409`, an aria2
`FileExistsError`, delayed verification, and network errors as the same boolean
failure. The in-memory five-minute cooldown eventually expires (or disappears on
restart), so AutoBangumi retries and can send repeated Telegram notifications.

The parser is not at fault: V1 and V2 correctly describe the same episode and
therefore intentionally share a canonical library path.

## Product decisions

- Add a global `revision_conflict_policy` setting with `hold` and `replace`.
- Default to `hold` for backward-compatible, non-destructive behavior.
- In `replace`, delete the old torrent and its data after the new revision is
  promoted successfully.
- A replacement is eligible only when Bangumi association, media type, effective
  season/episode, subtitle group, and resolution match, and the new revision is
  strictly higher.
- Automatic replacement initially supports only torrents whose complete raw file
  list contains exactly one file. Collections, season packs, torrents with a
  subtitle/NFO/extra file, and mixed resources fall back to `hold`.
- Use a recoverable three-stage operation: stage V1, promote V2, remove V1.

## Rename result contract

Replace the downloader rename boolean with a typed result:

- `RENAMED`: the target path was verified.
- `ALREADY_APPLIED`: the requested target is already owned by this task.
- `DESTINATION_EXISTS`: the downloader or filesystem positively identified a
  target collision.
- `RETRYABLE_FAILURE`: transport, server, filesystem, or verification failure
  that may succeed later.

qBittorrent `409` and aria2 `FileExistsError` map to
`DESTINATION_EXISTS`. Network errors and an unverified 2xx response map to
`RETRYABLE_FAILURE`. The facade must preserve the result rather than reducing it
to `bool`.

## Durable operation model

Add a `rename_operation` table keyed by downloader type, task id, save path,
source path, and target path. It stores operation kind, phase, old owner task,
deterministic temporary path, parsed identity metadata, attempt counters,
retry time, notification time, last error, and timestamps.

Each replacement phase is fenced by an expiring database lease and committed
with compare-and-swap semantics. This supplements the target uniqueness index:
multiple processes may observe the same row, but only the lease holder can run
the phase and persist its transition.

Normal conflict phases are `CONFLICT` and `RETRY_WAIT`. Replacement phases are:

```text
PLANNED -> OLD_STAGED -> NEW_PROMOTED -> OLD_REMOVED -> DONE
```

Downloader calls never run inside a SQLite transaction. Each step first
reconciles observable task/file state, performs one idempotent action, verifies
the result, and only then persists the next phase. A uniqueness constraint on the
canonical target prevents two rename loops from replacing it concurrently.

Recovery rules:

- If V1 already has the deterministic temporary path, advance to `OLD_STAGED`.
- If V2 already has the canonical path, advance to `NEW_PROMOTED`.
- Before promotion, a permanent failure restores V1 if the canonical path is
  empty and records a conflict.
- After promotion, never roll back to V1; retry forward cleanup until the old task
  is gone.
- Existing `ab:renamed` tasks are filtered before file and offset queries.
  Completion tagging moves to the end of the media/subtitle pass.

## Replacement admission

Parse both original torrent names with the configured generic parser. Require:

1. different downloader task ids but the same numeric `ab:<bangumi_id>` link;
2. normalized save paths and canonical output paths are equal;
3. both releases are single, numbered resources;
4. media type and effective season/episode identity are equal after offsets;
5. normalized subtitle groups and resolutions are equal;
6. `new_revision > old_revision`, treating an absent revision as V1;
7. both complete downloader file lists contain exactly one file;
8. exactly one old task owns the canonical path.

Any ambiguity is a terminal `hold` conflict. RSS admission remains unchanged;
download policy and rename conflict policy stay separate.

## Downloader behavior

For qBittorrent, `renameFile` stages and promotes each task, with file-list
verification after every action. `deleteFiles=true` is allowed only after the
single-file guard has passed.

For aria2, rename remains an AutoBangumi filesystem move recorded in
`aria2_gid.renamed_paths`. Before moving a file, aria2 persists an intent with
the source and target paths plus the source filesystem identity. A restart may
finalize the move only when the target still has that exact identity; an
unrelated existing target remains a conflict. Old-version cleanup must resolve
the old gid's current renamed path, delete that deterministic temporary file,
call `forceRemove` without generic file deletion, and delete the sidecar only
after success or an explicit not-found response. This prevents cleanup from
deleting the V2 file now occupying aria2's original path.

## Configuration and UI

Expose one global select in the existing Bangumi management settings:

- Keep existing file (`hold`, default)
- Replace with higher revision (`replace`)

The destructive option includes explicit help text stating that the old torrent
and its data are deleted only after successful V2 promotion. The existing config
form remains the source of truth; no new component or store is needed.

## Notifications and recovery

Create a typed rename-conflict system event. Emit it only when an operation first
enters `CONFLICT`; never reuse the successful episode notification. Retryable
errors do not notify on every backoff cycle.

Expose authenticated endpoints to list conflict operations and request a retry.
Retry clears terminal state only; the next rename pass revalidates every safety
condition. Completed and stale retry records are pruned with bounded retention.

## Verification

Tests cover qB and aria2 result mapping, completion-tag filtering, two rename
cycles plus process restart, persistent retry backoff, strict V1/V2 admission,
rollback before promotion, forward recovery after promotion, aria2 renamed-path
cleanup, multi-file fallback, one-shot conflict notification, migration
idempotence, config round-trip, and the Vue setting. The exact Mikan Classic V1
and V2 titles from #1078 are retained as a regression fixture.

Release target: `3.3.4-beta.2` from `3.3-dev`.

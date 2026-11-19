# Download review example

Requires SDK 0.7. Select `download-review/review` under **Settings → Plugins → Download admission**. The default holds downloads. Enabling `approved` allows parsed episodes and skips older revisions when the same RSS batch contains a newer release with the same group, subtitle, resolution and source.

This example demonstrates the host gate and candidate snapshots. A production version selector should store decisions per entry, paginate candidates, and account for pending submissions; use `ctx.downloads.submissions()` for the shared intent ledger.

Run `uv run pytest` and `ab-plugin validate .` before packaging. No private host imports are needed.

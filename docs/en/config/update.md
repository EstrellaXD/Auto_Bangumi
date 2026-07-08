# Software Update

![update](/image/config/update.png){width=700}{class=ab-shadow-card}

The Software Update panel checks, applies and rolls back AutoBangumi updates.

- **Update channel**:
  - Stable: stable releases only.
  - Beta: includes prereleases.
- **Check automatically**: checks once when entering the settings page; the backend also checks periodically and writes update notifications.
- **Check for updates**: manually refreshes version information for the current channel.
- **Update now**: downloads, verifies, unpacks and applies an update, then restarts.
- **Rollback**: appears when a rollback target exists.

::: warning
In-app updates require the container to run with a restart policy such as `restart: unless-stopped`. Update bundles are checked with sha256 and ed25519 signatures.
:::

## `config.json`

Section: `update`

| Key | Description | Type | WebUI field | Default |
| --- | --- | --- | --- | --- |
| `channel` | `stable` or `beta` | string | Update channel | `stable` |
| `auto_check` | Automatically check for updates | boolean | Check automatically | `true` |

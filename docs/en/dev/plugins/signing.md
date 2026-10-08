# Signing and Distribution

A plugin has one of four sources. The trust level is different for each:

| Source | Location | Signature | How to enable |
| --- | --- | --- | --- |
| Built-in | Part of AB | Released with AB | Available by default |
| Signed catalog | `config/plugins/<id>/<version>/` | ed25519 signature, AB verifies | Call the install API. Install also enables |
| Local directory | `config/plugins/local/<id>/` | None | Turn on "Allow unsigned plugins", then enable |
| pip package | entry point `autobangumi.plugins` | None | Same as above |

When two plugins have the same id, the priority is: built-in > signed catalog > local > pip. For an unsigned plugin, the user must first turn on "Allow unsigned plugins" in Settings → Plugins, then enable the plugin. While the switch is off, AB runs no code of an unsigned plugin.

## The signed catalog

AB downloads `catalog.json` from the GitHub release `plugins`. The catalog contains:

```json
{
  "schema": 2,
  "plugins": [
    {
      "id": "ntfy-notifier",
      "name": "ntfy notifier",
      "version": "0.1.0",
      "kind": "plugin",
      "extension_points": ["notifier"],
      "sdk": ">=0.5,<1",
      "min_ab_version": "4.0.0",
      "description": "…",
      "asset": "ntfy-notifier-0.1.0.zip",
      "sha256": "…"
    }
  ]
}
```

`catalog.json` and each zip have a `.sig` file with the same name. It is an ed25519 signature over all bytes of the file, encoded in base64. The public key is part of the AB image. It is the same key that the online update uses.

At install time AB checks, in this order:

1. The signature of `catalog.json`.
2. The sha256 and the signature of the zip. AB refuses unsigned packages and packages with a bad signature.
3. Zip-slip protection when it unpacks. AB refuses paths that leave the target directory.
4. The manifest must pass the same checks as `ab-plugin validate`. The `id` and `version` of the manifest must equal the catalog entry. The `sdk` range must include the current SDK. The AB version must be at least `min_ab_version`.
5. The id must not be a reserved id (`core`, `local`) and must not equal a built-in plugin.

After these checks, AB unpacks the plugin to `config/plugins/<id>/<version>/`, writes `installed.json` that points to that version, then loads and enables the plugin. Uninstall removes only directories that have `installed.json`. It never removes a local plugin of the user.

A catalog plugin can depend only on the standard library and on packages that AB already has. AB does not run pip. Put third-party pure-Python libraries in `vendor/`.

::: tip Install from the WebUI
In Settings → Plugins, go to the "Plugin catalog" area and select "Browse catalog". You can then install and update catalog plugins. A plugin installed from the catalog has an "Uninstall" button on its card. Built-in, local and pip plugins do not have one.
:::

API:

| Request | Description |
| --- | --- |
| `GET /api/v1/plugins/catalog` | The catalog entries and the version that is installed here. Returns 502 if the catalog is unreachable |
| `POST /api/v1/plugins/{id}/install` | Install and enable |
| `DELETE /api/v1/plugins/{id}` | Uninstall |

::: warning Reserved paths
The host owns `/plugins/{id}/install` and `/plugins/catalog`. The `api_router` of a plugin must not use `install`, `catalog` or `web` as a route path.
:::

## Publish a plugin

Only a maintainer who has the signing private key can publish the catalog. The steps:

1. The author runs `ab-plugin pack .` and gets a zip.
2. The author opens a GitHub issue with the zip and the source address to ask for a listing.
3. The maintainer reviews the source, then runs this command on one or more zips:

   ```bash
   uv run --no-project --with cryptography python scripts/build_plugin_catalog.py \
       --key ~/.autobangumi/update-signing-key.pem --min-ab 4.0.0 \
       --out release-assets dist/*.zip
   ```

   The script writes `catalog.json`, the zips and their `.sig` files.
4. The maintainer uploads the whole directory to the release `plugins` (and overwrites the old files).

A user sees the new version through `GET /api/v1/plugins/catalog`.

## Publish the SDK

The SDK is a wheel in the attachments of the 4.0 beta and stable GitHub releases. CI builds it with `uv build --wheel backend/sdk`. The same release has `autobangumi-plugin-skill-<version>.zip`. It is a plugin-development skill for AI coding assistants. Unpack it in the skills directory of the assistant.

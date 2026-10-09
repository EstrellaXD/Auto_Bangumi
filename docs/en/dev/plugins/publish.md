# List a Plugin

The source of a plugin stays in the author's own public GitHub repository. To list or update a plugin, the author opens a PR to `EstrellaXD/Auto_Bangumi` (base branch `4.0-dev`). The PR adds or edits one file: `plugins/registry/<id>.toml`.

CI checks the code that this file points to. A maintainer reads the code and merges. After the merge, CI packs and signs the plugin and publishes it to the signed catalog.

::: tip Version requirement
AutoBangumi 4.0.0-beta.2 and later trust the plugin key. 4.0.0-beta.1 cannot install plugins from the new catalog.
:::

## The registry entry

The file `plugins/registry/<id>.toml` has three fields:

```toml
repo = "owner/name"   # public GitHub repository
commit = "<40-char full SHA>"   # tags can move, a SHA cannot
path = "."   # optional subdirectory of the plugin, default is the repo root
```

- The file name must equal the `id` in `plugin.toml`.
- `commit` must be a full 40-character SHA. A short SHA or a tag is rejected.
- The name, version, `sdk` range, authors and permissions come from `plugin.toml` at that commit. Do not repeat them in the entry.

A PR can change several entries. We recommend one plugin per PR.

## Steps

1. Prepare the repository. It must be public. Commit `plugin.toml`, the plugin code and `tests/`. If the plugin has a frontend, put its source in `web-src/` and commit `package.json` and `pnpm-lock.yaml`.
2. Check locally:

   ```bash
   ab-plugin validate .
   uv run pytest
   pnpm install --frozen-lockfile && pnpm build   # only with a frontend
   ```

   `tests/` must contain at least 1 test, and all tests must pass. The contract tests that `ab-plugin new` generates meet this rule.
3. Push the code to the public repository.
4. Get the full SHA:

   ```bash
   git rev-parse HEAD
   ```

5. Fork `EstrellaXD/Auto_Bangumi`, add `plugins/registry/<id>.toml`, and open a PR to `4.0-dev`. Change only files under `plugins/registry/`. In the PR description, use the plugin template (`?template=plugin.md`) and tick each item.

## CI rules

The job `check` of the workflow `plugin-registry.yml` runs on the PR. It has read-only permissions and no secrets. For each changed entry, it first fetches the pinned commit. Then it checks the rules below. If one rule fails, CI rejects the entry:

- `commit` is not a full 40-character SHA.
- The file name differs from the manifest `id`.
- The `id` clashes with a built-in plugin, or it is a reserved id.
- `ab-plugin validate` fails.
- For an update, the version is not higher than the listed version.
- For an update, `repo` changed. To transfer a plugin, refer to "Transfer a plugin" below.
- `tests/` has no tests, or a test fails.
- The plugin has a frontend but no `web-src/`. A frontend must be committed as source in `web-src/`, with `package.json` and `pnpm-lock.yaml`. CI runs `pnpm install --frozen-lockfile --ignore-scripts && pnpm build` with pnpm 9 and Node 20. It resolves `@autobangumi/plugin-ui` to the package of this repository. It discards any committed `web/`.

When the checks pass, CI packs the plugin with `ab-plugin pack` and writes a Job Summary with:

- The version change.
- A compare link (update) or a tree link (new plugin).
- The validate and test results.
- The extension points.
- The declared permissions.
- Whether the plugin has a frontend.
- The sha256 of the zip.

## After the merge

A maintainer (CODEOWNERS: @EstrellaXD) reads the code at the compare link and merges.

After the merge, CI rebuilds the catalog incrementally. An entry whose `commit` did not change reuses its existing zip. CI then signs `catalog.json` and every zip with a dedicated plugin signing key. This key is not the update key. Last, CI uploads the files to the GitHub release `plugins`.

A user sees the new plugin or version through `GET /api/v1/plugins/catalog`. For the catalog format and the signature, refer to [Signing and Distribution](/en/dev/plugins/signing).

## Update a plugin

1. Change the code in your repository and raise `version` in `plugin.toml`.
2. Push, then get the new full SHA with `git rev-parse HEAD`.
3. Open a PR to `4.0-dev`. In `plugins/registry/<id>.toml`, change only `commit` to the new SHA.

The version must be higher than the listed version. If not, CI rejects the PR.

## Transfer a plugin

You cannot change `repo` in an update. To move a plugin to another repository, use two PRs:

1. The first PR removes `plugins/registry/<id>.toml`.
2. After it is merged, the second PR adds the file again with the new `repo`. CI then checks it as a new plugin, so the old version does not limit it.

## Remove a plugin

Open a PR that removes `plugins/registry/<id>.toml`. After the merge, the plugin leaves the catalog. Copies that users already installed are not deleted.

## Dependencies and redistribution

- A plugin can depend only on the standard library and on packages that AutoBangumi already ships. Put third-party pure-Python libraries in `vendor/`.
- A license is not required. But by opening the PR, the author agrees that AutoBangumi redistributes the packed plugin in its release.

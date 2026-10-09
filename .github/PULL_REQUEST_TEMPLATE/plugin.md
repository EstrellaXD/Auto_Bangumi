<!-- Plugin listing PR. Base branch: 4.0-dev. Docs: https://autobangumi.org/dev/plugins/publish -->

## Plugin

- id:
- repo:
- commit (40-char SHA):
- New plugin / update (old version -> new version):

## Author checklist

- [ ] This PR changes only files under `plugins/registry/`.
- [ ] `commit` is a full 40-character SHA, and it is pushed to a public repository.
- [ ] `sha256` matches the value in the CI summary (leave it out in the first push; CI shows it).
- [ ] The file name equals the `id` in `plugin.toml`.
- [ ] `tests/` has at least 1 test, and all tests pass.
- [ ] `ab-plugin validate` passes.
- [ ] For an update, `version` is higher than the listed version, and `repo` is unchanged.
- [ ] If the plugin has a frontend, its source is in `web-src/` with `package.json` and `pnpm-lock.yaml`.
- [ ] The plugin depends only on the standard library and packages that AutoBangumi ships. Other pure-Python libraries are in `vendor/`.
- [ ] I agree that AutoBangumi redistributes the packed plugin in its release.

## Maintainer review checklist

- [ ] I read all code at the compare link (update) or tree link (new plugin) in the Job Summary.
- [ ] The plugin connects only to documented hosts.
- [ ] The plugin writes nothing outside `config/`.
- [ ] If there is a frontend, I read `web-src/` line by line. It runs on the main origin.
- [ ] The declared `permissions` match what the code does.

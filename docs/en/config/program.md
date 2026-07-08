# Program Settings

## WebUI

![program](/image/config/program.png){width=700}{class=ab-shadow-card}

The Config page has a searchable section rail on the left. `program` and `log` are global settings; after changing them, click **Save & restart** at the bottom.

- **RSS check interval**: how often AutoBangumi refreshes RSS feeds and creates download tasks, in seconds.
- **Rename interval**: how often AutoBangumi checks downloader tasks and organizes files, in seconds.
- **WebUI port**: the backend and WebUI port. In Docker deployments, update the container port mapping as well.
- **Debug**: enables verbose logs. Disable it after troubleshooting.

## `config.json`

Section: `program`

| Key | Description | Type | WebUI field | Default |
| --- | --- | --- | --- | --- |
| `rss_time` | RSS check interval | integer seconds | RSS check interval | `900` |
| `rename_time` | Rename interval | integer seconds | Rename interval | `60` |
| `webui_port` | WebUI port | integer | WebUI Port | `7892` |

Section: `log`

| Key | Description | Type | WebUI field | Default |
| --- | --- | --- | --- | --- |
| `debug_enable` | Enable debug logs | boolean | Debug | `false` |

# Frequently Asked Questions

## WebUI

### WebUI Address

The default port is 7892. For server deployments, access `http://serverhost:7892`. For local deployments, access `http://localhost:7892`. If you changed the port, remember to also update the Docker port mapping.

### Default Username and Password

- Default username: `admin`, default password: `adminadmin`.
- Please change your password after first login.

### Changing or Resetting Password

- Change password: After logging in, click `···` in the upper right, click `Profile`, and modify your username and password.
- There is currently no simple password reset method. If you forget your password, delete the `data/data.db` file and restart.

### Why don't my configuration changes take effect?

- After changing configuration, click the **Apply** button, then click **Restart** in the `···` menu to restart the main process.
- If Debug mode is enabled, click **Shutdown** in the `···` menu to restart the container.

### How to check if the program is running normally

The new WebUI has a small dot in the upper right corner. Green means running normally, red means an error occurred and the program is paused.

### Poster wall not showing images

- If your version is 3.0:
    AB uses `mikanani.me` addresses as poster image sources by default. If images aren't showing, your network cannot access these images.
- If your version is 3.1 or later:
  - If posters show an error icon, the images are missing. Click the refresh poster button in the upper right menu to fetch TMDB posters.
  - If posters fail to load, clear your browser cache.
  - When using `mikanime.tv` as the RSS address, client-side proxies may prevent poster loading. Add a `direct` rule for it.

## How Does v3.0 Manage Bangumi

After upgrading to v3.0, AB can manage anime torrents and download rules in the WebUI. It relies on the torrent download path and rule name.
If you manually change torrent download paths in QB, you may encounter issues like notifications missing posters or failed torrent deletion.
Please manage anime and torrents within AB as much as possible.

## Downloads and Keyword Filtering

### Download Path

**What should I put for the download path?**
- This parameter just needs to match your qBittorrent configuration:
  - Docker: If qB uses `/downloads`, then set `/downloads/Bangumi`. You can change `Bangumi` to anything.
  - Linux/macOS: If it's `/home/usr/downloads` or `/User/UserName/Downloads`, just append `/Bangumi` at the end.
  - Windows: Change `D:\Media\` to `D:\Media\Bangumi`

### Downloads not starting automatically

Check AutoBangumi's logs for any torrent-related entries.
- If none exist, check if your subscription is correct.

### Downloads not saved in the correct directory

- Check if the [download path](#download-path) is correct.
- Check qBittorrent's PGID and PUID configuration for folder creation permissions. Try manually downloading any torrent to a specified directory — if errors occur or the directory isn't created, it's a permissions issue.
- Check qBittorrent's default settings: Saving Management should be set to Manual (Saving Management >> Default Torrent Management Mode >> Manual).

### Downloading many unsubscribed anime

- Check if your Mikan subscription includes all subtitle groups for a single anime. Subscribe to only one group per anime, and enable advanced subscriptions.
  - Advanced subscriptions can be enabled in Mikan Project's user settings.
- Regex filtering may be insufficient — see the next section for expanding regex.
- If neither applies, report with logs at [Issues][ISSUE].

### How to write filter keywords

Filter keywords in AB are regular expressions, added only when rules are created. To expand rules after creation, use the WebUI (v3.0+) to configure each anime individually.
- Filter keywords are regex — separate unwanted keywords with `|`.
- The default `720|\d+-\d+` rule filters out all collections and 720P anime. Add filters before deploying AB; subsequent environment variable changes only affect new rules.
- Common regex keywords (separated by `|`):
  - `720` — filters 720, 720P, 720p, etc.
  - `\d+-\d+` — filters collections like [1-12]
  - `[Bb]aha` — filters Baha releases
  - `[Bb]ilibili`, `[Bb]-Global` — filters Bilibili releases
  - `繁`, `CHT` — filters Traditional Chinese subtitles
- To match specific keywords, add in QB's include field: `XXXXX+1080P\+` where `1080P\+` matches 1080P+ releases.

### First deployment downloaded unwanted anime

1. Delete extra automatic download rules and files in QB.
2. Check subscriptions and filter rules.
3. Visit the resetRule API in your browser: `http://localhost:7892/api/v1/resetRule` to reset rules.
4. Restart AB.

### AB identifies fewer RSS entries than subscribed

In newer versions, AB's filter also filters all RSS entries by default. Don't add all filters at once. For fine-grained control, configure each anime individually in the WebUI.

### Filter keywords not working

- Check if the **global filter** parameter is set correctly.
- Check QB's RSS auto-download rules — you can see matched RSS on the right side, adjust download rules, and click save to identify which keyword is causing issues.

## Episode Completion

### Episode completion not working

Check if the **Episode completion** parameter is correctly configured.

## File Renaming

### Parse error `Cannot parse XXX`

- AB does not currently support parsing collections.
- If it's not a collection, report the issue on GitHub Issues.

### `Rename failed` or renaming errors

- Check file paths. Standard storage path should be `/title/Season/Episode.mp4`. Non-standard paths cause naming errors — check your qBittorrent configuration.
- Check if the `download path` is filled in correctly. Incorrect paths prevent proper renaming.
- For other issues, report on GitHub Issues.

### No automatic renaming

- Check if the torrent category in QB is `Bangumi`.
- AB only renames downloaded files.

### How to rename non-AB anime with AB

- Simply change the torrent's category to `Bangumi`.
- Note: The torrent must be stored in a `Title/Season X/` folder to trigger renaming.

### How to rename collections

1. Change the collection's category to `Bangumi`.
2. Change the collection's storage path to `Title/Season X/`.
3. Wait for the collection to finish downloading, and renaming will complete.

## Docker

### How to auto-update

Run a `watchtower` daemon in Docker to automatically update your containers.

[watchtower](https://containrrr.dev/watchtower) official documentation

### Updating with Docker Compose

If your AB is deployed with Docker Compose, use `docker compose pull` to update.
After pulling the new image, use `docker compose up -d` to restart.

You can also add `pull_policy: always` to your `docker-compose.yml` to pull the latest image on every start.

### What to do if an upgrade causes issues

Since configurations may vary, upgrades might cause the program to fail. In this case, delete all previous data and generated configuration files, then restart the container.
Then reconfigure in the WebUI.
If upgrading from an older version, first refer to the [upgrade guide](/changelog/2.6).

If you encounter issues not covered above, report them at [Issues][ISSUE] using the bug template.


[ISSUE]: https://github.com/EstrellaXD/Auto_Bangumi/issues

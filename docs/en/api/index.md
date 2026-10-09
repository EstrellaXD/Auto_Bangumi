# REST API Reference

AutoBangumi provides a REST API under `/api/v1`. The WebUI uses the same API.

**Base URL:** `http://your-host:7892/api/v1`

**Interactive docs:** This page lists only the endpoints and their purpose. For the request and response fields, use `http://your-host:7892/docs` on a running instance. FastAPI makes this Swagger UI from the code. Plugin routes are not in `/docs`.

## Authentication

AB accepts two types of credential:

- **Browser session**: send the form fields `username` and `password` to `POST /auth/login`. If the login is correct, AB sets the HttpOnly cookie `token`. The WebUI uses this method.
- **API token**: create a token with `scope=api` in Settings → Users & Access → API tokens (or call `POST /tokens`). AB shows the plain token one time only. Send it in the header `Authorization: Bearer <token>`.

```bash
curl -H "Authorization: Bearer $AB_TOKEN" http://your-host:7892/api/v1/status
```

- If a request has an `Authorization` header, AB checks only that token. It ignores the cookie.
- A request with no credential or a bad credential gets `401`.
- The account endpoints (`/auth/update`, `/users`, `/tokens`, and Passkey registration and management) accept only a browser session. An API token gets `403`.
- These endpoints need no authentication: `/auth/login`, `/passkey/auth/*`, the setup wizard `/setup/*` (`GET /setup/status` is always available; the other endpoints return `403` after setup is complete) and `/health` at the root path.
- `/auth/refresh_token` and `/auth/logout` ignore the `Authorization` header. They use only the session cookie. `refresh_token` returns `401` if there is no valid cookie. `security.login_whitelist` limits login and Passkey login.
- For local development, set the environment variable `AB_DEV_NO_AUTH=1` to skip all authentication. Do not set it in production.

## Authentication and accounts

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/auth/login` | Log in with user name and password. Sets the session cookie |
| `POST` | `/auth/refresh_token` | Extend the current session |
| `POST` | `/auth/logout` | End the current session and clear the cookie |
| `GET` | `/auth/me` | The current user |
| `POST` | `/auth/update` | Change the current account and rotate all of its sessions |
| `GET` / `POST` | `/users` | List / create users |
| `PATCH` / `DELETE` | `/users/{user_id}` | Change / delete a user |
| `GET` / `POST` | `/tokens` | List / create API tokens (`scope` is `api` or `mcp`; `expires_at` is optional) |
| `DELETE` | `/tokens/{token_id}` | Revoke a token |
| `POST` | `/passkey/register/options`, `/passkey/register/verify` | Register a Passkey |
| `POST` | `/passkey/auth/options`, `/passkey/auth/verify` | Log in with a Passkey |
| `GET` | `/passkey/list` | List the Passkeys of the current user |
| `POST` | `/passkey/delete` | Delete a Passkey |

## Program

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/status` | Version, run state and first-run flag |
| `POST` | `/start`, `/stop`, `/restart` | Start / stop / restart the background tasks |
| `POST` | `/shutdown` | Stop the program |
| `GET` | `/check/downloader` | Check that the default downloader is available |
| `GET` | `/log` | Read the log |
| `POST` | `/log/clear` | Clear the log |
| `GET` | `/update/check` | Get the latest version and the online update state |
| `POST` | `/update/apply` | Download and apply the latest update, then restart |
| `POST` | `/update/rollback` | Go back to the previous update. If there is no backup, go back to the version in the image |
| `GET` | `/health` (root path, not under `/api/v1`) | Liveness probe. Always returns `200`: `{"status", "version", "db_ok"}` |

## Configuration

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/config/get` | The current configuration. Secret fields are masked |
| `PATCH` | `/config/update` | Save and reload the configuration. A masked secret field keeps its old value |
| `POST` | `/config/llm/models` | List the models of the selected LLM provider |
| `GET` | `/config/llm/providers` | List the LLM providers |
| `POST` | `/config/llm/providers/{provider_id}/install` | Install an LLM provider plugin |
| `DELETE` | `/config/llm/providers/{provider_id}` | Remove an LLM provider plugin |
| `POST` | `/config/llm/providers/{provider_id}/auth/begin`, `/auth/complete` | Authorization flow for subscription providers |
| `GET` | `/config/llm/providers/{provider_id}/auth/status` | Authorization state |
| `DELETE` | `/config/llm/providers/{provider_id}/auth` | Disconnect the authorization |

## Bangumi

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/bangumi/get/all` | All bangumi rules |
| `GET` | `/bangumi/get/{bangumi_id}` | One rule |
| `PATCH` | `/bangumi/update/{bangumi_id}` | Change a rule |
| `DELETE` | `/bangumi/delete/{bangumi_id}` | Delete a rule |
| `POST` | `/bangumi/delete/many` | Delete many rules |
| `POST` | `/bangumi/disable/{bangumi_id}`, `/bangumi/enable/{bangumi_id}` | Disable / enable a rule |
| `POST` | `/bangumi/disable/many` | Disable many rules |
| `PATCH` | `/bangumi/archive/{bangumi_id}`, `/bangumi/unarchive/{bangumi_id}` | Archive / unarchive |
| `PATCH` | `/bangumi/{bangumi_id}/weekday` | Set the broadcast weekday manually |
| `GET` | `/bangumi/refresh/poster/all`, `/bangumi/refresh/poster/{bangumi_id}` | Refresh posters |
| `GET` | `/bangumi/refresh/calendar` | Refresh the broadcast calendar |
| `GET` | `/bangumi/refresh/metadata` | Refresh TMDB metadata and archive series that have ended |
| `POST` | `/bangumi/reset/all` | Delete all rules |
| `GET` | `/bangumi/needs-review` | Bangumi whose episode offset needs a check |
| `GET` | `/bangumi/suggest-offset/{bangumi_id}` | Suggest an offset from the TMDB episode counts |
| `POST` | `/bangumi/detect-offset` | Find a season or episode mismatch with TMDB |
| `POST` | `/bangumi/apply-offset/{bangumi_id}`, `/bangumi/apply-offset/many` | Apply the suggested offset and start a rename pass |
| `POST` | `/bangumi/dismiss-review/{bangumi_id}` | Clear the "needs review" flag |
| `GET` / `DELETE` | `/bangumi/{bangumi_id}/torrents` | List / delete the torrent records of the bangumi |
| `DELETE` | `/bangumi/{bangumi_id}/torrents/{torrent_id}` | Delete one torrent record |
| `GET` / `DELETE` | `/bangumi/torrents/orphans` | List / delete torrent records that belong to no bangumi |
| `GET` | `/bangumi/torrents/orphans/count` | Number of orphan torrent records |
| `DELETE` | `/bangumi/torrents/orphans/{torrent_id}` | Delete one orphan torrent record |

## Movies

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/movie/get/all`, `/movie/get/{movie_id}` | All movie rules / one movie rule |
| `PATCH` | `/movie/update/{movie_id}` | Change |
| `DELETE` | `/movie/delete/{movie_id}` | Delete |
| `DELETE` | `/movie/disable/{movie_id}` | Disable |
| `GET` | `/movie/enable/{movie_id}` | Enable |

## RSS feeds

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/rss` | All feeds |
| `POST` | `/rss/add` | Add a feed |
| `PATCH` | `/rss/update/{rss_id}` | Change a feed |
| `DELETE` | `/rss/delete/{rss_id}` | Delete a feed |
| `POST` | `/rss/delete/many` | Delete many feeds |
| `PATCH` | `/rss/disable/{rss_id}` | Disable |
| `POST` | `/rss/disable/many`, `/rss/enable/many` | Disable / enable many feeds |
| `POST` | `/rss/refresh/all`, `/rss/refresh/{rss_id}` | Refresh now |
| `GET` | `/rss/torrent/{rss_id}` | Torrents of the feed |
| `POST` | `/rss/analysis` | Analyze an RSS link and return the bangumi that AB finds |
| `POST` | `/rss/collect` | Download a full season (collect) |
| `POST` | `/rss/subscribe` | Subscribe |

## Search

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/search/bangumi?site=<site>&keywords=<keywords>` | Server-Sent Events. Sends the results one by one. Separate keywords with spaces |
| `GET` | `/search/provider` | Available search sites, including sites from plugins |
| `GET` / `PUT` | `/search/provider/config` | Read / save the search sites that the user configured |

## Downloader

AB 4.0 can have more than one downloader instance (`plugins.instances`). The torrent list includes all instances. Each item has a `downloader_id`.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/downloader/instances` | Downloader instances: `{"default": <default instance id>, "instances": [{"id", "provider"}]}` |
| `GET` | `/downloader/torrents` | Torrents of all instances. AB skips an instance that is not available |
| `POST` | `/downloader/torrents/pause`, `/resume`, `/delete` | Pause / resume / delete torrents |
| `POST` | `/downloader/torrents/tag` | Tag a torrent with a bangumi id |
| `POST` | `/downloader/torrents/tag/auto` | Tag all untagged torrents from their name and path |
| `GET` | `/downloader/rename-conflicts` | Rename conflicts that wait for the user |
| `POST` | `/downloader/rename-conflicts/{operation_id}/retry` | Clear one conflict. The next rename pass checks it again |

## Notification center

| Method | Path | Description |
| --- | --- | --- |
| `GET` / `DELETE` | `/notification/messages` | List / clear the in-app notifications |
| `GET` | `/notification/messages/unread-count` | Number of unread notifications |
| `POST` | `/notification/messages/read-all` | Mark all as read |
| `POST` | `/notification/messages/{message_id}/read` | Mark one as read |
| `DELETE` | `/notification/messages/{message_id}` | Delete one |
| `POST` | `/notification/test` | Test a saved notification channel by its index |
| `POST` | `/notification/test-config` | Test a channel configuration that is not saved |

## Event stream

`GET /events/stream` is one Server-Sent Events connection. The WebUI uses it instead of polling.

| `event` | When AB sends it | `data` |
| --- | --- | --- |
| `status` | Each 3 seconds | The same structure as `GET /status` |
| `downloader` | Each 5 seconds | Torrents of all instances. `null` when the downloader is not available |
| `log` | Each 10 seconds | The end of the log |
| `update` | When an online update runs and its progress changes | Update progress |
| `notification` | When the connection opens, and when the notification center changes | Notification center state, with the unread count `unread_count` |
| `bus` | When an event goes on the event bus | `{"kind": <event name>, "payload": {...}}`, for host events and plugin events |

```bash
curl -N -H "Authorization: Bearer $AB_TOKEN" http://your-host:7892/api/v1/events/stream
```

For the event names and fields in `bus` frames, refer to [Plugin development → Events](/en/dev/plugins/events). Frontend plugin components use `host.events.on(kind, callback)` to get the same frames.

## Plugins

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/plugins` | Plugins that AB found, their state, the config form schema and the current config (masked) |
| `PUT` | `/plugins/settings` | Change `allow_unsigned` (allow unsigned plugins) |
| `PUT` | `/plugins/{plugin_id}` | Enable / disable a plugin or change its config. The change applies at once. A bad config gets `422` |
| `GET` | `/plugins/providers` | Provider ids from plugins, grouped by extension point |
| `GET` | `/plugins/ui` | Frontend slots that enabled plugins declare |
| `GET` | `/plugins/catalog` | Plugins in the signed catalog. `502` if AB cannot get the catalog |
| `POST` | `/plugins/{plugin_id}/install` | Install or upgrade a plugin from the signed catalog, then enable it |
| `DELETE` | `/plugins/{plugin_id}` | Remove a plugin that came from the signed catalog |
| `GET` | `/plugins/{plugin_id}/web/{path}` | Static frontend files in the `web/` directory of the plugin |
| Any | `/plugins/{plugin_id}/{path}` | Routes of the plugin. Refer to [REST routes](/en/dev/plugins/points/api-router) |

## Setup wizard

These endpoints need no authentication. `GET /setup/status` is always available and returns `need_setup` (`false` after setup). The other endpoints are available only before the first setup is complete. After that, they return `403`. `/setup/complete` also needs a browser session, or an `admin` account that still has the factory password `adminadmin`. Otherwise it returns `403`.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/setup/status` | Tells if the setup wizard is necessary |
| `POST` | `/setup/test-downloader` | Test the downloader connection |
| `POST` | `/setup/test-rss` | Test an RSS link |
| `POST` | `/setup/test-notification` | Send a test notification |
| `POST` | `/setup/complete` | Save all wizard settings and mark the setup as complete |

## MCP

AB provides an MCP server under `/mcp` at the root path. The Streamable HTTP transport endpoint is `/mcp`. The legacy SSE transport is still available: a client connects to `GET /mcp/sse` and sends messages to `POST /mcp/messages/`.

- Access control is different from the REST API. The client IP must be in `security.mcp_whitelist`, or the request must have a token with `scope=mcp` (`Authorization: Bearer <token>`). If `mcp_whitelist` is empty, AB refuses all IP-based access. Tokens still work.
- Built-in tools: `list_anime`, `get_anime`, `search_anime`, `subscribe_anime`, `unsubscribe_anime`, `list_downloads`, `list_rss_feeds`, `get_program_status`, `refresh_feeds`, `update_anime`.
- Built-in resources: `autobangumi://anime/list`, `autobangumi://anime/{id}`, `autobangumi://status`, `autobangumi://rss/feeds`.
- A tool from an enabled plugin has the name `<plugin id>__<id>`. A resource from a plugin has the URI `autobangumi://plugins/<plugin id>/<id>`. Refer to [MCP tools and resources](/en/dev/plugins/points/mcp).

## Responses and errors

- Many action endpoints return `{"status": true, "msg_en": "...", "msg_zh": "..."}`. Query endpoints return the data directly. For the exact structure, refer to `/docs`.
- Errors use standard HTTP status codes: `401` not authenticated, `403` not permitted, `404` not found, `422` validation failed, `500` server error.

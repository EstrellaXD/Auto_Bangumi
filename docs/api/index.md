# REST API Reference

AutoBangumi exposes a REST API at `/api/v1`. All endpoints (except login and setup) require JWT authentication.

**Base URL:** `http://your-host:7892/api/v1`

**Authentication:** Include the JWT token as a cookie or `Authorization: Bearer <token>` header.

**Interactive Docs:** When running in development mode, Swagger UI is available at `http://your-host:7892/docs`.

---

## Authentication

### Login

```
POST /auth/login
```

Authenticate with username and password.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:** Sets authentication cookie with JWT token.

### Refresh Token

```
GET /auth/refresh_token
```

Refresh the current authentication token.

### Logout

```
GET /auth/logout
```

Clear authentication cookies and log out.

### Update Credentials

```
POST /auth/update
```

Update username and/or password.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

---

## Passkey / WebAuthn <Badge type="tip" text="v3.2+" />

Passwordless authentication using WebAuthn/FIDO2 Passkeys.

### Register Passkey

```
POST /passkey/register/options
```

Get WebAuthn registration options (challenge, relying party info).

```
POST /passkey/register/verify
```

Verify and save the Passkey registration response from the browser.

### Authenticate with Passkey

```
POST /passkey/auth/options
```

Get WebAuthn authentication challenge options.

```
POST /passkey/auth/verify
```

Verify the Passkey authentication response and issue a JWT token.

### Manage Passkeys

```
GET /passkey/list
```

List all registered Passkeys for the current user.

```
POST /passkey/delete
```

Delete a registered Passkey by credential ID.

---

## Configuration

### Get Configuration

```
GET /config/get
```

Retrieve the current application configuration.

**Response:** Full configuration object including `program`, `downloader`, `rss_parser`, `bangumi_manager`, `notification`, `proxy`, and `experimental_openai` sections.

### Update Configuration

```
PATCH /config/update
```

Partially update the application configuration. Only include fields you want to change.

**Request Body:** Partial configuration object.

---

## Bangumi (Anime Rules)

### List All Bangumi

```
GET /bangumi/get/all
```

Get all anime download rules.

### Get Bangumi by ID

```
GET /bangumi/get/{bangumi_id}
```

Get a specific anime rule by ID.

### Update Bangumi

```
PATCH /bangumi/update/{bangumi_id}
```

Update an anime rule's metadata (title, season, episode offset, etc.).

### Delete Bangumi

```
DELETE /bangumi/delete/{bangumi_id}
```

Delete a single anime rule and its associated torrents.

```
DELETE /bangumi/delete/many/
```

Batch delete multiple anime rules.

**Request Body:**
```json
{
  "bangumi_ids": [1, 2, 3]
}
```

### Disable / Enable Bangumi

```
DELETE /bangumi/disable/{bangumi_id}
```

Disable an anime rule (keeps files, stops downloading).

```
DELETE /bangumi/disable/many/
```

Batch disable multiple anime rules.

```
GET /bangumi/enable/{bangumi_id}
```

Re-enable a previously disabled anime rule.

### Poster Refresh

```
GET /bangumi/refresh/poster/all
```

Refresh poster images for all anime from TMDB.

```
GET /bangumi/refresh/poster/{bangumi_id}
```

Refresh the poster image for a specific anime.

### Calendar

```
GET /bangumi/refresh/calendar
```

Refresh the anime broadcast calendar data from Bangumi.tv.

### Reset All

```
GET /bangumi/reset/all
```

Delete all anime rules. Use with caution.

---

## RSS Feeds

### List All Feeds

```
GET /rss
```

Get all configured RSS feeds.

### Add Feed

```
POST /rss/add
```

Add a new RSS feed subscription.

**Request Body:**
```json
{
  "url": "string",
  "aggregate": true,
  "parser": "mikan"
}
```

### Enable / Disable Feeds

```
POST /rss/enable/many
```

Enable multiple RSS feeds.

```
PATCH /rss/disable/{rss_id}
```

Disable a single RSS feed.

```
POST /rss/disable/many
```

Batch disable multiple RSS feeds.

### Delete Feeds

```
DELETE /rss/delete/{rss_id}
```

Delete a single RSS feed.

```
POST /rss/delete/many
```

Batch delete multiple RSS feeds.

### Update Feed

```
PATCH /rss/update/{rss_id}
```

Update an RSS feed's configuration.

### Refresh Feeds

```
GET /rss/refresh/all
```

Manually trigger a refresh of all RSS feeds.

```
GET /rss/refresh/{rss_id}
```

Refresh a specific RSS feed.

### Get Torrents from Feed

```
GET /rss/torrent/{rss_id}
```

Get the list of torrents parsed from a specific RSS feed.

### Analysis & Subscription

```
POST /rss/analysis
```

Analyze an RSS URL and extract anime metadata without subscribing.

**Request Body:**
```json
{
  "url": "string"
}
```

```
POST /rss/collect
```

Download all episodes from an RSS feed (for completed anime).

```
POST /rss/subscribe
```

Subscribe to an RSS feed for automatic ongoing downloads.

---

## Search

### Search Bangumi (Server-Sent Events)

```
GET /search/bangumi?keyword={keyword}&provider={provider}
```

Search for anime torrents. Returns results as a Server-Sent Events (SSE) stream for real-time updates.

**Query Parameters:**
- `keyword` — Search keyword
- `provider` — Search provider (e.g., `mikan`, `nyaa`, `dmhy`)

**Response:** SSE stream with parsed search results.

### List Search Providers

```
GET /search/provider
```

Get the list of available search providers.

---

## Program Control

### Get Status

```
GET /status
```

Get program status including version, running state, and first_run flag.

**Response:**
```json
{
  "status": "running",
  "version": "3.2.0",
  "first_run": false
}
```

### Start Program

```
GET /start
```

Start the main program (RSS checking, downloading, renaming).

### Restart Program

```
GET /restart
```

Restart the main program.

### Stop Program

```
GET /stop
```

Stop the main program (WebUI remains accessible).

### Shutdown

```
GET /shutdown
```

Shutdown the entire application (restarts the Docker container).

### Check Downloader

```
GET /check/downloader
```

Test connectivity to the configured downloader (qBittorrent).

---

## Downloader Management <Badge type="tip" text="v3.2+" />

Manage torrents in the downloader directly from AutoBangumi.

### List Torrents

```
GET /downloader/torrents
```

Get all torrents in the Bangumi category.

### Pause Torrents

```
POST /downloader/torrents/pause
```

Pause torrents by hash.

**Request Body:**
```json
{
  "hashes": ["hash1", "hash2"]
}
```

### Resume Torrents

```
POST /downloader/torrents/resume
```

Resume paused torrents by hash.

**Request Body:**
```json
{
  "hashes": ["hash1", "hash2"]
}
```

### Delete Torrents

```
POST /downloader/torrents/delete
```

Delete torrents with optional file deletion.

**Request Body:**
```json
{
  "hashes": ["hash1", "hash2"],
  "delete_files": false
}
```

---

## Setup Wizard <Badge type="tip" text="v3.2+" />

These endpoints are only available during first-run setup (before setup is complete). They do **not** require authentication. After setup completes, all endpoints return `403 Forbidden`.

### Check Setup Status

```
GET /setup/status
```

Check if setup wizard is needed (first run).

**Response:**
```json
{
  "need_setup": true
}
```

### Test Downloader Connection

```
POST /setup/test-downloader
```

Test connection to a downloader with provided credentials.

**Request Body:**
```json
{
  "type": "qbittorrent",
  "host": "172.17.0.1:8080",
  "username": "admin",
  "password": "adminadmin",
  "ssl": false
}
```

### Test RSS Feed

```
POST /setup/test-rss
```

Validate an RSS feed URL is accessible and parseable.

**Request Body:**
```json
{
  "url": "https://mikanime.tv/RSS/MyBangumi?token=xxx"
}
```

### Test Notification

```
POST /setup/test-notification
```

Send a test notification with provided settings.

**Request Body:**
```json
{
  "type": "telegram",
  "token": "bot_token",
  "chat_id": "chat_id"
}
```

### Complete Setup

```
POST /setup/complete
```

Save all configuration and mark setup as complete. Creates the sentinel file `config/.setup_complete`.

**Request Body:** Full configuration object.

---

## Logs

### Get Logs

```
GET /log
```

Retrieve the full application log file.

### Clear Logs

```
GET /log/clear
```

Clear the log file.

---

## Response Format

All API responses follow a consistent format:

```json
{
  "msg_en": "Success message in English",
  "msg_zh": "Success message in Chinese",
  "status": true
}
```

Error responses include appropriate HTTP status codes (400, 401, 403, 404, 500) with error messages in both languages.

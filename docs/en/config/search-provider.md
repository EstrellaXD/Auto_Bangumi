# Search Providers

![search provider](/image/config/search-provider.png){width=700}{class=ab-shadow-card}

Search providers power WebUI torrent search and search-based subscription. Built-in providers are `mikan`, `nyaa` and `dmhy`; default providers cannot be deleted, but their URL templates can be edited.

Search provider changes are saved immediately to `config/search_provider.json`; they do not use the bottom **Save & restart** button.

## Custom URL

A custom URL template must contain `%s`, which is replaced with the search keywords.

```txt
https://example.com/search?q=%s
```

## PT Site (NexusPHP)

![NexusPHP search provider](/image/config/search-provider-nexusphp.png){width=700}{class=ab-shadow-card}

The NexusPHP mode generates a `torrentrss.php` RSS search template from a site URL, passkey and optional category IDs.

::: warning
Some newer native NexusPHP sites no longer honor the `search` parameter and may return latest torrents for any keyword. Verify that RSS search filters correctly on your site before adding it.
:::

## `search_provider.json`

Default path: `config/search_provider.json`

```json
{
  "mikan": {
    "url": "https://mikanani.me/RSS/Search?searchstr=%s",
    "parser": "mikan"
  }
}
```

| Key | Description |
| --- | --- |
| `url` | Search URL template. Must contain `%s` |
| `parser` | Parser used for this provider. Legacy URL-only entries are normalized automatically |

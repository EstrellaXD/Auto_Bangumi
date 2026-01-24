# Torrent Search

Since v3.1, AB includes a search feature for quickly finding anime.

## Using the Search Feature

::: warning
The search feature relies on the main program's parser. The current version does not support parsing collections. A `warning` when parsing collections is normal behavior.
:::

The search bar is located in the AB top bar. You can select the source site on the right side of the search bar, such as: Mikan Project, Nyaa, etc.

Select the source site, enter keywords, and AB will automatically parse and display search results. To add an anime, click the add button on the right side of the card.

::: tip
When the source is **Mikan**, AB uses the `mikan` parser by default. For other sources, the TMDB parser is used.
:::

## Adding Custom Sources

Users can manually add source sites by editing `config/search_provider.json`.

Default configuration:
```json
{
  "mikan": "https://mikanani.me/RSS/Search?searchstr=%s",
  "nyaa": "https://nyaa.si/?page=rss&q=%s&c=0_0&f=0",
  "dmhy": "http://dmhy.org/topics/rss/rss.xml?keyword=%s",
  "bangumi.moe": "https://bangumi.moe/rss/search/%s"
}
```

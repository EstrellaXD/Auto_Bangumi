# Parser Settings

The parser extracts structured metadata such as title, season, episode and subgroup from RSS item titles.

::: tip
Since v3.1, the parser type for each RSS feed is configured when adding or editing that feed. This page controls only the global parser switch, language and filters.
:::

## WebUI

![parser](/image/config/parser.png){width=700}{class=ab-shadow-card}

- **Enable**: enables RSS parsing.
- **Language**: preferred parser language. Supported values are `zh`, `jp` and `en`.
- **Exclude**: global filter rules. Plain strings and regular expressions are supported.

## `config.json`

Section: `rss_parser`

| Key | Description | Type | WebUI field | Default |
| --- | --- | --- | --- | --- |
| `enable` | Enable RSS parser | boolean | Enable | `true` |
| `filter` | Global filters | string array | Exclude | `["720", "\\d+-\\d+"]` |
| `language` | Parser language | string | Language | `zh` |

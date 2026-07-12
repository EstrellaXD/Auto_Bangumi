# Parser Settings

The parser extracts structured metadata such as title, season, episode and subgroup from RSS item titles.

::: tip
Since v3.1, the source parser for each RSS feed is configured when adding or editing that feed. This page controls the global switch, title parser, language and filters.
:::

## WebUI

- **Enable**: enables RSS parsing.
- **Title parser**: `Classic parser (Stable)` preserves the existing behavior. `Universal parser (Preview)` adds episode ranges, OVAs, movies and mixed collections. The engines never silently fall back to each other.
- **Language**: preferred parser language. Supported values are `zh`, `jp` and `en`.
- **Exclude**: global filter rules. Plain strings and regular expressions are supported.

## `config.json`

Section: `rss_parser`

| Key | Description | Type | WebUI field | Default |
| --- | --- | --- | --- | --- |
| `enable` | Enable RSS parser | boolean | Enable | `true` |
| `engine` | Title parser: `classic` or `tokenizer` | string | Title parser | `classic` |
| `filter` | Global filters | string array | Exclude | `["720", "\\d+-\\d+"]` |
| `language` | Parser language | string | Language | `zh` |

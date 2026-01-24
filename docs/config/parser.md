# Parser Settings

AB's parser is used to parse aggregated RSS links. When new entries appear in the RSS feed, AB will parse the titles and generate automatic download rules.

::: tip
Since v3.1, parser settings have moved to individual RSS settings. To configure the **parser type**, see [Setting up parser for RSS][add_rss].
:::

## Parser Settings in WebUI

![parser](../image/config/parser.png){width=500}{class=ab-shadow-card}

<br/>

- **Enable**: Whether to enable the RSS parser.
- **Language** is the RSS parser language. Currently supports `zh`, `jp`, and `en`.
- **Exclude** is the global RSS parser filter. You can enter strings or regular expressions, and AB will filter out matching entries during RSS parsing.

## `config.json` Configuration Options

The corresponding options in the configuration file are:

Configuration section: `rss_parser`

| Parameter | Description           | Type    | WebUI Option         | Default        |
|-----------|-----------------------|---------|---------------------|----------------|
| enable    | Enable RSS parser     | Boolean | Enable RSS parser   | true           |
| filter    | RSS parser filter     | Array   | Filter              | [720,\d+-\d+] |
| language  | RSS parser language   | String  | RSS parser language | zh             |


[rss_token]: rss
[add_rss]: /feature/rss#parser-settings
[reproxy]: proxy#reverse-proxy

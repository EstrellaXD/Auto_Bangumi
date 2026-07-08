# Player Settings

Player settings control the **Player** page in the sidebar.

![player](/image/config/player.png){width=700}{class=ab-shadow-card}

- **Type**:
  - `jump`: opening the Player page jumps to the external media server.
  - `iframe`: embeds the media server inside AutoBangumi.
- **Player URL**: Jellyfin, Emby, Plex or another media server URL. If no protocol is provided, the frontend adds `http://`.

::: tip
Player settings are stored in browser local storage. They are not part of `config.json` and do not require **Save & restart**.
:::

---
title: RSS Management
---

# RSS Management

## Adding Collections

AB provides two manual download methods:
**Collect** and **Subscribe**.
- **Collect** downloads all episodes at once, suitable for completed anime.
- **Subscribe** adds an automatic download rule with the corresponding RSS link, suitable for ongoing anime.

### Parsing RSS Links

AB supports parsing collection RSS links from all resource sites. Find the collection RSS for your desired anime on the corresponding site, click the **+** button in the upper right corner of AB, and paste the RSS link in the popup window.

### Adding Downloads

If parsing succeeds, a window will appear showing the parsed anime information. Click **Collect** or **Subscribe** to add it to the download queue.

### Common Issues

If a parsing error occurs, it may be due to an incorrect RSS link or an unsupported subtitle group naming format.

## Managing Bangumi

Since v3.0, AB provides manual anime management in the WebUI, allowing you to manually adjust incorrectly parsed anime information.

### Editing Anime Information

In the anime list, click the anime poster to enter the anime information page.
After modifying the information, click **Apply**.
AB will readjust the directory and automatically rename files based on your changes.


### Deleting Anime

Since v3.0, you can manually delete anime. Click the anime poster, enter the information page, and click **Delete**.

::: warning
After deleting anime, if the RSS subscription hasn't been cancelled, AB will still re-parse it. To disable the download rule, use [Disable Anime](#disabling-anime).
:::

### Disabling Anime

Since v3.0, you can manually disable anime. Click the anime poster, enter the information page, and click **Disable**.

Once disabled, the anime poster will be grayed out and sorted to the end. To re-enable the download rule, click **Enable**.

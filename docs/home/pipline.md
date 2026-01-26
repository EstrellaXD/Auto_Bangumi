# How AutoBangumi Works

AutoBangumi (AB for short) is essentially an RSS parser. It parses RSS feeds from anime torrent sites, extracts metadata from torrent titles, generates download rules, and sends them to qBittorrent for downloading. After downloading, it organizes files into a standard media library directory structure.

## Pipeline Overview

1. **RSS Parsing** — AB periodically fetches and parses your subscribed RSS feeds
2. **Title Analysis** — Torrent titles are parsed to extract anime name, episode number, season, subtitle group, and resolution
3. **Rule Generation** — Download rules are created in qBittorrent based on the parsed information
4. **Download Management** — qBittorrent handles the actual downloading of torrents
5. **File Organization** — Downloaded files are renamed and moved into a standardized directory structure
6. **Media Library Ready** — The organized files can be directly recognized by Plex, Jellyfin, and other media servers

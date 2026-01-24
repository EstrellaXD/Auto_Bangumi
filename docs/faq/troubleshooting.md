---
title: Troubleshooting
---

## General Troubleshooting Flow

1. If AB fails to start, check if the startup command is correct. If incorrect and you don't know how to fix it, try redeploying AB.
2. After deploying AB, check the logs first. If you see output like the following, AB is running normally and connected to QB:
      ```
      [2022-07-09 21:55:19,164] INFO:	                _        ____                                    _
      [2022-07-09 21:55:19,165] INFO:	     /\        | |      |  _ \                                  (_)
      [2022-07-09 21:55:19,166] INFO:	    /  \  _   _| |_ ___ | |_) | __ _ _ __   __ _ _   _ _ __ ___  _
      [2022-07-09 21:55:19,167] INFO:	   / /\ \| | | | __/ _ \|  _ < / _` | '_ \ / _` | | | | '_ ` _ \| |
      [2022-07-09 21:55:19,167] INFO:	  / ____ \ |_| | || (_) | |_) | (_| | | | | (_| | |_| | | | | | | |
      [2022-07-09 21:55:19,168] INFO:	 /_/    \_\__,_|\__\___/|____/ \__,_|_| |_|\__, |\__,_|_| |_| |_|_|
      [2022-07-09 21:55:19,169] INFO:	                                            __/ |
      [2022-07-09 21:55:19,169] INFO:	                                           |___/
      [2022-07-09 21:55:19,170] INFO:	Version 3.0.1  Author: EstrellaXD Twitter: https://twitter.com/Estrella_Pan
      [2022-07-09 21:55:19,171] INFO:	GitHub: https://github.com/EstrellaXD/Auto_Bangumi/
      [2022-07-09 21:55:19,172] INFO:	Starting AutoBangumi...
      [2022-07-09 21:55:20,717] INFO:	Add RSS Feed successfully.
      [2022-07-09 21:55:21,761] INFO:	Start collecting RSS info.
      [2022-07-09 21:55:23,431] INFO:	Finished
      [2022-07-09 21:55:23,432] INFO:	Running....
      ```
   1. If you see this log, AB cannot connect to qBittorrent. Check if qBittorrent is running. If it is, go to the [Network Issues](/faq/network) section.
        ```
        [2022-07-09 22:01:24,534] WARNING:  Cannot connect to qBittorrent, wait 5min and retry
        ```
   2. If you see this log, AB cannot connect to Mikan RSS. Go to the [Network Issues](/faq/network) section.
        ```
        [2022-07-09 21:55:21,761] INFO:	    Start collecting RSS info.
        [2022-07-09 22:01:24,534] WARNING:  Connected Failed, please check DNS/Connection
        ```
3. At this point, QB should have download tasks.
   1. If downloads show path issues, check QB's "Saving Management" → "Default Torrent Management Mode" is set to "Manual".
   2. If all downloads show exclamation marks or no category folders are created in the download path, check QB's permissions.
4. If none of the above resolves the issue, try redeploying a fresh qBittorrent.
5. If still unsuccessful, report with logs at [Issues](https://www.github.com/EstrellaXD/Auto_Bangumi/issues).

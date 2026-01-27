---
title: 故障排除
---

## 一般故障排除流程

1. 如果 AB 无法启动，请检查启动命令是否正确。如果不正确且您不知道如何修复，请尝试重新部署 AB。
2. 部署 AB 后，首先检查日志。如果您看到类似以下的输出，说明 AB 正常运行并已连接到 QB：
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
   1. 如果您看到此日志，说明 AB 无法连接到 qBittorrent。请检查 qBittorrent 是否正在运行。如果正在运行，请前往[网络问题](/faq/network)部分。
        ```
        [2022-07-09 22:01:24,534] WARNING:  Cannot connect to qBittorrent, wait 5min and retry
        ```
   2. 如果您看到此日志，说明 AB 无法连接到 Mikan RSS。请前往[网络问题](/faq/network)部分。
        ```
        [2022-07-09 21:55:21,761] INFO:	    Start collecting RSS info.
        [2022-07-09 22:01:24,534] WARNING:  Connected Failed, please check DNS/Connection
        ```
3. 此时，QB 应该有下载任务了。
   1. 如果下载显示路径问题，请检查 QB 的"保存管理"→"默认 Torrent 管理模式"是否设置为"手动"。
   2. 如果所有下载都显示感叹号或下载路径中没有创建分类文件夹，请检查 QB 的权限。
4. 如果以上都无法解决问题，请尝试重新部署一个全新的 qBittorrent。
5. 如果仍然不成功，请携带日志在 [Issues](https://www.github.com/EstrellaXD/Auto_Bangumi/issues) 报告。

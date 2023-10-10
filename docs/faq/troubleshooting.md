---
title: 排错流程
---

## 💡 通用排错流程
1. 如果 AB 无法正常启动，请检查启动命令是否正确, 如果发现启动命令不正确且不会修改，请尝试重新部署 AB。
2. 部署完 AB 之后请先查看 Log。如果运行如下说明 AB 运行正常，且与 QB 连接良好：
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
      [2022-07-09 22:01:24,534] INFO:	[NC-Raws] 继母的拖油瓶是我的前女友 - 01 (B-Global 1920x1080 HEVC AAC MKV) [0B604F3A].mkv >> 继母的拖油瓶是我的前女友 S01E01.mkv
      ```
   1. 如果出现如下 LOG，说明 AB 无法连接 qBittorrent，请检查 qBittorrent 是否正常运行，如果 qBittorrent 正常运行，转跳 [网络问题](/faq/#🌍-网络链接) 部分进行排查。
        ```
        [2022-07-09 22:01:24,534] WARNING:  Cannot connect to qBittorrent, wait 5min and retry
        ```
   2. 如果出现如下 LOG，说明 AB 无法连接到 Mikan RSS，请转跳到 [网络问题](/faq/network) 部分进行排查。
        ```
        [2022-07-09 21:55:21,761] INFO:	    Start collecting RSS info.
        [2022-07-09 22:01:24,534] WARNING:  Connected Failed，please check DNS/Connection
        ```
3. 此时 QB 应该存在下载任务。
   1. 如果下载任务出现路径问题，请检查 QB 设置中的「保存管理」中的「默认种子管理模式」是否为「手动」，若不是请调整为「手动」。
   2. 如果下载全部为感叹号，或者下载路径中没有新建归类文件夹，请检查 QB 的权限。
4. 如果上述排查均不能生效，请尝试重新部署一个新的 qBittorrent。
5. 如果仍然无效，请带着 LOG 到 [issue](https://www.github.com/EstrellaXD/Auto_Bangumi/issues) 反馈。


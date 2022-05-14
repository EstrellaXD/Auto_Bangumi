# 全自动追番方案
## 说明
本项目根据 qBittorrent, Plex 以及 infuse 搭建
![Image](https://cdn.sspai.com/2022/02/09/d94ec60db1c136f6b12ba3dca31e5f5f.png?imageView2/2/w/1120/q/90/interlace/1/ignore-error/1)
完整教程请移步 [自动追番机器建立教程](https://www.craft.do/s/48MFW9QwaCQMzt)
### 需要依赖
```bash
pip install qbittorrent-api
```

## 自动下载规则建立
```shell
python3 rule_set.py --name <新番名称>
```

## 不符合规则的番剧重命名
### rename_qb
在 `rename_qb.py` 中填入 QB 的地址和用户名密码。

然后直接运行 `rename_qb.py` 即可, 如果只想对新番进行重命名，可以添加 `categories="Bangumi"` 语句

根据 `qBittorrent` API 自动重命名下载的种子文件，且不会让种子失效。

- 可以作为 `bash` 脚本运行
- 可以构建 `crontab` 定时运行
```shell
0,30 * * * * python3 /path/rename_qb.py
```
- 也可以监测文件夹变化运行。

### rename_hash
需要 QB 下载完成之后反向输入种子的哈希值，可以编写 Shell 脚本：
```shell
#!/bin/bash
hash = $1

/usr/bin/python3 /path/rename_hash.py --hash $hash
```
QB 中调用该脚本并且引入 **%I** 属性

# 声明
本项目的自动改名规则根据 [miracleyoo/anime_renamer](https://github.com/miracleyoo/anime_renamer) 项目

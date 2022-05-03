# 新番重命名

- 需要依赖
```bash
pip install qbittorrent_api
```
# 使用说明
## rename_qb
在 `rename_qb.py` 中填入 QB 的地址和用户名密码。

然后直接运行 `rename_qb.py` 即可, 如果只想对新番进行重命名，可以添加 `categories="Bangumi"` 语句

根据 `qBittorrent` API 自动重命名下载的种子文件，且不会让种子失效。

- 可以作为 `bash` 脚本运行
- 可以构建 `crontab` 定时运行
- 也可以监测文件夹变化运行。

## rename_hash
需要 QB 下载完成之后反向输入种子的哈希值，可以编写 Shell 脚本：
```shell
#!/bin/bash
hash = $1

/usr/bin/python3 /path/rename_hash.py --hash $hash
```
QB 中调用该脚本并且引入 **%I** 属性
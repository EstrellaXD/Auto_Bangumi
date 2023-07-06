# 下载器设置

## WebUI 设置

![downloader](../image/config/downloader.png)

- `type` 为下载器类型，目前支持 `qbittorrent` 下载器，目前暂不支持修改。
- `host` 为下载器地址。[下载器链接问题][1]
- `path` 为映射的下载器下载路径。[下载器路径问题][2]
- `ssl` 为下载器是否使用 SSL。

## `config.json` 中的配置选项

在配置文件中对应选项如下：

配置文件部分：`downloader`

| 参数名      | 参数说明        | 参数类型 | WebUI 对应选项  | 默认值                |
|----------|-------------|------|-------------|--------------------|
| type     | 下载器类型       | 字符串  | 下载器类型       | qbittorrent        |
| host     | 下载器地址       | 字符串  | 下载器地址       | 172.17.0.1:8080    |
| username | 下载器用户名      | 字符串  | 下载器用户名      | admin              |
| password | 下载器密码       | 字符串  | 下载器密码       | adminadmin         |
| path     | 下载器下载路径     | 字符串  | 下载器下载路径     | /downloads/Bangumi |
| ssl      | 下载器是否使用 SSL | 布尔值  | 下载器是否使用 SSL | false              |

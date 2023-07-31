# 主程序运行配置

## WebUI 配置

![program](../image/config/program.png){width=500}{class=ab-shadow-card}

<br/>

- Interval Time 参数的单位为秒，如果你需要设置为分钟，请自行转换为秒。
- RSS 为 RSS 检查时间间隔，这个参数影响自动下载规则生成的周期间隔。
- Rename 为重命名检查时间间隔，如果你需要修改重命名检查时间间隔，请修改此参数。
- WebUI Port 为端口，请注意如果你使用 Docker 部署，修改后需要在 Docker 中重新映射端口。


## `config.json` 中的配置选项

在配置文件中对应选项如下：

配置文件部分：`program`

| 参数名         | 参数说明       | 参数类型     | WebUI 对应选项 | 默认值  |
|-------------|------------|----------|------------|------|
| rss_time    | RSS 检查时间间隔 | 以秒为单位的整数 | RSS 检查时间间隔 | 7200 |
| rename_time | 重命名检查时间间隔  | 以秒为单位的整数 | 重命名检查时间间隔  | 60   |
| webui_port  | WebUI 端口   | 以整数为单位   | WebUI 端口   | 7892 |



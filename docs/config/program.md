# 程序设置

## WebUI 配置

![program](/image/config/program.png){width=500}{class=ab-shadow-card}

<br/>

- 时间间隔参数的单位为秒。如需设置分钟，请换算为秒。
- RSS 为 RSS 检查间隔，影响自动下载规则的生成频率。
- 重命名为重命名检查间隔，如需调整重命名检查频率可修改此项。
- WebUI 端口为端口号。注意：如果使用 Docker，更改端口后需要在 Docker 中重新映射端口。


## `config.json` 配置选项

配置文件中的对应选项如下：

配置节：`program`

| 参数        | 说明           | 类型          | WebUI 选项        | 默认值 |
|-------------|----------------|---------------|-------------------|--------|
| rss_time    | RSS 检查间隔   | 整数（秒）    | RSS 检查间隔      | 7200   |
| rename_time | 重命名检查间隔 | 整数（秒）    | 重命名检查间隔    | 60     |
| webui_port  | WebUI 端口     | 整数          | WebUI 端口        | 7892   |

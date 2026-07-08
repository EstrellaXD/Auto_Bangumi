# 程序设置

## WebUI 配置

![program](/image/config/program.png){width=700}{class=ab-shadow-card}

设置页左侧可以搜索并跳转到不同分区。`program` 与 `log` 配置属于全局保存项，修改后需要点击底部的 **保存并重启** 才会生效。

- **RSS 检查间隔**：自动刷新 RSS、生成下载任务的周期，单位为秒。
- **重命名间隔**：扫描下载器并整理文件的周期，单位为秒。
- **WebUI 端口**：AutoBangumi 后端与 WebUI 使用的端口。Docker 部署时，如果改动此项，还需要同步修改容器端口映射。
- **调试**：启用更详细的日志输出，排查问题后建议关闭。

## `config.json` 配置选项

配置节：`program`

| 参数 | 说明 | 类型 | WebUI 选项 | 默认值 |
| --- | --- | --- | --- | --- |
| `rss_time` | RSS 检查间隔 | 整数（秒） | RSS 检查间隔 | `900` |
| `rename_time` | 重命名检查间隔 | 整数（秒） | 重命名间隔 | `60` |
| `webui_port` | WebUI 端口 | 整数 | WebUI 端口 | `7892` |

配置节：`log`

| 参数 | 说明 | 类型 | WebUI 选项 | 默认值 |
| --- | --- | --- | --- | --- |
| `debug_enable` | 启用调试日志 | 布尔值 | 调试 | `false` |

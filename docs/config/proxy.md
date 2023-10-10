# 代理和反向代理

## 代理

![proxy](../image/config/proxy.png){width=500}{class=ab-shadow-card}

<br/>

AB 支持 HTTP 代理和 SOCKS5 代理，通过设置代理可以解决一些网络问题。

- **Enable**: 是否启用代理。
- **Type** 为代理类型。
- **Host** 为代理地址。
- **Port** 为代理端口。

::: tip
在 **Socks5** 模式下，需要添加用户名和密码。
:::

## `config.json` 中的配置选项

在配置文件中对应选项如下：

配置文件部分：`proxy`

| 参数名      | 参数说明   | 参数类型 | WebUI 对应选项 | 默认值   |
|----------|--------|------|------------|-------|
| enable   | 是否启用代理 | 布尔值  | 代理         | false |
| type     | 代理类型   | 字符串  | 代理类型       | http  |
| host     | 代理地址   | 字符串  | 代理地址       |
| port     | 代理端口   | 整数   | 代理端口       |
| username | 代理用户名  | 字符串  | 代理用户名      |
| password | 代理密码   | 字符串  | 代理密码       |

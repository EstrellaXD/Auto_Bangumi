# Notification Settings

## WebUI Configuration

![notification](../image/config/notifier.png){width=500}{class=ab-shadow-card}

<br/>

- **Enable** enables notifications. If disabled, the settings below will not take effect.
- **Type** is the notification type. Currently supported:
  - Telegram
  - Wecom
  - Bark
  - ServerChan
- **Chat ID** only needs to be filled in when using `telegram` notifications. [How to get Telegram Bot Chat ID][1]
- **Wecom**: Fill in the custom push URL in the Chat ID field, and add [Rich Text Message][2] type on the server side. [Wecom Configuration Guide][3]

## `config.json` Configuration Options

The corresponding options in the configuration file are:

Configuration section: `notification`

| Parameter | Description       | Type    | WebUI Option     | Default  |
|-----------|------------------|---------|-----------------|----------|
| enable    | Enable notifications | Boolean | Notifications   | false    |
| type      | Notification type | String  | Notification type | telegram |
| token     | Notification token | String | Notification token |         |
| chat_id   | Notification Chat ID | String | Notification Chat ID |       |


[1]: https://core.telegram.org/bots#6-botfather
[2]: https://github.com/umbors/wecomchan-alifun
[3]: https://github.com/easychen/wecomchan

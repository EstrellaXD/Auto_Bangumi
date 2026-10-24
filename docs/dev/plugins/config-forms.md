# 配置表单

插件声明 `config_model`（pydantic 模型），WebUI 在 设置 → 插件 里据此自动生成表单，插件作者不需要写前端。

```python
from pydantic import BaseModel, Field
from ab_sdk import Plugin, secret_field

class Options(BaseModel):
    endpoint: str = Field("https://push.example.com", title="推送地址")
    key: str = secret_field(description="推送密钥")
    retries: int = Field(3, ge=0, le=10, title="重试次数")

class MyPlugin(Plugin[Options]):
    config_model = Options
```

## 字段类型

| Python 类型 | 表单控件 |
| --- | --- |
| `str` | 文本框 |
| `secret_field()` 声明的 `str` | 密码框 |
| `int` / `float` | 数字框（`int` 输入后取整） |
| `bool` | 开关 |
| `Literal[...]` / `Enum` | 下拉框 |
| `list[str]` | 标签输入 |
| `list[<BaseModel>]` | 对象数组：每行一组子字段，可添加和删除行 |
| 其它（`dict`、嵌套对象） | 显示为「不支持的字段」，请直接编辑 `config.json` |

`Field(title=..., description=...)` 成为标签和说明文字。`Optional[T]` 按 `T` 渲染。默认值用于未保存过的字段。

## 校验

- 保存时 AB 用模型校验。不合法的值返回 HTTP 422，不会写入配置。
- 在 `field_validator` 里做深度校验：例如内置的 `rename` 在保存时试渲染模板，写错的模板当场被拒绝。
- 没有默认值的必填字段在首次启用时缺失，插件进入错误状态。用户填写并保存后，插件自动恢复。
- 未启用的插件也显示表单：AB 导入可信插件的代码，只读取 `config_model`，不调用 `setup`。尚未开启「允许未签名插件」的本地插件不执行任何代码，也就没有表单。

## 秘密字段

`secret_field()` 声明密码、令牌、Cookie 等。

- WebUI 以密码框渲染。
- 读取配置的接口只返回掩码。浏览器永远拿不到原值。
- 保存时收到掩码，AB 保留原值。掩码处理覆盖嵌套结构，对象数组行里的秘密字段也会掩码。数组行数被改变而无法对应原行时，该秘密字段被清空，需要用户重新输入。

配置保存在 `config.json` 的 `plugins.options.<插件 id>` 下，启用开关在 `plugins.enabled.<插件 id>`。

## 超出表单的界面

表单满足不了时（图表、操作按钮、列表），插件可以提供前端组件，见 [前端挂载点](/dev/plugins/frontend-slots)。内置 `hardlink` 的「链接已有文件」按钮就是一个 `settings.section` 组件。

# Config Forms

A plugin declares `config_model` (a pydantic model). The WebUI makes a form from it in Settings → Plugins. The plugin author does not write frontend code.

```python
from pydantic import BaseModel, Field
from ab_sdk import Plugin, secret_field

class Options(BaseModel):
    endpoint: str = Field("https://push.example.com", title="Endpoint")
    key: str = secret_field(description="Push key")
    retries: int = Field(3, ge=0, le=10, title="Retries")

class MyPlugin(Plugin[Options]):
    config_model = Options
```

## Field types

| Python type | Form control |
| --- | --- |
| `str` | Text box |
| `str` declared with `secret_field()` | Password box |
| `int` / `float` | Number box (`int` is rounded after input) |
| `bool` | Switch |
| `Literal[...]` / `Enum` | Drop-down list |
| `list[str]` | Tag input |
| `list[<BaseModel>]` | Object array: one group of sub-fields per row; the user can add and delete rows |
| Other types (`dict`, nested object) | Shown as "unsupported field". Edit `config.json` directly |

`Field(title=..., description=...)` becomes the label and the help text. `Optional[T]` renders as `T`. The default value fills fields that the user did not save.

## Validation

- AB validates with the model when the user saves. An invalid value gets HTTP 422 and AB does not write it.
- Use a `field_validator` for deep checks. For example, the built-in `rename` plugin renders the template one time when the user saves. A wrong template is refused at once.
- A required field with no default is missing at first enable. The plugin goes to the error state. When the user fills the field and saves, the plugin recovers.
- A disabled plugin also shows its form. AB imports the code of a trusted plugin and reads only `config_model`. It does not call `setup`. A local plugin that is not allowed yet (unsigned and "Allow unsigned plugins" is off) runs no code, so it has no form.

## Secret fields

`secret_field()` declares passwords, tokens, Cookies and similar values.

- The WebUI shows a password box.
- The read API returns only a mask. The browser never gets the real value.
- When a save contains the mask, AB keeps the old value. Masking also works in nested structures, including secret fields in object-array rows. If the row count changed and AB cannot match a row, AB clears that secret field and the user must enter it again.

AB stores the configuration in `config.json` at `plugins.options.<plugin id>`. The enable switch is at `plugins.enabled.<plugin id>`.

## UI beyond forms

When a form is not enough (charts, action buttons, lists), a plugin can provide a frontend component. See [Frontend slots](/en/dev/plugins/frontend-slots). The "backfill" button of the built-in `hardlink` plugin is a `settings.section` component.

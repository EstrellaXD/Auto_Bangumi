"""插件配置中秘密字段的掩码与还原。

插件用 ``ab_sdk.secret_field()`` 声明秘密字段（JSON Schema 中带 ``secret``
标记，或 ``format: password`` / ``writeOnly``）。读接口返回掩码，写接口收到
掩码时还原为已保存的值，与 /config 对密码类字段的处理一致。
"""

from typing import Any

MASK = "********"


def secret_keys(schema: dict[str, Any] | None) -> set[str]:
    props = (schema or {}).get("properties", {})
    return {
        key
        for key, prop in props.items()
        if prop.get("secret")
        or prop.get("writeOnly")
        or prop.get("format") == "password"
    }


def _keys(options: dict[str, Any], schema: dict[str, Any] | None) -> set[str]:
    # 插件代码本进程未加载过时没有 schema，无法区分秘密字段：全部按秘密处理
    return set(options) if schema is None else secret_keys(schema)


def mask_options(
    options: dict[str, Any], schema: dict[str, Any] | None
) -> dict[str, Any]:
    masked = dict(options)
    for key in _keys(options, schema):
        if isinstance(masked.get(key), str) and masked[key]:
            masked[key] = MASK
    return masked


def restore_options(
    incoming: dict[str, Any], current: dict[str, Any], schema: dict[str, Any] | None
) -> dict[str, Any]:
    for key in _keys(incoming, schema):
        if incoming.get(key) == MASK:
            if key in current:
                incoming[key] = current[key]
            else:
                incoming.pop(key)
    return incoming

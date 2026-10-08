"""插件配置中秘密字段的掩码与还原。

插件用 ``ab_sdk.secret_field()`` 声明秘密字段（JSON Schema 中带 ``secret``
标记，或 ``format: password`` / ``writeOnly``）。读接口返回掩码，写接口收到
掩码时还原为已保存的值，与 /config 对密码类字段的处理一致。

秘密字段可以出现在嵌套对象、对象数组和字典值里。数组行没有稳定 id，还原时
先按「掩码后内容相同」把回传行对应到已保存的行，因此删除、调换行不会串用密码。
"""

from typing import Any

MASK = "********"


# 无 schema（插件代码本进程未加载过）时无法区分秘密字段：所有字符串都按秘密处理
_ALL: dict[str, Any] = {"secret": True}
_ALL["additionalProperties"] = _ALL["items"] = _ALL
_MISSING = object()


def _branches(schema: dict[str, Any], root: dict[str, Any]) -> list[dict[str, Any]]:
    """展开 $ref 与 anyOf / oneOf（如 ``Server | None``）后的候选分支。"""
    while "$ref" in schema:
        schema = root["$defs"][schema["$ref"].rsplit("/", 1)[-1]]
    subs = schema.get("anyOf", []) + schema.get("oneOf", [])
    return [b for s in subs for b in _branches(s, root)] if subs else [schema]


def _is_secret(branches: list[dict[str, Any]]) -> bool:
    return any(
        b.get("secret") or b.get("writeOnly") or b.get("format") == "password"
        for b in branches
    )


def _child(branches: list[dict[str, Any]], key: str) -> dict[str, Any]:
    subs = [
        b.get("properties", {}).get(key, b.get("additionalProperties"))
        for b in branches
    ]
    return {"anyOf": [s for s in subs if isinstance(s, dict)]}


def _items(branches: list[dict[str, Any]]) -> dict[str, Any]:
    subs = [b.get("items") for b in branches]
    return {"anyOf": [s for s in subs if isinstance(s, dict)]}


def _mask(value: Any, schema: dict[str, Any], root: dict[str, Any]) -> Any:
    branches = _branches(schema, root)
    if isinstance(value, str):
        return MASK if value and _is_secret(branches) else value
    if isinstance(value, dict):
        return {k: _mask(v, _child(branches, k), root) for k, v in value.items()}
    if isinstance(value, list):
        return [_mask(v, _items(branches), root) for v in value]
    return value


def _restore(
    value: Any, current: Any, schema: dict[str, Any], root: dict[str, Any]
) -> Any:
    """返回还原后的值；掩码值没有可还原的已保存值时返回 ``_MISSING``（丢弃）。"""
    branches = _branches(schema, root)
    if isinstance(value, str):
        if value == MASK and _is_secret(branches):
            return current if isinstance(current, str) else _MISSING
        return value
    if isinstance(value, dict):
        saved = current if isinstance(current, dict) else {}
        restored = {
            k: _restore(v, saved.get(k), _child(branches, k), root)
            for k, v in value.items()
        }
        return {k: v for k, v in restored.items() if v is not _MISSING}
    if isinstance(value, list):
        saved_rows = current if isinstance(current, list) else []
        item = _items(branches)
        masked = [_mask(c, item, root) for c in saved_rows]
        rows: list[Any] = []
        for i, row in enumerate(value):
            if i < len(masked) and masked[i] == row:
                j = i
            elif row in masked:
                j = masked.index(row)
            elif len(value) == len(saved_rows):
                j = i  # 行内容也改过且行数未变：按位置对应
            else:
                j = -1  # 无法确定对应行：宁可丢弃掩码，不串用别行的密码
            r = _restore(row, saved_rows[j] if j >= 0 else None, item, root)
            if r is not _MISSING:
                rows.append(r)
        return rows
    return value


def mask_options(
    options: dict[str, Any], schema: dict[str, Any] | None
) -> dict[str, Any]:
    return _mask(options, _ALL if schema is None else schema, schema or _ALL)


def restore_options(
    incoming: dict[str, Any], current: dict[str, Any], schema: dict[str, Any] | None
) -> dict[str, Any]:
    return _restore(
        incoming, current, _ALL if schema is None else schema, schema or _ALL
    )

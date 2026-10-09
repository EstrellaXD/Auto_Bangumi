import { hasKey } from './id-label';
import type { SchemaField } from './plugin-schema';

type Translate = (key: string) => string;

/**
 * 内置插件的名称、描述与配置字段文案：清单和 config_model 里只有中文，前端在
 * `builtin_plugins.<id>` 下为它们各配一份翻译。没有收录的插件（第三方）原样显示
 * 后端给的文字。
 */
function root(pluginId: string): string {
  return `builtin_plugins.${pluginId.replaceAll('-', '_')}`;
}

function pick(t: Translate, key: string, fallback: string): string {
  return hasKey(key) ? t(key) : fallback;
}

export function pluginName(t: Translate, id: string, fallback: string): string {
  return pick(t, `${root(id)}.name`, fallback);
}

export function pluginDescription(
  t: Translate,
  id: string,
  fallback: string
): string {
  return pick(t, `${root(id)}.description`, fallback);
}

/** 字段文案：`fields.<key>.title / description`，对象数组的子字段嵌套在父字段下 */
export function localizeFields(
  t: Translate,
  id: string,
  fields: SchemaField[],
  parent = `${root(id)}.fields`
): SchemaField[] {
  return fields.map((field) => {
    const base = `${parent}.${field.key}`;
    return {
      ...field,
      label: pick(t, `${base}.title`, field.label),
      description: pick(t, `${base}.description`, field.description),
      itemFields: localizeFields(t, id, field.itemFields, base),
    };
  });
}

/** 后端 blocked 原因代码（如 not_enabled）的文案；其它错误原样显示 */
export function pluginReason(t: Translate, error: string): string {
  return pick(t, `config.plugins_set.reason.${error}`, error);
}

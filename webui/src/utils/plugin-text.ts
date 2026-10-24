import { hasKey } from './id-label';
import type { SchemaField } from './plugin-schema';
import type { PluginInfo } from '#/plugins';

type Translate = (key: string) => string;
type Plugin = Pick<PluginInfo, 'id' | 'source'>;

/**
 * 内置插件的名称、描述与配置字段文案：清单和 config_model 里只有中文，前端在
 * `builtin_plugins.<id>` 下为它们各配一份翻译。没有收录的插件（第三方）原样显示
 * 后端给的文字。
 */
function root(plugin: Plugin): string | null {
  // 按 id 查找会让同 id 的第三方插件借用内置插件的文案
  return plugin.source === 'builtin'
    ? `builtin_plugins.${plugin.id.replaceAll('-', '_')}`
    : null;
}

function pick(t: Translate, key: string | null, fallback: string): string {
  return key !== null && hasKey(key) ? t(key) : fallback;
}

export function pluginName(
  t: Translate,
  plugin: Plugin & { name: string }
): string {
  const base = root(plugin);
  return pick(t, base && `${base}.name`, plugin.name);
}

export function pluginDescription(
  t: Translate,
  plugin: Plugin & { description: string }
): string {
  const base = root(plugin);
  return pick(t, base && `${base}.description`, plugin.description);
}

/** 字段文案：`fields.<key>.title / description`，对象数组的子字段嵌套在父字段下 */
export function localizeFields(
  t: Translate,
  plugin: Plugin,
  fields: SchemaField[]
): SchemaField[] {
  const base = root(plugin);
  return base ? localizeUnder(t, `${base}.fields`, fields) : fields;
}

function localizeUnder(
  t: Translate,
  parent: string,
  fields: SchemaField[]
): SchemaField[] {
  return fields.map((field) => {
    const base = `${parent}.${field.key}`;
    return {
      ...field,
      label: pick(t, `${base}.title`, field.label),
      description: pick(t, `${base}.description`, field.description),
      itemFields: localizeUnder(t, base, field.itemFields),
    };
  });
}

/** 后端 blocked 原因代码（如 not_enabled）的文案；其它错误原样显示 */
export function pluginReason(t: Translate, error: string): string {
  return pick(t, `config.plugins_set.reason.${error}`, error);
}

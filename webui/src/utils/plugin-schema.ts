import type { JsonSchema, JsonSchemaProperty } from '#/plugins';

export type SchemaFieldKind =
  | 'text'
  | 'password'
  | 'number'
  | 'switch'
  | 'select'
  | 'tags'
  | 'unsupported';

export interface SchemaField {
  key: string;
  label: string;
  description: string;
  kind: SchemaFieldKind;
  /** select 的候选值 */
  options: (string | number)[];
  /** integer 字段输入后取整 */
  integer: boolean;
  default: unknown;
}

/** 解开 pydantic 生成的 $ref 与 Optional（anyOf: [T, null]） */
function resolve(
  prop: JsonSchemaProperty,
  defs: Record<string, JsonSchemaProperty>
): JsonSchemaProperty {
  if (prop.$ref) {
    const name = prop.$ref.split('/').pop() ?? '';
    return { ...defs[name], ...prop, $ref: undefined };
  }
  if (prop.anyOf) {
    const inner = prop.anyOf.find((p) => p.type !== 'null');
    if (inner) return { ...resolve(inner, defs), ...prop, anyOf: undefined };
  }
  return prop;
}

function kindOf(prop: JsonSchemaProperty): SchemaFieldKind {
  if (prop.enum) return 'select';
  switch (prop.type) {
    case 'string':
      return prop.secret || prop.writeOnly || prop.format === 'password'
        ? 'password'
        : 'text';
    case 'integer':
    case 'number':
      return 'number';
    case 'boolean':
      return 'switch';
    case 'array':
      return prop.items?.type === 'string' ? 'tags' : 'unsupported';
    default:
      return 'unsupported';
  }
}

/** 把插件 config_model 的 JSON Schema 转成表单字段描述（保持声明顺序） */
export function schemaFields(schema: JsonSchema | null): SchemaField[] {
  if (!schema?.properties) return [];
  const defs = schema.$defs ?? {};
  return Object.entries(schema.properties).map(([key, raw]) => {
    const prop = resolve(raw, defs);
    return {
      key,
      label: prop.title ?? key,
      description: prop.description ?? '',
      kind: kindOf(prop),
      options: prop.enum ?? [],
      integer: prop.type === 'integer',
      default: prop.default,
    };
  });
}

/** 未保存过的字段用 schema 默认值填充，供表单初始展示 */
export function fillSchemaDefaults(
  fields: SchemaField[],
  options: Record<string, unknown>
): Record<string, unknown> {
  const result: Record<string, unknown> = { ...options };
  for (const field of fields) {
    if (!(field.key in result) && field.default !== undefined) {
      result[field.key] = JSON.parse(JSON.stringify(field.default));
    }
  }
  return result;
}

import type { JsonSchema, JsonSchemaProperty } from '#/plugins';

export type SchemaFieldKind =
  | 'text'
  | 'password'
  | 'number'
  | 'switch'
  | 'select'
  | 'tags'
  | 'objects'
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
  /** objects（对象数组）每一行的字段 */
  itemFields: SchemaField[];
  default: unknown;
  /** 出现在 schema 的 required 列表中（pydantic 中没有默认值的字段） */
  required: boolean;
  /** Optional 字段（anyOf 含 null），清空时存为 null */
  nullable: boolean;
  /** number 字段的取值范围 */
  minimum?: number;
  maximum?: number;
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

function kindOf(
  prop: JsonSchemaProperty,
  items: JsonSchemaProperty | undefined
): SchemaFieldKind {
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
      if (items?.type === 'string') return 'tags';
      return items?.properties ? 'objects' : 'unsupported';
    default:
      return 'unsupported';
  }
}

function buildFields(
  properties: Record<string, JsonSchemaProperty>,
  defs: Record<string, JsonSchemaProperty>,
  required: string[] = []
): SchemaField[] {
  return Object.entries(properties).map(([key, raw]) => {
    const prop = resolve(raw, defs);
    const items = prop.items && resolve(prop.items, defs);
    return {
      key,
      label: prop.title ?? key,
      description: prop.description ?? '',
      kind: kindOf(prop, items),
      options: prop.enum ?? [],
      integer: prop.type === 'integer',
      itemFields: items?.properties
        ? buildFields(items.properties, defs, items.required)
        : [],
      default: prop.default,
      required: required.includes(key),
      nullable: Boolean(raw.anyOf?.some((p) => p.type === 'null')),
      minimum: prop.minimum,
      maximum: prop.maximum,
    };
  });
}

/** 把插件 config_model 的 JSON Schema 转成表单字段描述（保持声明顺序） */
export function schemaFields(schema: JsonSchema | null): SchemaField[] {
  if (!schema?.properties) return [];
  return buildFields(schema.properties, schema.$defs ?? {}, schema.required);
}

/**
 * 未保存过的字段用 schema 默认值填充，供表单初始展示。深拷贝 options：
 * 表单会原地修改嵌套行，与已保存的 options 共用对象会让脏值检测失效。
 */
export function fillSchemaDefaults(
  fields: SchemaField[],
  options: Record<string, unknown>
): Record<string, unknown> {
  const result: Record<string, unknown> = JSON.parse(JSON.stringify(options));
  for (const field of fields) {
    if (!(field.key in result) && field.default !== undefined) {
      result[field.key] = JSON.parse(JSON.stringify(field.default));
    }
  }
  return result;
}

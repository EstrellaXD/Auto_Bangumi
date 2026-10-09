/** 插件 config_model 生成的 JSON Schema（只用到表单渲染需要的子集） */
export interface JsonSchemaProperty {
  type?:
    | 'string'
    | 'integer'
    | 'number'
    | 'boolean'
    | 'array'
    | 'object'
    | 'null';
  title?: string;
  description?: string;
  default?: unknown;
  enum?: (string | number)[];
  format?: string;
  /** ab_sdk.secret_field() 标记的秘密字段 */
  secret?: boolean;
  writeOnly?: boolean;
  items?: JsonSchemaProperty;
  /** 对象类型（数组元素等）的子字段 */
  properties?: Record<string, JsonSchemaProperty>;
  anyOf?: JsonSchemaProperty[];
  $ref?: string;
  minimum?: number;
  maximum?: number;
}

export interface JsonSchema {
  title?: string;
  properties?: Record<string, JsonSchemaProperty>;
  required?: string[];
  $defs?: Record<string, JsonSchemaProperty>;
}

export type PluginState = 'active' | 'disabled' | 'error';

export interface PluginInfo {
  id: string;
  name: string;
  version: string;
  /** catalog：经签名目录安装，只有它能在界面上卸载 */
  source: 'builtin' | 'catalog' | 'local' | 'pip';
  signed: boolean;
  state: PluginState;
  enabled: boolean;
  description: string;
  permissions: string[];
  error: string | null;
  config_schema: JsonSchema | null;
  options: Record<string, unknown>;
}

export interface PluginsOverview {
  allow_unsigned: boolean;
  plugins: PluginInfo[];
}

/** 签名目录（GitHub release `plugins`）中的插件，以及本机已安装的版本 */
export interface CatalogEntry {
  id: string;
  name: string;
  version: string;
  kind: string;
  extension_points: string[];
  description: string;
  min_ab_version: string;
  authors: string[];
  permissions: string[];
  has_web: boolean;
  /** 源码位置：作者仓库与固定的 commit */
  repo: string;
  commit: string;
  readme: string;
  installed_version: string | null;
}

/** 插件提供的 Provider id，按扩展点分组 */
export interface PluginProviders {
  downloader: string[];
  notifier: string[];
  search_site: string[];
  metadata_provider: string[];
  rename_strategy: string[];
}

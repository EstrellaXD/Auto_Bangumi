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
  /** 对象类型（数组元素等）中必填的子字段 */
  required?: string[];
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
  /** 该插件当前登记的 Provider id，按扩展点分组（只含非空项；未启用时为空） */
  providers: Partial<PluginProviders>;
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
  /** 插件依赖的 ab_sdk 版本范围 */
  sdk: string;
  min_ab_version: string;
  authors: string[];
  permissions: string[];
  has_web: boolean;
  /** 源码位置：作者仓库与固定的 commit */
  repo: string;
  commit: string;
  /** 插件在仓库中的子目录，"." 为仓库根 */
  path: string;
  readme: string;
  installed_version: string | null;
  /** 目录版本比已安装版本新（后端按 PEP 440 比较） */
  update_available: boolean;
}

/** 插件提供的 Provider id，按扩展点分组 */
export interface PluginProviders {
  downloader: string[];
  notifier: string[];
  search_site: string[];
  metadata_provider: string[];
  rename_strategy: string[];
}

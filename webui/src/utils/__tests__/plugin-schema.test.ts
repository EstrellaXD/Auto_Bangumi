import { describe, expect, it } from 'vitest';
import { fillSchemaDefaults, schemaFields } from '../plugin-schema';
import type { JsonSchema } from '#/plugins';

// 与 pydantic v2 的 model_json_schema() 输出形状一致
const schema: JsonSchema = {
  title: 'Options',
  properties: {
    site: { type: 'string', title: 'Site', default: 'https://a' },
    cookie: { type: 'string', title: 'Cookie', secret: true, default: '' },
    limit: { type: 'integer', title: 'Limit', default: 10 },
    ratio: { type: 'number', title: 'Ratio' },
    enabled: { type: 'boolean', title: 'Enabled', default: true },
    mode: { $ref: '#/$defs/Mode', default: 'copy' },
    quality: { enum: ['1080p', '720p'], type: 'string', title: 'Quality' },
    tags: { type: 'array', items: { type: 'string' }, default: [] },
    note: {
      anyOf: [{ type: 'string' }, { type: 'null' }],
      title: 'Note',
      default: null,
    },
    nested: { type: 'object', title: 'Nested' },
  },
  $defs: {
    Mode: { enum: ['copy', 'hardlink'], type: 'string', title: 'Mode' },
  },
};

describe('schemaFields', () => {
  it('maps pydantic schema types to form controls in declaration order', () => {
    const fields = schemaFields(schema);
    expect(fields.map((f) => [f.key, f.kind])).toEqual([
      ['site', 'text'],
      ['cookie', 'password'],
      ['limit', 'number'],
      ['ratio', 'number'],
      ['enabled', 'switch'],
      ['mode', 'select'],
      ['quality', 'select'],
      ['tags', 'tags'],
      ['note', 'text'],
      ['nested', 'unsupported'],
    ]);
    const mode = fields.find((f) => f.key === 'mode')!;
    expect(mode.options).toEqual(['copy', 'hardlink']);
    expect(mode.default).toBe('copy');
    expect(fields.find((f) => f.key === 'limit')!.integer).toBe(true);
    expect(fields.find((f) => f.key === 'ratio')!.integer).toBe(false);
  });

  it('maps arrays of objects to nested item fields', () => {
    const [field] = schemaFields({
      properties: {
        path_map: {
          type: 'array',
          title: 'Path map',
          items: { $ref: '#/$defs/PathMap' },
          default: [],
        },
      },
      $defs: {
        PathMap: {
          type: 'object',
          properties: {
            downloader: {
              type: 'string',
              title: 'Downloader',
              default: 'default',
            },
            from: { type: 'string', title: 'From' },
            to: { type: 'string', title: 'To' },
          },
        },
      },
    });
    expect(field.kind).toBe('objects');
    expect(field.itemFields.map((f) => [f.key, f.kind])).toEqual([
      ['downloader', 'text'],
      ['from', 'text'],
      ['to', 'text'],
    ]);
    // 新增一行时只带有默认值的字段
    expect(fillSchemaDefaults(field.itemFields, {})).toEqual({
      downloader: 'default',
    });
  });

  it('marks fields from the required lists at top level and in $ref items', () => {
    const fields = schemaFields({
      properties: {
        url: { type: 'string' },
        note: { type: 'string', default: '' },
        rows: { type: 'array', items: { $ref: '#/$defs/Row' } },
      },
      required: ['url'],
      $defs: {
        Row: {
          type: 'object',
          properties: { from: { type: 'string' }, to: { type: 'string' } },
          required: ['to'],
        },
      },
    });
    expect(fields.map((f) => [f.key, f.required])).toEqual([
      ['url', true],
      ['note', false],
      ['rows', false],
    ]);
    expect(fields[2].itemFields.map((f) => [f.key, f.required])).toEqual([
      ['from', false],
      ['to', true],
    ]);
  });

  it('returns no fields without a schema', () => {
    expect(schemaFields(null)).toEqual([]);
  });
});

describe('fillSchemaDefaults', () => {
  it('fills only missing keys and copies mutable defaults', () => {
    const fields = schemaFields(schema);
    const result = fillSchemaDefaults(fields, {
      site: 'https://b',
      cookie: '********',
    });
    expect(result.site).toBe('https://b');
    expect(result.cookie).toBe('********');
    expect(result.limit).toBe(10);
    expect(result.note).toBeNull();
    (result.tags as string[]).push('x');
    expect(schema.properties!.tags.default).toEqual([]);
  });
});

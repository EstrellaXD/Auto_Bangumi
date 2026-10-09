import { flushPromises, mount } from '@vue/test-utils';
import { NSelect } from 'naive-ui';
import PluginSchemaForm from '../plugin-schema-form.vue';
import type { JsonSchema } from '#/plugins';
import { schemaFields } from '@/utils/plugin-schema';

const confirmMock = vi.fn();
vi.mock('@/hooks/useConfirm', () => ({
  useConfirm: () => ({ confirm: confirmMock }),
}));
vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({ t: (key: string) => key }),
}));

function mountForm(schema: JsonSchema, model: Record<string, unknown>) {
  return mount(PluginSchemaForm, {
    props: { fields: schemaFields(schema), modelValue: model },
    global: { mocks: { $t: (key: string) => key } },
  });
}

describe('plugin-schema-form', () => {
  it('should keep the option type when an integer enum is selected', async () => {
    const fields = schemaFields({
      properties: { level: { type: 'integer', enum: [1, 2, 3], default: 1 } },
    });
    const model: Record<string, unknown> = { level: 1 };
    const wrapper = mount(PluginSchemaForm, {
      props: { fields, modelValue: model },
    });

    const select = wrapper.findComponent(NSelect);
    expect(select.props('value')).toBe(1);
    expect(
      (select.props('options') as { value: unknown }[]).map((o) => o.value)
    ).toEqual([1, 2, 3]);

    select.vm.$emit('update:value', 2);
    expect(model.level).toBe(2);
  });
});

describe('plugin-schema-form number clear', () => {
  it.each([
    [{ type: 'integer' as const, default: 5 }, 5],
    [{ type: 'integer' as const }, undefined],
  ])('should reset %j to its default when cleared', async (prop, expected) => {
    const fields = schemaFields({ properties: { n: prop } });
    const model: Record<string, unknown> = { n: 9 };
    const wrapper = mount(PluginSchemaForm, {
      props: { fields, modelValue: model },
    });
    await wrapper.find('input').setValue('');
    expect(model.n).toBe(expected);
  });
});

describe('plugin-schema-form row removal', () => {
  const schema: JsonSchema = {
    properties: {
      rows: {
        type: 'array',
        items: {
          type: 'object',
          properties: { url: { type: 'string', default: '' } },
        },
      },
    },
  };

  beforeEach(() => confirmMock.mockReset());

  it.each([
    // [行内容, 确认结果, 是否询问, 删除后的行数]
    [{ url: '' }, undefined, false, 0],
    [{ url: 'http://a' }, true, true, 0],
    [{ url: 'http://a' }, false, true, 1],
  ])(
    'should remove row %j after confirm=%s',
    async (row, confirmed, asked, left) => {
      confirmMock.mockResolvedValue(confirmed);
      const model: Record<string, unknown> = { rows: [row] };
      const wrapper = mountForm(schema, model);

      await wrapper
        .findAll('button')
        .find((b) => b.text() === 'config.plugins_set.remove_row')!
        .trigger('click');
      await flushPromises();

      expect(confirmMock).toHaveBeenCalledTimes(asked ? 1 : 0);
      expect(model.rows).toHaveLength(left);
    }
  );
});

describe('plugin-schema-form validation', () => {
  it.each([
    [{ url: '' }, 'config.plugins_set.field_required'],
    [{ url: 'x', n: 0 }, 'config.plugins_set.field_min'],
    [{ url: 'x', n: 11 }, 'config.plugins_set.field_max'],
    [{ url: 'x', n: 5 }, null],
  ])('should show the error for %j', (model, error) => {
    const wrapper = mountForm(
      {
        properties: {
          url: { type: 'string' },
          n: { type: 'integer', minimum: 1, maximum: 10 },
        },
        required: ['url'],
      },
      model
    );
    const alert = wrapper.find('[role="alert"]');
    if (error) expect(alert.text()).toBe(error);
    else expect(alert.exists()).toBe(false);
  });
});

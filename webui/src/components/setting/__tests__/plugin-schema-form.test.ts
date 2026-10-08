import { mount } from '@vue/test-utils';
import { NSelect } from 'naive-ui';
import PluginSchemaForm from '../plugin-schema-form.vue';
import { schemaFields } from '@/utils/plugin-schema';

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

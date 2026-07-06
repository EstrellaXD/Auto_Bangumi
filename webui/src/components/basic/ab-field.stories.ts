import type { Meta, StoryObj } from '@storybook/vue3';

import AbField from './ab-field.vue';
import AbInput from './ab-input.vue';

const meta: Meta<typeof AbField> = {
  title: 'basic/ab-field',
  component: AbField,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbField>;

export const Template: Story = {
  render: () => ({
    components: { AbField, AbInput },
    template: `
      <div style="display:flex;flex-direction:column;gap:20px;max-width:520px">
        <ab-field
          label="RSS link"
          description="Mikan personal feed. Token stays on this machine."
          required
        >
          <ab-input model-value="https://mikanani.me/RSS/MyBangumi" />
        </ab-field>
        <ab-field label="Rename offset" error="Must be an integer, e.g. -12">
          <ab-input model-value="abc" />
        </ab-field>
      </div>`,
  }),
};

import type { Meta, StoryObj } from '@storybook/vue3';
import { ref } from 'vue';

import AbInput from './ab-input.vue';

const meta: Meta<typeof AbInput> = {
  title: 'basic/ab-input',
  component: AbInput,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbInput>;

export const Template: Story = {
  render: () => ({
    components: { AbInput },
    setup() {
      const text = ref('https://mikanani.me/RSS/MyBangumi');
      const secret = ref('token-123');
      const broken = ref('abc');
      return { text, secret, broken };
    },
    template: `
      <div style="display:flex;flex-direction:column;gap:14px;max-width:320px">
        <ab-input v-model="text" clearable placeholder="RSS link" />
        <ab-input v-model="secret" type="password" />
        <ab-input v-model="broken" error />
        <ab-input model-value="disabled" disabled />
      </div>`,
  }),
};

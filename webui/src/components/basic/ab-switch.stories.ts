import type { Meta, StoryObj } from '@storybook/vue3';
import { ref } from 'vue';

import AbSwitch from './ab-switch.vue';

const meta: Meta<typeof AbSwitch> = {
  title: 'basic/ab-switch',
  component: AbSwitch,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbSwitch>;

export const Template: Story = {
  render: () => ({
    components: { AbSwitch },
    setup() {
      const on = ref(true);
      const off = ref(false);
      return { on, off };
    },
    template: `
      <div style="display:flex;gap:14px;align-items:center">
        <ab-switch v-model="on" aria-label="Auto rename" />
        <ab-switch v-model="off" aria-label="Proxy" />
        <ab-switch :model-value="true" disabled aria-label="Disabled" />
      </div>`,
  }),
};

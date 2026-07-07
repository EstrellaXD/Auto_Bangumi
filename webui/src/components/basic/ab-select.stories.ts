import type { Meta, StoryObj } from '@storybook/vue3';
import { ref } from 'vue';

import AbSelect from './ab-select.vue';

const meta: Meta<typeof AbSelect> = {
  title: 'basic/ab-select',
  component: AbSelect,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbSelect>;

export const Template: Story = {
  render: () => ({
    components: { AbSelect },
    setup() {
      const value = ref('mikan');
      return { value };
    },
    template: `
      <ab-select
        v-model="value"
        :items="['mikan', 'dmhy', 'nyaa']"
        style="width:200px"
      />`,
  }),
};

import type { Meta, StoryObj } from '@storybook/vue3';
import { ref } from 'vue';

import AbSplitButton from './ab-split-button.vue';

const meta: Meta<typeof AbSplitButton> = {
  title: 'basic/ab-split-button',
  component: AbSplitButton,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbSplitButton>;

export const Template: Story = {
  render: () => ({
    components: { AbSplitButton },
    setup() {
      const value = ref('enable');
      const options = [
        { label: 'Enable rule', value: 'enable' },
        { label: 'Enable + collect season', value: 'collect' },
        { label: 'Archive rule', value: 'archive' },
      ];
      return { value, options };
    },
    template:
      '<ab-split-button v-model:value="value" :options="options" />',
  }),
};

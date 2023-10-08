import type { Meta, StoryObj } from '@storybook/vue3';

import AbTag from './ab-tag.vue';

const meta: Meta<typeof AbTag> = {
  title: 'basic/ab-tag',
  component: AbTag,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbTag>;

export const Template: Story = {
  render: (args) => ({
    components: { AbTag },
    setup() {
      return { args };
    },
    template: '<ab-tag v-bind="args" />',
  }),
};

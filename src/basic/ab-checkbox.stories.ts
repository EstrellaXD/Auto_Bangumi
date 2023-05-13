import type { Meta, StoryObj } from '@storybook/vue3';

import AbCheckbox from './ab-checkbox.vue';

const meta: Meta<typeof AbCheckbox> = {
  title: 'basic/ab-checkbox',
  component: AbCheckbox,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbCheckbox>;

export const Template: Story = {
  render: (args) => ({
    components: { AbCheckbox },
    setup() {
      return { args };
    },
    template: '<ab-checkbox v-bind="args" />',
  }),
};

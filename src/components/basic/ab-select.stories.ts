import type { Meta, StoryObj } from '@storybook/vue3';

import AbSelect from './ab-select.vue';

const meta: Meta<typeof AbSelect> = {
  title: 'basic/ab-select',
  component: AbSelect,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbSelect>;

export const Template: Story = {
  render: (args) => ({
    components: { AbSelect },
    setup() {
      return { args };
    },
    template: '<ab-select v-bind="args" />',
  }),
};

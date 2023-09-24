import type { Meta, StoryObj } from '@storybook/vue3';

import AbSwitch from './ab-switch.vue';

const meta: Meta<typeof AbSwitch> = {
  title: 'basic/ab-switch',
  component: AbSwitch,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbSwitch>;

export const Template: Story = {
  render: (args) => ({
    components: { AbSwitch },
    setup() {
      return { args };
    },
    template: '<ab-switch v-bind="args" />',
  }),
};

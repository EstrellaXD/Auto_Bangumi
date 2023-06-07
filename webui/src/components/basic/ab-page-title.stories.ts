import type { Meta, StoryObj } from '@storybook/vue3';

import AbPageTitle from './ab-page-title.vue';

const meta: Meta<typeof AbPageTitle> = {
  title: 'basic/ab-PageTitle',
  component: AbPageTitle,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbPageTitle>;

export const Template: Story = {
  render: (args) => ({
    components: { AbPageTitle },
    setup() {
      return { args };
    },
    template: '<ab-page-title v-bind="args" />',
  }),
};

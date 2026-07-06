import type { Meta, StoryObj } from '@storybook/vue3';

import AbButton from './ab-button.vue';
import AbTooltip from './ab-tooltip.vue';

const meta: Meta<typeof AbTooltip> = {
  title: 'basic/ab-tooltip',
  component: AbTooltip,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbTooltip>;

export const Template: Story = {
  args: { content: 'Refresh all RSS feeds' },
  render: (args) => ({
    components: { AbTooltip, AbButton },
    setup() {
      return { args };
    },
    template: `
      <ab-tooltip v-bind="args">
        <ab-button variant="secondary">Hover me</ab-button>
      </ab-tooltip>`,
  }),
};

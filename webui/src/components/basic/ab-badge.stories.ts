import type { Meta, StoryObj } from '@storybook/vue3';

import AbBadge from './ab-badge.vue';

const meta: Meta<typeof AbBadge> = {
  title: 'basic/ab-badge',
  component: AbBadge,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbBadge>;

export const Template: Story = {
  render: () => ({
    components: { AbBadge },
    template: `
      <div style="display:flex;gap:14px;align-items:center">
        <ab-badge :count="3" />
        <ab-badge :count="120" />
        <ab-badge dot />
        <ab-badge :count="0" />
      </div>`,
  }),
};

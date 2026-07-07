import type { Meta, StoryObj } from '@storybook/vue3';

import AbSkeleton from './ab-skeleton.vue';

const meta: Meta<typeof AbSkeleton> = {
  title: 'basic/ab-skeleton',
  component: AbSkeleton,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbSkeleton>;

export const Template: Story = {
  render: () => ({
    components: { AbSkeleton },
    template: `
      <div style="display:flex;flex-direction:column;gap:24px;max-width:420px">
        <ab-skeleton preset="lines" />
        <ab-skeleton preset="row" :count="2" />
      </div>`,
  }),
};

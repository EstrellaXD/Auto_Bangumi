import type { Meta, StoryObj } from '@storybook/vue3';

import AbProgress from './ab-progress.vue';

const meta: Meta<typeof AbProgress> = {
  title: 'basic/ab-progress',
  component: AbProgress,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbProgress>;

export const Template: Story = {
  render: () => ({
    components: { AbProgress },
    template: `
      <div style="display:flex;flex-direction:column;gap:14px;max-width:360px">
        <ab-progress :value="72" label="72%" />
        <ab-progress :value="31" label="31%" state="error" />
      </div>`,
  }),
};

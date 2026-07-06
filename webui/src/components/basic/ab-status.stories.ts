import type { Meta, StoryObj } from '@storybook/vue3';

import AbStatus from './ab-status.vue';

const meta: Meta<typeof AbStatus> = {
  title: 'basic/ab-status',
  component: AbStatus,
  tags: ['autodocs'],
  argTypes: {
    state: {
      control: 'select',
      options: ['running', 'stopped', 'paused', 'degraded'],
    },
  },
};

export default meta;
type Story = StoryObj<typeof AbStatus>;

export const Template: Story = {
  args: { state: 'running', label: 'Running', detail: 'next poll 3 min' },
  render: (args) => ({
    components: { AbStatus },
    setup() {
      return { args };
    },
    template: '<ab-status v-bind="args" />',
  }),
};

export const AllStates: Story = {
  render: () => ({
    components: { AbStatus },
    template: `
      <div style="display:flex;flex-direction:column;gap:10px">
        <ab-status state="running" label="Running" detail="next poll 3 min" />
        <ab-status state="stopped" label="Stopped" detail="downloader unreachable" />
        <ab-status state="paused" label="Paused" detail="by user" />
        <ab-status state="degraded" label="Degraded" detail="2 feeds failing" />
        <ab-status state="running" size="sm" label="Compact" />
      </div>`,
  }),
};

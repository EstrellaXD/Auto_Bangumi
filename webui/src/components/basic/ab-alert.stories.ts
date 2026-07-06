import type { Meta, StoryObj } from '@storybook/vue3';

import AbAlert from './ab-alert.vue';

const meta: Meta<typeof AbAlert> = {
  title: 'basic/ab-alert',
  component: AbAlert,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbAlert>;

export const Template: Story = {
  render: () => ({
    components: { AbAlert },
    template: `
      <div style="display:flex;flex-direction:column;gap:10px;max-width:520px">
        <ab-alert type="info" title="Heads up.">
          Version 3.3 moves renaming to the server — no action needed.
        </ab-alert>
        <ab-alert type="warning" title="Feed unreachable.">
          Mikan timed out twice — check the proxy settings.
        </ab-alert>
        <ab-alert type="danger" title="Parse failed." closable>
          The torrent title could not be parsed.
        </ab-alert>
      </div>`,
  }),
};

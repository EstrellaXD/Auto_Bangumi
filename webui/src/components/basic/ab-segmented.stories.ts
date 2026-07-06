import type { Meta, StoryObj } from '@storybook/vue3';
import { ref } from 'vue';

import AbSegmented from './ab-segmented.vue';

const meta: Meta<typeof AbSegmented> = {
  title: 'basic/ab-segmented',
  component: AbSegmented,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbSegmented>;

export const Template: Story = {
  render: () => ({
    components: { AbSegmented },
    setup() {
      const view = ref('all');
      const options = [
        { label: 'All', value: 'all' },
        { label: 'Airing', value: 'airing' },
        { label: 'Archived', value: 'archived' },
      ];
      return { view, options };
    },
    template:
      '<ab-segmented v-model:value="view" :options="options" aria-label="View" />',
  }),
};

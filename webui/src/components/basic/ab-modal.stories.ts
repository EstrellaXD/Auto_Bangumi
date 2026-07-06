import type { Meta, StoryObj } from '@storybook/vue3';
import { ref } from 'vue';

import AbButton from './ab-button.vue';
import AbModal from './ab-modal.vue';

const meta: Meta<typeof AbModal> = {
  title: 'basic/ab-modal',
  component: AbModal,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof AbModal>;

export const Template: Story = {
  render: () => ({
    components: { AbModal, AbButton },
    setup() {
      const show = ref(false);
      return { show };
    },
    template: `
      <div>
        <ab-button variant="primary" @click="show = true">Open modal</ab-button>
        <ab-modal v-model:show="show" title="Delete rule?" size="sm">
          <p style="margin:0;color:var(--color-text-secondary)">
            “葬送的芙莉莲 第二季” stops updating. Downloaded files stay on disk.
          </p>
          <template #footer>
            <ab-button size="sm" @click="show = false">Cancel</ab-button>
            <ab-button size="sm" variant="danger" @click="show = false">
              Delete rule
            </ab-button>
          </template>
        </ab-modal>
      </div>`,
  }),
};

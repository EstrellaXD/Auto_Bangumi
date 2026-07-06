import { describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import AbMenu from '../ab-menu.vue';

const items = (handler = vi.fn()) => [
  { key: 'enable', label: 'Enable rule', handler },
  { key: 'archive', label: () => 'Archive rule' },
  { key: 'delete', label: 'Delete rule', danger: true },
];

describe('ab-menu', () => {
  it('renders item labels (string and function) after opening', async () => {
    const wrapper = mount(AbMenu, {
      props: { items: items() },
      slots: { trigger: '<button type="button">Actions</button>' },
      attachTo: document.body,
    });
    await wrapper.find('button').trigger('click');
    expect(wrapper.text()).toContain('Enable rule');
    expect(wrapper.text()).toContain('Archive rule');
  });

  it('calls the item handler and emits select on item click', async () => {
    const handler = vi.fn();
    const wrapper = mount(AbMenu, {
      props: { items: items(handler) },
      slots: { trigger: '<button type="button">Actions</button>' },
      attachTo: document.body,
    });
    await wrapper.find('button').trigger('click');
    await wrapper.findAll('[role="menuitem"]')[0].trigger('click');
    expect(handler).toHaveBeenCalledTimes(1);
    expect(wrapper.emitted('select')?.[0]?.[0]).toMatchObject({
      key: 'enable',
    });
  });

  it('marks danger items with the danger class', async () => {
    const wrapper = mount(AbMenu, {
      props: { items: items() },
      slots: { trigger: '<button type="button">Actions</button>' },
      attachTo: document.body,
    });
    await wrapper.find('button').trigger('click');
    const entries = wrapper.findAll('[role="menuitem"]');
    expect(entries[2].classes()).toContain('ab-menu-item--danger');
  });
});

import { afterEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import AbMenu from '../ab-menu.vue';

// NDropdown 把菜单传送到 document.body，断言从 document 查，测试之间清空
afterEach(() => {
  document.body.innerHTML = '';
});

function menuItems() {
  return document.querySelectorAll<HTMLElement>('[role="menuitem"]');
}

function items(handler = vi.fn()) {
  return [
    { key: 'enable', label: 'Enable rule', handler },
    { key: 'archive', label: () => 'Archive rule' },
    { key: 'delete', label: 'Delete rule', danger: true },
  ];
}

describe('ab-menu', () => {
  it('should render item labels (string and function) after opening', async () => {
    const wrapper = mount(AbMenu, {
      props: { items: items() },
      slots: { trigger: '<button type="button">Actions</button>' },
      attachTo: document.body,
    });
    await wrapper.find('button').trigger('click');
    expect(document.body.textContent).toContain('Enable rule');
    expect(document.body.textContent).toContain('Archive rule');
  });

  it('should call the item handler and emits select on item click', async () => {
    const handler = vi.fn();
    const wrapper = mount(AbMenu, {
      props: { items: items(handler) },
      slots: { trigger: '<button type="button">Actions</button>' },
      attachTo: document.body,
    });
    await wrapper.find('button').trigger('click');
    menuItems()[0].click();
    await flushPromises();
    expect(handler).toHaveBeenCalledTimes(1);
    expect(wrapper.emitted('select')?.[0]?.[0]).toMatchObject({
      key: 'enable',
    });
  });

  it('should expose the popup state on the trigger', async () => {
    const wrapper = mount(AbMenu, {
      props: { items: items() },
      slots: { trigger: '<button type="button">Actions</button>' },
      attachTo: document.body,
    });
    const trigger = wrapper.find('button');
    expect(trigger.attributes('aria-haspopup')).toBe('menu');
    expect(trigger.attributes('aria-expanded')).toBe('false');
    await trigger.trigger('click');
    expect(trigger.attributes('aria-expanded')).toBe('true');
  });

  it('should move focus into the menu and announce the highlighted item when opened', async () => {
    const wrapper = mount(AbMenu, {
      props: { items: items() },
      slots: { trigger: '<button type="button">Actions</button>' },
      attachTo: document.body,
    });
    const trigger = wrapper.find('button');
    (trigger.element as HTMLElement).focus();
    await trigger.trigger('click');
    await flushPromises();
    const menu = document.querySelector<HTMLElement>('[role="menu"]')!;
    expect(document.activeElement).toBe(menu);

    menu.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
    await flushPromises();
    expect(menu.getAttribute('aria-activedescendant')).toBe(menuItems()[0].id);

    menu.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await flushPromises();
    expect(document.activeElement).toBe(trigger.element);
  });

  it('should mark danger items with the danger class', async () => {
    const wrapper = mount(AbMenu, {
      props: { items: items() },
      slots: { trigger: '<button type="button">Actions</button>' },
      attachTo: document.body,
    });
    await wrapper.find('button').trigger('click');
    expect(menuItems()[2].classList).toContain('ab-menu-item--danger');
  });
});

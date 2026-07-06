import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import AbList from '../ab-list.vue';

const items = [
  { id: 1, name: '葬送的芙莉莲 第二季' },
  { id: 2, name: 'Re:从零开始的异世界生活' },
  { id: 3, name: '怪兽8号' },
];

describe('ab-list', () => {
  it('should render one row per item via the row slot', () => {
    const wrapper = mount(AbList, {
      props: { items },
      slots: { row: `<template #row="{ item }">{{ item.name }}</template>` },
    });
    expect(wrapper.findAll('.ab-list-row')).toHaveLength(3);
    expect(wrapper.text()).toContain('怪兽8号');
  });

  it('should emit selection updates when a checkbox is toggled', async () => {
    const wrapper = mount(AbList, {
      props: { items, selectable: true, selected: [] },
    });
    const boxes = wrapper.findAll('input[type="checkbox"]');
    // 第一个是全选，其后每行一个
    await boxes[1].setValue(true);
    expect(wrapper.emitted('update:selected')?.at(-1)).toEqual([[1]]);
  });

  it('should toggle every row when select-all is clicked', async () => {
    const wrapper = mount(AbList, {
      props: { items, selectable: true, selected: [] },
    });
    await wrapper.find('.ab-list-selectall input').setValue(true);
    expect(wrapper.emitted('update:selected')?.at(-1)).toEqual([[1, 2, 3]]);
  });

  it('should show skeleton rows while loading', () => {
    const wrapper = mount(AbList, {
      props: { items: [], loading: true },
    });
    expect(wrapper.find('.ab-skeleton').exists()).toBe(true);
  });

  it('should show the empty slot when there are no items', () => {
    const wrapper = mount(AbList, {
      props: { items: [] },
      slots: { empty: '<p id="empty-msg">nothing</p>' },
    });
    expect(wrapper.find('#empty-msg').exists()).toBe(true);
  });

  it('should emit row-click with the item', async () => {
    const wrapper = mount(AbList, { props: { items } });
    await wrapper.findAll('.ab-list-row')[2].trigger('click');
    expect(wrapper.emitted('row-click')?.[0]?.[0]).toMatchObject({ id: 3 });
  });
});

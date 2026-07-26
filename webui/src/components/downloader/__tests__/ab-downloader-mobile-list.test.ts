/* eslint-disable vue/one-component-per-file */
import { defineComponent } from 'vue';
import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import AbDownloaderMobileList from '../ab-downloader-mobile-list.vue';
import type { TorrentGroup } from '#/downloader';

vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({ t: (key: string) => key }),
}));

const ProgressStub = defineComponent({
  name: 'AbProgress',
  props: {
    value: Number,
    label: String,
    state: String,
    ariaLabel: String,
  },
  template:
    '<div data-progress :data-value="value" :aria-label="ariaLabel">{{ label }}</div>',
});

const TagStub = defineComponent({
  name: 'AbTag',
  props: { title: String, type: String },
  template: '<span data-status>{{ title }}</span>',
});

const groups: TorrentGroup[] = [
  {
    name: 'Frieren / Season 2',
    savePath: '/media/Frieren/Season 2',
    totalSize: 2 * 1024 ** 3,
    overallProgress: 0.5,
    count: 1,
    torrents: [
      {
        hash: 'hash-1',
        name: '[Group] Frieren S02E01 1080p',
        size: 2 * 1024 ** 3,
        progress: 0.5,
        dlspeed: 1024 ** 2,
        upspeed: 512 * 1024,
        num_seeds: 8,
        num_leechs: 3,
        state: 'downloading',
        eta: 3660,
        category: 'Bangumi',
        save_path: '/media/Frieren/Season 2',
        added_on: 1,
      },
    ],
  },
];

function mountList(selectedHashes: string[] = []) {
  return mount(AbDownloaderMobileList, {
    props: { groups, selectedHashes },
    global: {
      stubs: {
        AbProgress: ProgressStub,
        AbTag: TagStub,
      },
    },
  });
}

describe('ab-downloader-mobile-list', () => {
  it('should render one compact card for each torrent', () => {
    const wrapper = mountList();

    expect(wrapper.findAll('.mobile-torrent')).toHaveLength(1);
  });

  it('should keep secondary torrent details collapsed initially', () => {
    const wrapper = mountList();

    expect(wrapper.find('.mobile-torrent__details').exists()).toBe(false);
  });

  it('should reveal secondary torrent details when expanded', async () => {
    const wrapper = mountList();

    await wrapper.get('.mobile-torrent__expand').trigger('click');

    expect(wrapper.get('.mobile-torrent__details').text()).toContain(
      '/media/Frieren/Season 2'
    );
  });

  it('should expose the detail state to assistive technology', async () => {
    const wrapper = mountList();
    const expand = wrapper.get('.mobile-torrent__expand');

    await expand.trigger('click');

    expect(expand.attributes('aria-expanded')).toBe('true');
  });

  it('should emit the torrent hash when its selection control is pressed', async () => {
    const wrapper = mountList();

    await wrapper.get('.mobile-torrent__select').trigger('click');

    expect(wrapper.emitted('toggle-hash')).toEqual([['hash-1']]);
  });

  it('should emit the group when its selection control is pressed', async () => {
    const wrapper = mountList();

    await wrapper.get('.mobile-group__select').trigger('click');

    expect(wrapper.emitted('toggle-group')?.[0]?.[0]).toEqual(groups[0]);
  });

  it('should mark a selected torrent without relying on color alone', () => {
    const wrapper = mountList(['hash-1']);

    expect(
      wrapper.get('.mobile-torrent__select').attributes('aria-pressed')
    ).toBe('true');
  });

  it('should name the group selection control with its group', () => {
    const wrapper = mountList();

    expect(
      wrapper.get('.mobile-group__select').attributes('aria-label')
    ).toContain('Frieren / Season 2');
  });

  it('should name the detail control with its torrent', () => {
    const wrapper = mountList();

    expect(
      wrapper.get('.mobile-torrent__expand').attributes('aria-label')
    ).toContain('[Group] Frieren S02E01 1080p');
  });

  it('should show the torrent percentage only once', () => {
    const wrapper = mountList();
    const torrentText = wrapper.get('.mobile-torrent').text();

    expect(torrentText.match(/50%/g)).toHaveLength(1);
  });

  it('should give the progress bar a torrent-specific accessible name', () => {
    const wrapper = mountList();

    expect(wrapper.get('[data-progress]').attributes('aria-label')).toContain(
      '[Group] Frieren S02E01 1080p'
    );
  });
});

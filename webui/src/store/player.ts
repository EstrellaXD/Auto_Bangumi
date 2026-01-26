import { useLocalStorage } from '@vueuse/core';

type MediaPlayerType = 'jump' | 'iframe';

function normalizeUrl(url: string): string {
  if (!url) return '';
  const trimmed = url.trim();
  if (!trimmed) return '';
  // If URL already has a protocol, return as-is
  if (/^https?:\/\//i.test(trimmed)) {
    return trimmed;
  }
  // Otherwise, prepend http://
  return `http://${trimmed}`;
}

export const usePlayerStore = defineStore('player', () => {
  const types = ref<MediaPlayerType[]>(['jump', 'iframe']);
  const type = useLocalStorage<MediaPlayerType>('media-player-type', 'jump');
  const rawUrl = useLocalStorage('media-player-url', '');

  const url = computed(() => normalizeUrl(rawUrl.value));

  function setUrl(value: string) {
    rawUrl.value = value;
  }

  return {
    types,
    type,
    url,
    rawUrl,
    setUrl,
  };
});

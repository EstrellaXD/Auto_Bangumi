import { useLocalStorage } from '@vueuse/core';

type MediaPlayerType = 'jump' | 'iframe';

export const usePlayerStore = defineStore('player', () => {
  const types = ref<MediaPlayerType[]>(['jump', 'iframe']);
  const type = useLocalStorage<MediaPlayerType>('media-player-type', 'jump');
  const url = useLocalStorage<string>('media-player-url', '');

  return {
    types,
    type,
    url,
  };
});

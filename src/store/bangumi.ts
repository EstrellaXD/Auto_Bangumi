import type { BangumiRule } from '#/bangumi';

export const useBangumiStore = defineStore('bangumi', () => {
  const message = useMessage();
  const data = ref<BangumiRule[]>();

  const getAll = async () => {
    const res = await apiBangumi.getAll();
    data.value = res.sort((a, b) => b.id - a.id);
  };

  const updateRule = async (newRule: BangumiRule) => {
    try {
      const res = await apiBangumi.updateRule(newRule);
      if (res.status === 'success') {
        message.success('Update Success!');
        return true;
      } else {
        message.error('Update Failed!');
      }
    } catch (error) {
      message.error('Operation Failed!');
    }
  };

  const removeRule = async (bangumiId: number, deleteFile = false) => {
    try {
      const res = await apiBangumi.deleteRule(bangumiId, deleteFile);
      if (res.status === 'success') {
        message.success(`${res.msg} Success!`);
        return true;
      } else {
        message.error('Delete Failed!');
      }
    } catch (error) {
      message.error('Operation Failed!');
    }
  };

  return { data, getAll, updateRule, removeRule };
});

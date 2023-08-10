import type { BangumiRule } from '#/bangumi';
import { ruleTemplate } from '#/bangumi';

export const useBangumiStore = defineStore('bangumi', () => {
  const message = useMessage();

  const bangumi = ref<BangumiRule[]>();
  const editRule = reactive<{
    show: boolean;
    item: BangumiRule;
  }>({
    show: false,
    item: ruleTemplate,
  });

  const { execute: getAll, onResult: onBangumiResult } = useApi(
    apiBangumi.getAll
  );
  const { execute: updateRule, onResult: onUpdateRuleResult } = useApi(
    apiBangumi.updateRule
  );
  const { execute: enableRule, onResult: onEnableRuleResult } = useApi(
    apiBangumi.enableRule
  );
  const { execute: disableRule, onResult: onDisableRuleResult } = useApi(
    apiBangumi.disableRule
  );
  const { execute: deleteRule, onResult: onDeleteRuleResult } = useApi(
    apiBangumi.deleteRule
  );

  onBangumiResult((res) => {
    function sort(arr: BangumiRule[]) {
      return arr.sort((a, b) => b.id - a.id);
    }

    const enabled = sort(res.filter((e) => !e.deleted));
    const disabled = sort(res.filter((e) => e.deleted));

    bangumi.value = [...enabled, ...disabled];
  });

  function refresh() {
    editRule.show = false;
    getAll();
  }

  function actionSuccess({ msg }) {
    message.success(msg);
    refresh();
  }
  onUpdateRuleResult(actionSuccess);
  onDisableRuleResult(actionSuccess);
  onEnableRuleResult(actionSuccess);
  onDeleteRuleResult(actionSuccess);

  function openEditPopup(data: BangumiRule) {
    editRule.show = true;
    editRule.item = data;
  }

  function ruleManage(
    type: 'disable' | 'delete',
    id: number,
    deleteFile: boolean
  ) {
    if (type === 'disable') {
      disableRule(id, deleteFile);
    }
    if (type === 'delete') {
      deleteRule(id, deleteFile);
    }
  }

  return {
    bangumi,
    editRule,

    getAll,
    updateRule,
    enableRule,
    disableRule,
    deleteRule,
    openEditPopup,
    ruleManage,
  };
});

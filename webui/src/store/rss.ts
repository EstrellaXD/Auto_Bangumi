import type { RSS } from '#/rss';
import type { ApiSuccess } from '#/api';

export const useRSSStore = defineStore('rss', () => {
    const message = useMessage();
    const rss = ref<RSS[]>();
    const selectedRSS= ref<number[]>([]);

    const { execute: getAll, onResult: onRSSResult } = useApi(
        apiRSS.get
    );
    const { execute: updateRSS, onResult: onUpdateRSSResult } = useApi(
        apiRSS.update
    );
    const { execute: disableRSS, onResult: onDisableRSSResult} = useApi(
        apiRSS.disableMany
    );
    const { execute: deleteRSS, onResult: onDeleteRSSResult } = useApi(
        apiRSS.deleteMany
    );


    onRSSResult((res) => {
        function sort(arr: RSS[]) {
            return arr.sort((a, b) => b.id - a.id);
        }

        const enabled = sort(res.filter((e) => e.enabled));
        const disabled = sort(res.filter((e) => !e.enabled));

        rss.value = [...enabled, ...disabled];
    });

    function refresh() {
        getAll();
    }

    function disableSelected() {
        disableRSS(selectedRSS.value);
    }

    function deleteSelected() {
        deleteRSS(selectedRSS.value);
    }

    function actionSuccess(apiRes: ApiSuccess) {
        message.success(apiRes.msg_en);
        refresh();
    }

    function appendSelected(id: number) {
        selectedRSS.value.push(id);
    }

    onUpdateRSSResult(actionSuccess);
    onDeleteRSSResult(actionSuccess);
    onDisableRSSResult(actionSuccess)

    return {
        rss,
        getAll,
        refresh,
        selectedRSS,
        disableSelected,
        deleteSelected,
        appendSelected,
    };
});

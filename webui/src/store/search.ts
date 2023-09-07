import {ref} from 'vue';
import {
    Subject,
    debounceTime,
    filter,
    switchMap,
    tap,
} from "rxjs";
import type {BangumiRule} from "#/bangumi";


export function useSearchStore() {
    const bangumiList = ref<BangumiRule[]>([]);
    const inputValue = ref<string>('');
    const selectingProvider = ref<boolean>(false);

    const providers = ref<string[]>(['mikan', 'dmhy', 'nyaa']);
    const provider = ref<string>('mikan');

    const input$ = new Subject<string>();

    watch(inputValue, input => {
        input$.next(input);
    })

    const {execute: getProviders, onResult: onGetProvidersResult} = useApi(
        apiSearch.getProvider
    );

    onGetProvidersResult((res) => {
        providers.value = res;
    });

    /**
     * - 输入中 debounce 600ms 后触发搜索
     * - 按回车或点击搜索 icon 按钮后触发搜索
     * - 切换 provider 源站时触发搜索
     */

    const bangumiInfo$ = input$.pipe(
        debounceTime(600),
        tap(() => {
            // 有输入更新后清理之前的搜索结果
            bangumiList.value = [];
        }),
        filter(Boolean),
        // switchMap 把输入 keyword 查询为 bangumiInfo$ 流，多次输入自动取消并停止前一次查询
        switchMap((input: string) => apiSearch.get(input, provider.value)),
        tap((bangumi: BangumiRule) => {
            bangumiList.value.push(bangumi);
        }),
    )
        .subscribe()

    function onSearch() {
        input$.next(inputValue.value);
    }

    function onSelect(site: string) {
        provider.value = site;
        selectingProvider.value = !selectingProvider.value
        onSearch();
    }

    return {
        input$,
        bangumiInfo$,
        inputValue,
        selectingProvider,
        onSelect,
        onSearch,
        provider,
        getProviders,
        providers,
        bangumiList,
    };
}
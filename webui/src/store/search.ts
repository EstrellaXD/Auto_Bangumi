import {ref} from 'vue';
import {
    Subject,
    debounceTime,
    filter,
    switchMap,
    takeUntil, tap,
} from "rxjs";
import type {BangumiRule} from "#/bangumi";


export function useSearchStore() {
    const bangumiList = ref<BangumiRule[]>([]);
    const inputValue = ref<string>('');
    const selectingProvider = ref<boolean>(false);

    const providers = ref<string[]>(['mikan', 'dmhy', 'nyaa']);
    const provider = ref<string>('mikan');

    const input$ = new Subject<string>();

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
            bangumiList.value = [];
        }),
        filter(Boolean),
        switchMap((input: string) => apiSearch.get(input, provider.value).pipe(takeUntil(input$))),
        tap((bangumi: BangumiRule) => {
            bangumiList.value.push(bangumi);
        }),
    )
        .subscribe()

    function onInput(e: Event) {
        const value = (e.target as HTMLInputElement).value;
        input$.next(value);
        inputValue.value = value;
    }

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
        onInput,
        onSearch,
        provider,
        getProviders,
        providers,
        bangumiList,
    };
}
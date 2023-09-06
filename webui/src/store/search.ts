import {ref} from 'vue';
import {
    Subject,
    debounceTime,
    filter,
    switchMap,
    tap,
} from "rxjs";
import type {BangumiRule} from "#/bangumi";


export function useSearchStore () {
    const bangumiList = ref<BangumiRule[]>([]);

    const providers = ref<string[]>(['mikan', 'dmhy', 'nyaa']);
    const provider = ref<string>('mikan');

    const input$ = new Subject<string>();

    const {execute: getProviders, onResult: onGetProvidersResult} = useApi(
        apiSearch.getProvider
    );

    onGetProvidersResult((res) => {
        providers.value = res;
    });

    const bangumiInfo$ = input$.pipe(
        debounceTime(600),
        tap(() => {
            bangumiList.value = [];
        }),
        filter(Boolean),
        switchMap((input: string) => apiSearch.get(input, provider.value)),
        tap((bangumi: BangumiRule) => {
            bangumiList.value.push(bangumi);
        }),
    )
    .subscribe()

    return {
        input$,
        bangumiInfo$,
        provider,
        getProviders,
        providers,
        bangumiList,
    };
}
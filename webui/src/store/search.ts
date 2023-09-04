import {
    Subject,
    tap,
    map,
    switchMap,
    debounceTime,
} from "rxjs";
import type {BangumiRule} from "#/bangumi";


export const useSearchStore = defineStore('search', () => {
    const input$ = new Subject<string>();
    const onInput = (e: Event) => input$.next(e.target);
    const providers = ref<string[]>(['mikan', 'dmhy', 'nyaa']);
    const site = ref<string>('mikan');

    const bangumiInfo$ = apiSearch.get('魔女之旅');

    const {execute: getProviders, onResult: onGetProvidersResult} = useApi(
        apiSearch.getProvider
    );

    onGetProvidersResult((res) => {
        providers.value = res;
    });

    input$.pipe(
        debounceTime(1000),
        tap((input: string) => {
            console.log('input', input)
            // clear Search Result List

        }),
        switchMap((input: string) => apiSearch.get(input, site.value)),
        tap((bangumi: BangumiRule) => console.log(bangumi)),
        tap((bangumi: BangumiRule) => {
            console.log('bangumi', bangumi)
            // set bangumi info to Search Result List
        }),
    ).subscribe({
        complete() {
            // end of stream, stop loading animation
        }
    }, (err) => {
        console.error(err);
    });


    return {
        onInput,

        bangumiInfo$,
        site,
        getProviders,
        providers,
    };
});
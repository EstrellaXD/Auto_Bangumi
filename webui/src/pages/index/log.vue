<script lang="ts" setup>
definePage({
  name: 'Log',
});

const { onUpdate, offUpdate, reset, copy } = useLogStore();
const { log } = storeToRefs(useLogStore());
const { version } = useAppInfo();

onActivated(() => {
  onUpdate();
});

onDeactivated(() => {
  offUpdate();
});
</script>

<template>
  <div overflow-auto mt-12 flex-grow>
    <div flex="~ wrap gap-12">
      <ab-container :title="$t('log.title')" w-660 grow>
        <div rounded-10 border="1 solid black" overflow-auto p-10 max-h-60vh>
          <pre text-main>{{ log }}</pre>
        </div>

        <div flex="~ justify-end gap-x-10" mt-12>
          <ab-button type="warn" size="small" @click="reset">
            {{ $t('log.reset') }}
          </ab-button>

          <ab-button size="small" @click="copy">
            {{ $t('log.copy') }}
          </ab-button>
        </div>
      </ab-container>

      <div grow w-500 space-y-20>
        <ab-container :title="$t('log.contact_info')">
          <div space-y-12>
            <ab-label label="Github">
              <ab-button
                size="small"
                link="https://github.com/EstrellaXD/Auto_Bangumi"
                target="_blank"
              >
                {{ $t('log.go') }}
              </ab-button>
            </ab-label>

            <ab-label label="Official Website">
              <ab-button
                size="small"
                link="https://autobangumi.org"
                target="_blank"
              >
                {{ $t('log.go') }}
              </ab-button>
            </ab-label>

            <div line></div>

            <ab-label label="X">
              <ab-button
                size="small"
                link="https://twitter.com/Estrella_Pan"
                target="_blank"
              >
                {{ $t('log.go') }}
              </ab-button>
            </ab-label>

            <ab-label label="Telegram Group">
              <ab-button
                size="small"
                link="https://t.me/autobangumi"
                target="_blank"
              >
                {{ $t('log.join') }}
              </ab-button>
            </ab-label>
          </div>
        </ab-container>

        <ab-container :title="$t('log.bug_repo')">
          <div space-y-12>
            <ab-button
              mx-auto
              text-16
              w-300
              h-46
              rounded-10
              link="https://github.com/EstrellaXD/Auto_Bangumi/issues"
            >
              Github Issues
            </ab-button>

            <div line></div>

            <div text="center primary h3">
              <span>Version: </span>
              <span>{{ version }}</span>
            </div>
          </div>
        </ab-container>
      </div>
    </div>
  </div>
</template>

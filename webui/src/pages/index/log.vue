<script lang="ts" setup>
const { onUpdate, offUpdate, reset, copy } = useLogStore();
const { log } = storeToRefs(useLogStore());
const { version } = useAppInfo();

onActivated(() => {
  onUpdate();
});

onDeactivated(() => {
  offUpdate();
});

definePage({
  name: 'Log',
});
</script>

<template>
  <div overflow-auto mt-12px flex-grow>
    <div flex="~ wrap" gap-12px>
      <ab-container :title="$t('log.title')" w-660px grow>
        <div
          rounded-10px
          border="1px solid black"
          overflow-auto
          p-10px
          max-h-60vh
        >
          <pre text-main>{{ log }}</pre>
        </div>

        <div flex="~ justify-end" space-x-10px mt-12px>
          <ab-button type="warn" size="small" @click="reset">{{
            $t('log.reset')
          }}</ab-button>
          <ab-button size="small" @click="copy">{{ $t('log.copy') }}</ab-button>
        </div>
      </ab-container>

      <div grow w-500px space-y-20px>
        <ab-container :title="$t('log.contact_info')">
          <div space-y-12px>
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
          <div space-y-12px>
            <ab-button
              mx-auto
              text-16px
              w-300px
              h-46px
              rounded-10px
              link="https://github.com/EstrellaXD/Auto_Bangumi/issues"
              >Github Issue</ab-button
            >

            <div line></div>

            <div text-center text-primary text-h3>
              <span>Version: </span>
              <span>{{ version }}</span>
            </div>
          </div>
        </ab-container>
      </div>
    </div>
  </div>
</template>

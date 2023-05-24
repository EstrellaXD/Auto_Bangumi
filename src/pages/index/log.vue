<script lang="ts" setup>
const { onUpdate } = useLogStore();
const { log } = storeToRefs(useLogStore());

onBeforeMount(() => onUpdate());

definePage({
  name: 'Log',
});
</script>

<template>
  <div flex="~ wrap" gap-12px>
    <ab-container title="Log" w-660px grow>
      <div
        rounded-10px
        border="1px solid black"
        overflow-auto
        p-10px
        max-h-60vh
      >
        <pre text-main>{{ log }}</pre>
      </div>
    </ab-container>

    <div grow w-500px space-y-20px>
      <ab-container title="Contact Infomation">
        <div space-y-12px>
          <ab-label label="Github">
            <ab-button
              size="small"
              link="https://github.com/EstrellaXD/Auto_Bangumi"
              target="_blank"
            >
              Go
            </ab-button>
          </ab-label>

          <ab-label label="WebUI Repo">
            <ab-button
              size="small"
              link="https://github.com/Rewrite0/Auto_Bangumi_WebUI"
              target="_blank"
            >
              Go
            </ab-button>
          </ab-label>

          <div line></div>

          <ab-label label="Twitter">
            <ab-button
              size="small"
              link="https://twitter.com/Estrella_Pan"
              target="_blank"
            >
              Go
            </ab-button>
          </ab-label>

          <ab-label label="Telegram">
            <ab-button
              size="small"
              link="https://t.me/autobangumi"
              target="_blank"
            >
              Join
            </ab-button>
          </ab-label>
        </div>
      </ab-container>

      <ab-container title="Bug Report">
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

          <ab-button
            mx-auto
            text-16px
            w-300px
            h-46px
            rounded-10px
            link="mailto:estrellaxd05@gmail.com"
            >Email Contact</ab-button
          >
        </div>
      </ab-container>
    </div>
  </div>
</template>

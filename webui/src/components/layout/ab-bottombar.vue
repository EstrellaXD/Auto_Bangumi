<script lang="ts" setup>
import { Home } from "@icon-park/vue-next";
</script>

<template>
  <div class="flex w-full bg-white shadow">
    <div class="flex-1 flex justify-center items-center">
      <router-link to="/bangumi">
        <Home size={24} />
      </router-link>
    </div>
    <div class="flex-1 flex justify-center items-center">
      <router-link to="/setting">
        <Home size={24} />
      </router-link>
    </div>
    <div class="flex-1 flex justify-center items-center">
      <router-link to="/about">
        <Home size={24} />
      </router-link>
    </div>
  </div>
</template>



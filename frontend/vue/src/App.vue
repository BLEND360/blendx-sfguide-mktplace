<template>
  <v-app>
    <v-app-bar
      app
      color="primary"
      dark
      elevation="2"
      height="70"
    >
      <img
        :src="require('@/assets/blendx-logo.png')"
        alt="BlendX"
        class="logo"
      />
    </v-app-bar>

    <v-main>
      <LLMCall/>
    </v-main>
  </v-app>
</template>

<script>
import LLMCall from './components/LLMCall';

export default {
  name: 'App',

  components: {
    LLMCall,
  },

  data: () => ({
    //
  }),
};
</script>

<style scoped>
.logo {
  height: 50px;
  margin-left: 16px;
}
</style>

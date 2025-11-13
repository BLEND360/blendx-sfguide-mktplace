<template>
  <v-app>
    <v-app-bar
      app
      color="primary"
      dark
    >
    <v-app-bar-nav-icon></v-app-bar-nav-icon>

    <v-toolbar-title>BlendX</v-toolbar-title>
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

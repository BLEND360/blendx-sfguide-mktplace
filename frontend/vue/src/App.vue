<template>
  <v-app>
    <v-app-bar
      app
      color="primary"
      dark
    >
    <v-app-bar-nav-icon></v-app-bar-nav-icon>

    <v-toolbar-title>Simple Clerks App</v-toolbar-title>    
  </v-app-bar>

    <v-main>
      <TopClerks/>
      <LLMCall/>
    </v-main>
  </v-app>
</template>

<script>
import TopClerks from './components/TopClerks';
import LLMCall from './components/LLMCall';

export default {
  name: 'App',

  components: {
    TopClerks,
    LLMCall,
  },

  data: () => ({
    //
  }),
};
</script>

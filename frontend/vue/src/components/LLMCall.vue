<template>
  <v-card class="mx-auto ma-10 pa-4" elevation="2" max-width="950">
    <v-card-title>LLM Call</v-card-title>
    <v-container>
      <v-row justify="center" class="my-4">
        <v-col cols="12" class="text-center">
          <v-btn
            color="primary"
            large
            @click="llm_call"
            :loading="loading"
            :disabled="loading"
          >
            RUN CREW
          </v-btn>
        </v-col>
      </v-row>

      <v-row v-if="response" class="mt-6">
        <v-col cols="12">
          <v-card outlined>
            <v-card-subtitle>Response:</v-card-subtitle>
            <v-card-text>
              <pre class="response-text">{{ response }}</pre>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <v-row v-if="error" class="mt-6">
        <v-col cols="12">
          <v-alert type="error">
            {{ error }}
          </v-alert>
        </v-col>
      </v-row>
    </v-container>
  </v-card>
</template>

<script>
import axios from 'axios'

export default {
  name: 'LLMCall',

  data: () => ({
    response: null,
    loading: false,
    error: null,
  }),

  methods: {
    llm_call() {
      this.loading = true
      this.error = null
      this.response = null

      const baseUrl = process.env.VUE_APP_API_URL
      axios.get(baseUrl + "/llm-call")
        .then(r => {
          this.response = r.data.response
          this.loading = false
        })
        .catch(error => {
          console.log("Error reading llm-call", error)
          this.error = "Error calling LLM endpoint: " + (error.response?.data?.message || error.message)
          this.loading = false
        })
    }
  }
}
</script>

<style scoped>
.response-text {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: monospace;
  background-color: #f5f5f5;
  padding: 16px;
  border-radius: 4px;
}
</style>

<template>
  <v-card class="mx-auto ma-10 pa-4" elevation="2" max-width="950">
    <v-card-title>LLM Call</v-card-title>
    <v-container>
      <v-row justify="center" class="my-4">
        <v-col cols="12" class="text-center">
          <v-btn
            color="primary"
            large
            @click="startCrew"
            :loading="loading"
            :disabled="loading"
          >
            RUN CREW
          </v-btn>
        </v-col>
      </v-row>

      <v-row v-if="status && loading" class="mt-6">
        <v-col cols="12">
          <v-card outlined>
            <v-card-text class="text-center">
              <v-progress-circular
                indeterminate
                color="primary"
                class="mb-3"
              ></v-progress-circular>
              <div>{{ statusMessage }}</div>
              <div class="text-caption mt-2">Execution ID: {{ executionId }}</div>
            </v-card-text>
          </v-card>
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
    executionId: null,
    status: null,
    statusMessage: 'Starting crew execution...',
    pollingInterval: null,
    pollingAttempts: 0,
    maxPollingAttempts: 120, // 10 minutes (5 seconds * 120)
  }),

  methods: {
    async startCrew() {
      this.loading = true
      this.error = null
      this.response = null
      this.status = null
      this.executionId = null
      this.pollingAttempts = 0

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        // Step 1: Start crew execution
        const startResponse = await axios.post(baseUrl + "/crew/start")
        this.executionId = startResponse.data.execution_id
        this.status = startResponse.data.status
        this.statusMessage = 'Crew is processing...'

        console.log('Crew started with ID:', this.executionId)

        // Step 2: Start polling for results
        this.startPolling()
      } catch (error) {
        console.error("Error starting crew:", error)
        this.error = "Error starting crew: " + (error.response?.data?.detail || error.message)
        this.loading = false
      }
    },

    startPolling() {
      this.pollingInterval = setInterval(async () => {
        await this.checkStatus()
      }, 5000) // Poll every 5 seconds
    },

    stopPolling() {
      if (this.pollingInterval) {
        clearInterval(this.pollingInterval)
        this.pollingInterval = null
      }
    },

    async checkStatus() {
      this.pollingAttempts++

      if (this.pollingAttempts > this.maxPollingAttempts) {
        this.stopPolling()
        this.error = "Polling timeout after 10 minutes. The crew may still be processing."
        this.loading = false
        return
      }

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        const statusResponse = await axios.get(baseUrl + `/crew/status/${this.executionId}`)
        const data = statusResponse.data

        console.log(`Polling attempt ${this.pollingAttempts}:`, data.status)

        if (data.status === 'COMPLETED') {
          this.stopPolling()
          this.response = data.result?.raw || JSON.stringify(data.result, null, 2)
          this.loading = false
          this.statusMessage = 'Crew execution completed!'
        } else if (data.status === 'ERROR') {
          this.stopPolling()
          this.error = data.error || 'Unknown error occurred'
          this.loading = false
        } else if (data.status === 'PROCESSING') {
          this.statusMessage = `Crew is processing... (${this.pollingAttempts * 5}s elapsed)`
        }
      } catch (error) {
        console.error("Error checking status:", error)
        this.stopPolling()
        this.error = "Error checking status: " + (error.response?.data?.detail || error.message)
        this.loading = false
      }
    }
  },

  beforeUnmount() {
    // Clean up polling interval if component is destroyed
    this.stopPolling()
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

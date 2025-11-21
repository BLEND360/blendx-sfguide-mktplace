<template>
  <v-card class="mx-auto ma-10 pa-4" elevation="2" max-width="950">
    <v-card-title>Test checks</v-card-title>
    <v-container>
      <v-row justify="center" class="my-4">
        <v-col cols="12" md="3" class="text-center">
          <v-btn
            color="secondary"
            large
            @click="testCortex"
            :loading="testingCortex"
            :disabled="loading || testingCortex || testingLitellm || testingSecrets"
            block
          >
            TEST CORTEX
          </v-btn>
        </v-col>
        <v-col cols="12" md="3" class="text-center">
          <v-btn
            color="info"
            large
            @click="testLitellm"
            :loading="testingLitellm"
            :disabled="loading || testingCortex || testingLitellm || testingSecrets"
            block
          >
            TEST LITELLM
          </v-btn>
        </v-col>
        <v-col cols="12" md="3" class="text-center">
          <v-btn
            color="warning"
            large
            @click="testSecrets"
            :loading="testingSecrets"
            :disabled="loading || testingCortex || testingLitellm || testingSecrets"
            block
          >
            TEST SECRETS
          </v-btn>
        </v-col>
        <v-col cols="12" md="3" class="text-center">
          <v-btn
            color="primary"
            large
            @click="startCrew"
            :loading="loading"
            :disabled="loading || testingCortex || testingLitellm || testingSecrets || listingCrews"
            block
          >
            RUN CREW
          </v-btn>
        </v-col>
        <v-col cols="12" md="3" class="text-center">
          <v-btn
            color="success"
            large
            @click="listCrews"
            :loading="listingCrews"
            :disabled="loading || testingCortex || testingLitellm || testingSecrets || listingCrews"
            block
          >
            LIST CREWS
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

      <v-row v-if="crewExecutions" class="mt-6">
        <v-col cols="12">
          <v-card outlined>
            <v-card-subtitle>Crew Executions:</v-card-subtitle>
            <v-card-text>
              <v-simple-table>
                <template v-slot:default>
                  <thead>
                    <tr>
                      <th class="text-left">Execution ID</th>
                      <th class="text-left">Crew Name</th>
                      <th class="text-left">Status</th>
                      <th class="text-left">Started At</th>
                      <th class="text-left">Updated At</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="exec in crewExecutions" :key="exec.execution_id">
                      <td class="text-monospace">{{ exec.execution_id.substring(0, 8) }}...</td>
                      <td>{{ exec.crew_name }}</td>
                      <td>
                        <v-chip
                          small
                          :color="getStatusColor(exec.status)"
                          dark
                        >
                          {{ exec.status }}
                        </v-chip>
                      </td>
                      <td>{{ formatDate(exec.execution_timestamp) }}</td>
                      <td>{{ formatDate(exec.updated_at) }}</td>
                    </tr>
                  </tbody>
                </template>
              </v-simple-table>
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
    testingCortex: false,
    testingLitellm: false,
    testingSecrets: false,
    listingCrews: false,
    crewExecutions: null,
  }),

  methods: {
    async testCortex() {
      this.testingCortex = true
      this.error = null
      this.response = null

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        console.log('Testing Cortex via SQL...')
        const response = await axios.get(baseUrl + "/test-cortex")

        if (response.data.status === 'success') {
          this.response = `✅ Cortex Test Successful!\n\nMethod: ${response.data.method}\nModel: ${response.data.model}\n\nResponse:\n${response.data.response}`
        } else {
          this.error = `❌ Cortex Test Failed: ${response.data.message}`
        }
      } catch (error) {
        console.error("Error testing Cortex:", error)
        this.error = "Error testing Cortex: " + (error.response?.data?.detail || error.message)
      } finally {
        this.testingCortex = false
      }
    },

    async testLitellm() {
      this.testingLitellm = true
      this.error = null
      this.response = null

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        console.log('Testing LiteLLM...')
        const response = await axios.get(baseUrl + "/test-litellm")

        if (response.data.status === 'success') {
          this.response = `✅ LiteLLM Test Successful!\n\nMethod: ${response.data.method}\nModel: ${response.data.model}\nLLM Type: ${response.data.llm_type}\n\nResponse:\n${response.data.response}`
        } else {
          let errorMsg = `❌ LiteLLM Test Failed: ${response.data.message}`
          if (response.data.error_type) {
            errorMsg += `\n\nError Type: ${response.data.error_type}`
          }
          if (response.data.status_code) {
            errorMsg += `\nStatus Code: ${response.data.status_code}`
          }
          if (response.data.api_response) {
            errorMsg += `\n\nAPI Response: ${response.data.api_response}`
          }
          this.error = errorMsg
        }
      } catch (error) {
        console.error("Error testing LiteLLM:", error)
        let errorMsg = "Error testing LiteLLM: " + (error.response?.data?.detail || error.message)
        if (error.response?.data) {
          errorMsg += "\n\nDetails: " + JSON.stringify(error.response.data, null, 2)
        }
        this.error = errorMsg
      } finally {
        this.testingLitellm = false
      }
    },

    async testSecrets() {
      this.testingSecrets = true
      this.error = null
      this.response = null

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        console.log('Testing Secrets...')
        const response = await axios.get(baseUrl + "/test-secrets")

        let output = `Secrets Test Results\n${'='.repeat(50)}\n\n`
        output += `Status: ${response.data.status === 'success' ? '✅' : '⚠️'} ${response.data.status.toUpperCase()}\n`
        output += `Message: ${response.data.message}\n\n`

        // Environment Variables
        output += `Environment Variables:\n${'-'.repeat(50)}\n`
        if (response.data.environment_variables?.SERPER_API_KEY) {
          const serperEnv = response.data.environment_variables.SERPER_API_KEY
          if (serperEnv.found) {
            output += `✅ SERPER_API_KEY: Found (${serperEnv.preview})\n`
            output += `   Length: ${serperEnv.length} characters\n`
          } else {
            output += `❌ SERPER_API_KEY: Not found\n`
          }
        }
        output += `\n`

        // Snowflake Secrets
        output += `Snowflake Secrets:\n${'-'.repeat(50)}\n`
        if (response.data.secrets?.serper_api_key) {
          const serperSecret = response.data.secrets.serper_api_key
          if (serperSecret.found) {
            output += `✅ serper_api_key: Found (${serperSecret.preview})\n`
            output += `   Length: ${serperSecret.length} characters\n`
          } else {
            output += `❌ serper_api_key: Not found\n`
            if (serperSecret.error) {
              output += `   Error: ${serperSecret.error}\n`
            }
          }
        }
        output += `\n`

        // OAuth Token
        output += `OAuth Token:\n${'-'.repeat(50)}\n`
        if (response.data.oauth_token) {
          if (response.data.oauth_token.found) {
            output += `✅ OAuth Token: Found\n`
            output += `   Length: ${response.data.oauth_token.length} characters\n`
          } else {
            output += `❌ OAuth Token: Not found\n`
          }
          if (response.data.oauth_token.error) {
            output += `   Error: ${response.data.oauth_token.error}\n`
          }
        }
        output += `\n`

        // Recommendations
        if (response.data.recommendations && response.data.recommendations.length > 0) {
          output += `Recommendations:\n${'-'.repeat(50)}\n`
          response.data.recommendations.forEach((rec, idx) => {
            output += `${idx + 1}. ${rec}\n`
          })
        }

        this.response = output

      } catch (error) {
        console.error("Error testing Secrets:", error)
        this.error = "Error testing Secrets: " + (error.response?.data?.detail || error.message)
      } finally {
        this.testingSecrets = false
      }
    },

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
    },

    async listCrews() {
      this.listingCrews = true
      this.error = null
      this.response = null
      this.crewExecutions = null

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        console.log('Fetching crew executions...')
        const response = await axios.get(baseUrl + "/crew/executions?limit=20")

        if (response.data.executions) {
          this.crewExecutions = response.data.executions
          console.log(`Found ${this.crewExecutions.length} crew executions`)
        } else {
          this.error = "No executions found"
        }
      } catch (error) {
        console.error("Error listing crews:", error)
        this.error = "Error listing crews: " + (error.response?.data?.detail || error.message)
      } finally {
        this.listingCrews = false
      }
    },

    getStatusColor(status) {
      switch (status) {
        case 'COMPLETED':
          return 'success'
        case 'PROCESSING':
          return 'info'
        case 'ERROR':
          return 'error'
        default:
          return 'grey'
      }
    },

    formatDate(dateString) {
      if (!dateString) return 'N/A'
      const date = new Date(dateString)
      return date.toLocaleString()
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

.text-monospace {
  font-family: monospace;
  font-size: 0.9em;
}
</style>

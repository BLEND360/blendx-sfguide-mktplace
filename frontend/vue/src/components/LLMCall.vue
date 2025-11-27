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
            :disabled="loading || testingCortex || testingLitellm || testingSecrets || testingSerper"
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
            :disabled="loading || testingCortex || testingLitellm || testingSecrets || testingSerper"
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
            :disabled="loading || testingCortex || testingLitellm || testingSecrets || testingSerper"
            block
          >
            TEST SECRETS
          </v-btn>
        </v-col>
        <v-col cols="12" md="3" class="text-center">
          <v-btn
            color="orange"
            large
            @click="testSerper"
            :loading="testingSerper"
            :disabled="loading || testingCortex || testingLitellm || testingSecrets || testingSerper"
            block
          >
            TEST SERPER
          </v-btn>
        </v-col>
      </v-row>
      <v-row justify="center" class="my-4">
        <v-col cols="12" md="3" class="text-center">
          <v-btn
            color="primary"
            large
            @click="startCrew"
            :loading="loading"
            :disabled="loading || testingCortex || testingLitellm || testingSecrets || testingSerper || listingCrews || loadingExternal"
            block
          >
            RUN CREW
          </v-btn>
        </v-col>
        <v-col cols="12" md="4" class="text-center">
          <v-btn
            color="purple"
            large
            @click="startExternalToolCrew"
            :loading="loadingExternal"
            :disabled="loading || testingCortex || testingLitellm || testingSecrets || testingSerper || listingCrews || loadingExternal"
            block
            class="external-tool-btn"
          >
            RUN CREW WITH EXTERNAL TOOL
          </v-btn>
        </v-col>
        <v-col cols="12" md="4" class="text-center">
          <v-btn
            color="success"
            large
            @click="listCrews"
            :loading="listingCrews"
            :disabled="loading || testingCortex || testingLitellm || testingSecrets || testingSerper || listingCrews || loadingExternal"
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

      <v-row v-if="statusExternal && loadingExternal" class="mt-6">
        <v-col cols="12">
          <v-card outlined>
            <v-card-text class="text-center">
              <v-progress-circular
                indeterminate
                color="purple"
                class="mb-3"
              ></v-progress-circular>
              <div>{{ statusMessageExternal }}</div>
              <div class="text-caption mt-2">Execution ID: {{ executionIdExternal }}</div>
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
    testingSerper: false,
    listingCrews: false,
    crewExecutions: null,
    loadingExternal: false,
    executionIdExternal: null,
    statusExternal: null,
    statusMessageExternal: 'Starting external tool crew execution...',
    pollingIntervalExternal: null,
    pollingAttemptsExternal: 0,
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
        output += `Status: ${response.data.status === 'success' ? '✅' : '⚠️'} ${response.data.status.toUpperCase()}\n\n`

        // Secrets
        output += `Secrets:\n${'-'.repeat(50)}\n`
        if (response.data.secrets?.SERPER_API_KEY) {
          const serperSecret = response.data.secrets.SERPER_API_KEY
          if (serperSecret.found) {
            output += `✅ SERPER_API_KEY: Found (${serperSecret.preview})\n`
            output += `   Source: ${serperSecret.source}\n`
            output += `   Length: ${serperSecret.length} characters\n`
          } else {
            output += `❌ SERPER_API_KEY: Not found\n`
          }
        } else {
          output += `❌ SERPER_API_KEY: Not found\n`
        }
        output += `\n`

        // Secrets Directory Info
        if (response.data.secrets_directory) {
          output += `Secrets Directory:\n${'-'.repeat(50)}\n`
          if (response.data.secrets_directory.exists) {
            output += `✅ /secrets directory exists\n`
            output += `   Contents: ${JSON.stringify(response.data.secrets_directory.contents)}\n`
          } else {
            output += `❌ /secrets directory not found\n`
          }
        }

        this.response = output

      } catch (error) {
        console.error("Error testing Secrets:", error)
        this.error = "Error testing Secrets: " + (error.response?.data?.detail || error.message)
      } finally {
        this.testingSecrets = false
      }
    },

    async testSerper() {
      this.testingSerper = true
      this.error = null
      this.response = null

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        console.log('Testing Serper API...')
        const response = await axios.get(baseUrl + "/test-serper")

        if (response.data.status === 'success') {
          let output = `✅ Serper API Test Successful!\n${'='.repeat(50)}\n\n`
          output += `Search Query: "${response.data.search_query}"\n`
          output += `HTTP Status: ${response.data.http_status}\n`
          output += `Results Found: ${response.data.results_count}\n\n`

          if (response.data.response_preview) {
            output += `First Result Preview:\n${'-'.repeat(50)}\n`
            output += `Title: ${response.data.response_preview.title}\n`
            output += `Link: ${response.data.response_preview.link}\n`
            output += `Snippet: ${response.data.response_preview.snippet}\n\n`
          }

          output += `Full Response:\n${'-'.repeat(50)}\n`
          output += JSON.stringify(response.data.full_response, null, 2)

          this.response = output
        } else {
          let errorMsg = `❌ Serper API Test Failed\n${'='.repeat(50)}\n\n`
          errorMsg += `Message: ${response.data.message}\n`
          if (response.data.http_status) {
            errorMsg += `HTTP Status: ${response.data.http_status}\n`
          }
          if (response.data.error_type) {
            errorMsg += `Error Type: ${response.data.error_type}\n`
          }
          if (response.data.response) {
            errorMsg += `\nResponse:\n${JSON.stringify(response.data.response, null, 2)}`
          }
          if (response.data.raw_response) {
            errorMsg += `\nRaw Response:\n${response.data.raw_response}`
          }
          this.error = errorMsg
        }
      } catch (error) {
        console.error("Error testing Serper:", error)
        this.error = "Error testing Serper API: " + (error.response?.data?.detail || error.message)
        if (error.response?.data) {
          this.error += "\n\nDetails: " + JSON.stringify(error.response.data, null, 2)
        }
      } finally {
        this.testingSerper = false
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
    },

    async startExternalToolCrew() {
      this.loadingExternal = true
      this.error = null
      this.response = null
      this.statusExternal = null
      this.executionIdExternal = null
      this.pollingAttemptsExternal = 0

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        // Step 1: Start external tool crew execution
        const startResponse = await axios.post(baseUrl + "/crew/start-external-tool")
        this.executionIdExternal = startResponse.data.execution_id
        this.statusExternal = startResponse.data.status
        this.statusMessageExternal = 'External tool crew is processing...'

        console.log('External tool crew started with ID:', this.executionIdExternal)

        // Step 2: Start polling for results
        this.startPollingExternal()
      } catch (error) {
        console.error("Error starting external tool crew:", error)
        this.error = "Error starting external tool crew: " + (error.response?.data?.detail || error.message)
        this.loadingExternal = false
      }
    },

    startPollingExternal() {
      this.pollingIntervalExternal = setInterval(async () => {
        await this.checkStatusExternal()
      }, 5000) // Poll every 5 seconds
    },

    stopPollingExternal() {
      if (this.pollingIntervalExternal) {
        clearInterval(this.pollingIntervalExternal)
        this.pollingIntervalExternal = null
      }
    },

    async checkStatusExternal() {
      this.pollingAttemptsExternal++

      if (this.pollingAttemptsExternal > this.maxPollingAttempts) {
        this.stopPollingExternal()
        this.error = "Polling timeout after 10 minutes. The external tool crew may still be processing."
        this.loadingExternal = false
        return
      }

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        const statusResponse = await axios.get(baseUrl + `/crew/status/${this.executionIdExternal}`)
        const data = statusResponse.data

        console.log(`External tool polling attempt ${this.pollingAttemptsExternal}:`, data.status)

        if (data.status === 'COMPLETED') {
          this.stopPollingExternal()
          this.response = data.result?.raw || JSON.stringify(data.result, null, 2)
          this.loadingExternal = false
          this.statusMessageExternal = 'External tool crew execution completed!'
        } else if (data.status === 'ERROR') {
          this.stopPollingExternal()
          this.error = data.error || 'Unknown error occurred in external tool crew'
          this.loadingExternal = false
        } else if (data.status === 'PROCESSING') {
          this.statusMessageExternal = `External tool crew is processing... (${this.pollingAttemptsExternal * 5}s elapsed)`
        }
      } catch (error) {
        console.error("Error checking external tool status:", error)
        this.stopPollingExternal()
        this.error = "Error checking external tool status: " + (error.response?.data?.detail || error.message)
        this.loadingExternal = false
      }
    }
  },

  beforeUnmount() {
    // Clean up polling intervals if component is destroyed
    this.stopPolling()
    this.stopPollingExternal()
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

.external-tool-btn {
  font-size: 0.85rem !important;
  line-height: 1.2 !important;
  padding: 12px 8px !important;
}
</style>

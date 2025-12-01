<template>
  <v-container fluid class="fill-height pa-0">
    <v-row class="fill-height" no-gutters>
      <!-- Left Sidebar - Test Buttons -->
      <v-col cols="12" md="3" class="sidebar-col">
        <v-card class="fill-height sidebar-dark" tile elevation="2">
          <v-card-title class="py-3">
            <v-icon left dark>mdi-cog</v-icon>
            Test Controls
          </v-card-title>
          <v-card-text class="pa-3">
            <v-btn
              color="secondary"
              block
              class="mb-2 dark-text"
              @click="testCortex"
              :loading="testingCortex"
              :disabled="anyTestLoading"
            >
              <v-icon left>mdi-brain</v-icon>
              TEST CORTEX
            </v-btn>

            <v-btn
              color="secondary"
              block
              class="mb-2 dark-text"
              @click="testLitellm"
              :loading="testingLitellm"
              :disabled="anyTestLoading"
            >
              <v-icon left>mdi-robot</v-icon>
              TEST LITELLM
            </v-btn>

            <v-btn
              color="secondary"
              block
              class="mb-2 dark-text"
              @click="testSecrets"
              :loading="testingSecrets"
              :disabled="anyTestLoading"
            >
              <v-icon left>mdi-key</v-icon>
              TEST SECRETS
            </v-btn>

            <v-btn
              color="secondary"
              block
              class="mb-2 dark-text"
              @click="testSerper"
              :loading="testingSerper"
              :disabled="anyTestLoading"
            >
              <v-icon left>mdi-magnify</v-icon>
              TEST SERPER
            </v-btn>

            <v-divider class="my-3"></v-divider>

            <v-btn
              color="accent"
              block
              class="mb-2 dark-text"
              @click="startCrew"
              :loading="loading"
              :disabled="anyTestLoading"
            >
              <v-icon left>mdi-play</v-icon>
              RUN CREW
            </v-btn>

            <v-btn
              color="accent"
              block
              class="mb-2 dark-text"
              @click="startExternalToolCrew"
              :loading="loadingExternal"
              :disabled="anyTestLoading"
            >
              <v-icon left>mdi-tools</v-icon>
              RUN CREW EXTERNAL
            </v-btn>

            <v-btn
              color="success"
              block
              class="mb-2"
              @click="listCrews"
              :loading="listingCrews"
              :disabled="anyTestLoading"
              dark
            >
              <v-icon left>mdi-format-list-bulleted</v-icon>
              LIST CREWS
            </v-btn>
          </v-card-text>

          <!-- Test Results Section -->
          <v-card-text v-if="testResponse" class="pa-3 pt-0">
            <v-divider class="mb-3"></v-divider>
            <v-card outlined class="test-result-card">
              <v-card-subtitle class="pb-1">Test Result:</v-card-subtitle>
              <v-card-text class="pt-0">
                <pre class="response-text small-text">{{ testResponse }}</pre>
              </v-card-text>
            </v-card>
          </v-card-text>

          <!-- Crew Executions Table -->
          <v-card-text v-if="crewExecutions" class="pa-3 pt-0">
            <v-divider class="mb-3"></v-divider>
            <v-card outlined>
              <v-card-subtitle class="pb-1">Crew Executions:</v-card-subtitle>
              <v-card-text class="pt-0">
                <v-simple-table dense>
                  <template v-slot:default>
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="exec in crewExecutions" :key="exec.execution_id">
                        <td class="text-monospace">{{ exec.execution_id.substring(0, 8) }}...</td>
                        <td>
                          <v-chip x-small :color="getStatusColor(exec.status)" dark>
                            {{ exec.status }}
                          </v-chip>
                        </td>
                      </tr>
                    </tbody>
                  </template>
                </v-simple-table>
              </v-card-text>
            </v-card>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Main Chat Area -->
      <v-col cols="12" md="9" class="chat-col">
        <v-card class="fill-height d-flex flex-column" tile>
          <v-card-title class="primary white--text py-3">
            <v-icon left dark>mdi-chat</v-icon>
            NL Generator Chat
          </v-card-title>

          <!-- Chat Messages Area -->
          <v-card-text class="flex-grow-1 chat-messages pa-4" ref="chatMessages">
            <!-- Welcome message -->
            <div v-if="chatMessages.length === 0" class="text-center grey--text py-8">
              <v-icon size="64" color="grey lighten-1">mdi-chat-processing-outline</v-icon>
              <p class="mt-4">Send a message to generate a workflow with the NL Generator</p>
            </div>

            <!-- Chat messages -->
            <div v-for="(msg, index) in chatMessages" :key="index" class="mb-4">
              <!-- User message -->
              <div v-if="msg.type === 'user'" class="d-flex justify-end">
                <v-card class="user-message pa-3" color="primary" dark max-width="70%">
                  <div class="message-text">{{ msg.content }}</div>
                </v-card>
              </div>

              <!-- System/Bot message -->
              <div v-else class="d-flex justify-start">
                <v-card class="bot-message pa-3" outlined max-width="85%">
                  <!-- Loading state -->
                  <div v-if="msg.status === 'loading'" class="d-flex align-center">
                    <v-progress-circular indeterminate color="primary" size="20" class="mr-3"></v-progress-circular>
                    <span>{{ msg.statusMessage || 'Processing...' }}</span>
                  </div>

                  <!-- Error state -->
                  <v-alert v-else-if="msg.status === 'error'" type="error" dense class="mb-0">
                    {{ msg.error }}
                  </v-alert>

                  <!-- Success state with tabs -->
                  <div v-else-if="msg.status === 'completed'">
                    <div class="mb-2">
                      <v-chip small color="success" class="mr-2">
                        <v-icon left small>mdi-check</v-icon>
                        {{ msg.workflow.status }}
                      </v-chip>
                      <span class="font-weight-medium">{{ msg.workflow.title }}</span>
                    </div>

                    <v-tabs v-model="msg.activeTab" background-color="grey lighten-4" class="rounded">
                      <v-tab>
                        <v-icon left small>mdi-text-box-outline</v-icon>
                        Rationale
                      </v-tab>
                      <v-tab>
                        <v-icon left small>mdi-code-braces</v-icon>
                        YAML
                      </v-tab>
                      <v-tab>
                        <v-icon left small>mdi-sitemap</v-icon>
                        Diagram
                      </v-tab>
                    </v-tabs>

                    <v-tabs-items v-model="msg.activeTab">
                      <!-- Rationale Tab -->
                      <v-tab-item>
                        <v-card flat class="pa-3 mt-2">
                          <div class="rationale-text">{{ msg.workflow.rationale }}</div>
                        </v-card>
                      </v-tab-item>

                      <!-- YAML Tab -->
                      <v-tab-item>
                        <v-card flat class="pa-3 mt-2">
                          <div class="d-flex justify-end mb-2">
                            <v-btn small text color="primary" @click="copyToClipboard(msg.workflow.yaml_text)">
                              <v-icon left small>mdi-content-copy</v-icon>
                              Copy YAML
                            </v-btn>
                          </div>
                          <pre class="yaml-text">{{ msg.workflow.yaml_text }}</pre>
                        </v-card>
                      </v-tab-item>

                      <!-- Mermaid Diagram Tab -->
                      <v-tab-item>
                        <v-card flat class="pa-3 mt-2">
                          <div class="d-flex justify-end mb-2">
                            <v-btn small text color="primary" @click="copyToClipboard(msg.workflow.mermaid)">
                              <v-icon left small>mdi-content-copy</v-icon>
                              Copy Mermaid
                            </v-btn>
                          </div>
                          <div class="mermaid-container" :ref="'mermaid-' + index">
                            <div v-html="msg.mermaidSvg" v-if="msg.mermaidSvg"></div>
                            <div v-else class="text-center grey--text pa-4">
                              <v-progress-circular indeterminate color="primary" size="30"></v-progress-circular>
                              <p class="mt-2">Rendering diagram...</p>
                            </div>
                          </div>
                        </v-card>
                      </v-tab-item>
                    </v-tabs-items>
                  </div>
                </v-card>
              </div>
            </div>
          </v-card-text>

          <!-- Error Alert -->
          <v-alert v-if="error" type="error" dismissible class="mx-4 mb-2" @input="error = null">
            {{ error }}
          </v-alert>

          <!-- Chat Input Area -->
          <v-card-actions class="pa-4 chat-input-area">
            <v-textarea
              v-model="userMessage"
              outlined
              dense
              rows="2"
              auto-grow
              placeholder="Describe the workflow you want to create..."
              hide-details
              class="flex-grow-1"
              @keydown.enter.ctrl="sendMessage"
              @keydown.enter.meta="sendMessage"
              :disabled="isGenerating"
            ></v-textarea>
            <v-btn
              color="primary"
              fab
              small
              class="ml-3"
              @click="sendMessage"
              :loading="isGenerating"
              :disabled="!userMessage.trim() || isGenerating"
            >
              <v-icon>mdi-send</v-icon>
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import axios from 'axios'
import mermaid from 'mermaid'

export default {
  name: 'LLMCall',

  data: () => ({
    // Chat state
    userMessage: '',
    chatMessages: [],
    isGenerating: false,
    error: null,

    // Test states
    testResponse: null,
    testingCortex: false,
    testingLitellm: false,
    testingSecrets: false,
    testingSerper: false,

    // Crew states
    loading: false,
    loadingExternal: false,
    listingCrews: false,
    crewExecutions: null,

    // Crew execution tracking
    executionId: null,
    status: null,
    statusMessage: 'Starting crew execution...',
    pollingInterval: null,
    pollingAttempts: 0,
    maxPollingAttempts: 120,

    // External crew tracking
    executionIdExternal: null,
    statusExternal: null,
    statusMessageExternal: 'Starting external tool crew execution...',
    pollingIntervalExternal: null,
    pollingAttemptsExternal: 0,

    // NL Generator polling
    nlPollingInterval: null,
    nlPollingAttempts: 0,
  }),

  computed: {
    anyTestLoading() {
      return this.testingCortex || this.testingLitellm || this.testingSecrets ||
             this.testingSerper || this.loading || this.loadingExternal ||
             this.listingCrews || this.isGenerating
    }
  },

  mounted() {
    // Initialize mermaid
    mermaid.initialize({
      startOnLoad: false,
      theme: 'default',
      securityLevel: 'loose',
      flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'basis'
      }
    })
  },

  methods: {
    async sendMessage() {
      if (!this.userMessage.trim() || this.isGenerating) return

      const message = this.userMessage.trim()
      this.userMessage = ''
      this.error = null

      // Add user message to chat
      this.chatMessages.push({
        type: 'user',
        content: message
      })

      // Add bot response placeholder
      const botMessageIndex = this.chatMessages.length
      this.chatMessages.push({
        type: 'bot',
        status: 'loading',
        statusMessage: 'Starting workflow generation...',
        activeTab: 0
      })

      this.isGenerating = true
      this.scrollToBottom()

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        // Call async endpoint
        const response = await axios.post(baseUrl + '/nl-ai-generator-async', {
          user_request: message
        })

        const workflowId = response.data.workflow_id
        this.chatMessages[botMessageIndex].statusMessage = `Workflow ID: ${workflowId.substring(0, 8)}... Processing...`

        // Start polling
        this.startNLPolling(workflowId, botMessageIndex)
      } catch (error) {
        console.error('Error starting NL generator:', error)
        this.chatMessages[botMessageIndex].status = 'error'
        this.chatMessages[botMessageIndex].error = error.response?.data?.detail || error.message
        this.isGenerating = false
      }
    },

    startNLPolling(workflowId, messageIndex) {
      this.nlPollingAttempts = 0
      this.nlPollingInterval = setInterval(async () => {
        await this.checkNLStatus(workflowId, messageIndex)
      }, 3000)
    },

    stopNLPolling() {
      if (this.nlPollingInterval) {
        clearInterval(this.nlPollingInterval)
        this.nlPollingInterval = null
      }
    },

    async checkNLStatus(workflowId, messageIndex) {
      this.nlPollingAttempts++

      if (this.nlPollingAttempts > this.maxPollingAttempts) {
        this.stopNLPolling()
        this.chatMessages[messageIndex].status = 'error'
        this.chatMessages[messageIndex].error = 'Timeout: Generation took too long'
        this.isGenerating = false
        return
      }

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        const response = await axios.get(baseUrl + `/nl-ai-generator-async/${workflowId}`)
        const data = response.data

        if (!data.found) {
          this.chatMessages[messageIndex].statusMessage = `Processing... (${this.nlPollingAttempts * 3}s)`
          return
        }

        const workflow = data.workflow
        const status = workflow.status

        if (status === 'COMPLETED') {
          this.stopNLPolling()
          this.chatMessages[messageIndex].status = 'completed'
          this.chatMessages[messageIndex].workflow = workflow
          this.chatMessages[messageIndex].mermaidSvg = null
          this.isGenerating = false

          // Render mermaid diagram
          this.$nextTick(() => {
            this.renderMermaid(messageIndex, workflow.mermaid)
          })
        } else if (status === 'ERROR' || status === 'FAILED') {
          this.stopNLPolling()
          this.chatMessages[messageIndex].status = 'error'
          this.chatMessages[messageIndex].error = workflow.error || 'Generation failed'
          this.isGenerating = false
        } else {
          // Still pending/processing
          this.chatMessages[messageIndex].statusMessage = `Status: ${status} (${this.nlPollingAttempts * 3}s)`
        }
      } catch (error) {
        console.error('Error checking NL status:', error)
        // Don't stop on transient errors, keep polling
        if (this.nlPollingAttempts > 5) {
          this.stopNLPolling()
          this.chatMessages[messageIndex].status = 'error'
          this.chatMessages[messageIndex].error = error.response?.data?.detail || error.message
          this.isGenerating = false
        }
      }
    },

    async renderMermaid(messageIndex, mermaidCode) {
      try {
        const id = `mermaid-${messageIndex}-${Date.now()}`
        const { svg } = await mermaid.render(id, mermaidCode)
        this.$set(this.chatMessages[messageIndex], 'mermaidSvg', svg)
      } catch (error) {
        console.error('Error rendering mermaid:', error)
        this.$set(this.chatMessages[messageIndex], 'mermaidSvg', `<pre class="error-text">Error rendering diagram: ${error.message}</pre>`)
      }
    },

    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.chatMessages
        if (container) {
          container.scrollTop = container.scrollHeight
        }
      })
    },

    copyToClipboard(text) {
      navigator.clipboard.writeText(text).then(() => {
        // Could add a snackbar notification here
        console.log('Copied to clipboard')
      }).catch(err => {
        console.error('Failed to copy:', err)
      })
    },

    // Test methods
    async testCortex() {
      this.testingCortex = true
      this.error = null
      this.testResponse = null

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        const response = await axios.get(baseUrl + "/test-cortex")
        if (response.data.status === 'success') {
          this.testResponse = `Cortex: ${response.data.model}\n${response.data.response}`
        } else {
          this.testResponse = `Cortex Failed: ${response.data.message}`
        }
      } catch (error) {
        this.error = "Error testing Cortex: " + (error.response?.data?.detail || error.message)
      } finally {
        this.testingCortex = false
      }
    },

    async testLitellm() {
      this.testingLitellm = true
      this.error = null
      this.testResponse = null

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        const response = await axios.get(baseUrl + "/test-litellm")
        if (response.data.status === 'success') {
          this.testResponse = `LiteLLM: ${response.data.model}\n${response.data.response}`
        } else {
          this.testResponse = `LiteLLM Failed: ${response.data.message}`
        }
      } catch (error) {
        this.error = "Error testing LiteLLM: " + (error.response?.data?.detail || error.message)
      } finally {
        this.testingLitellm = false
      }
    },

    async testSecrets() {
      this.testingSecrets = true
      this.error = null
      this.testResponse = null

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        const response = await axios.get(baseUrl + "/test-secrets")
        let output = `Secrets: ${response.data.status}\n`
        if (response.data.secrets?.SERPER_API_KEY?.found) {
          output += `SERPER_API_KEY: Found`
        } else {
          output += `SERPER_API_KEY: Not found`
        }
        this.testResponse = output
      } catch (error) {
        this.error = "Error testing Secrets: " + (error.response?.data?.detail || error.message)
      } finally {
        this.testingSecrets = false
      }
    },

    async testSerper() {
      this.testingSerper = true
      this.error = null
      this.testResponse = null

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        const response = await axios.get(baseUrl + "/test-serper")
        if (response.data.status === 'success') {
          this.testResponse = `Serper: ${response.data.results_count} results\n${response.data.response_preview?.title || ''}`
        } else {
          this.testResponse = `Serper Failed: ${response.data.message}`
        }
      } catch (error) {
        this.error = "Error testing Serper: " + (error.response?.data?.detail || error.message)
      } finally {
        this.testingSerper = false
      }
    },

    // Crew methods
    async startCrew() {
      this.loading = true
      this.error = null
      this.testResponse = null
      this.pollingAttempts = 0

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        const startResponse = await axios.post(baseUrl + "/crew/start")
        this.executionId = startResponse.data.execution_id
        this.status = startResponse.data.status
        this.testResponse = `Crew started: ${this.executionId.substring(0, 8)}...`
        this.startPolling()
      } catch (error) {
        this.error = "Error starting crew: " + (error.response?.data?.detail || error.message)
        this.loading = false
      }
    },

    startPolling() {
      this.pollingInterval = setInterval(async () => {
        await this.checkStatus()
      }, 5000)
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
        this.error = "Polling timeout"
        this.loading = false
        return
      }

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        const statusResponse = await axios.get(baseUrl + `/crew/status/${this.executionId}`)
        const data = statusResponse.data

        if (data.status === 'COMPLETED') {
          this.stopPolling()
          this.testResponse = `Crew completed!\n${data.result?.raw || JSON.stringify(data.result, null, 2)}`
          this.loading = false
        } else if (data.status === 'ERROR') {
          this.stopPolling()
          this.error = data.error || 'Unknown error'
          this.loading = false
        } else {
          this.testResponse = `Crew processing... (${this.pollingAttempts * 5}s)`
        }
      } catch (error) {
        this.stopPolling()
        this.error = "Error checking status: " + (error.response?.data?.detail || error.message)
        this.loading = false
      }
    },

    async startExternalToolCrew() {
      this.loadingExternal = true
      this.error = null
      this.testResponse = null
      this.pollingAttemptsExternal = 0

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        const startResponse = await axios.post(baseUrl + "/crew/start-external-tool")
        this.executionIdExternal = startResponse.data.execution_id
        this.statusExternal = startResponse.data.status
        this.testResponse = `External crew started: ${this.executionIdExternal.substring(0, 8)}...`
        this.startPollingExternal()
      } catch (error) {
        this.error = "Error starting external crew: " + (error.response?.data?.detail || error.message)
        this.loadingExternal = false
      }
    },

    startPollingExternal() {
      this.pollingIntervalExternal = setInterval(async () => {
        await this.checkStatusExternal()
      }, 5000)
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
        this.error = "Polling timeout"
        this.loadingExternal = false
        return
      }

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        const statusResponse = await axios.get(baseUrl + `/crew/status/${this.executionIdExternal}`)
        const data = statusResponse.data

        if (data.status === 'COMPLETED') {
          this.stopPollingExternal()
          this.testResponse = `External crew completed!\n${data.result?.raw || JSON.stringify(data.result, null, 2)}`
          this.loadingExternal = false
        } else if (data.status === 'ERROR') {
          this.stopPollingExternal()
          this.error = data.error || 'Unknown error'
          this.loadingExternal = false
        } else {
          this.testResponse = `External crew processing... (${this.pollingAttemptsExternal * 5}s)`
        }
      } catch (error) {
        this.stopPollingExternal()
        this.error = "Error checking status: " + (error.response?.data?.detail || error.message)
        this.loadingExternal = false
      }
    },

    async listCrews() {
      this.listingCrews = true
      this.error = null
      this.testResponse = null
      this.crewExecutions = null

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        const response = await axios.get(baseUrl + "/crew/executions?limit=10")
        if (response.data.executions) {
          this.crewExecutions = response.data.executions
        } else {
          this.error = "No executions found"
        }
      } catch (error) {
        this.error = "Error listing crews: " + (error.response?.data?.detail || error.message)
      } finally {
        this.listingCrews = false
      }
    },

    getStatusColor(status) {
      switch (status) {
        case 'COMPLETED': return 'success'
        case 'PROCESSING': return 'info'
        case 'ERROR': return 'error'
        default: return 'grey'
      }
    }
  },

  beforeDestroy() {
    this.stopPolling()
    this.stopPollingExternal()
    this.stopNLPolling()
  }
}
</script>

<style scoped>
.fill-height {
  height: calc(100vh - 70px);
}

.sidebar-col {
  border-right: 1px solid #e0e0e0;
  overflow-y: auto;
}

.sidebar-dark {
  background-color: #053057 !important;
  color: white !important;
}

.sidebar-dark .v-card__title {
  color: white !important;
}

.sidebar-dark .v-card__subtitle {
  color: rgba(255, 255, 255, 0.7) !important;
}

.sidebar-dark .v-divider {
  border-color: rgba(255, 255, 255, 0.2) !important;
}

.sidebar-dark .test-result-card {
  background-color: rgba(255, 255, 255, 0.1) !important;
  border-color: rgba(255, 255, 255, 0.2) !important;
}

.sidebar-dark .test-result-card .v-card__subtitle {
  color: rgba(255, 255, 255, 0.7) !important;
}

.sidebar-dark .response-text {
  background-color: rgba(0, 0, 0, 0.3) !important;
  color: #A2F3F3 !important;
}

.sidebar-dark .v-data-table {
  background-color: transparent !important;
}

.sidebar-dark .v-data-table th,
.sidebar-dark .v-data-table td {
  color: white !important;
  border-color: rgba(255, 255, 255, 0.2) !important;
}

.dark-text {
  color: #053057 !important;
}

.dark-text .v-icon {
  color: #053057 !important;
}

.chat-col {
  background-color: #F4F3F0;
}

.chat-messages {
  overflow-y: auto;
  background-color: #F4F3F0;
}

.chat-input-area {
  border-top: 1px solid #e0e0e0;
  background-color: white;
}

.user-message {
  border-radius: 18px 18px 4px 18px;
}

.bot-message {
  border-radius: 18px 18px 18px 4px;
  background-color: white;
}

.message-text {
  white-space: pre-wrap;
  word-wrap: break-word;
}

.response-text {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: monospace;
  background-color: #f5f5f5;
  padding: 12px;
  border-radius: 4px;
  font-size: 0.85em;
  max-height: 200px;
  overflow-y: auto;
}

.small-text {
  font-size: 0.75em;
}

.yaml-text {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Fira Code', 'Consolas', monospace;
  background-color: #263238;
  color: #aabfc9;
  padding: 16px;
  border-radius: 4px;
  font-size: 0.85em;
  max-height: 400px;
  overflow-y: auto;
}

.rationale-text {
  white-space: pre-wrap;
  line-height: 1.6;
}

.mermaid-container {
  background-color: white;
  padding: 16px;
  border-radius: 4px;
  overflow-x: auto;
  text-align: center;
}

.mermaid-container svg {
  max-width: 100%;
  height: auto;
}

.error-text {
  color: #f44336;
  font-family: monospace;
}

.text-monospace {
  font-family: monospace;
  font-size: 0.85em;
}

.test-result-card {
  max-height: 300px;
  overflow-y: auto;
}
</style>

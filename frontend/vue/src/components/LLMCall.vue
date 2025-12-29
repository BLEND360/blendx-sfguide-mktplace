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
              color="info"
              block
              class="mb-3"
              @click="showInstructions = true"
              dark
            >
              <v-icon left>mdi-help-circle</v-icon>
              INSTRUCTIONS
            </v-btn>

            <v-btn
              color="info"
              block
              class="mb-3"
              @click="showExampleWorkflow = true"
              dark
            >
              <v-icon left>mdi-file-document-outline</v-icon>
              EXAMPLE WORKFLOW
            </v-btn>

            <v-divider class="mb-3"></v-divider>

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

        </v-card>
      </v-col>

      <!-- Main Chat Area -->
      <v-col cols="12" md="9" class="chat-col">
        <v-card class="fill-height d-flex flex-column" tile>
          <v-card-title class="primary white--text py-3 d-flex align-center">
            <v-icon left dark>{{ showHistoryInMain ? 'mdi-history' : 'mdi-chat' }}</v-icon>
            {{ showHistoryInMain ? 'Workflow History' : 'Workflow Generator Chat' }}
            <v-spacer></v-spacer>
            <v-btn
              small
              :color="showHistoryInMain ? 'white' : 'secondary'"
              :outlined="showHistoryInMain"
              :class="showHistoryInMain ? '' : 'dark-text'"
              @click="toggleHistoryView"
              :loading="loadingHistory"
              class="ml-2"
            >
              <v-icon left small>{{ showHistoryInMain ? 'mdi-chat' : 'mdi-history' }}</v-icon>
              {{ showHistoryInMain ? 'Back to Chat' : 'Load History' }}
            </v-btn>
          </v-card-title>

          <!-- Chat Messages Area -->
          <v-card-text class="flex-grow-1 chat-messages pa-4" ref="chatMessages">
            <!-- Workflow History View -->
            <div v-if="showHistoryInMain">
              <!-- Loading state -->
              <div v-if="loadingHistory" class="text-center py-8">
                <v-progress-circular indeterminate color="primary" size="50"></v-progress-circular>
                <p class="mt-4 grey--text">Loading workflow history...</p>
              </div>

              <!-- Empty state -->
              <div v-else-if="!workflowHistory || workflowHistory.length === 0" class="text-center grey--text py-8">
                <v-icon size="64" color="grey lighten-1">mdi-history</v-icon>
                <p class="mt-4">No workflows found in history</p>
                <v-btn color="primary" @click="loadWorkflowHistory" class="mt-2">
                  <v-icon left>mdi-refresh</v-icon>
                  Refresh
                </v-btn>
              </div>

              <!-- Workflow History Grid -->
              <div v-else>
                <v-row>
                  <v-col
                    v-for="workflow in workflowHistory"
                    :key="workflow.workflow_id"
                    cols="12"
                    sm="6"
                    md="4"
                    lg="3"
                  >
                    <v-card
                      class="workflow-card"
                      outlined
                      hover
                      @click="viewWorkflowDetails(workflow)"
                    >
                      <v-card-text class="pb-2">
                        <div class="d-flex align-center mb-1">
                          <v-icon small color="primary" class="mr-2">mdi-sitemap</v-icon>
                          <span class="workflow-card-title font-weight-medium text-truncate">
                            {{ workflow.title || 'Untitled Workflow' }}
                          </span>
                        </div>
                        <div class="text-caption grey--text mb-2">
                          <v-icon x-small class="mr-1">mdi-calendar</v-icon>
                          {{ formatDate(workflow.created_at) }}
                        </div>
                        <div class="workflow-rationale-preview text-caption grey--text text--darken-1 mb-2">
                          {{ truncateText(workflow.rationale, 100) }}
                        </div>
                        <v-chip x-small :color="getStatusColor(workflow.status)" dark>
                          {{ workflow.status }}
                        </v-chip>
                        <v-chip v-if="workflow.type" x-small outlined class="ml-1">
                          {{ workflow.type }}
                        </v-chip>
                      </v-card-text>
                      <v-card-actions class="pt-0">
                        <v-spacer></v-spacer>
                        <v-btn
                          x-small
                          text
                          color="primary"
                          @click.stop="viewWorkflowDetails(workflow)"
                        >
                          View Details
                          <v-icon right x-small>mdi-arrow-right</v-icon>
                        </v-btn>
                      </v-card-actions>
                    </v-card>
                  </v-col>
                </v-row>
              </div>
            </div>

            <!-- Chat View (original) -->
            <div v-else>
              <!-- Welcome message -->
              <div v-if="chatMessages.length === 0" class="text-center grey--text py-8">
                <v-icon size="64" color="grey lighten-1">mdi-chat-processing-outline</v-icon>
                <p class="mt-4">Send a message to generate a workflow</p>
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
                    <div class="mb-2 d-flex align-center justify-space-between">
                      <div>
                        <v-chip small color="success" class="mr-2">
                          <v-icon left small>mdi-check</v-icon>
                          {{ msg.workflow.status }}
                        </v-chip>
                        <span class="font-weight-medium">{{ msg.workflow.title }}</span>
                      </div>
                      <v-btn
                        small
                        color="primary"
                        @click="openSaveDialog(index, msg.workflow)"
                        :loading="savingWorkflow === index"
                      >
                        <v-icon left small>mdi-content-save</v-icon>
                        Save
                      </v-btn>
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
              class="ml-3"
              @click="sendMessage"
              :loading="isGenerating"
              :disabled="!userMessage.trim() || isGenerating"
            >
              <v-icon left>mdi-send</v-icon>
              Send
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <!-- Example Workflow Dialog -->
    <v-dialog v-model="showExampleWorkflow" max-width="900" scrollable>
      <v-card>
        <v-card-title class="primary white--text">
          <v-icon left dark>mdi-file-document-outline</v-icon>
          Example Workflow: AI News Summary
          <v-spacer></v-spacer>
          <v-btn icon dark @click="showExampleWorkflow = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-card-text class="pa-4">
          <h3 class="mb-3">Description</h3>
          <p class="mb-4">
            This workflow uses a <strong>News Research Crew</strong> to gather the latest AI news using SerperDev and website search tools,
            and a <strong>Summary Crew</strong> to synthesize this information into a well-structured markdown report.
            The flow is sequential, with the summary crew waiting for the research crew to complete before starting its work.
            The Content Synthesizer agent uses a lower temperature (0.3) for more consistent formatting, while the News Researcher
            uses a higher temperature (0.7) for more creative search strategies. The flow includes proper task chaining through the
            context parameter to ensure the summary is based on the gathered news data.
          </p>

          <v-divider class="my-4"></v-divider>

          <v-tabs v-model="exampleTab" background-color="grey lighten-4" class="rounded">
            <v-tab>
              <v-icon left small>mdi-code-braces</v-icon>
              YAML
            </v-tab>
            <v-tab>
              <v-icon left small>mdi-sitemap</v-icon>
              Diagram
            </v-tab>
          </v-tabs>

          <v-tabs-items v-model="exampleTab">
            <!-- YAML Tab -->
            <v-tab-item>
              <v-card flat class="pa-3 mt-2">
                <div class="d-flex justify-end mb-2">
                  <v-btn small text color="primary" @click="copyToClipboard(exampleYaml)">
                    <v-icon left small>mdi-content-copy</v-icon>
                    Copy YAML
                  </v-btn>
                </div>
                <pre class="yaml-text">{{ exampleYaml }}</pre>
              </v-card>
            </v-tab-item>

            <!-- Mermaid Diagram Tab -->
            <v-tab-item>
              <v-card flat class="pa-3 mt-2">
                <div class="d-flex justify-end mb-2">
                  <v-btn small text color="primary" @click="copyToClipboard(exampleMermaid)">
                    <v-icon left small>mdi-content-copy</v-icon>
                    Copy Mermaid
                  </v-btn>
                </div>
                <div class="mermaid-container">
                  <div v-html="exampleMermaidSvg" v-if="exampleMermaidSvg"></div>
                  <div v-else class="text-center grey--text pa-4">
                    <v-progress-circular indeterminate color="primary" size="30"></v-progress-circular>
                    <p class="mt-2">Rendering diagram...</p>
                  </div>
                </div>
              </v-card>
            </v-tab-item>
          </v-tabs-items>
        </v-card-text>

        <v-card-actions class="pa-4">
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="showExampleWorkflow = false">
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Instructions Dialog -->
    <v-dialog v-model="showInstructions" max-width="700" scrollable>
      <v-card>
        <v-card-title class="primary white--text">
          <v-icon left dark>mdi-information</v-icon>
          How to Use This Application
          <v-spacer></v-spacer>
          <v-btn icon dark @click="showInstructions = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-card-text class="pa-4">
          <h3 class="mb-3">Workflow Generator Chat</h3>
          <p class="mb-3">
            The main feature of this application is the <strong>Workflow Generator Chat</strong>.
            It allows you to describe a workflow in natural language, and the AI will generate:
          </p>
          <ul class="mb-4">
            <li><strong>YAML Configuration:</strong> A complete CrewAI workflow definition</li>
            <li><strong>Rationale:</strong> An explanation of why the workflow was designed this way</li>
            <li><strong>Mermaid Diagram:</strong> A visual representation of the workflow</li>
          </ul>

          <v-divider class="my-4"></v-divider>

          <h3 class="mb-3">How to Generate a Workflow</h3>
          <ol class="mb-4">
            <li>Type a description of the workflow you want in the chat input</li>
            <li>Press <kbd>Ctrl+Enter</kbd> (or <kbd>Cmd+Enter</kbd> on Mac) or click the send button</li>
            <li>Wait for the AI to process your request (this may take a few seconds)</li>
            <li>View the results in the three tabs: Rationale, YAML, and Diagram</li>
            <li>Use the "Copy" buttons to copy YAML or Mermaid code</li>
          </ol>

          <v-divider class="my-4"></v-divider>

          <h3 class="mb-3">Test Controls (Left Sidebar)</h3>
          <p class="mb-2">Use these buttons to verify the system is working correctly:</p>
          <ul class="mb-4">
            <li><strong>TEST CORTEX:</strong> Tests the Snowflake Cortex LLM connection</li>
            <li><strong>TEST LITELLM:</strong> Tests the LiteLLM integration</li>
            <li><strong>TEST SECRETS:</strong> Verifies that secrets (like API keys) are configured</li>
            <li><strong>TEST SERPER:</strong> Tests the Serper search API integration</li>
          </ul>

          <v-divider class="my-4"></v-divider>

          <h3 class="mb-3">Workflow History</h3>
          <p class="mb-2">Access and manage your previously generated workflows:</p>
          <ul class="mb-4">
            <li><strong>LOAD HISTORY:</strong> Click this button in the chat header to view all your saved workflows</li>
            <li><strong>Workflow Cards:</strong> Each workflow is displayed as a card showing the title, date, rationale preview, and status</li>
            <li><strong>View Details:</strong> Click on any workflow card to see the full details including Rationale, YAML, and Diagram</li>
            <li><strong>Back to Chat:</strong> Click this button to return to the chat interface</li>
            <li><strong>Save Workflows:</strong> After generating a workflow, use the "Save" button to add it to your history with a custom name</li>
          </ul>

          <v-alert type="info" dense class="mt-4">
            <strong>Tip:</strong> If you encounter errors, use the TEST buttons first to diagnose which service might be unavailable.
          </v-alert>
        </v-card-text>

        <v-card-actions class="pa-4">
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="showInstructions = false">
            Got it!
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Workflow Details Dialog -->
    <v-dialog v-model="showWorkflowDetails" max-width="900" scrollable>
      <v-card v-if="selectedWorkflow">
        <v-card-title class="primary white--text">
          <v-icon left dark>mdi-sitemap</v-icon>
          {{ selectedWorkflow.title || 'Workflow Details' }}
          <v-spacer></v-spacer>
          <v-btn icon dark @click="showWorkflowDetails = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-card-text class="pa-4">
          <div class="mb-3">
            <v-chip small :color="getStatusColor(selectedWorkflow.status)" dark class="mr-2">
              {{ selectedWorkflow.status }}
            </v-chip>
            <v-chip small outlined class="mr-2">
              <v-icon left small>mdi-calendar</v-icon>
              {{ formatDate(selectedWorkflow.created_at) }}
            </v-chip>
            <v-chip small outlined v-if="selectedWorkflow.type">
              <v-icon left small>mdi-tag</v-icon>
              {{ selectedWorkflow.type }}
            </v-chip>
          </div>

          <v-tabs v-model="workflowDetailsTab" background-color="grey lighten-4" class="rounded">
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

          <v-tabs-items v-model="workflowDetailsTab">
            <!-- Rationale Tab -->
            <v-tab-item>
              <v-card flat class="pa-3 mt-2">
                <div class="rationale-text">{{ selectedWorkflow.rationale || 'No rationale available' }}</div>
              </v-card>
            </v-tab-item>

            <!-- YAML Tab -->
            <v-tab-item>
              <v-card flat class="pa-3 mt-2">
                <div class="d-flex justify-end mb-2">
                  <v-btn small text color="primary" @click="copyToClipboard(selectedWorkflow.yaml_text)">
                    <v-icon left small>mdi-content-copy</v-icon>
                    Copy YAML
                  </v-btn>
                </div>
                <pre class="yaml-text">{{ selectedWorkflow.yaml_text || 'No YAML available' }}</pre>
              </v-card>
            </v-tab-item>

            <!-- Mermaid Diagram Tab -->
            <v-tab-item>
              <v-card flat class="pa-3 mt-2">
                <div class="d-flex justify-end mb-2">
                  <v-btn small text color="primary" @click="copyToClipboard(selectedWorkflow.mermaid)">
                    <v-icon left small>mdi-content-copy</v-icon>
                    Copy Mermaid
                  </v-btn>
                </div>
                <div class="mermaid-container">
                  <div v-html="selectedWorkflowMermaidSvg" v-if="selectedWorkflowMermaidSvg"></div>
                  <div v-else-if="selectedWorkflow.mermaid" class="text-center grey--text pa-4">
                    <v-progress-circular indeterminate color="primary" size="30"></v-progress-circular>
                    <p class="mt-2">Rendering diagram...</p>
                  </div>
                  <div v-else class="text-center grey--text pa-4">
                    <v-icon size="48" color="grey lighten-1">mdi-sitemap</v-icon>
                    <p class="mt-2">No diagram available</p>
                  </div>
                </div>
              </v-card>
            </v-tab-item>
          </v-tabs-items>
        </v-card-text>

        <v-card-actions class="pa-4">
          <v-spacer></v-spacer>
          <v-btn
            color="info"
            class="mr-2"
            @click="listWorkflowExecutions(selectedWorkflow)"
            :loading="loadingWorkflowExecutions"
          >
            <v-icon left>mdi-history</v-icon>
            List Executions
          </v-btn>
          <v-btn
            color="success"
            class="mr-2"
            @click="runWorkflowFromHistory(selectedWorkflow)"
            :loading="runningWorkflow === 'history'"
            :disabled="runningWorkflow !== null"
          >
            <v-icon left>mdi-play</v-icon>
            Run Workflow
          </v-btn>
          <v-btn color="primary" @click="showWorkflowDetails = false">
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Save Workflow Dialog -->
    <v-dialog v-model="showSaveDialog" max-width="500">
      <v-card>
        <v-card-title class="primary white--text">
          <v-icon left dark>mdi-content-save</v-icon>
          Save Workflow
          <v-spacer></v-spacer>
          <v-btn icon dark @click="showSaveDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-card-text class="pa-4">
          <p class="mb-4">Save this workflow to your history. You can modify the name if you'd like.</p>
          <v-text-field
            v-model="saveWorkflowTitle"
            label="Workflow Title"
            outlined
            dense
            placeholder="Enter a descriptive name"
            autofocus
            @keydown.enter="confirmSaveWorkflow"
          ></v-text-field>
          <v-alert v-if="saveError" type="error" dense class="mt-2">
            {{ saveError }}
          </v-alert>
        </v-card-text>

        <v-card-actions class="pa-4">
          <v-spacer></v-spacer>
          <v-btn text @click="showSaveDialog = false">
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            @click="confirmSaveWorkflow"
            :loading="savingWorkflow !== null"
            :disabled="!saveWorkflowTitle.trim()"
          >
            <v-icon left>mdi-content-save</v-icon>
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Run Workflow Input Dialog -->
    <v-dialog v-model="showRunInputDialog" max-width="500">
      <v-card>
        <v-card-title class="success white--text">
          <v-icon left dark>mdi-play</v-icon>
          Run Workflow
          <v-spacer></v-spacer>
          <v-btn icon dark @click="showRunInputDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-card-text class="pa-4">
          <p class="mb-4">
            You are about to run this workflow using ephemeral execution (no data will be persisted).
          </p>
          <v-chip small outlined class="mb-4">
            <v-icon left small>mdi-tag</v-icon>
            {{ workflowToRun?.type === 'run-build-flow' ? 'Flow' : 'Crew' }}
          </v-chip>
          <v-textarea
            v-model="runWorkflowInput"
            label="Input (optional)"
            outlined
            dense
            rows="3"
            placeholder="Enter any input for the workflow..."
            hint="Provide input data for your workflow. Leave empty if not needed."
            persistent-hint
          ></v-textarea>
        </v-card-text>

        <v-card-actions class="pa-4">
          <v-spacer></v-spacer>
          <v-btn text @click="showRunInputDialog = false">
            Cancel
          </v-btn>
          <v-btn
            color="success"
            @click="confirmRunWorkflow"
          >
            <v-icon left>mdi-play</v-icon>
            Run Workflow
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Run Workflow Result Dialog -->
    <v-dialog v-model="showRunResultDialog" max-width="800" persistent scrollable>
      <v-card>
        <v-card-title class="primary white--text">
          <v-icon left dark>mdi-cog</v-icon>
          Workflow Execution
          <v-spacer></v-spacer>
          <v-chip
            small
            :color="getStatusColor(runResultStatus)"
            dark
            class="mr-2"
          >
            {{ runResultStatus }}
          </v-chip>
          <v-btn
            icon
            dark
            @click="closeRunResultDialog"
            :disabled="runResultStatus === 'RUNNING'"
          >
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-card-text class="pa-4">
          <!-- Running state -->
          <div v-if="runResultStatus === 'RUNNING' || runResultStatus === 'STARTING'" class="text-center py-8">
            <v-progress-circular indeterminate color="primary" size="60" width="6"></v-progress-circular>
            <p class="mt-4 grey--text text--darken-1">
              {{ runResultStatus === 'STARTING' ? 'Starting workflow execution...' : 'Workflow is running...' }}
            </p>
            <p class="text-caption grey--text">
              Elapsed time: {{ ephemeralPollingAttempts * 5 }} seconds
            </p>
          </div>

          <!-- Error state -->
          <v-alert v-else-if="runResultStatus === 'FAILED' || runResultError" type="error" class="mb-0">
            <div class="font-weight-medium mb-2">Execution Failed</div>
            <pre class="error-result-text">{{ runResultError }}</pre>
          </v-alert>

          <!-- Success state -->
          <div v-else-if="runResultStatus === 'COMPLETED'">
            <v-alert type="success" dense class="mb-4">
              Workflow completed successfully!
            </v-alert>
            <v-card outlined class="result-card">
              <v-card-subtitle class="pb-1 d-flex align-center">
                <v-icon small class="mr-1">mdi-text-box-outline</v-icon>
                Execution Result
              </v-card-subtitle>
              <v-card-text>
                <div class="d-flex justify-end mb-2">
                  <v-btn small text color="primary" @click="copyToClipboard(getRawOutput(runResultData))">
                    <v-icon left small>mdi-content-copy</v-icon>
                    Copy Result
                  </v-btn>
                </div>
                <!-- Auto-detect content type and render appropriately -->
                <div v-if="detectContentType(runResultData) === 'markdown'" class="markdown-content" v-html="renderMarkdown(getRawOutput(runResultData))"></div>
                <pre v-else-if="detectContentType(runResultData) === 'json'" class="json-content">{{ formatJsonOutput(runResultData) }}</pre>
                <pre v-else class="result-text">{{ getRawOutput(runResultData) }}</pre>
              </v-card-text>
            </v-card>
          </div>
        </v-card-text>

        <v-card-actions class="pa-4" v-if="runResultStatus !== 'RUNNING' && runResultStatus !== 'STARTING'">
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="closeRunResultDialog">
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Workflow Executions Dialog -->
    <v-dialog v-model="showWorkflowExecutionsDialog" max-width="700" scrollable>
      <v-card>
        <v-card-title class="info white--text">
          <v-icon left dark>mdi-history</v-icon>
          Workflow Executions
          <v-spacer></v-spacer>
          <v-btn icon dark @click="showWorkflowExecutionsDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-card-text class="pa-4">
          <!-- Loading state -->
          <div v-if="loadingWorkflowExecutions" class="text-center py-8">
            <v-progress-circular indeterminate color="info" size="50"></v-progress-circular>
            <p class="mt-4 grey--text">Loading executions...</p>
          </div>

          <!-- Empty state -->
          <div v-else-if="!workflowExecutions || workflowExecutions.length === 0" class="text-center grey--text py-8">
            <v-icon size="64" color="grey lighten-1">mdi-playlist-remove</v-icon>
            <p class="mt-4">No executions found for this workflow</p>
          </div>

          <!-- Executions Table -->
          <v-simple-table v-else dense class="executions-table">
            <template v-slot:default>
              <thead>
                <tr>
                  <th>Execution ID</th>
                  <th>Status</th>
                  <th>Started</th>
                  <th>Updated</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="exec in workflowExecutions" :key="exec.execution_id">
                  <td class="text-monospace">{{ exec.execution_id.substring(0, 8) }}...</td>
                  <td>
                    <v-chip x-small :color="getStatusColor(exec.status)" dark>
                      {{ exec.status }}
                    </v-chip>
                  </td>
                  <td class="text-caption">{{ formatDate(exec.execution_timestamp) }}</td>
                  <td class="text-caption">{{ formatDate(exec.updated_at) }}</td>
                  <td>
                    <v-btn
                      x-small
                      text
                      color="primary"
                      @click="viewExecutionDetails(exec)"
                      :loading="viewingExecutionId === exec.execution_id"
                    >
                      <v-icon x-small left>mdi-eye</v-icon>
                      View
                    </v-btn>
                  </td>
                </tr>
              </tbody>
            </template>
          </v-simple-table>
        </v-card-text>

        <v-card-actions class="pa-4">
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="showWorkflowExecutionsDialog = false">
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Execution Details Dialog -->
    <v-dialog v-model="showExecutionDetailsDialog" max-width="800" scrollable>
      <v-card>
        <v-card-title class="primary white--text">
          <v-icon left dark>mdi-file-document-outline</v-icon>
          Execution Details
          <v-spacer></v-spacer>
          <v-chip
            small
            :color="getStatusColor(executionDetails?.status)"
            dark
            class="mr-2"
          >
            {{ executionDetails?.status }}
          </v-chip>
          <v-btn icon dark @click="showExecutionDetailsDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-card-text class="pa-4" v-if="executionDetails">
          <div class="mb-3">
            <v-chip small outlined class="mr-2">
              <v-icon left small>mdi-identifier</v-icon>
              {{ executionDetails.execution_id }}
            </v-chip>
          </div>

          <!-- Error state -->
          <v-alert v-if="executionDetails.error" type="error" class="mb-4">
            <div class="font-weight-medium mb-2">Execution Error</div>
            <pre class="error-result-text">{{ executionDetails.error }}</pre>
          </v-alert>

          <!-- Result -->
          <v-card v-if="executionDetails.result" outlined class="result-card">
            <v-card-subtitle class="pb-1 d-flex align-center">
              <v-icon small class="mr-1">mdi-text-box-outline</v-icon>
              Execution Result
            </v-card-subtitle>
            <v-card-text>
              <div class="d-flex justify-end mb-2">
                <v-btn small text color="primary" @click="copyToClipboard(getRawOutput(executionDetails.result))">
                  <v-icon left small>mdi-content-copy</v-icon>
                  Copy Result
                </v-btn>
              </div>
              <!-- Auto-detect content type and render appropriately -->
              <div v-if="detectContentType(executionDetails.result) === 'markdown'" class="markdown-content" v-html="renderMarkdown(getRawOutput(executionDetails.result))"></div>
              <pre v-else-if="detectContentType(executionDetails.result) === 'json'" class="json-content">{{ formatJsonOutput(executionDetails.result) }}</pre>
              <pre v-else class="result-text">{{ getRawOutput(executionDetails.result) }}</pre>
            </v-card-text>
          </v-card>

          <!-- No result message -->
          <div v-else-if="!executionDetails.error" class="text-center grey--text py-4">
            <v-icon size="48" color="grey lighten-1">mdi-file-document-outline</v-icon>
            <p class="mt-2">No result data available</p>
          </div>
        </v-card-text>

        <v-card-actions class="pa-4">
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="showExecutionDetailsDialog = false">
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script>
import axios from 'axios'
import mermaid from 'mermaid'

export default {
  name: 'LLMCall',

  data: () => ({
    // UI state
    showInstructions: false,
    showExampleWorkflow: false,
    exampleTab: 0,
    exampleMermaidSvg: null,

    // Example workflow data
    exampleYaml: `flow:
  flow_name: "AI News Summary Flow"
  verbose: true
  class_name: "AINewsSummaryFlow"
  crews: ["News Research Crew", "Summary Crew"]

execution_group_name: "AI News Analysis"

crews:
  - name: "News Research Crew"
    process: "sequential"
    verbose: true
    memory: true
    manager: null
    agents: ["AI News Researcher"]
    tasks: ["Gather AI News"]

  - name: "Summary Crew"
    process: "sequential"
    verbose: true
    memory: true
    manager: null
    agents: ["Content Synthesizer"]
    tasks: ["Create Summary Report"]

agents:
  - role: "AI News Researcher"
    goal: "Gather and analyze the latest artificial intelligence news and developments"
    backstory: "Expert technology researcher specializing in AI industry trends and developments"
    tools:
      - crewai_tools: ["SerperDevTool"]
    verbose: true
    llm:
      provider: "snowflake"
      model: "llama3.1-70b"
      temperature: 0.7
    allow_delegation: false

  - role: "Content Synthesizer"
    goal: "Create clear, well-structured markdown summaries of AI news and developments"
    backstory: "Experienced technical writer specializing in creating concise, informative summaries of complex topics"
    verbose: true
    llm:
      provider: "snowflake"
      model: "llama3.1-70b"
      temperature: 0.3
    allow_delegation: false

tasks:
  - name: "Gather AI News"
    description: "Research and collect the latest significant news and developments in artificial intelligence from the past week"
    agent: "AI News Researcher"
    expected_output: "A comprehensive collection of recent AI news items with sources and key details"
    tools:
      - crewai_tools: ["SerperDevTool"]
    context: []
    output_file: null

  - name: "Create Summary Report"
    description: "Create a well-structured markdown report summarizing the key AI news and developments, organized by category and importance"
    agent: "Content Synthesizer"
    expected_output: "A markdown-formatted report summarizing AI news with clear sections, highlights, and source references"
    tools: []
    context: ["Gather AI News"]
    output_file: null

flow_methods:
    - name: "run_research"
      type: "start"
      action: "run_crew"
      crew: "News Research Crew"
      output: "News research completed"
    - name: "run_summary"
      type: "listen"
      listen_to: ["run_research"]
      action: "run_crew"
      crew: "Summary Crew"
      output: "Summary creation completed"
    - name: "flow_complete"
      type: "listen"
      listen_to: ["run_summary"]
      output: "AI news summary flow completed successfully"`,

    exampleMermaid: `---
title: AI News Summary Flow
---
flowchart LR
    %% Global Tools Section
    Tool_SerperDev[("SerperDev API")]

    %% News Research Phase
    subgraph Crew_Research["News Research Crew"]
        Agent_Researcher(("AI News Researcher Agent"))
        Task_GatherNews["Gather AI News"]
        Flow_Research{{"Research Complete"}}

        Agent_Researcher -->|"executes"| Task_GatherNews
        Task_GatherNews -->|"completes"| Flow_Research
    end

    %% Summary Creation Phase
    subgraph Crew_Summary["Summary Crew"]
        Agent_Synthesizer(("Content Synthesizer Agent"))
        Task_CreateSummary["Create Summary Report"]
        Flow_Summary{{"Summary Complete"}}

        Agent_Synthesizer -->|"executes"| Task_CreateSummary
        Task_CreateSummary -->|"completes"| Flow_Summary
    end

    %% Final Output
    FinalReport[/"AI News Summary Report.md"/]

    %% Cross-crew Dependencies
    Flow_Research -->|"provides news data"| Task_CreateSummary
    Flow_Summary ==>|"delivers"| FinalReport

    %% Tool Usage
    Tool_SerperDev -.->|"supports research"| Agent_Researcher

    %% Apply consistent pastel colors
    class Crew_Research,Crew_Summary crewStyle
    class Agent_Researcher,Agent_Synthesizer agentStyle
    class Task_GatherNews,Task_CreateSummary taskStyle
    class Flow_Research,Flow_Summary flowStyle
    class Tool_SerperDev toolStyle
    class FinalReport outputStyle

    %% Color definitions
    classDef crewStyle fill:#E8F4FD,stroke:#5B9BD5,stroke-width:2px
    classDef agentStyle fill:#F2E8F7,stroke:#9575CD,stroke-width:2px
    classDef taskStyle fill:#E8F5E8,stroke:#81C784,stroke-width:2px
    classDef flowStyle fill:#FFF3E0,stroke:#FFB74D,stroke-width:2px
    classDef toolStyle fill:#FCE4EC,stroke:#F06292,stroke-width:2px
    classDef outputStyle fill:#FFEBEE,stroke:#E91E63,stroke-width:3px`,

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
    testingEaiEnv: false,

    // NL Generator polling
    nlPollingInterval: null,
    nlPollingAttempts: 0,

    // Workflow History
    workflowHistory: null,
    loadingHistory: false,
    showWorkflowDetails: false,
    selectedWorkflow: null,
    workflowDetailsTab: 0,
    showHistoryInMain: false,
    selectedWorkflowMermaidSvg: null,

    // Save Workflow Dialog
    showSaveDialog: false,
    saveWorkflowTitle: '',
    workflowToSave: null,
    savingWorkflow: null,
    saveMessageIndex: null,
    saveError: null,

    // Run Workflow (Ephemeral Execution)
    runningWorkflow: null,
    ephemeralExecutionId: null,
    ephemeralPollingInterval: null,
    ephemeralPollingAttempts: 0,
    maxEphemeralPollingAttempts: 360,  // 30 minutes at 5-second intervals
    showRunResultDialog: false,
    runResultStatus: null,
    runResultData: null,
    runResultError: null,
    runWorkflowInput: '',
    showRunInputDialog: false,
    workflowToRun: null,
    runMessageIndex: null,

    // Workflow Executions
    showWorkflowExecutionsDialog: false,
    workflowExecutions: null,
    loadingWorkflowExecutions: false,
    showExecutionDetailsDialog: false,
    executionDetails: null,
    viewingExecutionId: null,
  }),

  computed: {
    // Only disable test buttons when another test is running (not during workflow generation)
    anyTestLoading() {
      return this.testingCortex || this.testingLitellm || this.testingSecrets ||
             this.testingSerper || this.testingEaiEnv || this.loadingHistory
    }
  },

  watch: {
    showExampleWorkflow(val) {
      if (val && !this.exampleMermaidSvg) {
        this.$nextTick(() => {
          this.renderExampleMermaid()
        })
      }
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

      // If we're in history view, switch to chat view first
      if (this.showHistoryInMain) {
        this.showHistoryInMain = false
      }

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
      if (!mermaidCode) {
        this.$set(this.chatMessages[messageIndex], 'mermaidSvg', `<pre class="error-text">No diagram data available</pre>`)
        return
      }
      try {
        const id = `mermaid-${messageIndex}-${Date.now()}`
        const { svg } = await mermaid.render(id, mermaidCode)
        this.$set(this.chatMessages[messageIndex], 'mermaidSvg', svg)
      } catch (error) {
        console.error('Error rendering mermaid:', error)
        this.$set(this.chatMessages[messageIndex], 'mermaidSvg', `<pre class="error-text">Error rendering diagram: ${error.message}</pre>`)
      }
    },

    async renderExampleMermaid() {
      try {
        const id = `mermaid-example-${Date.now()}`
        const { svg } = await mermaid.render(id, this.exampleMermaid)
        this.exampleMermaidSvg = svg
      } catch (error) {
        console.error('Error rendering example mermaid:', error)
        this.exampleMermaidSvg = `<pre class="error-text">Error rendering diagram: ${error.message}</pre>`
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
        const serperKey = response.data.secrets?.SERPER_API_KEY
        if (serperKey?.found) {
          output += `SERPER_API_KEY: Found\n`
          output += `  Source: ${serperKey.source}\n`
          output += `  Preview: ${serperKey.preview}\n`
          output += `  Length: ${serperKey.length}`
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

    getStatusColor(status) {
      switch (status) {
        case 'COMPLETED': return 'success'
        case 'PROCESSING': return 'info'
        case 'PENDING': return 'warning'
        case 'ERROR': return 'error'
        case 'FAILED': return 'error'
        default: return 'grey'
      }
    },

    // Workflow History methods
    async loadWorkflowHistory() {
      this.loadingHistory = true
      this.error = null

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        const response = await axios.get(baseUrl + '/nl-ai-generator-async/workflows?limit=20&status_filter=COMPLETED')
        if (response.data.workflows) {
          this.workflowHistory = response.data.workflows
        } else {
          this.workflowHistory = []
        }
      } catch (error) {
        this.error = "Error loading workflow history: " + (error.response?.data?.detail || error.message)
        this.workflowHistory = []
      } finally {
        this.loadingHistory = false
      }
    },

    async toggleHistoryView() {
      this.showHistoryInMain = !this.showHistoryInMain
      if (this.showHistoryInMain && (!this.workflowHistory || this.workflowHistory.length === 0)) {
        await this.loadWorkflowHistory()
      }
    },

    truncateText(text, maxLength) {
      if (!text) return ''
      if (text.length <= maxLength) return text
      return text.substring(0, maxLength) + '...'
    },

    viewWorkflowDetails(workflow) {
      this.selectedWorkflow = workflow
      this.workflowDetailsTab = 0
      this.selectedWorkflowMermaidSvg = null
      this.showWorkflowDetails = true

      // Render mermaid diagram if available
      if (workflow.mermaid) {
        this.$nextTick(() => {
          this.renderSelectedWorkflowMermaid(workflow.mermaid)
        })
      }
    },

    async renderSelectedWorkflowMermaid(mermaidCode) {
      if (!mermaidCode) return
      try {
        const id = `mermaid-details-${Date.now()}`
        const { svg } = await mermaid.render(id, mermaidCode)
        this.selectedWorkflowMermaidSvg = svg
      } catch (error) {
        console.error('Error rendering mermaid:', error)
        this.selectedWorkflowMermaidSvg = `<pre class="error-text">Error rendering diagram: ${error.message}</pre>`
      }
    },

    formatDate(dateString) {
      if (!dateString) return ''
      const date = new Date(dateString)
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    },

    // Save Workflow methods
    openSaveDialog(messageIndex, workflow) {
      this.saveMessageIndex = messageIndex
      this.workflowToSave = workflow
      // Use existing title, or extract from YAML, or generate default
      this.saveWorkflowTitle = workflow.title || this.extractFlowNameFromYaml(workflow.yaml_text) || ''
      this.saveError = null
      this.showSaveDialog = true
    },

    extractFlowNameFromYaml(yamlText) {
      if (!yamlText) return null
      try {
        // Look for flow_name or crew_name in the YAML
        const flowNameMatch = yamlText.match(/flow_name:\s*["']?([^"'\n]+)["']?/i)
        if (flowNameMatch) return flowNameMatch[1].trim()

        const crewNameMatch = yamlText.match(/crew_name:\s*["']?([^"'\n]+)["']?/i)
        if (crewNameMatch) return crewNameMatch[1].trim()

        return null
      } catch (e) {
        return null
      }
    },

    async confirmSaveWorkflow() {
      if (!this.saveWorkflowTitle.trim() || !this.workflowToSave) return

      this.savingWorkflow = this.saveMessageIndex
      this.saveError = null

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        const response = await axios.put(
          baseUrl + `/nl-ai-generator-async/${this.workflowToSave.workflow_id}`,
          {
            title: this.saveWorkflowTitle.trim()
          }
        )

        if (response.data.success) {
          // Update the workflow title in the chat message
          if (this.saveMessageIndex !== null && this.chatMessages[this.saveMessageIndex]) {
            this.chatMessages[this.saveMessageIndex].workflow.title = this.saveWorkflowTitle.trim()
          }

          // Refresh workflow history if it's loaded
          if (this.workflowHistory) {
            this.loadWorkflowHistory()
          }

          this.showSaveDialog = false
        } else {
          this.saveError = response.data.message || 'Failed to save workflow'
        }
      } catch (error) {
        console.error('Error saving workflow:', error)
        this.saveError = error.response?.data?.detail || error.message || 'Failed to save workflow'
      } finally {
        this.savingWorkflow = null
      }
    },

    // Run Workflow methods
    runWorkflow(messageIndex, workflow) {
      this.runMessageIndex = messageIndex
      this.workflowToRun = workflow
      this.runWorkflowInput = ''
      this.showRunInputDialog = true
    },

    runWorkflowFromHistory(workflow) {
      this.runMessageIndex = 'history'
      this.workflowToRun = workflow
      this.runWorkflowInput = ''
      this.showWorkflowDetails = false
      this.showRunInputDialog = true
    },

    async confirmRunWorkflow() {
      if (!this.workflowToRun) return

      this.showRunInputDialog = false
      this.runningWorkflow = this.runMessageIndex
      this.runResultError = null
      this.runResultData = null
      this.runResultStatus = 'STARTING'

      const baseUrl = process.env.VUE_APP_API_URL
      const workflow = this.workflowToRun

      // Determine endpoint based on workflow type
      // type is "run-build-flow" or "run-build-crew"
      const isFlow = workflow.type === 'run-build-flow'
      const endpoint = isFlow ? '/ephemeral/run-flow-async' : '/ephemeral/run-crew-async'

      try {
        const response = await axios.post(baseUrl + endpoint, {
          yaml_text: workflow.yaml_text,
          input: this.runWorkflowInput || null,
          workflow_id: workflow.workflow_id || null
        })

        this.ephemeralExecutionId = response.data.execution_id
        this.runResultStatus = 'RUNNING'
        this.showRunResultDialog = true

        // Start polling for results
        this.startEphemeralPolling()
      } catch (error) {
        console.error('Error starting workflow execution:', error)
        this.runResultError = error.response?.data?.detail || error.message
        this.runResultStatus = 'FAILED'
        this.showRunResultDialog = true
        this.runningWorkflow = null
      }
    },

    startEphemeralPolling() {
      this.ephemeralPollingAttempts = 0
      this.ephemeralPollingInterval = setInterval(async () => {
        await this.checkEphemeralStatus()
      }, 5000)  // Poll every 5 seconds
    },

    stopEphemeralPolling() {
      if (this.ephemeralPollingInterval) {
        clearInterval(this.ephemeralPollingInterval)
        this.ephemeralPollingInterval = null
      }
    },

    async checkEphemeralStatus() {
      this.ephemeralPollingAttempts++

      if (this.ephemeralPollingAttempts > this.maxEphemeralPollingAttempts) {
        this.stopEphemeralPolling()
        this.runResultError = 'The workflow is taking longer than expected. You can check the result later in "List Executions".'
        this.runResultStatus = 'PENDING'
        this.runningWorkflow = null
        return
      }

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        const response = await axios.get(baseUrl + `/ephemeral/status/${this.ephemeralExecutionId}`)
        const data = response.data

        this.runResultStatus = data.status

        if (data.status === 'COMPLETED') {
          this.stopEphemeralPolling()
          this.runResultData = data.result
          this.runningWorkflow = null
        } else if (data.status === 'FAILED' || data.status === 'NOT_FOUND') {
          this.stopEphemeralPolling()
          this.runResultError = data.result || 'Workflow execution failed'
          this.runningWorkflow = null
        }
        // If still RUNNING, continue polling
      } catch (error) {
        console.error('Error checking ephemeral status:', error)
        // Don't stop on transient errors, keep polling
        if (this.ephemeralPollingAttempts > 5 && error.response?.status >= 500) {
          this.stopEphemeralPolling()
          this.runResultError = error.response?.data?.detail || error.message
          this.runResultStatus = 'FAILED'
          this.runningWorkflow = null
        }
      }
    },

    closeRunResultDialog() {
      this.showRunResultDialog = false
      // Cleanup the ephemeral execution from memory
      if (this.ephemeralExecutionId) {
        const baseUrl = process.env.VUE_APP_API_URL
        axios.delete(baseUrl + `/ephemeral/status/${this.ephemeralExecutionId}`).catch(() => {})
        this.ephemeralExecutionId = null
      }
    },

    formatRunResult(result) {
      if (!result) return 'No result'
      if (typeof result === 'string') return result
      if (Array.isArray(result)) {
        return result.map((r, i) => `--- Result ${i + 1} ---\n${r}`).join('\n\n')
      }
      return JSON.stringify(result, null, 2)
    },

    // Workflow Executions methods
    async listWorkflowExecutions(workflow) {
      if (!workflow || !workflow.workflow_id) return

      this.loadingWorkflowExecutions = true
      this.workflowExecutions = null
      this.showWorkflowExecutionsDialog = true

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        const response = await axios.get(
          baseUrl + `/crew/executions/workflow/${workflow.workflow_id}?limit=20`
        )
        if (response.data.executions) {
          this.workflowExecutions = response.data.executions
        } else {
          this.workflowExecutions = []
        }
      } catch (error) {
        console.error('Error loading workflow executions:', error)
        this.workflowExecutions = []
      } finally {
        this.loadingWorkflowExecutions = false
      }
    },

    async viewExecutionDetails(exec) {
      this.viewingExecutionId = exec.execution_id
      this.executionDetails = null

      const baseUrl = process.env.VUE_APP_API_URL

      try {
        const response = await axios.get(baseUrl + `/crew/status/${exec.execution_id}`)
        this.executionDetails = response.data
        this.showExecutionDetailsDialog = true
      } catch (error) {
        console.error('Error loading execution details:', error)
        this.executionDetails = {
          execution_id: exec.execution_id,
          status: exec.status,
          error: error.response?.data?.detail || error.message
        }
        this.showExecutionDetailsDialog = true
      } finally {
        this.viewingExecutionId = null
      }
    },

    // Get raw output from result (handles different result formats)
    getRawOutput(result) {
      if (!result) return 'No result'
      if (typeof result === 'string') return result
      if (result.raw) return result.raw
      return JSON.stringify(result, null, 2)
    },

    // Detect content type: 'json', 'markdown', or 'text'
    detectContentType(result) {
      const raw = this.getRawOutput(result)
      if (!raw || raw === 'No result') return 'text'

      // Check if it's JSON (object or array)
      if (typeof result === 'object' && !result.raw) {
        return 'json'
      }

      // Check if the raw content looks like JSON
      const trimmed = raw.trim()
      if ((trimmed.startsWith('{') && trimmed.endsWith('}')) ||
          (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
        try {
          JSON.parse(trimmed)
          return 'json'
        } catch (e) {
          // Not valid JSON, continue checking
        }
      }

      // Check if it contains markdown patterns
      const markdownPatterns = [
        /^#{1,6}\s+.+$/m,           // Headers: # ## ### etc
        /\*\*.+?\*\*/,              // Bold: **text**
        /^[-*]\s+.+$/m,             // Bullet lists: - item or * item
        /^\d+\.\s+.+$/m,            // Numbered lists: 1. item
        /\[.+?\]\(.+?\)/,           // Links: [text](url)
        /^>\s+.+$/m,                // Blockquotes: > text
        /`{1,3}[^`]+`{1,3}/,        // Code: `code` or ```code```
        /^={3,}$|^-{3,}$/m          // Horizontal rules: === or ---
      ]

      for (const pattern of markdownPatterns) {
        if (pattern.test(raw)) {
          return 'markdown'
        }
      }

      return 'text'
    },

    // Format JSON output with indentation
    formatJsonOutput(result) {
      if (!result) return 'No result'
      if (typeof result === 'object') {
        return JSON.stringify(result, null, 2)
      }
      // Try to parse and re-format if it's a JSON string
      const raw = this.getRawOutput(result)
      try {
        const parsed = JSON.parse(raw)
        return JSON.stringify(parsed, null, 2)
      } catch (e) {
        return raw
      }
    },

    // Render markdown to HTML
    renderMarkdown(text) {
      if (!text) return ''
      let html = this.escapeHtml(text)

      // Convert headers
      html = html.replace(/^### (.+)$/gm, '<h4 class="mt-3 mb-2 primary--text">$1</h4>')
      html = html.replace(/^## (.+)$/gm, '<h3 class="mt-4 mb-2 primary--text">$1</h3>')
      html = html.replace(/^# (.+)$/gm, '<h2 class="mt-4 mb-2 primary--text">$1</h2>')

      // Convert bold and italic
      html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')

      // Convert inline code
      html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')

      // Convert bullet points
      html = html.replace(/^[-*] (.+)$/gm, '<li>$1</li>')
      html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul class="ml-4 mb-2">$&</ul>')

      // Convert numbered lists
      html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>')

      // Convert blockquotes
      html = html.replace(/^> (.+)$/gm, '<blockquote class="blockquote">$1</blockquote>')

      // Convert newlines to br
      html = html.replace(/\n/g, '<br>')

      return `<div class="markdown-rendered">${html}</div>`
    },

    escapeHtml(text) {
      const div = document.createElement('div')
      div.textContent = text
      return div.innerHTML
    }
  },

  beforeDestroy() {
    this.stopNLPolling()
    this.stopEphemeralPolling()
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

/* Crew Executions Table Styles */
.crew-table-card {
  background-color: #1e1e1e !important;
  border-color: rgba(255, 255, 255, 0.3) !important;
}

.crew-table {
  background-color: #1e1e1e !important;
}

.crew-table th,
.crew-table td {
  background-color: #1e1e1e !important;
  border-color: rgba(255, 255, 255, 0.2) !important;
  color: white !important;
}

.crew-table >>> .v-data-table__wrapper {
  background-color: #1e1e1e !important;
}

.crew-table >>> table {
  background-color: #1e1e1e !important;
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

/* Workflow History Styles */
.workflow-history-list {
  max-height: 300px;
  overflow-y: auto;
}

.workflow-history-item {
  background-color: rgba(255, 255, 255, 0.1) !important;
  border-color: rgba(255, 255, 255, 0.2) !important;
  transition: background-color 0.2s ease;
}

.workflow-history-item:hover {
  background-color: rgba(255, 255, 255, 0.2) !important;
}

.workflow-title {
  font-weight: 500;
  font-size: 0.9em;
  color: white;
}

.workflow-date {
  font-size: 0.75em;
}

/* Main Area Workflow History Grid Styles */
.workflow-card {
  cursor: pointer;
  transition: all 0.2s ease;
  height: 100%;
}

.workflow-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.workflow-card .v-card__title {
  font-size: 0.95rem !important;
  line-height: 1.3;
  word-break: break-word;
}

.workflow-rationale-preview {
  line-height: 1.4;
  max-height: 60px;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

/* Run Workflow Result Styles */
.result-card {
  max-height: 500px;
  overflow-y: auto;
}

.result-text {
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

.error-result-text {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: monospace;
  font-size: 0.85em;
  margin: 0;
}

/* Executions Table Styles */
.executions-table th {
  font-weight: 600;
  background-color: #f5f5f5;
}

.executions-table td {
  vertical-align: middle;
}

/* Markdown Content Styles */
.markdown-content {
  padding: 16px;
  background-color: #fafafa;
  border-radius: 4px;
  max-height: 500px;
  overflow-y: auto;
}

.markdown-rendered {
  line-height: 1.7;
  color: #333;
}

.markdown-rendered h2,
.markdown-rendered h3,
.markdown-rendered h4 {
  font-weight: 600;
  margin-top: 16px;
  margin-bottom: 8px;
}

.markdown-rendered h2 {
  font-size: 1.25em;
  border-bottom: 1px solid #e0e0e0;
  padding-bottom: 4px;
}

.markdown-rendered h3 {
  font-size: 1.1em;
}

.markdown-rendered h4 {
  font-size: 1em;
}

.markdown-rendered ul,
.markdown-rendered ol {
  padding-left: 24px;
  margin-bottom: 12px;
}

.markdown-rendered li {
  margin-bottom: 4px;
}

.markdown-rendered strong {
  font-weight: 600;
  color: #1a1a1a;
}

.markdown-rendered em {
  font-style: italic;
  color: #555;
}

.markdown-rendered .inline-code {
  background-color: #e8e8e8;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 0.9em;
}

.markdown-rendered .blockquote {
  border-left: 3px solid #1976d2;
  padding-left: 12px;
  margin: 8px 0;
  color: #555;
  font-style: italic;
}

/* JSON Content Styles */
.json-content {
  background-color: #263238;
  color: #aabfc9;
  padding: 16px;
  border-radius: 4px;
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 0.85em;
  overflow-x: auto;
  max-height: 500px;
  overflow-y: auto;
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>

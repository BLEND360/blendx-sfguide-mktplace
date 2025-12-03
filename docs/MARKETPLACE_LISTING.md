# Snowflake Marketplace Listing Guide

This document covers how to create a marketplace listing and common issues when publishing a Snowflake Native App to the Marketplace.

---

## Listing Content

When creating a new listing in the Snowflake Marketplace, you need to fill in the following fields:

### Title

```
BlendX CrewAI Agent Workflows
```

### Subtitle

```
Run AI agent workflows powered by Snowflake Cortex LLMs directly in your Snowflake account
```

### Description

```
BlendX is a Snowflake Native Application that enables you to run CrewAI agent workflows directly within your Snowflake environment, powered by Snowflake Cortex LLMs.

Key Features:
- Run multi-agent AI workflows using CrewAI framework
- Powered by Snowflake Cortex LLMs - no external API keys required for LLM access
- External tool integration via Serper API for web search capabilities
- Secure execution within Snowpark Container Services (SPCS)
- Built-in secret management through Snowflake references
- Interactive web interface for generating and monitoring workflows

The application leverages Snowflake's native AI capabilities through Cortex, ensuring your data stays within your Snowflake account while enabling sophisticated AI agent interactions.

Use Cases:
- Automated research and data gathering
- Content generation and summarization
- Multi-step reasoning tasks
- Web-enhanced AI workflows with real-time search
```

### Business Needs

| Name | Description |
|------|-------------|
| AI-Powered Workflow Automation | Automate complex multi-step business processes using AI agents that can reason, research, and execute tasks autonomously within your Snowflake environment. |
| Intelligent Data Research | Enable AI agents to gather, analyze, and synthesize information from multiple sources including web search, helping teams make data-driven decisions faster. |
| Content Generation at Scale | Generate reports, summaries, and content using multi-agent AI workflows powered by Snowflake Cortex LLMs without exposing data to external services. |
| Secure AI Operations | Run AI agent workflows entirely within Snowflake's secure environment, ensuring data governance and compliance while leveraging advanced AI capabilities. |

### Categories

- AI/ML
- Native Apps
- Data Science
- Automation

### Quick Start / Getting Started

```
## Quick Start Guide

### Step 1: Install the Application
Click "Get" to install the application in your Snowflake account.

### Step 2: Grant Privileges
When prompted, grant the following privileges:
- IMPORTED PRIVILEGES ON SNOWFLAKE DB
- CREATE COMPUTE POOL
- BIND SERVICE ENDPOINT
- CREATE WAREHOUSE
- EXECUTE MANAGED TASK
- CREATE EXTERNAL ACCESS INTEGRATION

### Step 3: Configure Serper API (Optional - for web search)

If you want to use web search capabilities, create a secret with your Serper API key:

```sql
CREATE DATABASE IF NOT EXISTS secrets_db;
CREATE SCHEMA IF NOT EXISTS secrets_db.app_secrets;

CREATE SECRET IF NOT EXISTS secrets_db.app_secrets.serper_api_key
  TYPE = GENERIC_STRING
  SECRET_STRING = '<your_serper_api_key>';
```

Get your API key from https://serper.dev

### Step 4: Activate and Start

1. Click "Activate" in the application page
2. Configure references (Serper secret if using web search)
3. Start the application:

```sql
CALL <app_name>.app_public.start_app('<pool_name>', '<warehouse_name>');
```

### Step 5: Access the Application

Get the application URL:

```sql
CALL <app_name>.app_public.app_url();
```

Open the URL in your browser to access the web interface.
```

### Example Usage

```
## Example: Running a Test Workflow

1. Open the application URL in your browser
2. Click "TEST CORTEX" to verify LLM connectivity
3. Click "RUN TEST CREW" to execute a basic CrewAI workflow
4. View results in the interface

## Example: Web Search Workflow

After configuring Serper API:
1. Click "TEST SERPER" to verify API connectivity
2. Click "RUN TEST EXTERNAL TOOL" to run a workflow with web search
```

### Documentation URL

```
https://github.com/your-org/blendx-sfguide-mktplace
```

### Support Email

```
support@blend360.com
```

### Legal Terms / Terms of Service

```
TERMS OF SERVICE

By installing and using this application ("BlendX"), you agree to the following terms:

1. LICENSE GRANT
   The provider grants you a non-exclusive, non-transferable license to use this application within your Snowflake account.

2. DATA PROCESSING
   - All data processing occurs within your Snowflake account
   - The application uses Snowflake Cortex LLMs for AI processing
   - If configured, external API calls may be made to Serper (google.serper.dev) for web search functionality
   - No data is transmitted to the application provider

3. THIRD-PARTY SERVICES
   - Snowflake Cortex: Subject to Snowflake's terms of service
   - Serper API (optional): Subject to Serper's terms of service (https://serper.dev/terms)

4. COMPUTE COSTS
   Usage of this application will incur Snowflake compute costs for:
   - Snowpark Container Services (SPCS) compute pool
   - Snowflake Cortex LLM usage
   - Warehouse usage

5. DISCLAIMER
   THE APPLICATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND. THE PROVIDER DISCLAIMS ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.

6. LIMITATION OF LIABILITY
   IN NO EVENT SHALL THE PROVIDER BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE USE OF THIS APPLICATION.

7. SUPPORT
   Support is provided on a best-effort basis. Contact: support@your-company.com
```

### Privacy Policy

```
PRIVACY POLICY

1. DATA COLLECTION
   This application does not collect, store, or transmit any personal data to the application provider.

2. DATA PROCESSING
   All data processing occurs within your Snowflake account:
   - AI processing uses Snowflake Cortex LLMs
   - Workflow execution data is stored in your Snowflake account
   - Optional web search queries are sent to Serper API if configured

3. THIRD-PARTY SERVICES
   If you configure the Serper API integration:
   - Search queries are sent to google.serper.dev
   - Serper's privacy policy applies: https://serper.dev/privacy

4. DATA RETENTION
   - Workflow execution logs are stored in your Snowflake account
   - You control all data retention through your Snowflake account settings

5. CONTACT
   For privacy-related questions: privacy@your-company.com
```

---

## Prerequisites

Before creating a marketplace listing, ensure:

1. Your application package has `distribution = EXTERNAL`
2. You have a valid version registered
3. The release directive is properly configured

## Diagnostic Commands

### Check versions and patches

```sql
USE ROLE <your_package_role>;
SHOW VERSIONS IN APPLICATION PACKAGE <your_package_name>;
```

### Check release directives

```sql
USE ROLE <your_package_role>;
SHOW RELEASE DIRECTIVES IN APPLICATION PACKAGE <your_package_name>;
```

### Check release channels

```sql
USE ROLE <your_package_role>;
SHOW RELEASE CHANNELS IN APPLICATION PACKAGE <your_package_name>;
```

### Describe application package

```sql
USE ROLE <your_package_role>;
DESCRIBE APPLICATION PACKAGE <your_package_name>;
```

## Common Errors and Solutions

### Error: "The Release Directive of this application package contains invalid patch to share to external account"

This error occurs when the release directive is not properly configured for external sharing.

#### Cause

When release channels are enabled (default for new application packages), you must use channel-specific syntax to set the release directive.

#### Solution

**For packages WITH release channels enabled:**

```sql
USE ROLE <your_package_role>;
ALTER APPLICATION PACKAGE <your_package_name>
  MODIFY RELEASE CHANNEL DEFAULT
  SET DEFAULT RELEASE DIRECTIVE
    VERSION = <version_name>
    PATCH = <patch_number>;
```

Example:

```sql
USE ROLE naspcs_role;
ALTER APPLICATION PACKAGE spcs_app_pkg_test
  MODIFY RELEASE CHANNEL DEFAULT
  SET DEFAULT RELEASE DIRECTIVE
    VERSION = V1
    PATCH = 0;
```

**For packages WITHOUT release channels (legacy):**

```sql
USE ROLE <your_package_role>;
ALTER APPLICATION PACKAGE <your_package_name>
  SET DEFAULT RELEASE DIRECTIVE
    VERSION = <version_name>
    PATCH = <patch_number>;
```

#### How to check if release channels are enabled

```sql
DESCRIBE APPLICATION PACKAGE <your_package_name>;
```

Look for `release_channels` property. If it says `ENABLED`, use the channel-specific syntax.

### Error: "Release channels not specified for application package with release channels enabled"

This error occurs when you try to use the legacy `SET DEFAULT RELEASE DIRECTIVE` syntax on a package that has release channels enabled.

#### Solution

Use the `MODIFY RELEASE CHANNEL` syntax instead:

```sql
ALTER APPLICATION PACKAGE <your_package_name>
  MODIFY RELEASE CHANNEL DEFAULT
  SET DEFAULT RELEASE DIRECTIVE
    VERSION = <version>
    PATCH = <patch>;
```

## Release Channels Overview

When release channels are enabled, packages have three default channels:

| Channel | Description |
|---------|-------------|
| `DEFAULT` | Production channel for reviewed/approved versions |
| `ALPHA` | May contain versions where security review was not approved |
| `QA` | Internal testing only, versions never reviewed by Snowflake |

### Adding a version to a release channel

```sql
ALTER APPLICATION PACKAGE <package_name>
  MODIFY RELEASE CHANNEL <channel_name>
  ADD VERSION <version>;
```

### Removing a version from a release channel

```sql
ALTER APPLICATION PACKAGE <package_name>
  MODIFY RELEASE CHANNEL <channel_name>
  DROP VERSION <version>;
```

## Setting Up a Marketplace Listing

### 1. Verify package configuration

```sql
DESCRIBE APPLICATION PACKAGE <your_package_name>;
-- distribution should be EXTERNAL
```

### 2. Ensure version is in the DEFAULT channel

```sql
SHOW RELEASE CHANNELS IN APPLICATION PACKAGE <your_package_name>;
-- Check that DEFAULT channel has your version listed
```

### 3. Set the release directive

```sql
ALTER APPLICATION PACKAGE <your_package_name>
  MODIFY RELEASE CHANNEL DEFAULT
  SET DEFAULT RELEASE DIRECTIVE
    VERSION = <your_version>
    PATCH = 0;
```

### 4. Verify release directive

```sql
SHOW RELEASE DIRECTIVES IN APPLICATION PACKAGE <your_package_name>;
-- release_status should be DEPLOYED
```

## Scheduled Upgrades

You can schedule upgrades for consumers using `UPGRADE_AFTER`:

```sql
ALTER APPLICATION PACKAGE <your_package_name>
  MODIFY RELEASE CHANNEL DEFAULT
  SET DEFAULT RELEASE DIRECTIVE
    VERSION = <new_version>
    PATCH = 0
    UPGRADE_AFTER = '2025-01-15T10:00:00Z';
```

## References

- [ALTER APPLICATION PACKAGE RELEASE DIRECTIVE](https://docs.snowflake.com/en/sql-reference/sql/alter-application-package-release-directive)
- [Publish an app using release channels](https://docs.snowflake.com/en/developer-guide/native-apps/release-channels)
- [Set the release directive for an app](https://docs.snowflake.com/en/developer-guide/native-apps/update-app-release-directive)

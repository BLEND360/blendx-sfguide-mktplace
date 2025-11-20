# BlendX Snowflake Native App Deployment Guide

This README explains the exact, correct, and production-safe flow for deploying a Snowflake Native App using the BlendX architecture. It clearly separates provider-side responsibilities from consumer-side execution and includes the fixed and validated scripts.

⸻

🚀 Overview

A Snowflake Native App deployment has three phases:
	1.	Provider – builds and publishes the Application Package.
	2.	Consumer (Initial Install) – installs the app for the first time and pairs required references.
	3.	Consumer (Upgrades) – upgrades the app when a new version is released.

This document describes the required configuration, scripts, and workflow.

⸻

🧩 Architecture Components

Provider Account

Responsible for:
	•	Managing the Application Package
	•	Hosting the app code in a Snowflake stage
	•	Publishing versions via ALTER APPLICATION PACKAGE ... ADD VERSION
	•	Defining references in manifest.yml

Consumer Account

Responsible for:
	•	Creating secrets
	•	Creating External Access Integrations (EAI)
	•	Installing the application instance
	•	Pairing the instance with required references
	•	Upgrading when new versions are released

⸻

📦 1. Provider Workflow

1.1 Requirements

Provider must:
	•	Have a working manifest.yml defining:
	•	references: section (SECRET + EAI)
	•	callbacks: register_single_reference and get_config_for_ref
	•	Have all app code uploaded to a stage
	•	Execute with a role having:
	•	CREATE APPLICATION PACKAGE
	•	MODIFY permissions for new versions

⸻

1.2 Provider Script (provider.sql)

Executed in the provider account:
	•	Creates the application package (first time only)
	•	Registers new versions
	•	Adds versions to release channels
	•	Sets the default release directive

This script must NOT:
	•	Create references (these live in manifest.yml)
	•	Add external access integrations with SQL

⸻

🏗️ 2. Consumer Initial Installation

The consumer runs initial-install.sh once per account.

It performs:
	1.	Validates that:
	•	serper_api_key SECRET exists
	•	serper_external_access EAI exists
	2.	Creates the application instance:

CREATE APPLICATION <instance>
  FROM APPLICATION PACKAGE <package>
  USING VERSION <version>;


	3.	Pairs references:

ALTER APPLICATION <instance> SET REFERENCES = (
  SECRET serper_api_key
);


	4.	Pairs external access integrations:

ALTER APPLICATION <instance> SET EXTERNAL_ACCESS_INTEGRATIONS = (
  serper_external_access
);


	5.	Grants permissions:
	•	Warehouse
	•	Compute Pool

This script must NOT:
	•	Alter the application package
	•	Add internal references
	•	Add EAIs via SQL

⸻

🔁 3. Consumer Upgrade Flow

The consumer runs deploy.sh to:
	1.	Register the new package version (provider must have published it)
	2.	Add the version to the release channel (DEFAULT)
	3.	Set the default release directive
	4.	Upgrade the installed application instance

This allows smooth upgrades without reinstalling.

⸻

📄 Required Files Summary

1. manifest.yml (Provider)

Contains:
	•	References definitions
	•	Object types (SECRET, EXTERNAL ACCESS INTEGRATION)
	•	Callbacks

2. setup.sql (Provider – executed inside app)

Contains:
	•	Internal app schema/role setup
	•	Registration callbacks (register_single_reference)
	•	Configuration callbacks (get_config_for_ref)

3. provider.sql (Provider)

Responsible for:
	•	Creating the app package
	•	Adding versions
	•	Publishing to release channels

4. initial-install.sh (Consumer)

Responsible for:
	•	Initial creation of the app instance
	•	Pairing references + external access

5. deploy.sh (Consumer)

Responsible for:
	•	Upgrades
	•	Adding new versions to release channels
	•	Setting release directives

⸻

🧪 Testing the App

After installation, test the application by:
	•	Invoking the public procedures
	•	Triggering containers in compute pools
	•	Ensuring EAIs work (requests in Python should succeed)

⸻

✔ Final Notes
	•	All reference creation and EAI creation must be done in the consumer account, not the provider.
	•	All reference declaration must occur in manifest.yml, not setup.sql or deploy scripts.
	•	Package modification is provider-only.
	•	initial-install.sh should never try to modify the package.

This README provides the correct and complete workflow for Snowflake Native Apps following Snowflake’s latest API and packaging rules.